#%%
import pandas as pd
import geopandas as gpd
import ast
import time
from fiona.crs import from_epsg
from multiprocessing import current_process, Pool
import utils.commutes as commutes_utils
import utils.geometry as geom_utils
import utils.files as files
import utils.networks as nw
import utils.utils as utils
import utils.routing as rt

#%% initialize graph
start_time = time.time()
nts = [0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6, 10, 20, 40]
graph = files.get_network_full_noise()
print('Graph of', graph.size(), 'edges read.')
edge_gdf = nw.get_edge_gdf(graph)
node_gdf = nw.get_node_gdf(graph)
print('Network features extracted.')
nw.set_graph_noise_costs(edge_gdf, graph, nts)
edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
print('Noise costs set.')
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Spatial index built.')
utils.print_duration(start_time, 'Network initialized.')

#%% read commutes stops
home_stops_path = 'outputs/YKR_commutes_output/home_stops'
origins_stops_files = commutes_utils.get_axyind_filenames(path=home_stops_path)
origins_paths_files = commutes_utils.get_axyind_filenames(path='outputs/YKR_commutes_output/home_paths')
origins_stops_files

#%% prepare for path calculation loop
# calculate origin-stop paths
def get_origin_stop_paths(row):
    from_latLon = row['DT_origin_latLon']
    to_latLon = row['stop_latLon']
    paths = rt.get_short_quiet_paths(graph, from_latLon, to_latLon, edge_gdf, node_gdf, nts, remove_geom_prop=False, logging=False)
    return paths

# find non processed axyinds for path calculations
axyinds_not_processed = [file for file in origins_stops_files if file not in origins_paths_files]
axyinds_not_processed

#%% function for calculating short & quiet paths
def get_origin_stops_paths_df(home_stops_file):
    home_stops = pd.read_csv(home_stops_path+'/'+home_stops_file)
    home_stops['DT_origin_latLon'] = [ast.literal_eval(d) for d in home_stops['DT_origin_latLon']]
    home_stops['stop_latLon'] = [ast.literal_eval(d) for d in home_stops['stop_latLon']]
    home_paths = []
    for idx, row in home_stops.iterrows():
        paths = get_origin_stop_paths(row)
        paths_dicts = [path['properties'] for path in paths]
        paths_df = gpd.GeoDataFrame(paths_dicts)
        paths_df['path_id'] = row['uniq_id']
        paths_df['from_axyind'] = row['from_axyind']
        paths_df['to_pt_mode'] = row['to_pt_mode']
        paths_df['count'] = row['count']
        paths_df['prob'] = row['prob']
        paths_df['DT_len_diff'] = [round(row['DT_walk_dist'] - length,1) for length in paths_df['length']]
        home_paths.append(paths_df)
    # collect 
    home_paths_df = pd.concat(home_paths, ignore_index=True)
    # save as axyind.csv table before proceeding to next axyind
    home_walks_g_to_file = home_paths_df.drop(columns=['geometry'])
    home_walks_g_to_file.to_csv('outputs/YKR_commutes_output/home_paths/axyind_'+str(row['from_axyind'])+'.csv')
    return home_paths_df

#%% process origins with pool
pool = Pool(processes=4)
home_paths_dfs = pool.map(get_origin_stops_paths_df, origins_stops_files)
all_home_paths_df = gpd.GeoDataFrame(pd.concat(home_paths_dfs, ignore_index=True), crs=from_epsg(3879))

#%% check path GDFs
all_home_paths_df.plot()
all_home_paths_df.head(100)

#%%
all_home_paths_df.to_file('outputs/YKR_commutes_output/test.gpkg', layer='paths_test', driver='GPKG')

#%%