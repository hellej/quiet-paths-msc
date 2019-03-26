#%%
import pandas as pd
import geopandas as gpd
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw

#%% READ DATA
graph_proj = files.get_noise_network_graph()
pois = files.get_pois()
koskela = pois.loc[pois['name'] == 'Koskela']
kumpula = pois.loc[pois['name'] == 'Kumpulan kampus']

#%% SET NOISE IMPEDANCES TO NETWORK
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edges = nw.get_edge_gdf(edge_dicts, ['uvkey', 'geometry', 'length', 'noises', 'th_noises'])
#%%
edge_n_costs = nw.get_noise_costs(edges)
edge_n_costs.head(20)
#%%
nw.update_segment_costs(edge_n_costs, graph_proj)
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_dicts[:2]

#%% GET SHORTEST PATH FOR REFERENCE
path_list = []
from_xy = geom_utils.get_xy_from_geom(list(koskela['geometry'])[0])
to_xy = geom_utils.get_xy_from_geom(list(kumpula['geometry'])[0])
path_params = rt.get_shortest_path_params(graph_proj, from_xy, to_xy)
shortest_path = rt.get_shortest_path(graph_proj, path_params)
path_geom = nw.get_edge_geometries(graph_proj, shortest_path)
path_list.append({**path_geom, **{'type': 'short'}})


#%%
path_geom

#%%
