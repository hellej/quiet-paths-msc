#%% IMPORT MODULES FOR NETWORK CONSTRUCTION
import pandas as pd
import geopandas as gpd
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
# ox.save_graphml(graph_proj, filename='kumpula_u_g.graphml', folder='graphs', gephi=False)

#%% READ NETWORK
# graph_proj = nw.get_walk_network(koskela_kumpula_box)
graph_proj = files.get_undirected_network_graph()
node_count = len(graph_proj)
print('Nodes in the graph:', node_count)
# get all edges as list of dicts
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_count = len(edge_dicts)
print('Edges in the graph:', edge_count)
edge_dicts[:2]

#%% ADD MISSING GEOMETRIES TO EDGES ONE BY ONE
# print('Adding missing geometries to edges...')
# nw.add_missing_edge_geometries(edge_dicts, graph_proj)

#%% ADD MISSING GEOMETRIES TO EDGES WITH POOL
def get_edge_geoms(edge_dict):
    return nw.get_missing_edge_geometries(edge_dict, graph_proj)
start_time = time.time()
pool = Pool(processes=4)
edge_geom_dicts = pool.map(get_edge_geoms, edge_dicts)
pool.close()
for edge_d in edge_geom_dicts:
        nx.set_edge_attributes(graph_proj, { edge_d['uvkey']: {'geometry': edge_d['geometry'], 'length': edge_d['length']}})
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
    edge_noise_dicts.append(nw.get_edge_noise_exps(edge_dict, noise_polys, graph_proj))
    utils.print_progress(idx+1, len(edge_set), True)
time_elapsed = round(time.time() - start_time,1)
edge_time = round(time_elapsed/len(edge_set),1)
print('\n--- %s minutes ---' % (round(time_elapsed/60, 1)))
print('--- %s seconds per edge ---' % (edge_time))
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
print('\n--- %s minutes ---' % (round(time_elapsed/60, 1)))
print('--- %s seconds per edge ---' % (edge_time))
edge_noise_dicts[:3]

#%% update edge attributes with noise dicts
for edge_d in edge_noise_dicts:
    nx.set_edge_attributes(graph_proj, { edge_d['uvkey']: {'noises': edge_d['noises'], 'th_noises': edge_d['th_noises']}})

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
    utils.print_progress(idx+1, len(edge_chunks), True)
pool.close()
time_elapsed = round(time.time() - start_time, 1)
edge_time = round(time_elapsed/len(edge_set), 1)
print('\n--- %s minutes ---' % (round(time_elapsed/60, 1)))
print('--- %s seconds per edge ---' % (edge_time))

#%% update edge attributes with lists of noise dicts
for edge_noise_dicts in edge_noise_dict_chunks:
    for edge_d in edge_noise_dicts:
        nx.set_edge_attributes(graph_proj, { edge_d['uvkey']: {'noises': edge_d['noises'], 'th_noises': edge_d['th_noises']}})

print('Edge noise attributes set.')
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_dicts[:3]

#%% EXTRACT NOISES TO SEGMENTS QUICKLY
def get_segment_noises_df(edge_dicts):
    edge_gdf_sub = nw.get_edge_gdf(edge_dicts, ['geometry', 'length', 'uvkey'])
    # add noise split lines as list
    edge_gdf_sub['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in edge_gdf_sub['geometry']]
    # explode new rows from split lines column
    split_lines = nw.explode_edges_to_noise_parts(edge_gdf_sub)
    # join noises to split lines
    split_line_noises = exps.get_noise_attrs_to_split_lines(split_lines, noise_polys)
    # aggregate noises back to segments
    segment_noises = nw.aggregate_segment_noises(split_line_noises)
    return segment_noises

#%% WITHOUT POOL
start_time = time.time()
segment_noises = get_segment_noises_df(edge_dicts[:200])

time_elapsed = round(time.time() - start_time, 1)
edge_time = round(time_elapsed/200, 3)
print('\n--- %s seconds ---' % (round(time_elapsed, 1)))
print('--- %s seconds per edge ---' % (edge_time))
segment_noises.head()

#%% WITH POOL
edge_set = edge_dicts[:400]
edge_chunks = utils.get_list_chunks(edge_set, 150)
start_time = time.time()

pool = Pool(processes=4)
segment_noise_dfs = pool.map(get_segment_noises_df, edge_chunks)

time_elapsed = round(time.time() - start_time, 1)
edge_time = round(time_elapsed/400, 3)
print('\n--- %s seconds ---' % (round(time_elapsed, 1)))
print('--- %s seconds per edge ---' % (edge_time))

#%% UPDATE NOISES TO GRAPH
for segment_noises in segment_noise_dfs:
    nw.update_segment_noises(segment_noises, graph_proj)

#%% EDGE GDFS FROM GRAPH
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edges = nw.get_edge_gdf(edge_dicts, ['geometry', 'length', 'noises', 'th_noises'])
edges.head()

#%% 
edges.to_file('data/networks.gpkg', layer='koskela_edges_noise', driver="GPKG")

# nodes = ox.graph_to_gdfs(graph_proj, nodes=True, edges=False, node_geometry=True)
# edges = edges[['geometry', 'u', 'v', 'length', 'noises', 'th_noises']]
# nodes.to_file('data/networks.gpkg', layer='koskela_nodes_noise', driver="GPKG")

#%%
