#%%
import pytest
import json
import geopandas as gpd
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.exposures as exps
import utils.quiet_paths as qp
import utils.utils as utils
import utils.tests as tests
from fiona.crs import from_epsg
import unittest
import time

#%% 
def get_short_quiet_paths(from_latLon, to_latLon):
    # start_time = time.time()
    # # get origin & target nodes
    # from_latLon = {'lat': float(from_lat), 'lon': float(from_lon)}
    # to_latLon = {'lat': float(to_lat), 'lon': float(to_lon)}
    # print('from:', from_latLon)
    # print('to:', to_latLon)
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)
    # find origin and target nodes from closest edges
    orig_node = rt.get_nearest_node(graph, from_xy, edge_gdf, node_gdf, nts, False)
    target_node = rt.get_nearest_node(graph, to_xy, edge_gdf, node_gdf, nts, False, orig_node=orig_node)
    # utils.print_duration(start_time, 'Origin & target nodes set.')
    # start_time = time.time()
    # get shortest path
    path_list = []
    shortest_path = rt.get_shortest_path(graph, orig_node['node'], target_node['node'], 'length')
    path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, 'length', True, True)
    path_list.append({**path_geom, **{'id': 'short_p','type': 'short', 'nt': 0}})
    # get quiet paths to list
    for nt in nts:
        cost_attr = 'nc_'+str(nt)
        shortest_path = rt.get_shortest_path(graph, orig_node['node'], target_node['node'], cost_attr)
        path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, cost_attr, True, True)
        path_list.append({**path_geom, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})
    # remove linking edges of the origin / target nodes
    nw.remove_linking_edges_of_new_node(graph, orig_node)
    nw.remove_linking_edges_of_new_node(graph, target_node)
    # collect quiet paths to gdf
    gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
    paths_gdf = rt.aggregate_quiet_paths(gdf)
    # get exposures to noises along the paths
    paths_gdf['th_noises'] = [exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in paths_gdf['noises']]
    # add noise exposure index (same as noise cost with noise tolerance: 1)
    costs = { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }
    paths_gdf['nei'] = [round(nw.get_noise_cost(noises, costs, 1), 1) for noises in paths_gdf['noises']]
    paths_gdf['nei_norm'] = paths_gdf.apply(lambda row: round(row.nei / (0.6 * row.total_length), 4), axis=1)
    # # gdf to dicts
    # path_dicts = qp.get_geojson_from_q_path_gdf(paths_gdf)
    # # group paths with nearly identical geometries
    # unique_paths = qp.remove_duplicate_geom_paths(path_dicts, tolerance=25)
    # # calculate exposure differences to shortest path
    # path_comps = rt.get_short_quiet_paths_comparison_for_dicts(unique_paths)
    # # return paths as GeoJSON (FeatureCollection)
    # utils.print_duration(start_time, 'Routing done.')
    return paths_gdf

#%% initialize graph
start_time = time.time()
nts = [0.1, 0.15, 0.25, 0.5, 1, 1.5, 2, 4, 6, 10, 20, 40]
# graph = files.get_network_full_noise_v2(directed=False)
graph = files.get_network_kumpula_noise(version=2)
print('Graph of', graph.size(), 'edges read.')
edge_gdf = nw.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'])
node_gdf = nw.get_node_gdf(graph)
# print('Network features extracted.')
nw.set_graph_noise_costs(edge_gdf, graph, nts)
edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
print('Noise costs set.')
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
# print('Spatial index built.')
utils.print_duration(start_time, 'Network initialized.')

#%% read test locations
origin_latLon = tests.get_origin_lat_lon()
target_locations = tests.get_target_locations()
to_latLon_1 = list(target_locations['latLon'])[0]
to_latLon_2 = list(target_locations['latLon'])[1]
to_latLon_3 = list(target_locations['latLon'])[2]
to_latLon_4 = list(target_locations['latLon'])[3]

def get_path_stats(origin_latLon, to_latLon):
    test_paths = get_short_quiet_paths(origin_latLon, to_latLon)
    sp = test_paths.query("type == 'short'")
    qp = test_paths.query("type == 'quiet'")
    p_count = len(test_paths)
    sp_count = len(sp)
    qp_count = len(qp)
    sp_len = round(sp['total_length'].sum(), 1)
    qp_len_sum = round(qp['total_length'].sum(), 1)
    return { 'p_count': p_count, 'sp_count': sp_count, 'qp_count': qp_count, 'sp_len': sp_len, 'qp_len_sum': qp_len_sum }

class TestQuietPaths(unittest.TestCase):

    def test_quiet_path_1(self):
        compare_d = { 'p_count': 7, 'sp_count': 1, 'qp_count': 6, 'sp_len': 2043.0, 'qp_len_sum': 16711.4 }
        stats = get_path_stats(origin_latLon, to_latLon_1)
        self.assertDictEqual(stats, compare_d) 

    def test_quiet_path_2(self):
        compare_d = { 'p_count': 9, 'sp_count': 1, 'qp_count': 8, 'sp_len': 1547.5, 'qp_len_sum': 16059.9 }
        stats = get_path_stats(origin_latLon, to_latLon_2)
        self.assertDictEqual(stats, compare_d) 

    def test_quiet_path_3(self):
        compare_d = { 'p_count': 8, 'sp_count': 1, 'qp_count': 7, 'sp_len': 1288.6, 'qp_len_sum': 10522.9 }
        stats = get_path_stats(origin_latLon, to_latLon_3)
        self.assertDictEqual(stats, compare_d) 

    def test_quiet_path_4(self):
        compare_d = { 'p_count': 4, 'sp_count': 1, 'qp_count': 3, 'sp_len': 1317.8, 'qp_len_sum': 4180.3 }
        stats = get_path_stats(origin_latLon, to_latLon_4)
        self.assertDictEqual(stats, compare_d) 

if __name__ == '__main__':
    unittest.main()
