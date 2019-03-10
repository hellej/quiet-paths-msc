#%% IMPORT MODULES FOR NETWORK ANALYSIS
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import utils.geometry as geom_utils
import utils.networks as nw
import utils.noise_overlays as noise_utils
import utils.utils as utils


#%% GET BOUNDING BOX POLYGONS
koskela_box = geom_utils.project_to_wgs(nw.get_koskela_box())
# koskela_kumpula_box = geom_utils.project_to_wgs(nw.get_koskela_kumpula_box())
noise_polys = noise_utils.get_noise_polygons()

#%% GET NETWORK
graph_proj = nw.get_walk_network(koskela_box)
# graph_proj = ox.load_graphml('koskela_test.graphml', folder='graphs')

#%% GET NODES & EDGES (AS GDFS) FROM GRAPH
nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)

#%% ADD MISSING GEOMETRIES TO EDGES
graph_size = len(graph_proj)
for idx, node_from in enumerate(graph_proj):
    utils.print_progress(idx, graph_size)
    if (idx < 0):
        break
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
            try:
                edge_geom = edge_d['geometry']
            except KeyError:
                print('add missing geometry...')
                # interpolate missing geometry as straigth line between nodes
                edge_geom = nw.get_edge_geom_from_node_pair(nodes, node_from, node_to)
                # set geometry attribute of the edge
                nx.set_edge_attributes(graph_proj, { edge_uvkey: {'geometry': edge_geom} })
            # set length attribute
            nx.set_edge_attributes(graph_proj, { edge_uvkey: {'length': round(edge_d['geometry'].length, 3)} })
            # print all edge attributes
            # print('edge', edge_k, ':', graph_proj[node_from][node_to][edge_k])

#%% ADD CUMULATIVE NOISE EXPOSURES TO EDGES
for idx, node_from in enumerate(graph_proj):
    utils.print_progress(idx, graph_size)
    if (idx < 5):
        continue
    if (idx > 10):
        break
    # list of nodes to which node_from is connected to
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
            line_noises = noise_utils.get_line_noises(edge_d['geometry'], noise_polys)
            if (line_noises.empty):
                noise_dict = {}
            else:
                noise_dict = noise_utils.get_cumulative_noises_dict(line_noises)
            th_noise_dict = noise_utils.get_th_noises_dict(noise_dict, [55,60,65,70])
            nx.set_edge_attributes(graph_proj, { edge_uvkey: {'noises': noise_dict, 'th_noises': th_noise_dict} })
            # print all edge attributes
            # print('edge', edge_k, ':', graph_proj[node_from][node_to][edge_k])

#%% EXPORT GRAPH TO FILE
ox.save_graphml(graph_proj, filename='koskela_test.graphml', folder='graphs', gephi=False)

#%%
