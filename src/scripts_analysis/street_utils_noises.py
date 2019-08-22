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
import utils.exposures as exps
import utils.quiet_paths as qp
import utils.plots as plots 
import utils.path_stats as pstats

edges_out_file = 'street_utils_run_1'
problem_axyinds = [3933756673875] # routing will be skipped from these

#%% initialize graph & extract edge_gdf
start_time = time.time()
nts = qp.get_noise_tolerances()
db_costs = qp.get_db_costs()
graph = files.get_network_full_noise(version=3)
# graph = files.get_network_kumpula_noise(version=3)
print('Graph of', graph.size(), 'edges read.')
edge_gdf = nw.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'])
node_gdf = nw.get_node_gdf(graph)
print('Network features extracted.')
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Spatial index built.')
utils.print_duration(start_time, 'Network initialized.')

#%% Create dict of unique edges { (u,v): 0, (u,v): 0, ... }
# function for creating identifier for edge's node pair
def form_edge_uvu_id(uvkey):
    uv = uvkey[:2]
    return tuple(sorted(uv))
# add edge_id for unique node pairs (group directions and parallel edges)
edges_subset = edge_gdf.copy()
edges_subset['edge_id'] = [form_edge_uvu_id(uvkey) for uvkey in edges_subset['uvkey']]
print('all edges count', len(edges_subset))
# sort edge gdf by edge length
edges_subset = edges_subset.sort_values(by=['length'], ascending=True)
edges_subset.head(3)
# drop duplicate edges
edges_subset = edges_subset.drop_duplicates(subset=['edge_id'], keep='first')
print('unique uv pair edge count', len(edges_subset))
# create edge dict
edges_d = {}
for edge in edges_subset.itertuples():
    edges_d[getattr(edge, 'edge_id')] = 0
print('edges in dict:', len(edges_d.keys()))

#%% define functions for calculating shortest paths
def get_origin_stop_paths(from_latLon=None, to_latLon=None):
    return rt.get_short_quiet_paths(graph, from_latLon, to_latLon, edge_gdf, node_gdf, nts=nts, db_costs=db_costs, remove_geom_prop=False, only_short=True, logging=False)

# function for calculating short path
def get_origin_stops_paths(home_stops_file):
    from_axyind = commutes_utils.get_xyind_from_filename(home_stops_file)
    if (from_axyind in problem_axyinds):
        print('skipping problematic axyind')
        return from_axyind
    try:
        home_stops = pd.read_csv(home_stops_path+'/'+home_stops_file)
        home_stops['DT_origin_latLon'] = [ast.literal_eval(d) for d in home_stops['DT_origin_latLon']]
        home_stops['dest_latLon'] = [ast.literal_eval(d) for d in home_stops['dest_latLon']]
        paths = []
        for idx, row in home_stops.iterrows():
            if (row['to_pt_mode'] == 'WALK'):
                continue
            path = get_origin_stop_paths(from_latLon=row['DT_origin_latLon'], to_latLon=row['dest_latLon'])
            if (path is None):
                print('routing error with:', row['from_axyind'], 'prob:', row['prob'])
                continue
            paths.append(tuple([path, row['utilization']]))
        return paths
    except Exception as e:
        print('Error with:', from_axyind)
        print(str(e))
        return from_axyind

#%% Read ODs of the first walks of the commutes
home_stops_path = 'outputs/YKR_commutes_output/home_stops'
axyinds = commutes_utils.get_xyind_filenames(path=home_stops_path)
to_process = axyinds #[:10]
print('Start processing', len(to_process), 'axyinds')

#%% routing analysis
# get list of lists per paths & utils from each axyind
pool = Pool(processes=4)
all_path_lists = pool.map(get_origin_stops_paths, to_process) # faster than below
# all_path_lists = [get_origin_stops_paths(axyind) for axyind in to_process]

#%% collect & filter out errors
errors = [path for path in all_path_lists if type(path) is int]
print('errors count:', len(errors))
all_path_lists = [path for path in all_path_lists if type(path) is not int]
print('path list count:', len(all_path_lists))
# explode all path lists to list of path-tuples (path, util)
all_paths = [path for paths in all_path_lists for path in paths]
print('all paths count:', len(all_paths))

