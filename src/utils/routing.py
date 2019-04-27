import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import time
from shapely.geometry import Point, LineString, MultiLineString, box
import utils.networks as nw
import utils.geometry as geom_utils
import utils.exposures as exps
import utils.utils as utils
from shapely.ops import nearest_points

def find_nearest_edge(xy, edge_gdf):
    start_time = time.time()
    edges_sind = edge_gdf.sindex
    point_geom = geom_utils.get_point_from_xy(xy)
    possible_matches_index = list(edges_sind.intersection(point_geom.buffer(100).bounds))
    possible_matches = edge_gdf.iloc[possible_matches_index].copy()
    possible_matches['distance'] = [geom.distance(point_geom) for geom in possible_matches['geometry']]
    shortest_dist = possible_matches['distance'].min()
    nearest = possible_matches['distance'] == shortest_dist
    nearest_edges =  possible_matches.loc[nearest]
    nearest_edge = nearest_edges.iloc[0]
    nearest_edge_dict = nearest_edge.to_dict()
    utils.print_duration(start_time, 'found nearest edge')
    return nearest_edge_dict

def find_nearest_node(xy, node_gdf):
    start_time = time.time()
    nodes_sind = node_gdf.sindex
    point_geom = geom_utils.get_point_from_xy(xy)
    possible_matches_index = list(nodes_sind.intersection(point_geom.buffer(700).bounds))
    possible_matches = node_gdf.iloc[possible_matches_index]
    points_union = possible_matches.geometry.unary_union
    nearest_geom = nearest_points(point_geom, points_union)[1]
    nearest = possible_matches.geometry.geom_equals(nearest_geom)
    nearest_point =  possible_matches.loc[nearest]
    nearest_node = nearest_point.index.tolist()[0]
    utils.print_duration(start_time, 'found nearest node')
    return nearest_node

def get_nearest_node(graph_proj, xy, edge_gdf, node_gdf, nts, add_new_edge_noises: bool, noise_polys):
    coords = geom_utils.get_coords_from_xy(xy)
    point = Point(coords)
    near_edge = find_nearest_edge(xy, edge_gdf)
    edge_geom = near_edge['geometry']
    point_edge_distance = near_edge['distance']
    nearest_node = find_nearest_node(xy, node_gdf)
    nearest_node_geom = geom_utils.get_point_from_xy(graph_proj.nodes[nearest_node])
    point_node_distance = point.distance(nearest_node_geom)
    if (point_node_distance - point_edge_distance > 5):
        # create a new node on the nearest edge nearest to the origin
        closest_line_point = geom_utils.get_closest_point_on_line(edge_geom, point)
        new_node = nw.add_new_node(graph_proj, closest_line_point)
        nw.add_linking_edges_for_new_node(graph_proj, new_node, closest_line_point, near_edge, nts, add_new_edge_noises, noise_polys)
        return new_node
    else:
        print('Nearby node exists:', nearest_node)
        return nearest_node

def get_shortest_path(graph_proj, orig_node, target_node, weight: str):
    if (orig_node != target_node):
        s_path = nx.shortest_path(G=graph_proj, source=orig_node, target=target_node, weight=weight)
        return s_path
    else:
        return None

def join_dt_path_attributes(s_paths_g_gdf, dt_paths):
    dt_paths_join = dt_paths.rename(index=str, columns={'path_dist': 'dt_total_length'})
    dt_paths_join = dt_paths_join[['dt_total_length', 'uniq_id', 'to_id', 'count']]
    merged = pd.merge(s_paths_g_gdf, dt_paths_join, how='inner', on='uniq_id')
    return merged

def get_short_quiet_paths_comparison(paths_gdf):
    shortest_p = paths_gdf.loc[paths_gdf['type'] == 'short'].squeeze()
    s_len = shortest_p.get('total_length')
    s_noises = shortest_p.get('noises')
    s_th_noises = shortest_p.get('th_noises')
    s_nei = shortest_p.get('nei')
    paths_gdf['noises_diff'] = [exps.get_noises_diff(s_noises, noises) for noises in paths_gdf['noises']]
    paths_gdf['th_noises_diff'] = [exps.get_noises_diff(s_th_noises, th_noises) for th_noises in paths_gdf['th_noises']]
    paths_gdf['len_diff'] = [round(total_len - s_len, 1) for total_len in paths_gdf['total_length']]
    paths_gdf['len_diff_rat'] = [round((len_diff / s_len)*100,1) for len_diff in paths_gdf['len_diff']]
    paths_gdf['nei_diff'] = [round(nei - s_nei, 1) for nei in paths_gdf['nei']]
    paths_gdf['nei_diff_rat'] = [round((nei_diff / s_nei)*100, 1) if s_nei > 0 else 0 for nei_diff in paths_gdf['nei_diff']]
    paths_gdf['path_score'] = paths_gdf.apply(lambda row: round((row.nei_diff / row.len_diff) * -1, 1) if row.len_diff > 0 else 0, axis=1)
    return paths_gdf

def aggregate_quiet_paths(paths_gdf):
    grouped = paths_gdf.groupby(['type', 'total_length'])
    gdfs = []
    for key, group in grouped:
        max_nt = group['nt'].max()
        min_nt = group['nt'].min()
        g_row = dict(group.iloc[0])
        g_row['min_nt'] = min_nt
        g_row['max_nt'] = max_nt
        g_row.pop('nt', None)
        gdfs.append(g_row)
    g_gdf = gpd.GeoDataFrame(gdfs, crs=geom_utils.get_etrs_crs())
    return g_gdf
