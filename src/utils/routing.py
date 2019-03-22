import pandas as pd
import osmnx as ox
import networkx as nx
import utils.networks as nw
import utils.geometry as geom_utils
from shapely.geometry import Point, LineString, MultiLineString, box

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

def get_shortest_path(graph_proj, from_xy, to_xy):
    from_coords = geom_utils.get_coords_from_xy(from_xy)
    to_coords = geom_utils.get_coords_from_xy(to_xy)
    orig_node = get_nearest_node(graph_proj, from_coords)
    target_node = get_nearest_node(graph_proj, to_coords)
    print('Nearest origin node for routing:', orig_node)
    print('Nearest target node for routing:', target_node)
    if (orig_node != target_node):
        s_path = nx.shortest_path(G=graph_proj, source=orig_node, target=target_node, weight='length')
        return s_path
    else:
        return None

def join_dt_path_attributes(s_paths_g_gdf, dt_paths):
    dt_paths_join = dt_paths.rename(index=str, columns={'path_dist': 'dt_total_length'})
    dt_paths_join = dt_paths_join[['dt_total_length', 'uniq_id', 'to_id', 'count']]
    merged = pd.merge(s_paths_g_gdf, dt_paths_join, how='inner', on='uniq_id')
    return merged
