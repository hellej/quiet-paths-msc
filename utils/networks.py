#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
from shapely.geometry import LineString, MultiLineString, box

extents = gpd.read_file('data/PT_hub_analysis/routing_inputs.gpkg', layer='extents')

def get_koskela_poly():
    koskela_rows = extents.loc[extents['info'] == 'Koskela']
    poly = list(koskela_rows['geometry'])[0]
    return poly

def get_koskela_box():
    poly = get_koskela_poly()
    bounds = poly.bounds
    return box(*bounds)

def get_koskela_kumpula_box():
    rows = extents.loc[extents['info'] == 'kumpula_koskela_poly']
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

def get_shortest_path(graph_proj, from_coords, to_coords):
    orig_node = ox.get_nearest_node(graph_proj, from_coords, method='euclidean')
    target_node = ox.get_nearest_node(graph_proj, to_coords, method='euclidean')
    if (orig_node != target_node):
        s_path = nx.shortest_path(G=graph_proj, source=orig_node, target=target_node, weight='length')
        print(s_path)
        return s_path
    return None

def get_edge_geometries(graph_proj, path, nodes):
    path_geoms = []
    lengths = []
    for idx, node_id in enumerate(path):
        if (idx == len(path)-1):
            break
        node_1 = path[idx]
        node_2 = path[idx+1]
        edge_d = graph_proj[node_1][node_2][0]
        print(edge_d)
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
    return {'multiline': multi_line, 'total_length': total_length}


def join_dt_path_attributes(s_paths_g_gdf, dt_paths):
    dt_paths_join = dt_paths.rename(index=str, columns={'path_dist': 'dt_total_length'})
    dt_paths_join = dt_paths_join[['dt_total_length', 'uniq_id', 'to_id', 'count']]
    merged = pd.merge(s_paths_g_gdf, dt_paths_join, how='inner', on='uniq_id')
    return merged
