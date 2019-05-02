#%%
import geopandas as gpd
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.quiet_paths as qp
import utils.exposures as exps
import utils.utils as utils
from fiona.crs import from_epsg
import time

#%% READ DATA
noise_polys = files.get_noise_polygons()
graph = files.get_network_kumpula_noise()
pois = files.get_pois()
koskela = pois.loc[pois['name'] == 'Koskela']
kumpula = pois.loc[pois['name'] == 'Kumpulan kampus']

#%% SET NOISE IMPEDANCES TO GRAPH
nts = [0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6]
nw.set_graph_noise_costs(graph, nts)

#%% GET GRAPH GDFS
edge_dicts = nw.get_all_edge_dicts(graph)
edge_gdf = nw.get_edge_gdf(edge_dicts, ['uvkey', 'geometry', 'noises'])
node_gdf = nw.get_node_gdf(graph)
edge_dicts[:2]

#%% GET ROUTING PARAMS
path_list = []
from_xy = geom_utils.get_xy_from_geom(list(koskela['geometry'])[0])
to_xy = geom_utils.get_xy_from_geom(list(kumpula['geometry'])[0])
print(from_xy)
print(to_xy)
start_time = time.time()
orig_node = rt.get_nearest_node(graph, from_xy, edge_gdf, node_gdf, nts, False, noise_polys)
target_node = rt.get_nearest_node
utils.print_duration(start_time, 'get all routing params')

#%% SHORTEST PATH
start_time = time.time()
shortest_path = rt.get_shortest_path(graph, orig_node['node'], target_node['node'], 'length')
path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, 'length', True, True)
path_list.append({**path_geom, **{'id': 'short_p','type': 'short', 'nt': 0}})
utils.print_duration(start_time, 'get shortest path & its geom')

#%% CALCULATE QUIET PATHS
for nt in nts:
    cost_attr = 'nc_'+str(nt)
    shortest_path = rt.get_shortest_path(graph, orig_node['node'], target_node['node'], cost_attr)
    path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, cost_attr, True, True)
    path_list.append({**path_geom, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})

#%% COLLECT PATHS TO GDF & GROUP SIMILAR PATHS
gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
paths_gdf = rt.aggregate_quiet_paths(gdf)
paths_gdf

#%% add cumulative noise exposures above threshold noise levels
paths_gdf['th_noises'] = [exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in paths_gdf['noises']]

# add noise exposure index (same as noise cost with noise tolerance: 1)
costs = { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }
paths_gdf['nei'] = [round(nw.get_noise_cost(noises, costs, 1), 1) for noises in paths_gdf['noises']]
paths_gdf['nei_norm'] = paths_gdf.apply(lambda row: round(row.nei / (0.6 * row.total_length), 4), axis=1)

#%% COLLECT & COMPARE PATHS IN DICTS
# gdf to dicts
path_dicts = qp.get_geojson_from_q_path_gdf(paths_gdf)
# aggregate paths based on similarity of the geometries
unique_paths = qp.remove_duplicate_geom_paths(path_dicts, 10)
# calculate exposure differences to shortest path
path_comps = rt.get_short_quiet_paths_comparison_for_dicts(unique_paths)

#%% EXPORT TO CSV
path_comps[['id', 'min_nt', 'max_nt', 'total_length','type', 'len_diff', 'len_diff_rat', 'nei', 'nei_norm', 'nei_diff_rat']].to_csv('outputs/quiet_paths.csv')
#%% EXPORT TO GDF
path_comps.to_file('outputs/quiet_paths.gpkg', layer='quiet_paths_t', driver="GPKG")

#%%