#%% define functions for aggregating path utlis to utilization of individual edges
def explode_path_util_to_edge_utils(path_util):
    # returns list of tuples: [(edge_id, util), ...]
    util = path_util[1]
    path = path_util[0]
    edge_utils = []
    for idx in range(0, len(path)-1):
        edge = tuple(sorted([path[idx], path[idx+1]]))
        edge_utils.append(tuple([edge, util]))
    return edge_utils

def add_edge_utils_to_dict(edge_utils):
    for edge_util in edge_utils:
        edge_id = edge_util[0]
        util = edge_util[1]
        try:
            edges_d[edge_id] += util
        except:
            continue

#%% aggregate edge utilizations
for path_util in all_paths:
    edge_utils = explode_path_util_to_edge_utils(path_util)
    add_edge_utils_to_dict(edge_utils)

#%% collect edge utilizations to dataframe
edge_utils_df = pd.DataFrame(list(edges_d.items()), index=edges_d.keys(), columns=['edge_id', 'util'])
edge_utils_df = edge_utils_df.sort_values('util', ascending=False)
edge_utils_df.head()

#%% merge edge utils to edge gdf
print('edge utils rows:', len(edge_utils_df))
print('edge gdf rows:', len(edges_subset))
edge_utils_gdf = pd.merge(edges_subset, edge_utils_df, how='left', on='edge_id')
print('merged rows:', len(edge_utils_gdf))
# edge_utils_gdf.head()

#%% add noise indexes to edge utils gdf
edge_utils_gdf['mdB'] = edge_utils_gdf.apply(lambda row: exps.get_mean_noise_level(row['noises'], row['length']), axis=1)
edge_utils_gdf['nei'] = [round(exps.get_noise_cost(noises=noises, db_costs=db_costs), 1) for noises in edge_utils_gdf['noises']]
edge_utils_gdf['nei_norm'] = edge_utils_gdf.apply(lambda row: round(row['nei'] / (0.6 * row['length']), 4), axis=1)

#%% export edges with noise & util attributes to file
all_path_lists_file = edge_utils_gdf.drop(columns=['uvkey', 'noises', 'edge_id'])
all_path_lists_file = all_path_lists_file.query('util > 0')
all_path_lists_file.to_file('outputs/YKR_commutes_output/edge_stats.gpkg', layer=edges_out_file, driver='GPKG')


#### READ & ANALYSE STREET STATS ####
#####################################

#%% read edge stats
edges =  gpd.read_file('outputs/YKR_commutes_output/edge_stats.gpkg', layer=edges_out_file)
edges.head()

#%% plot util vs mdB
edges_filt = edges.query('util < 2000')
fig = plots.scatterplot(edges_filt, xcol='util', ycol='mdB', xlabel='Street utilization', ylabel='Mean dB')
fig.savefig('plots/street_util_mdB.png', format='png', dpi=300)

#%% calculate basic statistic of mdB and utilizations
util_stats  = pstats.calc_basic_stats(edges, 'util', weight=None, percs=[5, 10, 15, 25, 75, 80, 85, 90, 95], col_prefix='util', add_varname=True, add_n=True)
db_stats = pstats.calc_basic_stats(edges, 'mdB', weight=None, percs=[5, 10, 15, 25, 75, 80, 85, 90, 95], col_prefix='mdB', add_varname=True, add_n=True)
street_stats = [util_stats, db_stats]
street_stats = pd.DataFrame(street_stats, columns=street_stats[0].keys())
street_stats

#%% extract highest overlapping percentiles of db and util
percs = ['p75', 'p80', 'p85', 'p90', 'p95']
for perc in percs:
    perc_edges = edges.query(f'''util > {util_stats[perc]} and mdB > {db_stats[perc]}''')
    perc_edges_ratio = round(100*len(perc_edges)/len(edges),2)
    print(perc, len(perc_edges), 'of', len(edges), '-',perc_edges_ratio, '% -', db_stats[perc], 'dB,', round(util_stats[perc]), 'util')

#%% extract percentile info to edges
edges['perc'] = 'p0'
def get_street_pc_value(row, perc):
    if (row['util'] > util_stats[perc] and row['mdB'] > db_stats[perc]):
        return perc
    else:
        return row['perc']

for perc in percs:
    edges['perc'] = edges.apply(lambda row: get_street_pc_value(row, perc), axis=1)

#%% export edges with percentile info to file
edges.to_file('outputs/YKR_commutes_output/edge_stats.gpkg', layer=edges_out_file+'percs', driver='GPKG')

#%%
