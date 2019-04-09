import pytest
import geopandas as gpd
import osmnx as ox
import time
import utils.geometry as geom_utils
import utils.exposures as exps
import utils.networks as nw
import utils.files as files
import utils.routing as rt
from shapely.geometry import LineString

# read data
walk = files.get_update_test_walk_line()
walk_geom = walk.loc[0, 'geometry']
noise_polys = files.get_noise_polygons()

def test_split_lines():
    split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
    count_split_lines = len(split_lines.index)
    mean_split_line_len = round(split_lines['length'].mean(),1)
    assert (count_split_lines, mean_split_line_len) == (19, 32.5)

def test_add_noises_to_split_lines():
    split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
    noise_lines = exps.add_noises_to_split_lines(noise_polys, split_lines)
    mean_noise =  round(noise_lines['db_lo'].mean(),1)
    min_noise = noise_lines['db_lo'].min()
    max_noise = noise_lines['db_lo'].max()
    assert (mean_noise, min_noise, max_noise) == (60.6, 45.0, 75.0)

def test_get_exposure_lens():
    split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
    noise_lines = exps.add_noises_to_split_lines(noise_polys, split_lines)
    noise_dict = exps.get_exposures(noise_lines)
    assert noise_dict == {45: 14.356, 50: 4.96, 55: 344.866, 60: 107.11, 65: 62.58, 70: 40.678, 75: 18.673}

def test_get_th_exposure_lens():
    split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
    noise_lines = exps.add_noises_to_split_lines(noise_polys, split_lines)
    noise_dict = exps.get_exposures(noise_lines)
    th_noise_dict = exps.get_th_exposures(noise_dict, [55, 60, 65, 70])
    assert th_noise_dict == {55: 573.907, 60: 229.041, 65: 121.931, 70: 59.351}

def test_get_exposure_lines():
    noise_lines = exps.get_exposure_lines(walk_geom, noise_polys)
    mean_noise =  round(noise_lines['db_lo'].mean(),1)
    min_noise = noise_lines['db_lo'].min()
    max_noise = noise_lines['db_lo'].max()
    assert (mean_noise, min_noise, max_noise) == (59.5, 40.0, 75.0)

def test_get_edge_dicts():
    graph_proj = files.get_network_graph()
    edge_dicts = nw.get_all_edge_dicts(graph_proj)
    edge_d = edge_dicts[0]
    assert (len(edge_dicts), edge_d['length'], type(edge_d['geometry'])) == (23471, 127.051, LineString)

def test_add_exposures_to_edges():
    graph_proj = files.get_network_graph()
    edge_dicts = nw.get_all_edge_dicts(graph_proj)
    edge_gdf = nw.get_edge_gdf(edge_dicts[:5], ['geometry', 'length', 'uvkey'])
    edge_gdf['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in edge_gdf['geometry']]
    split_lines = geom_utils.explode_lines_to_split_lines(edge_gdf, 'uvkey')
    split_line_noises = exps.get_noise_attrs_to_split_lines(split_lines, noise_polys)
    edge_noises = exps.aggregate_line_noises(split_line_noises, 'uvkey')
    nw.update_edge_noises(edge_noises, graph_proj)
    edge_dicts = nw.get_all_edge_dicts(graph_proj)
    edge_d = edge_dicts[0]
    print(edge_d)
    exp_len_sum = sum(edge_d['noises'].values())
    assert (edge_d['noises'], round(exp_len_sum,1)) == ({65: 107.025, 70: 20.027}, round(edge_d['length'],1))

def test_shortest_path():
    graph_proj = files.get_undirected_network_graph()
    pois = files.get_pois()
    koskela = pois.loc[pois['name'] == 'Koskela']
    kumpula = pois.loc[pois['name'] == 'Kumpulan kampus']
    from_xy = geom_utils.get_xy_from_geom(list(koskela['geometry'])[0])
    to_xy = geom_utils.get_xy_from_geom(list(kumpula['geometry'])[0])
    path_params = rt.get_shortest_path_params(graph_proj, from_xy, to_xy)
    shortest_path = rt.get_shortest_path(graph_proj, path_params, 'length')
    path_geom = nw.get_edge_geometries(graph_proj, shortest_path)
    assert (len(shortest_path), path_geom['total_length']) == (45, 1764.38)
