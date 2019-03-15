#%% IMPORT MODULES FOR NETWORK CONSTRUCTION
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

#%% GET BOUNDING BOX POLYGONS
koskela_box = geom_utils.project_to_wgs(nw.get_koskela_box())
koskela_kumpula_box = geom_utils.project_to_wgs(nw.get_koskela_kumpula_box())
noise_polys = noise_utils.get_noise_polygons()

#%% GET NETWORK
# graph_proj = nw.get_walk_network(koskela_kumpula_box)
# ox.save_graphml(graph_proj, filename='koskela_kumpula_test.graphml', folder='graphs', gephi=False)
graph_proj = ox.load_graphml('koskela_test.graphml', folder='graphs')
graph_size = len(graph_proj)

#%% ADD MISSING GEOMETRIES TO EDGES
def add_missing_edge_geometries(idx, node_from):
    utils.print_progress(idx, graph_size, True)
    # list of nodes to which node_from is connected to
    nodes_to = graph_proj[node_from]
    for node_to in nodes_to.keys():
        # all edges between node-from and node-to as dict (usually)
        edges = graph_proj[node_from][node_to]
        # usually only one edge is found between each origin-to-target-node -pair 
        # edge_k is unique identifier for edge between two nodes, integer (etc. 0 or 1) 
        for edge_k in edges.keys():
            # combine unique identifier for the edge
            edge_uvkey = (node_from, node_to, edge_k)
            # edge dict contains all edge attributes
            edge_d = edges[edge_k]
            if ('geometry' not in edge_d):
                # print('add missing geometry...')
                # interpolate missing geometry as straigth line between nodes
                edge_geom = nw.get_edge_geom_from_node_pair(graph_proj, node_from, node_to)
                # set geometry attribute of the edge
                nx.set_edge_attributes(graph_proj, { edge_uvkey: {'geometry': edge_geom} })
            # set length attribute
            nx.set_edge_attributes(graph_proj, { edge_uvkey: {'length': round(edge_d['geometry'].length, 3)} })
            # print all edge attributes
            # print('edge', edge_k, ':', graph_proj[node_from][node_to][edge_k])

for idx, node_from in enumerate(graph_proj):
    add_missing_edge_geometries(idx, node_from)

#%% FUNCTION FOR ADDING CUMULATIVE NOISE EXPOSURES TO EDGES
def add_edge_noise_exposures(node_from):
    # list of nodes to which node_from is connected to
    attr_set_dicts = []
    nodes_to = graph_proj[node_from]
    for node_to in nodes_to.keys():
        # all edges between node-from and node-to as dict (usually)
        edges = graph_proj[node_from][node_to]
        # usually only one edge is found between each origin-to-target-node -pair 
        # edge_k is unique identifier for edge between two nodes, integer (etc. 0 or 1) 
        for edge_k in edges.keys():
            # identifier for unique edge (tuple)
            edge_uvkey = (node_from, node_to, edge_k)
            # edge dict contains all edge attributes
            edge_d = edges[edge_k]
            # get cumulative noises dictionary for edge geometry
            if ('noises' not in edge_d):
                noise_lines = noise_utils.get_exposure_lines(edge_d['geometry'], noise_polys)
                if (noise_lines.empty):
                    noise_dict = {}
                else:
                    noise_dict = noise_utils.get_exposures(noise_lines)
                th_noise_dict = noise_utils.get_th_exposures(noise_dict, [55,60,65,70])
                attr_set_dict = { edge_uvkey: {'noises': noise_dict, 'th_noises': th_noise_dict} }
                # print('attr_set_dict:',attr_set_dict)
                attr_set_dicts.append(attr_set_dict)
    return attr_set_dicts

#%% COLLECT LIST OF NODES_FROM FOR TESTING NOISE EXTRACTION
nodes_from = []
for idx, node_from in enumerate(graph_proj):
    nodes_from.append(node_from)
    if (idx > 6):
        break
print('count nodes from:', len(nodes_from))

#%% EXTRACT NOISE ATTRIBUTES WITHOUT POOL
start_time = time.time()
attr_set_dicts = [add_edge_noise_exposures(node_from) for node_from in nodes_from]
print("--- %s seconds ---" % (time.time() - start_time))

#%% EXTRACT NOISE ATTRIBUTES WITH POOL
start_time = time.time()
pool = multiprocessing.Pool(processes=4)
attr_set_dicts = pool.map(add_edge_noise_exposures, nodes_from)
pool.close()
print("--- %s seconds ---" % (time.time() - start_time))

#%% SET EDGE ATTRIBUTES USING ATTRIBUTE LISTS
for attr_dict in attr_set_dicts:
    for attrs_d in attr_dict:
        nx.set_edge_attributes(graph_proj, attrs_d)

#%% PRINT EDGE ATTRIBUTES
for node_from in nodes_from:
    nw.print_edges_from_node_attributes(node_from, graph_proj)

#%% GET NODES & EDGES (AS GDFS) FROM GRAPH
nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)
edges.head(5)

#%% EXPORT NODES & EDGES TO FILES
edges = edges[['geometry', 'u', 'v', 'length', 'noises', 'th_noises']]
edges.to_file('data/networks.gpkg', layer='koskela_edges_noise', driver="GPKG")
nodes.to_file('data/networks.gpkg', layer='koskela_nodes_noise', driver="GPKG")

#%%
