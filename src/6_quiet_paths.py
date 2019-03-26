#%%
import pandas as pd
import geopandas as gpd
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
from fiona.crs import from_epsg

#%% READ DATA
graph_proj = files.get_noise_network_graph()
pois = files.get_pois()
koskela = pois.loc[pois['name'] == 'Koskela']
kumpula = pois.loc[pois['name'] == 'Kumpulan kampus']

#%%
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_gdf = nw.get_edge_gdf(edge_dicts, ['uvkey', 'geometry', 'length', 'noises'])
edge_gdf.head(2)

#%% SET NOISE IMPEDANCES TO NETWORK
def set_graph_noise_costs(edge_gdf, graph_proj, nt: 'noise tolerance, float: 0.0-2.0'):
    edge_n_costs = nw.get_noise_costs(edge_gdf, nt)
    nw.update_segment_costs(edge_n_costs, graph_proj)

set_graph_noise_costs(edge_gdf, graph_proj, 2)

#%% check added noise costs
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_dicts[:2]


#%% GET SHORTEST PATH FOR REFERENCE
path_list = []
from_xy = geom_utils.get_xy_from_geom(list(koskela['geometry'])[0])
to_xy = geom_utils.get_xy_from_geom(list(kumpula['geometry'])[0])
path_params = rt.get_shortest_path_params(graph_proj, from_xy, to_xy)

#%% shortest path
shortest_path = rt.get_shortest_path(graph_proj, path_params, 'length')
path_geom = nw.get_edge_geometries(graph_proj, shortest_path)
path_list.append({**path_geom, **{'type': 'short', 'nt': 0}})

#%% quiet path 1
shortest_path = rt.get_shortest_path(graph_proj, path_params, 'tot_cost')
path_geom = nw.get_edge_geometries(graph_proj, shortest_path)
path_list.append({**path_geom, **{'type': 'quiet', 'nt': 1}})

#%%
s_paths_gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
s_paths_gdf.plot()
s_paths_gdf.head()

#%%
s_paths_gdf.to_file('outputs/quiet_paths.gpkg', layer='quiet_paths_t', driver="GPKG")

#%%
