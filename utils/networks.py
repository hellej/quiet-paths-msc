#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString, MultiLineString, box
import utils.geometry as geom_utils

bboxes = gpd.read_file('data/extents_grids.gpkg', layer='bboxes')

def get_koskela_poly():
    koskela_rows = bboxes.loc[bboxes['name'] == 'koskela']
    poly = list(koskela_rows['geometry'])[0]
    return poly

def get_koskela_box():
    poly = get_koskela_poly()
    bounds = poly.bounds
    return box(*bounds)

def get_koskela_kumpula_box():
    rows = bboxes.loc[bboxes['name'] == 'koskela_kumpula']
    poly = list(rows['geometry'])[0]
    bounds = poly.bounds
    return box(*bounds)

def get_walk_network(extent_polygon):
    # DEFINE FILTER FOR WALKABLE ROADS
    cust_filter = ox.get_osm_filter('walk')
    # ["area"!~"yes"]["highway"!~"cycleway|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]
    cust_filter = '["area"!~"yes"]["highway"!~"trunk_link|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]'
    # GET NETWORK GRAPH
    graph = ox.graph_from_polygon(extent_polygon, custom_filter=cust_filter)
    # GRAPH TO PROJECTED GRAPH
    graph_proj = ox.project_graph(graph, from_epsg(3879))
    #fig, ax = ox.plot_graph(graph_proj)
    return graph_proj

def get_node_geom(graph_proj, node):
    node_d = graph_proj.node[node]
    return Point(node_d['x'], node_d['y'])

def get_edge_geom_from_node_pair(nodes, node_from, node_to):
    nodes_from_to = nodes.loc[[node_from, node_to]]
    return LineString(list(nodes_from_to.geometry.values))

def get_nearest_edges_nearest_node(graph_proj, yx):
    edge = ox.get_nearest_edge(graph_proj, yx)
    node1 = get_node_geom(graph_proj, edge[1])
    node2 = get_node_geom(graph_proj, edge[2])
    point = Point(yx[1], yx[0])
    if (point.distance(node1) > point.distance(node2)):
        return edge[2]
    else:
        return edge[1]

def print_edge_info(graph_proj, edge):
    node_from = edge[1]
    node_to = edge[2]
    print('OLD_EDGE_FROM:', node_from)
    print('OLD_EDGE_TO:', node_to)
    print('OLD_EDGE_ATTRS:', graph_proj[node_from][node_to])
    print('OLD_EDGE_NODE_FROM_ATTRS:', graph_proj.nodes[node_from])

def get_new_node_id(graph_proj):
    graph_nodes = graph_proj.nodes
    return  max(graph_nodes)+1

def get_new_node_attrs(graph_proj, point):
    new_node_id = get_new_node_id(graph_proj)
    print('NEW NODE ID', new_node_id)
    attrs = {'id': new_node_id, 'highway': '', 'osmid': '', 'ref': ''}
    wgs_point = geom_utils.project_to_wgs(point)
    geom_attrs = {**geom_utils.get_xy_from_geom(point), **geom_utils.get_lat_lon_from_geom(wgs_point)}
    new_node_attrs = {**attrs, **geom_attrs}
    return new_node_attrs

def add_new_node(graph_proj, point):
    attrs = get_new_node_attrs(graph_proj, point)
    print('NEW NODE ATTRS', attrs)
    graph_proj.add_node(attrs['id'], highway='', osmid='', ref='', x=attrs['x'], y=attrs['y'], lon=attrs['lon'], lat=attrs['lat'])
    return attrs['id']

