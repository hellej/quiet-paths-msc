import pandas as pd
import geopandas as gpd
import osmnx as ox
import utils.geometry as geom_utils
import utils.files as files
import utils.networks as nw
from multiprocessing import current_process, Pool
import networkx as nx
import time

# READ EXTENT
hel_poly = files.get_hel_poly()
hel_poly_buff = hel_poly.buffer(2000)
extent = geom_utils.project_to_wgs(hel_poly_buff)

# GET GRAPH
graph = nw.get_walk_network(extent)
ox.save_graphml(graph, filename='hel.graphml', folder='graphs', gephi=False)

# UNDIRECTED
graph_u = ox.get_undirected(graph)
ox.save_graphml(graph_u, filename='hel_u.graphml', folder='graphs', gephi=False)

# GET EDGE DICTS
edge_dicts = nw.get_all_edge_dicts(graph_u)
print('Edges in the graph:', len(edge_dicts))
edge_dicts[:2]

# MISSING GEOM ADDED
def get_edge_geoms(edge_dict):
    return nw.get_missing_edge_geometries(edge_dict, graph_u)
pool = Pool(processes=4)
edge_geom_dicts = pool.map(get_edge_geoms, edge_dicts)
pool.close()
for edge_d in edge_geom_dicts:
        nx.set_edge_attributes(graph_u, { edge_d['uvkey']: {'geometry': edge_d['geometry'], 'length': edge_d['length']}})
ox.save_graphml(graph_u, filename='hel_u_g.graphml', folder='graphs', gephi=False)

print('\nall done.')
