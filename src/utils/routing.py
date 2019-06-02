import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import time
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString, MultiLineString, box
from shapely.ops import nearest_points
import utils.networks as nw
import utils.geometry as geom_utils
import utils.exposures as exps
import utils.utils as utils
import utils.quiet_paths as qp

def find_nearest_edge(xy, edge_gdf):
    # start_time = time.time()
    edges_sind = edge_gdf.sindex
    point_geom = geom_utils.get_point_from_xy(xy)
    possible_matches_index = list(edges_sind.intersection(point_geom.buffer(120).bounds))
    possible_matches = edge_gdf.iloc[possible_matches_index].copy()
    possible_matches['distance'] = [geom.distance(point_geom) for geom in possible_matches['geometry']]
    shortest_dist = possible_matches['distance'].min()
    nearest = possible_matches['distance'] == shortest_dist
    nearest_edges =  possible_matches.loc[nearest]
    nearest_edge = nearest_edges.iloc[0]
    nearest_edge_dict = nearest_edge.to_dict()
    # utils.print_duration(start_time, 'found nearest edge')
    return nearest_edge_dict

def find_nearest_node(xy, node_gdf):
    # start_time = time.time()
    nodes_sind = node_gdf.sindex
    point_geom = geom_utils.get_point_from_xy(xy)
    possible_matches_index = list(nodes_sind.intersection(point_geom.buffer(700).bounds))
    possible_matches = node_gdf.iloc[possible_matches_index]
    points_union = possible_matches.geometry.unary_union
    nearest_geom = nearest_points(point_geom, points_union)[1]
    nearest = possible_matches.geometry.geom_equals(nearest_geom)
    nearest_point =  possible_matches.loc[nearest]
    nearest_node = nearest_point.index.tolist()[0]
    # utils.print_duration(start_time, 'found nearest node')
    return nearest_node

def get_nearest_node(graph_proj, xy, edge_gdf, node_gdf, nts, add_new_edge_noises: bool, noise_polys=None, orig_node=None, logging=True):
    coords = geom_utils.get_coords_from_xy(xy)
    point = Point(coords)
    near_edge = find_nearest_edge(xy, edge_gdf)
    edge_geom = near_edge['geometry']
    nearest_node = find_nearest_node(xy, node_gdf)
    nearest_node_geom = geom_utils.get_point_from_xy(graph_proj.nodes[nearest_node])
    # create a new node on the nearest edge nearest to the origin
    closest_line_point = geom_utils.get_closest_point_on_line(edge_geom, point)
    # if nearest node is same as closest point on closest edge, return nearest node
    near_edge_near_node_dist_diff = closest_line_point.distance(nearest_node_geom) 
    if (near_edge_near_node_dist_diff < 1):
        # print('nearest node is at end of the nearest edge at distance:', round(near_edge_near_node_dist_diff, 5))
        return {'node': nearest_node }
    if (orig_node is not None and 'link_edges' in orig_node):
        if (closest_line_point.distance(orig_node['link_edges']['link1']['geometry']) < 0.2):
            near_edge = orig_node['link_edges']['link1']
        if (closest_line_point.distance(orig_node['link_edges']['link2']['geometry']) < 0.2):
            near_edge = orig_node['link_edges']['link2']
    new_node = nw.add_new_node(graph_proj, closest_line_point, logging=logging)
    link_edges = nw.add_linking_edges_for_new_node(graph_proj, new_node, closest_line_point, near_edge, nts, add_new_edge_noises, noise_polys=noise_polys, logging=logging)
    return { 'node': new_node, 'link_edges': link_edges }

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

def get_short_quiet_paths_comparison_for_gdf(paths_gdf):
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

