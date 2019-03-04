#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
import utils.networks as nw
import ast
import utils.geometry as geom_utils
from shapely.geometry import Point, LineString, MultiPolygon

#%% GET BOUNDING BOX POLYGONS
koskela_box = nw.get_koskela_box()
koskela_kumpula_box = nw.get_koskela_kumpula_box()

#%% GET NETWORK
graph_proj = nw.get_walk_network(koskela_kumpula_box)

#%% GET NODES & EDGES (GDFS) FROM GRAPH
nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)
edges.head(3)

#%% EXPORT NODES & EDGES TO FILES
edges = edges[['geometry', 'u', 'v', 'length']]
edges.to_file('data/PT_hub_analysis/networks.gpkg', layer='koskela_edges')
nodes.to_file('data/PT_hub_analysis/networks.gpkg', layer='koskela_nodes')

#%% CALCULATE SHORTEST PATHS
dt_paths = gpd.read_file('data/PT_hub_analysis/walks_test.gpkg', layer='paths_g')
# list for shortest paths as dictionaries
shortest_paths = []
for idx, row in dt_paths.iterrows():
    if (idx==2000):
        break
    from_xy = ast.literal_eval(row['from_xy'])
    to_xy = ast.literal_eval(row['to_xy'])
    from_coords = geom_utils.get_coords_from_xy(from_xy)[::-1]
    to_coords = geom_utils.get_coords_from_xy(to_xy)[::-1]
    shortest_path = nw.get_shortest_path(graph_proj, from_coords, to_coords)
    if (shortest_path != None):
        s_path = {'uniq_id': row['uniq_id'], 'from_id': row['from_id'], 'path': shortest_path}
        print('Found path:', idx, ':', s_path)
        shortest_paths.append(s_path)
    else:
        print('Error in calculating shortest path for: ', row['uniq_id'])

#%% ADD EDGE GEOMETRIES TO SHORTEST PATHS
for s_path in shortest_paths:
    # route as edge geometries
    path_geom = nw.get_edge_geometries(graph_proj, s_path['path'], nodes)
    s_path['geometry'] = path_geom['multiline']
    s_path['total_length'] = path_geom['total_length']

s_paths_g_gdf = gpd.GeoDataFrame(shortest_paths, crs=from_epsg(3879))
s_paths_g_gdf.head(4)

#%% MERGE DIGITRANSIT PATH ATTRIBUTES TO SHORTEST PATHS
s_paths_g_gdf = nw.join_dt_path_attributes(s_paths_g_gdf, dt_paths)
s_paths_g_gdf['length_diff'] = s_paths_g_gdf.apply(lambda row: row['total_length'] - row['dt_total_length'], axis=1)
s_paths_g_gdf.head(4)

#%% SAVE SHORTEST PATHS TO FILE NEW
cols = ['from_id', 'to_id', 'geometry', 'uniq_id', 'total_length', 'dt_total_length', 'length_diff', 'count']
s_paths_g_gdf[cols].to_file('data/PT_hub_analysis/shortest_paths.gpkg', layer='shortest_paths_g', driver="GPKG")
s_paths_g_gdf.head(4)


#%%







#%%
# edge_test = graph_proj.edges(34815882, 3005727061)
# geom = nx.get_edge_attributes(graph_proj, 'geometry')
print(graph_proj[34815882][3005727061])

#%%
#%%

box_gdf = gpd.GeoDataFrame([{'name': 'koskela'}, {'name': 'koskela_kumpula'}], geometry=[koskela_box, koskela_kumpula_box], crs=from_epsg(4326))
box_gdf = box_gdf.to_crs(from_epsg(3879))
box_gdf.to_file('data/PT_hub_analysis/routing_inputs.gpkg', layer='bboxes')


#%%
place_name = 'Kamppi, Helsinki, Finland'
graph = ox.graph_from_place(place_name, network_type='walk')
fig, ax = ox.plot_graph(graph)

#%%
edges = ox.graph_to_gdfs(graph, nodes=False, edges=True)

#%%
print(edges.columns)
print(edges.crs)
print(edges['highway'].head())

#%%
def get_edge_type(edge):
    if (type(edge) == list):
        return edge[0]
    return edge

edges['edg_type'] = [get_edge_type(edge) for edge in edges['highway']]
print(edges['edg_type'].value_counts())

#%%
graph_proj = ox.project_graph(graph)
fig, ax = ox.plot_graph(graph_proj)

#%%
nodes_proj, edges_proj = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True)
print("Coordinate system:", edges_proj.crs)
print(edges_proj.head())

#%%
stats = ox.basic_stats(graph_proj)
print(stats)
# prettier print as json
print(json.dumps(stats))

#%%
# Get the Convex Hull of the network
convex_hull = edges_proj.unary_union.convex_hull
# Show output
convex_hull

#%%
area = convex_hull.area
print('area:', area)
# Calculate statistics with density information
stats = ox.basic_stats(graph_proj, area=area)
extended_stats = ox.extended_stats(graph_proj, ecc=True, bc=True, cc=True)
for key, value in extended_stats.items():
    stats[key] = value
pd.Series(stats)

#%%
pd.Series(stats)
stats

#%%
