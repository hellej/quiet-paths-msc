#%%
import pandas as pd
import geopandas as gpd
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.exposures as exps
from fiona.crs import from_epsg
import time

#%% READ DATA
noise_polys = files.get_noise_polygons()
graph_proj = files.get_noise_network_graph()
pois = files.get_pois()
koskela = pois.loc[pois['name'] == 'Koskela']
kumpula = pois.loc[pois['name'] == 'Kumpulan kampus']

#%%
nw.delete_unused_edge_attrs(graph_proj)
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_gdf = nw.get_edge_gdf(edge_dicts, ['uvkey', 'geometry', 'length', 'noises'])
edge_dicts[:2]

#%% SET NOISE IMPEDANCES TO NETWORK
def set_graph_noise_costs(edge_gdf, graph_proj, nt: 'noise tolerance, float: 0.0-2.0'):
    edge_n_costs = nw.get_noise_costs(edge_gdf, nt)
    nw.update_segment_costs(edge_n_costs, graph_proj)

#%% check added noise costs
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_dicts[:2]

#%% GET SHORTEST PATH FOR REFERENCE
path_list = []
from_xy = geom_utils.get_xy_from_geom(list(koskela['geometry'])[0])
to_xy = geom_utils.get_xy_from_geom(list(kumpula['geometry'])[0])
path_params = rt.get_shortest_path_params(graph_proj, from_xy, to_xy)

#%% SHORTEST PATH
shortest_path = rt.get_shortest_path(graph_proj, path_params, 'length')
path_geom = nw.get_edge_geometries(graph_proj, shortest_path)
path_list.append({**path_geom, **{'id': 'short_p','type': 'short', 'nt': 0}})

#%% CALCULATE QUIET PATHS
nts = [0.25, 0.5, 1, 1.5, 2]
for nt in nts:
    set_graph_noise_costs(edge_gdf, graph_proj, nt)
    shortest_path = rt.get_shortest_path(graph_proj, path_params, 'tot_cost')
    path_geom = nw.get_edge_geometries(graph_proj, shortest_path)
    path_list.append({**path_geom, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})

#%% ADD NOISE EXPOSURES
s_paths_gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
start_time = time.time()

# s_paths_gdf = exps.add_noise_exposures_to_gdf(s_paths_gdf, 'id', noise_polys)
s_paths_gdf['noises'] = [exps.get_exposures_for_geom(line_geom, noise_polys) for line_geom in s_paths_gdf['geometry']]
#%%
s_paths_gdf['th_noises'] = [exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in s_paths_gdf['noises']]

time_elapsed = round(time.time() - start_time, 1)
print('\n--- %s seconds ---' % (time_elapsed))

s_paths_gdf.plot()
s_paths_gdf.head(10)

#%%
s_paths_gdf.to_file('outputs/quiet_paths.gpkg', layer='quiet_paths_t', driver="GPKG")

#%%