def get_short_quiet_paths_comparison_for_dicts(paths):
    comp_paths = paths.copy()
    path_s = [path for path in comp_paths if path['properties']['type'] == 'short'][0]
    s_len = path_s['properties']['length']
    s_noises = path_s['properties']['noises']
    s_th_noises = path_s['properties']['th_noises']
    s_nei = path_s['properties']['nei']
    for path in comp_paths:
        props = path['properties']
        path['properties']['noises_diff'] = exps.get_noises_diff(s_noises, props['noises'])
        path['properties']['th_noises_diff'] = exps.get_noises_diff(s_th_noises, props['th_noises'], full_db_range=False)
        path['properties']['len_diff'] = round(props['length'] - s_len, 1)
        path['properties']['len_diff_rat'] = round((path['properties']['len_diff'] / s_len) * 100, 1) if s_len > 0 else 0
        path['properties']['nei_norm'] = round(path['properties']['nei_norm'], 2)
        path['properties']['nei_diff'] = round(path['properties']['nei'] - s_nei, 1)
        path['properties']['nei_diff_rat'] = round((path['properties']['nei_diff'] / s_nei) * 100, 1) if s_nei > 0 else 0
        path['properties']['path_score'] = round((path['properties']['nei_diff'] / path['properties']['len_diff']) * -1, 1) if path['properties']['len_diff'] > 0 else 0
    return comp_paths

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
    g_gdf = g_gdf.sort_values(by=['type', 'total_length'])
    return g_gdf

def get_short_quiet_paths(graph, from_latLon, to_latLon, edge_gdf, node_gdf, nts, remove_geom_prop=True, logging=True):
    start_time = time.time()
    # get origin & target nodes
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)
    # find origin and target nodes from closest edges
    orig_node = get_nearest_node(graph, from_xy, edge_gdf, node_gdf, nts, False, logging=logging)
    target_node = get_nearest_node(graph, to_xy, edge_gdf, node_gdf, nts, False, orig_node=orig_node, logging=logging)
    if (logging == True):
        utils.print_duration(start_time, 'Got params for routing.')
    start_time = time.time()
    # get shortest path
    path_list = []
    shortest_path = get_shortest_path(graph, orig_node['node'], target_node['node'], 'length')
    path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, 'length', True, True)
    path_list.append({**path_geom, **{'id': 'short_p','type': 'short', 'nt': 0}})
    # get quiet paths to list
    for nt in nts:
        cost_attr = 'nc_'+str(nt)
        shortest_path = get_shortest_path(graph, orig_node['node'], target_node['node'], cost_attr)
        path_geom = nw.get_edge_geoms_attrs(graph, shortest_path, cost_attr, True, True)
        path_list.append({**path_geom, **{'id': 'q_'+str(nt), 'type': 'quiet', 'nt': nt}})
    # remove linking edges of the origin / target nodes
    nw.remove_linking_edges_of_new_node(graph, orig_node)
    nw.remove_linking_edges_of_new_node(graph, target_node)
    # collect quiet paths to gdf
    gdf = gpd.GeoDataFrame(path_list, crs=from_epsg(3879))
    paths_gdf = aggregate_quiet_paths(gdf)
    # get exposures to noises along the paths
    paths_gdf['th_noises'] = [exps.get_th_exposures(noises, [55, 60, 65, 70]) for noises in paths_gdf['noises']]
    # add noise exposure index (same as noise cost with noise tolerance: 1)
    costs = { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }
    paths_gdf['nei'] = [round(nw.get_noise_cost(noises, costs, 1), 1) for noises in paths_gdf['noises']]
    paths_gdf['nei_norm'] = paths_gdf.apply(lambda row: round(row.nei / (0.6 * row.total_length), 4), axis=1)
    # gdf to dicts
    path_dicts = qp.get_geojson_from_q_path_gdf(paths_gdf)
    # group paths with nearly identical geometries
    unique_paths = qp.remove_duplicate_geom_paths(path_dicts, tolerance=25, remove_geom_prop=remove_geom_prop, logging=logging)
    # calculate exposure differences to shortest path
    path_comps = get_short_quiet_paths_comparison_for_dicts(unique_paths)
    # return paths as GeoJSON (FeatureCollection)
    if (logging == True):
        utils.print_duration(start_time, 'Routing done.')
    return path_comps
