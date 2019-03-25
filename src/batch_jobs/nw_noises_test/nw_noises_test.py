# IMPORT MODULES FOR NETWORK CONSTRUCTION
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import multiprocessing
import time
import utils.geometry as geom_utils
import utils.networks as nw
import utils.noise_overlays as noise_utils
import utils.utils as utils

# READ DATA
noise_polys = noise_utils.get_noise_polygons()
graph_proj = ox.load_graphml('koskela_kumpula_geom.graphml', folder='graphs')

node_count = len(graph_proj)
print('Nodes in the graph:', node_count)
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_count = len(edge_dicts)
print('Edges in the graph:', edge_count)
edge_dicts[:2]


# GET SUBSET OF EDGES FOR NOISE EXTRACTION TESTS
edge_set = edge_dicts[:60]

# EXPOSURES WITH POOL (TEST)
def get_edge_noise_exps(edge_dict):
    return nw.get_edge_noise_exps(edge_dict, noise_polys, graph_proj)
start_time = time.time()
pool = multiprocessing.Pool(processes=24)
edge_noise_dicts = pool.map(get_edge_noise_exps, edge_set)
pool.close()
time_elapsed = round(time.time() - start_time,1)
edge_time = round(time_elapsed/len(edge_set),1)
print('\n--- %s minutes ---' % (round(time_elapsed/60, 1)))
print('--- %s seconds per node ---' % (edge_time))
edge_noise_dicts[:3]
for edge_d in edge_noise_dicts:
    nx.set_edge_attributes(graph_proj, { edge_d['uvkey']: {'noises': edge_d['noises'], 'th_noises': edge_d['th_noises']}})

print('Edge noise attributes set.\n')
edge_dicts = nw.get_all_edge_dicts(graph_proj)
print(edge_dicts)
