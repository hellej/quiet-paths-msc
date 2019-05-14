#%% IMPORT MODULES FOR NETWORK ANALYSIS
import pandas as pd
import geopandas as gpd
import osmnx as ox
from fiona.crs import from_epsg
import ast
import utils.geometry as geom_utils
import utils.routing as rt
import utils.files as files
import utils.networks as nw

#%% READ GRAPH
graph_proj = files.get_network_kumpula_noise()

#%% GET GRAPH GDFS
edge_dicts = nw.get_all_edge_dicts(graph_proj)
edge_gdf = nw.get_edge_gdf(edge_dicts, ['uvkey', 'geometry'])
node_gdf = nw.get_node_gdf(graph_proj)
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex

#%% CALCULATE SHORTEST PATHS
dt_paths = gpd.read_file('outputs/DT_output_test.gpkg', layer='paths_g', driver="GPKG")
shortest_paths = []
for idx, row in dt_paths.iterrows():
    # if (row['from_id'] != 16932):
    #     continue
    # if (idx > 1):
    #     break
    from_xy = ast.literal_eval(row['from_xy'])
    to_xy = ast.literal_eval(row['to_xy'])

    orig_node = rt.get_nearest_node(graph, from_xy, edge_gdf, node_gdf, [], False, noise_polys)
    target_node = rt.get_nearest_node(graph, to_xy, edge_gdf, node_gdf, [], False, noise_polys)
    shortest_path = rt.get_shortest_path(graph_proj, orig_node, target_node, 'length')
    if (shortest_path != None):
        s_path = {'uniq_id': row['uniq_id'], 'from_id': row['from_id'], 'path': shortest_path}
        print('Found path no.', idx, ':', s_path)
        shortest_paths.append(s_path)
    else:
        print('Error in calculating shortest path for: ', row['uniq_id'])

#%% ADD EDGE GEOMETRIES TO SHORTEST PATHS
for s_path in shortest_paths:
    # route as edge geometries
    path_geom = nw.get_edge_geometries(graph_proj, s_path['path'])
    s_path['geometry'] = path_geom['geometry']
    s_path['total_length'] = path_geom['total_length']

s_paths_g_gdf = gpd.GeoDataFrame(shortest_paths, crs=from_epsg(3879))
s_paths_g_gdf.head(4)

#%% MERGE DIGITRANSIT PATH ATTRIBUTES TO SHORTEST PATHS
s_paths_g_gdf = rt.join_dt_path_attributes(s_paths_g_gdf, dt_paths)
s_paths_g_gdf['length_diff'] = s_paths_g_gdf.apply(lambda row: row['total_length'] - row['dt_total_length'], axis=1)
s_paths_g_gdf.head(4)

#%% SAVE SHORTEST PATHS TO FILE
cols = ['from_id', 'to_id', 'geometry', 'uniq_id', 'total_length', 'dt_total_length', 'length_diff', 'count']
s_paths_g_gdf[cols].to_file('outputs/shortest_paths.gpkg', layer='shortest_paths_undir', driver="GPKG")
s_paths_g_gdf.head(4)