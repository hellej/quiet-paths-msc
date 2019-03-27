import pandas as pd
import osmnx as ox
import networkx as nx
from shapely.geometry import Point, LineString, MultiLineString, box
import utils.networks as nw
import utils.geometry as geom_utils
import utils.exposures as exps

def get_nearest_node(graph_proj, coords):
    point = Point(coords)
    edge = ox.get_nearest_edge(graph_proj, coords[::-1])
    edge_geom = edge[0]
    point_edge_distance = point.distance(edge_geom)
    nearest_node = ox.get_nearest_node(graph_proj, coords[::-1], method='euclidean')
    nearest_node_geom = geom_utils.get_point_from_xy(graph_proj.nodes[nearest_node])
    point_node_distance = point.distance(nearest_node_geom)
    if (point_node_distance - point_edge_distance > 5):
        # create a new node on the nearest edge nearest to the origin
        closest_line_point = geom_utils.get_closest_point_on_line(edge_geom, point)
        new_node = nw.add_new_node(graph_proj, closest_line_point)
        nw.add_linking_edges_for_new_node(graph_proj, new_node, closest_line_point, edge)
        return new_node
    else:
        print('Nearby node exists')
        return nearest_node

def get_shortest_path_params(graph_proj, from_xy, to_xy):
    from_coords = geom_utils.get_coords_from_xy(from_xy)
    to_coords = geom_utils.get_coords_from_xy(to_xy)
    orig_node = get_nearest_node(graph_proj, from_coords)
    target_node = get_nearest_node(graph_proj, to_coords)
    return {'orig_node': orig_node, 'target_node':target_node}

def get_shortest_path(graph_proj, path_params: dict, weight: str):
    orig_node = path_params['orig_node']
    target_node = path_params['target_node']
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
    paths_gdf_g = paths_gdf.drop_duplicates(subset=['type', 'total_length']).copy()
    shortest_p = paths_gdf_g.loc[paths_gdf_g['type'] == 'short'].squeeze()
    s_len = shortest_p.get('total_length')
    s_th_noises = shortest_p.get('th_noises')
    paths_gdf_g['diff_len'] = [round(total_len - s_len, 1) for total_len in paths_gdf_g['total_length']]
    paths_gdf_g['diff_55_dB'] = [exps.get_th_exp_diff(65, th_noises, s_th_noises) for th_noises in paths_gdf_g['th_noises']]
    paths_gdf_g['diff_60_dB'] = [exps.get_th_exp_diff(60, th_noises, s_th_noises) for th_noises in paths_gdf_g['th_noises']]
    paths_gdf_g['diff_65_dB'] = [exps.get_th_exp_diff(65, th_noises, s_th_noises) for th_noises in paths_gdf_g['th_noises']]
    paths_gdf_g['diff_70_dB'] = [exps.get_th_exp_diff(70, th_noises, s_th_noises) for th_noises in paths_gdf_g['th_noises']]
    return paths_gdf_g