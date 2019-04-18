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
graph_proj = files.get_kumpula_noise_network()
pois = files.get_pois()
koskela = pois.loc[pois['name'] == 'Koskela']
kumpula = pois.loc[pois['name'] == 'Kumpulan kampus']

#%% SET NOISE IMPEDANCES TO GRAPH
nts = [0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6]
nw.set_graph_noise_costs(graph_proj, nts)

#%% GET GRAPH GDFS
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_gdf = nw.get_edge_gdf(edge_dicts, ['uvkey', 'geometry'])
node_gdf = nw.get_node_gdf(graph_proj)
edge_dicts[:2]

#%% GET ROUTING PARAMS
path_list = []
from_xy = geom_utils.get_xy_from_geom(list(koskela['geometry'])[0])
to_xy = geom_utils.get_xy_from_geom(list(kumpula['geometry'])[0])
print(from_xy)
print(to_xy)
start_time = time.time()
orig_node = rt.get_nearest_node(graph_proj, from_xy, edge_gdf, node_gdf, nts)
target_node = rt.get_nearest_node(graph_proj, to_xy, edge_gdf, node_gdf, nts)
utils.print_duration(start_time, 'get all routing params')

#%% SHORTEST PATH
start_time = time.time()
shortest_path = rt.get_shortest_path(graph_proj, orig_node, target_node, 'length')
path_geom = nw.get_edge_geoms_attrs(graph_proj, shortest_path, 'length', True, True)
path_list.append({**path_geom, **{'id': 'short_p','type': 'short', 'nt': 0}})
utils.print_duration(start_time, 'get shortest path & its geom')

#%% CALCULATE QUIET PATHS
for nt in nts:
    cost_attr = 'nc_'+str(nt)
    shortest_path = rt.get_shortest_path(graph_proj, orig_node, target_node, cost_attr)
    path_geom = nw.get_edge_geoms_attrs(graph_proj, shortest_path, cost_attr, True, True)
    path_list.append({**path_geom, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})

#%% GROUP SIMILAR PATHS
gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
paths_gdf = rt.aggregate_quiet_paths(gdf)
paths_gdf

#%% ADD NOISE EXPOSURES // ADDING ABOVE FROM EDGE ATTRIBUTES
# start_time = time.time()
# paths_gdf = exps.add_noise_exposures_to_gdf(paths_gdf, 'id', noise_polys)
# paths_gdf['noises'] = [exps.get_exposures_for_geom(line_geom, noise_polys) for line_geom in paths_gdf['geometry']]
paths_gdf['th_noises'] = [exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in paths_gdf['noises']]

# time_elapsed = round(time.time() - start_time, 1)
# print('\n--- %s seconds ---' % (time_elapsed))
# paths_gdf.plot()
# paths_gdf

#%% COMPARE LENGTHS & EXPOSURES
path_comps = rt.get_short_quiet_paths_comparison(paths_gdf)
path_comps

#%% FEATURES TO DICT -> JSON
path_dicts = qp.get_geojson_from_q_path_gdf(path_comps)
for path_dict in path_dicts:
    print(path_dict['properties']['length'])

#%% EXPORT TO CSV
path_comps[['id', 'min_nt', 'max_nt', 'total_length','type', 'diff_len', 'diff_rat', 'diff_60_dB', 'diff_70_dB']].to_csv('outputs/quiet_paths.csv')
#%% EXPORT TO GDF
path_comps.to_file('outputs/quiet_paths.gpkg', layer='quiet_paths_t', driver="GPKG")

#%%
