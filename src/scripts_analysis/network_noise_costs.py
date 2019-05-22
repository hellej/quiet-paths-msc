#%% IMPORT MODULES FOR NETWORK CONSTRUCTION
import pandas as pd
import osmnx as ox
import networkx as nx
from multiprocessing import current_process, Pool
import time
import utils.geometry as geom_utils
import utils.files as files
import utils.networks as nw
import utils.exposures as exps
import utils.utils as utils

#%% READ NOISE DATA
noise_polys = files.get_noise_polygons()

#%% SAVE NETWORK
# ox.save_graphml(graph, filename='kumpula_u_g_n.graphml', folder='graphs', gephi=False)

#%% READ NETWORK
# graph = nw.get_walk_network(koskela_kumpula_box)
graph = files.get_network_kumpula()
node_count = len(graph)
print('Nodes in the graph:', node_count)
# get all edges as list of dicts
edge_dicts = nw.get_all_edge_dicts(graph, attrs=['geometry', 'length'])
edge_count = len(edge_dicts)
print('Edges in the graph:', edge_count)
edge_dicts[:2]

#%% ADD MISSING GEOMETRIES TO EDGES ONE BY ONE
# print('Adding missing geometries to edges...')
# nw.add_missing_edge_geometries(edge_dicts, graph)

#%% ADD MISSING GEOMETRIES TO EDGES WITH POOL /// DONE ALREADY !!!
def get_edge_geoms(edge_dict):
    return nw.get_missing_edge_geometries(edge_dict, graph)
start_time = time.time()
pool = Pool(processes=4)
edge_geom_dicts = pool.map(get_edge_geoms, edge_dicts)
pool.close()
for edge_d in edge_geom_dicts:
        nx.set_edge_attributes(graph, { edge_d['uvkey']: {'geometry': edge_d['geometry'], 'length': edge_d['length']}})
time_elapsed = round(time.time() - start_time,1)
edge_time = round(time_elapsed/edge_count,2)
print("--- %s seconds ---" % (time_elapsed))
print("--- %s seconds per edge ---" % (edge_time))

#%% GET SUBSET OF EDGES FOR NOISE EXTRACTION TESTS
edge_set = edge_dicts[:15]

#%% EXPOSURES ONE BY ONE (TEST)
start_time = time.time()
edge_noise_dicts = []
for idx, edge_dict in enumerate(edge_set):
    edge_noise_dicts.append(nw.get_edge_noise_exps(edge_dict, noise_polys, graph))
    utils.print_progress(idx+1, len(edge_set), percentages=True)
time_elapsed = round(time.time() - start_time,1)
edge_time = round(time_elapsed/len(edge_set),1)
print('\n--- %s minutes ---' % (round(time_elapsed/60, 1)))
print('--- %s seconds per edge ---' % (edge_time))
edge_noise_dicts[:3]

#%% EXPOSURES WITH POOL (TEST)
def get_edge_noise_exps(edge_dict):
    return nw.get_edge_noise_exps(edge_dict, noise_polys, graph)
start_time = time.time()
pool = Pool(processes=4)
edge_noise_dicts = pool.map(get_edge_noise_exps, edge_set)
pool.close()
time_elapsed = round(time.time() - start_time,1)
edge_time = round(time_elapsed/len(edge_set),1)
print('\n--- %s minutes ---' % (round(time_elapsed/60, 1)))
print('--- %s seconds per edge ---' % (edge_time))
edge_noise_dicts[:3]

#%% update edge attributes with noise dicts
for edge_d in edge_noise_dicts:
    nx.set_edge_attributes(graph, { edge_d['uvkey']: {'noises': edge_d['noises'], 'th_noises': edge_d['th_noises']}})

#%% PROCESS EDGES WITH POOL IN CHUNKS
start_time = time.time()
pool = Pool(processes=4)
edge_set = edge_dicts[:65]
edge_chunks = utils.get_list_chunks(edge_set, 20)
edge_noise_dict_chunks = []
print('Extracting edge exposures...')
for idx, edge_chunk in enumerate(edge_chunks):
    edge_noise_dicts = pool.map(get_edge_noise_exps, edge_chunk)
    edge_noise_dict_chunks.append(edge_noise_dicts)
    utils.print_progress(idx+1, len(edge_chunks), percentages=True)
pool.close()
time_elapsed = round(time.time() - start_time, 1)
edge_time = round(time_elapsed/len(edge_set), 1)
print('\n--- %s minutes ---' % (round(time_elapsed/60, 1)))
print('--- %s seconds per edge ---' % (edge_time))

#%% update edge attributes with lists of noise dicts
for edge_noise_dicts in edge_noise_dict_chunks:
    for edge_d in edge_noise_dicts:
        nx.set_edge_attributes(graph, { edge_d['uvkey']: {'noises': edge_d['noises'], 'th_noises': edge_d['th_noises']}})

print('Edge noise attributes set.')
edge_dicts = nw.get_all_edge_dicts(graph)
edge_dicts[:3]


#%% FUNCTION FOR EXTRACTING NOISES TO EDGES QUICKLY
def get_edge_noises_df(edge_dicts):
    edge_gdf_sub = nw.get_edge_gdf(graph)
    # add noise split lines as list
    edge_gdf_sub['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in edge_gdf_sub['geometry']]
    # explode new rows from split lines column
    split_lines = geom_utils.explode_lines_to_split_lines(edge_gdf_sub, 'uvkey')
    # join noises to split lines
    split_line_noises = exps.get_noise_attrs_to_split_lines(split_lines, noise_polys)
    # aggregate noises back to edges
    edge_noises = exps.aggregate_line_noises(split_line_noises, 'uvkey')
    return edge_noises

#%% WITHOUT POOL
start_time = time.time()
edge_noises = get_edge_noises_df(edge_dicts[:200])

time_elapsed = round(time.time() - start_time, 1)
edge_time = round(time_elapsed/200, 3)
print('\n--- %s seconds ---' % (round(time_elapsed, 1)))
print('--- %s seconds per edge ---' % (edge_time))
edge_noises.head()

#%% WITH POOL
edge_set = edge_dicts[:400]
edge_chunks = utils.get_list_chunks(edge_set, 100)
start_time = time.time()

pool = Pool(processes=4)
edge_noise_dfs = pool.map(get_edge_noises_df, edge_chunks)

time_elapsed = round(time.time() - start_time, 1)
edge_time = round(time_elapsed/len(edge_set), 3)
print('\n--- %s seconds ---' % (round(time_elapsed, 1)))
print('--- %s seconds per edge ---' % (edge_time))

#%% UPDATE NOISES TO GRAPH
for edge_noises in edge_noise_dfs:
    nw.update_edge_noises(edge_noises, graph)

#%% EDGE GDFS FROM GRAPH
edge_dicts = nw.get_all_edge_dicts(graph)
edges = nw.get_edge_gdf(graph)
edges.head()

#%% 
edges.to_file('data/networks.gpkg', layer='koskela_edges_noise', driver="GPKG")

# nodes = ox.graph_to_gdfs(graph, nodes=True, edges=False, node_geometry=True)
# edges = edges[['geometry', 'u', 'v', 'length', 'noises', 'th_noises']]
# nodes.to_file('data/networks.gpkg', layer='koskela_nodes_noise', driver="GPKG")

#%%
