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
import utils.times as times
import utils.networks as nw
import utils.utils as utils
import utils.routing as rt

#%% initialize graph
start_time = time.time()
nts = [0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6, 10, 20, 40]
graph = files.get_network_full_noise_v2(directed=False)
print('Graph of', graph.size(), 'edges read.')
edge_gdf = nw.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'])
node_gdf = nw.get_node_gdf(graph)
print('Network features extracted.')
nw.set_graph_noise_costs(edge_gdf, graph, nts)
edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
print('Noise costs set.')
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Spatial index built.')
utils.print_duration(start_time, 'Network initialized.')

#%% find unprocessed axyinds for path calculation loop
# read commutes stops
home_stops_path = 'outputs/YKR_commutes_output/home_stops'
axyinds = commutes_utils.get_xyind_filenames(path=home_stops_path)
to_process = axyinds #[:5]
# to_process = axyinds_to_process
# to_process = ['axyind_3933756681125.csv'] # this threw error before
# to_process = ['axyind_3898756678375.csv'] # this threw error before
print('Start processing', len(to_process), 'axyinds')

#%% functions for calculating origin-stop paths
def get_origin_stop_paths(from_latLon=None, to_latLon=None):
    return rt.get_short_quiet_paths(graph, from_latLon, to_latLon, edge_gdf, node_gdf, nts, remove_geom_prop=False, logging=False)

# function for calculating short & quiet paths
def get_origin_stops_paths_df(home_stops_file):
    from_axyind = commutes_utils.get_xyind_from_filename(home_stops_file)
    try:
        home_stops = pd.read_csv(home_stops_path+'/'+home_stops_file)
        home_stops['DT_origin_latLon'] = [ast.literal_eval(d) for d in home_stops['DT_origin_latLon']]
        home_stops['dest_latLon'] = [ast.literal_eval(d) for d in home_stops['dest_latLon']]
        home_paths = []
        for idx, row in home_stops.iterrows():
            paths = get_origin_stop_paths(from_latLon=row['DT_origin_latLon'], to_latLon=row['dest_latLon'])
            if (paths is None):
                print('routing error with:', row['from_axyind'], 'prob:', row['prob'])
                continue
            paths_dicts = [path['properties'] for path in paths['paths']]
            paths_df = gpd.GeoDataFrame(paths_dicts)
            paths_df['path_id'] = row['uniq_id']
            paths_df['orig_offset'] = paths['orig_offset']
            paths_df['dest_offset'] = paths['dest_offset']
            paths_df['from_axyind'] = row['from_axyind']
            paths_df['to_pt_mode'] = row['to_pt_mode']
            paths_df['count'] = row['count']
            paths_df['util'] = row['utilization']
            paths_df['prob'] = row['prob']
            paths_df['DT_len'] = round(row['DT_walk_dist'], 1)
            paths_df['DT_len_diff'] = [round(length - row['DT_walk_dist'],1) for length in paths_df['length']]
            home_paths.append(paths_df)
        # collect
        return pd.concat(home_paths, ignore_index=True)
    except Exception as e:
        print('Error with:', from_axyind)
        print(str(e))
        return from_axyind

#%% process origins with pool
# select subset of axyinds to process
start_time = time.time()
pool = Pool(processes=4)
home_paths = pool.map(get_origin_stops_paths_df, to_process)
# home_paths = [get_origin_stops_paths_df(axyind) for axyind in to_process]
errors = [path for path in home_paths if type(path) is int]
home_paths_dfs = [path for path in home_paths if type(path) is not int]
print('ERRORS:', errors)
print('errors count:', len(errors))
print('path df count:', len(home_paths_dfs))
all_home_paths_df = gpd.GeoDataFrame(pd.concat(home_paths_dfs, ignore_index=True), crs=from_epsg(3879))
utils.print_duration(start_time, 'Got paths.')
axyind_time = round((time.time() - start_time)/len(to_process),2)
print('axyind_time (s):', axyind_time)
#%% check paths GDF
all_home_paths_df.head(3)

#%% export paths GDF
# all_home_paths_df.to_file('outputs/YKR_commutes_output/home_paths.gpkg', layer='run_3_set_2', driver='GPKG')

#%% combine path sets to GDF of all paths
# paths_1 = gpd.read_file('outputs/YKR_commutes_output/home_paths.gpkg', layer='run_3_set_1')
# paths_2 = gpd.read_file('outputs/YKR_commutes_output/home_paths.gpkg', layer='run_3_set_2')
# concat_paths = gpd.GeoDataFrame(pd.concat([paths_1, paths_2], ignore_index=True), crs=from_epsg(3879))
# concat_paths.to_file('outputs/YKR_commutes_output/home_paths.gpkg', layer='run_3_all', driver='GPKG')

# %% ad unique id for paths
# all_paths_gdf = paths
# all_paths_gdf['uniq_id'] = all_paths_gdf.apply(lambda row: row['path_id'] +'_'+ row['id'], axis=1)
# # find weirdly duplicate paths
# duplicate_paths = all_paths_gdf[all_paths_gdf.duplicated(subset=['uniq_id'])]
# duplicate_paths_axyinds = list(duplicate_paths['from_axyind'])
# print('duplicate paths:', duplicate_paths_axyinds)

#%% print path counts
# print(len(all_paths_gdf))
# paths_count = all_paths_gdf['uniq_id'].unique()
# print('paths:', len(paths_count))
# print('should be same as:', len(all_paths_gdf.index))
# processed_axyinds = all_paths_gdf['from_axyind'].unique()
# print('axyinds processed:', len(processed_axyinds))

#%% find axyinds to process based on axyinds in all_paths_gdf
# axyinds = commutes_utils.get_xyind_filenames(path='outputs/YKR_commutes_output/home_stops')
# processed_axyind_files = ['axyind_'+str(axyind)+'.csv' for axyind in processed_axyinds]
# axyinds_to_process = [axyind for axyind in axyinds if axyind not in processed_axyind_files]
# print('still to process:', axyinds_to_process)
# still to process: ['axyind_3933756673875.csv', 'axyind_3916256675875.csv', 'axyind_3818756674375.csv']

#%%
