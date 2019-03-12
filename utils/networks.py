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
    # define filter for acquiring walkable street network
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

def get_new_node_id(graph_proj):
    graph_nodes = graph_proj.nodes
    return  max(graph_nodes)+1

def get_new_node_attrs(graph_proj, point):
    attrs = {'id': get_new_node_id(graph_proj), 'highway': '', 'osmid': '', 'ref': ''}
    wgs_point = geom_utils.project_to_wgs(point)
    geom_attrs = {**geom_utils.get_xy_from_geom(point), **geom_utils.get_lat_lon_from_geom(wgs_point)}
    return { **attrs, **geom_attrs }

def add_new_node(graph_proj, point):
    attrs = get_new_node_attrs(graph_proj, point)
    print('Add new node with attrs:', attrs)
    graph_proj.add_node(attrs['id'], highway='', osmid='', ref='', x=attrs['x'], y=attrs['y'], lon=attrs['lon'], lat=attrs['lat'])
    return attrs['id']

def get_new_edge_attrs(graph_proj, old_edge):
    attrs = graph_proj[old_edge[1]][old_edge[2]][0]
    return attrs

def add_link_edges_for_new_node(graph_proj, new_node, closest_point, edge_o):
    edge_geom = edge_o[0]
    node_from = edge_o[1]
    node_to = edge_o[2]
    split_lines = geom_utils.split_line_at_point(edge_geom, closest_point)
    print('Edge geom splitted to', len(split_lines), 'lines')
    link1 = split_lines[0]
    link2 = split_lines[1]
    attrs = get_new_edge_attrs(graph_proj, edge_o)
    print('Add linking edges for new node with attrs:', attrs)
    graph_proj.add_edge(node_from, new_node, geometry=link1, length=link1.length, osmid=attrs['osmid'], highway=attrs['highway'], access='yes', oneway=attrs['oneway'])
    graph_proj.add_edge(new_node, node_from, geometry=link1, length=link1.length, osmid=attrs['osmid'], highway=attrs['highway'], access='yes', oneway=attrs['oneway'])
    graph_proj.add_edge(new_node, node_to, geometry=link2, length=link2.length, osmid=attrs['osmid'], highway=attrs['highway'], access='yes', oneway=attrs['oneway'])
    graph_proj.add_edge(node_to, new_node, geometry=link2, length=link2.length, osmid=attrs['osmid'], highway=attrs['highway'], access='yes', oneway=attrs['oneway'])

def get_or_create_nearest_node(graph_proj, coords):
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
        new_node = add_new_node(graph_proj, closest_line_point)
        add_link_edges_for_new_node(graph_proj, new_node, closest_line_point, edge)
        return new_node
    else:
        print('Nearby node exists')
        return nearest_node

def get_shortest_path(graph_proj, from_coords, to_coords):
    orig_node = get_or_create_nearest_node(graph_proj, from_coords)
    target_node = get_or_create_nearest_node(graph_proj, to_coords)
    print('Nearest origin node for routing:', orig_node)
    print('Nearest target node for routing:', target_node)
    if (orig_node != target_node):
        s_path = nx.shortest_path(G=graph_proj, source=orig_node, target=target_node, weight='length')
        return s_path
    else:
        return None

def get_edge_geometries(graph_proj, path, nodes):
    edge_geoms = []
    edge_lengths = []
    for idx in range(0, len(path)):
        if (idx == len(path)-1):
            break
        node_1 = path[idx]
        node_2 = path[idx+1]
        edge_d = graph_proj[node_1][node_2][0]
        print('Path edge no.', idx, ':', edge_d)
        try:
            edge_geoms.append(edge_d['geometry'])
            edge_lengths.append(edge_d['length'])
        except KeyError:
            print('Create missing edge geom')
            nodes_1_2 = nodes.loc[[node_1, node_2]]
            route_line = LineString(list(nodes_1_2.geometry.values))
            edge_geoms.append(route_line)
            edge_lengths.append(route_line.length)

    multi_line = MultiLineString(edge_geoms)
    total_length = round(sum(edge_lengths),2)
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