def get_or_create_nearest_node(graph_proj, coords):
    point = Point(coords)
    nearest_edge = ox.get_nearest_edge(graph_proj, coords[::-1])
    # print_edge_info(graph_proj, nearest_edge)
    edge_geom = nearest_edge[0]
    origin_edge_distance = point.distance(edge_geom)
    print('ORIGIN_EDGE_DISTANCE:', origin_edge_distance)
    nearest_node = ox.get_nearest_node(graph_proj, coords[::-1], method='euclidean')
    nearest_node_geom = geom_utils.get_point_from_xy(graph_proj.nodes[nearest_node])
    orig_node_distance = point.distance(nearest_node_geom)
    print('ORIGIN_NEAREST_NODE_DISTANCE:', orig_node_distance)

    if (orig_node_distance - origin_edge_distance > 5):
        print('proceed to adding new node')
        closest_point = geom_utils.get_closest_point_on_line(edge_geom, point)
        new_node = add_new_node(graph_proj, closest_point)
        return new_node
    else:
        print('nearest node is near enough')
        return nearest_node

    # print('edge:', nearest_edge)
    # print('point:', point)
    # print('edge len:', edge_geom.length)
    # print('point - edge -dist:', point.distance(edge_geom))
    projected = edge_geom.project(point)
    closest_point = edge_geom.interpolate(projected)
    # print('point point dist:', point.distance(closest_point))
    # print('closest_point:', closest_point)
    # print('dist:', edge_geom.distance(closest_point))
    # print('small dist:', edge_geom.distance(closest_point) < 1e-8)
    split_result = geom_utils.split_line_at_point(edge_geom, closest_point)
    # print('split_result:', split_result)
    for line in split_result:
        print('split_line length:', line.length)

def get_shortest_path(graph_proj, from_coords, to_coords):
    # get closest node or create new node if closest is far
    new_orig_node = get_or_create_nearest_node(graph_proj, from_coords)

    orig_node = ox.get_nearest_node(graph_proj, from_coords[::-1], method='euclidean')
    target_node = ox.get_nearest_node(graph_proj, to_coords[::-1], method='euclidean')
    print('NEAREST NODE FOUND FOR ROUTING:', orig_node)
    print('NEAREST NODE FOUND FOR ROUTING WITH NEW CODE:', new_orig_node)

    return
    if (orig_node != target_node):
        s_path = nx.shortest_path(G=graph_proj, source=orig_node, target=target_node, weight='length')
        return s_path
    return None

def get_edge_geometries(graph_proj, path, nodes):
    path_geoms = []
    lengths = []
    for idx in range(0, len(path)):
        print(idx)
        if (idx == len(path)-1):
            break
        node_1 = path[idx]
        node_2 = path[idx+1]
        edge_d = graph_proj[node_1][node_2][0]
        print('path edge', idx, ':', edge_d)
        try:
            path_geoms.append(edge_d['geometry'])
            lengths.append(edge_d['length'])
        except KeyError:
            print('geom missing')
            nodes_1_2 = nodes.loc[[node_1, node_2]]
            route_line = LineString(list(nodes_1_2.geometry.values))
            path_geoms.append(route_line)
            lengths.append(route_line.length)

    multi_line = MultiLineString(path_geoms)
    total_length = round(sum(lengths),2)
    return { 'multiline': multi_line, 'total_length': total_length }

def join_dt_path_attributes(s_paths_g_gdf, dt_paths):
    dt_paths_join = dt_paths.rename(index=str, columns={'path_dist': 'dt_total_length'})
    dt_paths_join = dt_paths_join[['dt_total_length', 'uniq_id', 'to_id', 'count']]
    merged = pd.merge(s_paths_g_gdf, dt_paths_join, how='inner', on='uniq_id')
    return merged

def print_edges_from_node_attributes(node_from, graph_proj):
    # list of nodes to which node_from is connected to
    nodes_to = graph_proj[node_from]
    for node_to in nodes_to.keys():
        # all edges between node-from and node-to as dict (usually)
        edges = graph_proj[node_from][node_to]
        # usually only one edge is found between each origin-to-target-node -pair 
        # edge_k is unique identifier for edge between two nodes, integer (etc. 0 or 1) 
        for edge_k in edges.keys():
            print('edge', edge_k, ':', graph_proj[node_from][node_to][edge_k])
