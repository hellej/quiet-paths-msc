#%% IMPORT MODULES FOR NETWORK CONSTRUCTION
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
from multiprocessing import current_process, Pool
import time
import utils.geometry as geom_utils
import utils.networks as nw
import utils.noise_overlays as noise_utils
import utils.utils as utils

#%% GET BOUNDING BOX POLYGONS
koskela_box = geom_utils.project_to_wgs(nw.get_koskela_box())
koskela_kumpula_box = geom_utils.project_to_wgs(nw.get_koskela_kumpula_box())
noise_polys = noise_utils.get_noise_polygons()

#%% GET NETWORK
# graph_proj = nw.get_walk_network(koskela_kumpula_box)
# ox.save_graphml(graph_proj, filename='koskela_kumpula_test.graphml', folder='graphs', gephi=False)
# graph_proj = ox.load_graphml('koskela_test.graphml', folder='graphs')
graph_proj = ox.load_graphml('koskela_kumpula_test.graphml', folder='graphs')
node_count = len(graph_proj)
print('Nodes in the graph:', node_count)

#%% SAVE NETWORK
# ox.save_graphml(graph_proj, filename='koskela_kumpula_geom.graphml', folder='graphs', gephi=False)

#%% GATHER ALL EDGE DICTS
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_count = len(edge_dicts)
print('Edges in the graph:', edge_count)
edge_dicts[:3]

#%% ADD MISSING GEOMETRIES TO EDGES
print('Adding missing geometries to edges...')
nw.add_missing_edge_geometries(edge_dicts, graph_proj)
# check that geometries got added
edge_dicts = nw.get_all_edge_dicts(graph_proj)

edge_set = edge_dicts[:7]

#%% EXPOSURES ONE BY ONE (TEST)
start_time = time.time()
edge_noise_dicts = []
for idx, edge_dict in enumerate(edge_set):
    edge_noise_dicts.append(nw.get_edge_noise_exps(edge_dict, noise_polys, graph_proj))
    utils.print_progress(idx+1, 7, True)
time_elapsed = round(time.time() - start_time,1)
edge_time = round(time_elapsed/len(edge_set),1)
print("--- %s seconds ---" % (time_elapsed))
print("--- %s seconds per edge ---" % (edge_time))
edge_noise_dicts[:3]

#%% EXPOSURES WITH POOL (TEST)
def get_edge_noise_exps(edge_dict):
    return nw.get_edge_noise_exps(edge_dict, noise_polys, graph_proj)
start_time = time.time()
pool = Pool(processes=4)
edge_noise_dicts = pool.map(get_edge_noise_exps, edge_set)
pool.close()
time_elapsed = round(time.time() - start_time,1)
edge_time = round(time_elapsed/len(edge_set),1)
print("--- %s seconds ---" % (time_elapsed))
print("--- %s seconds per edge ---" % (edge_time))
edge_noise_dicts[:3]

#%% PROCESS EDGES IN CHUNKS WITH POOL
start_time = time.time()
pool = Pool(processes=4)
edge_set = edge_dicts[:65]
edge_chunks = utils.get_list_chunks(edge_set, 20)
edge_noise_dict_chunks = []
print('Extracting edge exposures...')
for idx, edge_chunk in enumerate(edge_chunks):
    edge_noise_dicts = pool.map(get_edge_noise_exps, edge_chunk)
    edge_noise_dict_chunks.append(edge_noise_dicts)
    utils.print_progress(idx+1, len(edge_chunks), True)
pool.close()
time_elapsed = round(time.time() - start_time, 1)
edge_time = round(time_elapsed/len(edge_set), 1)
print('\n--- %s minute ---' % (round(time_elapsed/60)))
print('--- %s seconds per node ---' % (edge_time))

#%% SET EDGE ATTRIBUTES USING ATTRIBUTE LISTS
for edge_dicts in edge_noise_dict_chunks:
    for edge_d in edge_dicts:
        nx.set_edge_attributes(graph_proj, { edge_d['uvkey']: {'noises': edge_d['noises'], 'th_noises': edge_d['th_noises']}})

print('Edge noise attributes set.')
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_dicts[:3]

#%% GET NODES & EDGES (AS GDFS) FROM GRAPH
# nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)
# edges = edges[['geometry', 'u', 'v', 'length', 'noises', 'th_noises']]
# edges.to_file('data/networks.gpkg', layer='koskela_edges_noise', driver="GPKG")
# nodes.to_file('data/networks.gpkg', layer='koskela_nodes_noise', driver="GPKG")
