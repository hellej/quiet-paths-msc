import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
import ast
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString, MultiLineString, box
import utils.exposures as exps
import utils.geometry as geom_utils
import utils.utils as utils

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

def delete_unused_edge_attrs(graph_proj):
    for node_from in list(graph_proj.nodes):
        nodes_to = graph_proj[node_from]
        for node_to in nodes_to.keys():
            edges = graph_proj[node_from][node_to]
            for edge_k in edges.keys():
                try:
                    del graph_proj[node_from][node_to][edge_k]['oneway'] 
                    del graph_proj[node_from][node_to][edge_k]['maxspeed'] 
                    del graph_proj[node_from][node_to][edge_k]['name']
                except Exception:
                    pass

def export_nodes_edges_to_files(graph_proj):
    nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)
    edges = edges[['geometry', 'u', 'v', 'length']]
    edges.to_file('data/networks.gpkg', layer='koskela_edges', driver="GPKG")
    nodes.to_file('data/networks.gpkg', layer='koskela_nodes', driver="GPKG")

def get_node_geom(graph_proj, node):
    node_d = graph_proj.node[node]
    return Point(node_d['x'], node_d['y'])

def get_edge_geom_from_node_pair(graph_proj, node_1, node_2):
    node_1_geom = geom_utils.get_point_from_xy(graph_proj.nodes[node_1])
    node_2_geom = geom_utils.get_point_from_xy(graph_proj.nodes[node_2])
    edge_line = LineString([node_1_geom, node_2_geom])
    return edge_line

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

def add_linking_edges_for_new_node(graph_proj, new_node, closest_point, edge):
    edge_geom = edge[0]
    node_from = edge[1]
    node_to = edge[2]
    split_lines = geom_utils.split_line_at_point(edge_geom, closest_point)
    print('Edge geom splitted to', len(split_lines), 'lines')
    # for directed graphs, swap these two:
    link1 = split_lines[1]
    link2 = split_lines[0]
    attrs = get_new_edge_attrs(graph_proj, edge)
    print('Add linking edges for new node with attrs:', attrs)
    graph_proj.add_edge(node_from, new_node, geometry=link1, length=link1.length, osmid=attrs['osmid'], highway=attrs['highway'], access='yes') #, oneway=attrs['oneway'])
    graph_proj.add_edge(new_node, node_from, geometry=link1, length=link1.length, osmid=attrs['osmid'], highway=attrs['highway'], access='yes') #, oneway=attrs['oneway'])
    graph_proj.add_edge(new_node, node_to, geometry=link2, length=link2.length, osmid=attrs['osmid'], highway=attrs['highway'], access='yes') #, oneway=attrs['oneway'])
    graph_proj.add_edge(node_to, new_node, geometry=link2, length=link2.length, osmid=attrs['osmid'], highway=attrs['highway'], access='yes') #, oneway=attrs['oneway'])

def get_shortest_edge(edges, length):
    if (len(edges) == 1):
        return edges[0]
    s_edge = edges[0]
    for edge_k in edges.keys():
        if (edges[edge_k][length] < s_edge[length]):
            s_edge = edges[edge_k]
    return s_edge

def get_edge_line_coords(graph, node_from, edge_d):
    from_point = geom_utils.get_point_from_xy(graph.nodes[node_from])
    edge_line = edge_d['geometry']
    edge_coords = edge_line.coords
    first_point = Point(edge_coords[0])
    last_point = Point(edge_coords[len(edge_coords)-1])
    if(from_point.distance(first_point) > from_point.distance(last_point)):
        return edge_coords[::-1]
    return edge_coords

def get_edge_geometries(graph_proj, path):
    edge_lengths = []
    path_coords = []
    for idx in range(0, len(path)):
        if (idx == len(path)-1):
            break
        node_1 = path[idx]
        node_2 = path[idx+1]
        edges = graph_proj[node_1][node_2]
        edge_d = get_shortest_edge(edges, 'length')
        if ('geometry' in edge_d):
            edge_lengths.append(edge_d['length'])
            edge_coords = get_edge_line_coords(graph_proj, node_1, edge_d)
        else:
            edge_line = get_edge_geom_from_node_pair(graph_proj, node_1, node_2)
            edge_lengths.append(edge_line.length)
            edge_coords = edge_line.coords
        path_coords += edge_coords

    path_line = LineString(path_coords)
    total_length = round(sum(edge_lengths),2)
    return { 'geometry': path_line, 'total_length': total_length }

