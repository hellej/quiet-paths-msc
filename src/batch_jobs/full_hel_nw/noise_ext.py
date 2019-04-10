# IMPORT MODULES FOR NETWORK CONSTRUCTION
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

# READ NOISES
noise_polys = files.get_noise_polygons()

# READ NETWORK
graph = files.get_full_network()
print('Nodes in the graph:', len(graph))
# get all edges as list of dicts
edge_dicts = nw.get_all_edge_dicts(graph)
edge_count = len(edge_dicts)
print('Edges in the graph:', edge_count)

# FUNCTION FOR EXTRACTING NOISES TO EDGES QUICKLY
def get_edge_noises_df(edge_dicts):
    edge_gdf_sub = nw.get_edge_gdf(edge_dicts, ['geometry', 'length', 'uvkey'])
    # add noise split lines as list
    edge_gdf_sub['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in edge_gdf_sub['geometry']]
    # explode new rows from split lines column
    split_lines = geom_utils.explode_lines_to_split_lines(edge_gdf_sub, 'uvkey')
    # join noises to split lines
    split_line_noises = exps.get_noise_attrs_to_split_lines(split_lines, noise_polys)
    # aggregate noises back to edges
    edge_noises = exps.aggregate_line_noises(split_line_noises, 'uvkey')
    return edge_noises

# WITH POOL
edge_set = edge_dicts #[:9000]
edge_chunks = utils.get_list_chunks(edge_set, 2000)

pool = Pool(processes=24)
start_time = time.time()
edge_noise_dfs = pool.map(get_edge_noises_df, edge_chunks)
print('Noises extracted.')

# UPDATE NOISES TO GRAPH
for edge_noises in edge_noise_dfs:
    nw.update_edge_noises(edge_noises, graph)
print('Noises updated.')

# EXPORT GRAPH
ox.save_graphml(graph, filename='hel_u_g_n.graphml', folder='graphs', gephi=False)
print('Graph with noises exported.')

# SAVE GRAPH WITH ATTRIBUTE SUBSET
nw.delete_unused_edge_attrs(graph)
ox.save_graphml(graph, filename='hel_u_g_n_s.graphml', folder='graphs', gephi=False)
print('Graph with attribute subset exported.')

# PRINT TIMES
time_elapsed = time.time() - start_time
edge_time = round(time_elapsed/len(edge_set), 4)
print('\n--- %s minutes ---' % (round(time_elapsed/60, 2)))
print('--- %s seconds per edge ---' % (edge_time))
