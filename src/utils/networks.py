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

def get_unwalkable_network(extent_polygon):
    cust_filter_no_tunnels = '["area"!~"yes"]["highway"!~"trunk_link|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]["highway"~"service"]["layer"~"-1|-2|-3|-4|-5|-6|-7"]'
    # GET NETWORK GRAPH
    graph = ox.graph_from_polygon(extent_polygon, custom_filter=cust_filter_no_tunnels, retain_all=True)
    # GRAPH TO PROJECTED GRAPH
    graph_proj = ox.project_graph(graph, from_epsg(3879))
    #fig, ax = ox.plot_graph(graph_proj)
    return ox.get_undirected(graph_proj)

def osmid_to_string(osmid):
    if isinstance(osmid, list):
        osm_str = ''
        for osm_id in osmid:
            osm_str += str(osm_id)+'_'
    else:
        osm_str = str(osmid)
    return osm_str

def delete_unused_edge_attrs(graph_proj):
    save_attrs = ['uvkey', 'length', 'geometry', 'noises']
    for node_from in list(graph_proj.nodes):
        nodes_to = graph_proj[node_from]
        for node_to in nodes_to.keys():
            edges = graph_proj[node_from][node_to]
            for edge_k in edges.keys():
                edge = graph_proj[node_from][node_to][edge_k]
                edge_attrs = list(edge.keys())
                for attr in edge_attrs:
                    if (attr not in save_attrs):
                        del edge[attr]

def export_nodes_edges_to_files(graph_proj):
    nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)
    edges = edges[['geometry', 'u', 'v', 'length']]
    edges.to_file('data/networks.gpkg', layer='koskela_edges', driver="GPKG")
    nodes.to_file('data/networks.gpkg', layer='koskela_nodes', driver="GPKG")

def get_node_gdf(graph_proj):
    node_gdf = ox.graph_to_gdfs(graph_proj, nodes=True, edges=False, node_geometry=True, fill_edge_geometry=False)
    return node_gdf[['geometry']]

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
    new_node_id = get_new_node_id(graph_proj)
    wgs_point = geom_utils.project_to_wgs(point)
    geom_attrs = {**geom_utils.get_xy_from_geom(point), **geom_utils.get_lat_lon_from_geom(wgs_point)}
    return { 'id': new_node_id, **geom_attrs }

def add_new_node(graph_proj, point, logging=True):
    attrs = get_new_node_attrs(graph_proj, point)
    if (logging == True):
        print('add new node:', attrs['id'])
    graph_proj.add_node(attrs['id'], ref='', x=attrs['x'], y=attrs['y'], lon=attrs['lon'], lat=attrs['lat'])
    return attrs['id']

def estimate_link_noises(link_geom, edge_geom, edge_noises):
    link_noises = {}
    link_len_ratio = link_geom.length / edge_geom.length
    for db in edge_noises.keys():
        link_noises[db] = round(edge_noises[db] * link_len_ratio, 3)
    return link_noises

def get_edge_noise_cost_attrs(nts, edge_d, link_geom, b_add_noises: bool, noise_polys):
    cost_attrs = {}
    if (b_add_noises == True):
        # get link noise exposures accurately if b_add_noises = True
        cost_attrs['noises'] = exps.get_noise_dict_for_geom(link_geom, noise_polys)
    else:
        # estimate link noises based on link length - edge length -ratio and edge noises
        cost_attrs['noises'] = estimate_link_noises(link_geom, edge_d['geometry'], edge_d['noises'])
    for nt in nts:
        cost = get_noise_cost_from_noises_dict(link_geom, cost_attrs['noises'], nt)
        cost_attrs['nc_'+str(nt)] = cost
    return cost_attrs

def add_linking_edges_for_new_node(graph_proj, new_node, closest_point, edge, nts, b_add_noises, noise_polys=None, logging=True):
    edge_geom = edge['geometry']
    split_lines = geom_utils.split_line_at_point(edge_geom, closest_point)
    node_from = edge['uvkey'][0]
    node_to = edge['uvkey'][1]
    node_from_p = get_node_geom(graph_proj, node_from)
    node_to_p = get_node_geom(graph_proj, node_to)
    edge_first_p = Point(edge_geom.coords[0])
    if(edge_first_p.distance(node_from_p) < edge_first_p.distance(node_to_p)):
        link1 = split_lines[0]
        link2 = split_lines[1]
    else:
        link1 = split_lines[1]
        link2 = split_lines[0]
    if (logging == True):
        print('add linking edges between:', node_from, new_node, node_to)
    graph_proj.add_edge(node_from, new_node, geometry=link1, length=round(link1.length, 3), uvkey=(node_from, new_node, 0))
    graph_proj.add_edge(new_node, node_from, geometry=link1, length=round(link1.length, 3), uvkey=(new_node, node_from, 0))
    graph_proj.add_edge(new_node, node_to, geometry=link2, length=round(link2.length, 3), uvkey=(new_node, node_to, 0))
    graph_proj.add_edge(node_to, new_node, geometry=link2, length=round(link2.length, 3), uvkey=(node_to, new_node, 0))
    # set noise cost attributes for new edges if they will be used in quiet path routing
    if (len(nts) > 0):
        link1_noise_costs = get_edge_noise_cost_attrs(nts, edge, link1, b_add_noises, noise_polys)
        link2_noise_costs = get_edge_noise_cost_attrs(nts, edge, link2, b_add_noises, noise_polys)
        attrs = {
            (node_from, new_node, 0): link1_noise_costs,
            (new_node, node_from, 0): link1_noise_costs,
            (new_node, node_to, 0): link2_noise_costs,
            (node_to, new_node, 0): link2_noise_costs
        }
        nx.set_edge_attributes(graph_proj, attrs)
    return {'node_from': node_from, 'new_node': new_node, 'node_to': node_to}

