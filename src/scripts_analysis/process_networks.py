#%%
import geopandas as gpd
import osmnx as ox
import time
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.quiet_paths as qp
import utils.exposures as exps
import utils.utils as utils

#%% SET CONSTS
nts = [0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6, 10, 15, 20]

#%% READ GRAPH
graph = files.get_network_kumpula_noise()

#%% SET NOISE IMPEDANCES TO GRAPH
nw.set_graph_noise_costs(graph, nts)
edge_dicts = nw.get_all_edge_dicts(graph)
edge_dicts[:2]

#%% EXPORT GRAPH
ox.save_graphml(graph, filename='kumpula_u_g_n_c_s.graphml', folder='graphs', gephi=False)

#%% CHECK EXPORTED GRAPH
graph = files.get_network_kumpula_noise_costs(nts)
edge_dicts = nw.get_all_edge_dicts(graph)
edge_dicts[:2]


##### PROCESS FULL GRAPH #####

#%% READ GRAPH
graph = files.get_network_full_noise()

#%% SET NOISE IMPEDANCES TO GRAPH
nw.set_graph_noise_costs(graph, nts)
edge_dicts = nw.get_all_edge_dicts(graph)
edge_dicts[:2]

#%% EXPORT GRAPH
ox.save_graphml(graph, filename='hel_u_g_n_c_s.graphml', folder='graphs', gephi=False)

#%% CHECK EXPORTED GRAPH
graph = files.get_network_full_noise_costs(nts)
edge_dicts = nw.get_all_edge_dicts(graph)
edge_dicts[:2]


#%%