def get_all_edge_dicts(graph_proj):
    edge_dicts = []
    for node_from in list(graph_proj.nodes):
        nodes_to = graph_proj[node_from]
        for node_to in nodes_to.keys():
            # all edges between node-from and node-to as dict (usually)
            edges = graph_proj[node_from][node_to]
            # usually only one edge is found between each origin-to-target-node -pair 
            # edge_k is unique identifier for edge between two nodes, integer (etc. 0 or 1) 
            for edge_k in edges.keys():
                # combine unique identifier for the edge
                edge_uvkey = (node_from, node_to, edge_k)
                # edge dict contains all edge attributes
                edge_d = edges[edge_k]
                edge_d['uvkey'] = edge_uvkey
                edge_dicts.append(edge_d)
    return edge_dicts

def get_missing_edge_geometries(edge_dict, graph_proj):
    edge_d = {}
    edge_d['uvkey'] = edge_dict['uvkey']
    if ('geometry' not in edge_dict):
        node_from = edge_dict['uvkey'][0]
        node_to = edge_dict['uvkey'][1]
        # interpolate missing geometry as straigth line between nodes
        edge_geom = get_edge_geom_from_node_pair(graph_proj, node_from, node_to)
        edge_d['geometry'] = edge_geom
    else:
        edge_d['geometry'] = edge_dict['geometry']
    edge_d['length'] = round(edge_d['geometry'].length, 3)
    return edge_d

def add_missing_edge_geometries(edge_dicts, graph_proj):
    edge_count = len(edge_dicts)
    for idx, edge_d in enumerate(edge_dicts):
        if ('geometry' not in edge_d):
            node_from = edge_d['uvkey'][0]
            node_to = edge_d['uvkey'][1]
            # interpolate missing geometry as straigth line between nodes
            edge_geom = get_edge_geom_from_node_pair(graph_proj, node_from, node_to)
            # set geometry attribute of the edge
            nx.set_edge_attributes(graph_proj, { edge_d['uvkey']: {'geometry': edge_geom} })
        # set length attribute
        nx.set_edge_attributes(graph_proj, { edge_d['uvkey']: {'length': round(edge_d['geometry'].length, 3)} })
        utils.print_progress(idx+1, edge_count, True)

def get_edge_noise_exps(edge_dict, noise_polys, graph_proj):
    edge_d = {}
    if ('noises' not in edge_d):
        noise_lines = exps.get_exposure_lines(edge_dict['geometry'], noise_polys)
        if (noise_lines.empty):
            noise_dict = {}
        else:
            noise_dict = exps.get_exposures(noise_lines)
        edge_d['uvkey'] = edge_dict['uvkey']
        edge_d['noises'] = noise_dict
        return edge_d

def get_edge_gdf(edge_dicts, cols):
    edge_gdf = gpd.GeoDataFrame(edge_dicts, crs=from_epsg(3879))
    if 'noises' in cols:
        edge_gdf['noises'] = [ast.literal_eval(noises) if type(noises) == str else noises for noises in edge_gdf['noises']]
    return edge_gdf[cols]

def update_segment_noises(edge_gdf, graph_proj):
    for edge in edge_gdf.itertuples():
        nx.set_edge_attributes(graph_proj, { getattr(edge, 'uvkey'): { 'noises': getattr(edge, 'noises')}})

def update_segment_costs(edge_gdf, graph_proj, nt):
    cost_attr = 'nc_'+str(nt)
    for edge in edge_gdf.itertuples():
        nx.set_edge_attributes(graph_proj, { getattr(edge, 'uvkey'): { cost_attr: getattr(edge, 'tot_cost')}}) 

def get_noise_cost(noises: 'noise dictionary', costs: 'cost dictionary', nt: 'noise tolerance'):
    noise_cost = 0
    for db in noises:
        if (db in costs):
            noise_cost += noises[db] * costs[db] * nt
    return round(noise_cost,2)

def get_noise_costs(edge_gdf, nt: 'noise tolerance, float: 0.0-2.0'):
    costs = { 50: 0.05, 55: 0.1, 60: 0.2, 65: 0.3, 70: 0.4, 75: 0.6 }
    edge_gdf['noise_cost'] = [get_noise_cost(noises, costs, nt) for noises in edge_gdf['noises']]
    edge_gdf['tot_cost'] = edge_gdf.apply(lambda row: round(row.length + row.noise_cost,2), axis=1)
    edge_gdf['cost_rat'] = edge_gdf.apply(lambda row: int(round((row.noise_cost/row.length)*100)), axis=1)
    return edge_gdf

def set_graph_noise_costs(graph_proj, nts: 'list of noise tolerances, float: 0.0-2.0'):
    edge_dicts = get_all_edge_dicts(graph_proj)
    edge_gdf = get_edge_gdf(edge_dicts, ['uvkey', 'geometry', 'length', 'noises'])
    for nt in nts:
        edge_n_costs = get_noise_costs(edge_gdf, nt)
        update_segment_costs(edge_n_costs, graph_proj, nt)