def remove_linking_edges_of_new_node(graph, new_node_d):
    if ('link_edges' in new_node_d.keys()):
        link_edges = new_node_d['link_edges']
        graph.remove_edge(link_edges['node_from'], link_edges['new_node'])
        graph.remove_edge(link_edges['new_node'], link_edges['node_from'])
        graph.remove_edge(link_edges['new_node'], link_edges['node_to'])
        graph.remove_edge(link_edges['node_to'], link_edges['new_node'])

def get_shortest_edge(edges, weight):
    if (len(edges) == 1):
        return next(iter(edges.values()))
    s_edge = next(iter(edges.values()))
    for edge_k in edges.keys():
        if (weight in edges[edge_k].keys() and weight in s_edge.keys()):
            if (edges[edge_k][weight] < s_edge[weight]):
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

def get_edge_geoms_attrs(graph_proj, path, weight, geoms: bool, noises: bool):
    result = {}
    edge_lengths = []
    path_coords = []
    edge_exps = []
    for idx in range(0, len(path)):
        if (idx == len(path)-1):
            break
        node_1 = path[idx]
        node_2 = path[idx+1]
        edges = graph_proj[node_1][node_2]
        edge_d = get_shortest_edge(edges, weight)
        if geoms:
            if ('geometry' in edge_d):
                edge_lengths.append(edge_d['length'])
                edge_coords = get_edge_line_coords(graph_proj, node_1, edge_d)
            else:
                edge_line = get_edge_geom_from_node_pair(graph_proj, node_1, node_2)
                edge_lengths.append(edge_line.length)
                edge_coords = edge_line.coords
            path_coords += edge_coords
        if noises:
            if ('noises' in edge_d):
                edge_exps.append(edge_d['noises'])
    if geoms:
        path_line = LineString(path_coords)
        total_length = round(sum(edge_lengths),2)
        result['geometry'] = path_line
        result['total_length'] = total_length
    if noises:
        result['noises'] = exps.aggregate_exposures(edge_exps)
    return result

def get_all_edge_dicts(graph_proj, attrs=None):
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
                ed = { 'uvkey': edge_uvkey }
                if (isinstance(attrs, list)):
                    for attr in attrs:
                        ed[attr] = edges[edge_k][attr]
                else:
                    ed = edges[edge_k]
                    ed['uvkey'] = edge_uvkey
                edge_dicts.append(ed)
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
        utils.print_progress(idx+1, edge_count, percentages=True)

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

def get_edge_gdf(graph, attrs=None):
    edge_dicts = get_all_edge_dicts(graph, attrs=attrs)
    return gpd.GeoDataFrame(edge_dicts, crs=from_epsg(3879))

def update_edge_noises(edge_gdf, graph_proj):
    for edge in edge_gdf.itertuples():
        nx.set_edge_attributes(graph_proj, { getattr(edge, 'uvkey'): { 'noises': getattr(edge, 'noises')}})

def update_edge_costs(edge_gdf, graph_proj, nt):
    cost_attr = 'nc_'+str(nt)
    for edge in edge_gdf.itertuples():
        nx.set_edge_attributes(graph_proj, { getattr(edge, 'uvkey'): { cost_attr: getattr(edge, 'tot_cost')}}) 

def get_noise_cost(noises: 'noise dictionary', costs: 'cost dictionary', nt: 'noise tolerance'):
    noise_cost = 0
    for db in noises:
        if (db in costs):
            noise_cost += noises[db] * costs[db] * nt
    return round(noise_cost,2)

# def add_noise_costs_to_edge_gdf(edge_nc_gdf, nt: 'noise tolerance, float: 0.0-2.0'):
    # edge_nc_gdf['noise_cost'] = [get_noise_cost(noises, costs, nt) for noises in edge_nc_gdf['noises']]
    # edge_nc_gdf['cost_rat'] = edge_nc_gdf.apply(lambda row: int(round((row.noise_cost/row.length)*100)), axis=1)

def get_noise_cost_from_noises_dict(geom, noises_dict, nt):
    costs = { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }
    noise_cost = get_noise_cost(noises_dict, costs, nt)
    tot_cost = round(geom.length + noise_cost, 2)
    return tot_cost

def set_graph_noise_costs(edge_gdf, graph, nts: 'list of noise tolerances, float: 0.0-2.0'):
    costs = { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }
    edge_nc_gdf = edge_gdf.copy()
    for nt in nts:
        edge_nc_gdf['noise_cost'] = [get_noise_cost(noises, costs, nt) for noises in edge_nc_gdf['noises']]
        edge_nc_gdf['tot_cost'] = edge_nc_gdf.apply(lambda row: round(row['length'] + row['noise_cost'], 2), axis=1)
        update_edge_costs(edge_nc_gdf, graph, nt)
