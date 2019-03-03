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
data = {'name': ['Koskela', 'Koskela_Kumpula']}
# box_gdf = gpd.GeoDataFrame(data=data, geometry=[koskela_box, koskela_kumpula_box], crs=from_epsg(4326))
# box_gdf.to_file('data/PT_hub_analysis/routing_inputs.gpkg', layer='bboxes')

#%% DEFINE FILTER FOR WALKABLE ROADS
cust_filter = ox.get_osm_filter('walk')
# ["area"!~"yes"]["highway"!~"cycleway|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]
cust_filter = '["area"!~"yes"]["highway"!~"trunk_link|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]'

#%% GET NETWORK GRAPH
#graph = ox.graph_from_polygon(koskela_box, network_type='all')
graph = ox.graph_from_polygon(koskela_kumpula_box, custom_filter=cust_filter)
#fig, ax = ox.plot_graph(graph)

#%% GRAPH TO PROJECTED GRAPH
graph_proj = ox.project_graph(graph, from_epsg(3879))
#fig, ax = ox.plot_graph(graph_proj)

#%% GRAPH TO GDFS
nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)
edge_cols = ['geometry', 'u', 'v', 'length']
print('NODES', list(nodes))
print('EDGES', list(edges))
edges.head()

#%% GDFS TO FILES
nodes.to_file('data/PT_hub_analysis/networks.gpkg', layer='koskela_nodes')
edges = edges[edge_cols]
edges.to_file('data/PT_hub_analysis/networks.gpkg', layer='koskela_edges')

#%% GET SHORTEST PATHS
dt_paths = gpd.read_file('data/PT_hub_analysis/walks_test.gpkg', layer='paths_g')

def get_shortest_path(from_coords, to_coords):
    orig_node = ox.get_nearest_node(graph_proj, from_coords, method='euclidean')
    target_node = ox.get_nearest_node(graph_proj, to_coords, method='euclidean')
    if (orig_node != target_node):
        s_path = nx.shortest_path(G=graph_proj, source=orig_node, target=target_node, weight='length')
        print(s_path)
        return s_path
    return None

shortest_paths = []
for idx, row in dt_paths.iterrows():
    if (idx==600):
        break
    from_xy = ast.literal_eval(row['from_xy'])
    to_xy = ast.literal_eval(row['to_xy'])
    from_coords = geom_utils.get_coords_from_xy(from_xy)[::-1]
    to_coords = geom_utils.get_coords_from_xy(to_xy)[::-1]
    s_path = get_shortest_path(from_coords, to_coords)
    if (s_path != None):
        shortest_paths.append(s_path)

#%% ADD GEOMETRY TO SHORTEST PATHS
def get_edge_geometries(path):
    path_geoms = []
    for idx, node_id in enumerate(path):
        if (idx == len(path)-1):
            break
        # print(idx)
        # print(path[idx])
        # print(path[idx+1])
        node_1 = path[idx]
        node_2 = path[idx+1]
        edge_d = graph_proj[node_1][node_2]
        try:
            geom = edge_d[0]['geometry']
            path_geoms.append(geom)
            print(edge_d)
        except KeyError:
            print('geom missing')
            nodes_1_2 = nodes.loc[[node_1, node_2]]
            route_line = LineString(list(nodes_1_2.geometry.values))
            path_geoms.append(route_line)

    print(path_geoms)
    return path_geoms

lines = []
paths = []
path_geoms = []
for path in shortest_paths:
    # route as lines between nodes
    route_nodes = nodes.loc[path]
    route_line = LineString(list(route_nodes.geometry.values))
    lines.append(route_line)
    # route as path consisting of edges
    route_edges = ox.get_route_edge_attributes(graph_proj, path) # dictionarys for eac edge, geometry missing from some of them
    # print(route_edges) 
    route_eges_gdf = gpd.GeoDataFrame(route_edges, crs=from_epsg(3879))
    paths.append(route_eges_gdf)
    # gather edge geometries manually
    path_geoms += get_edge_geometries(path)

#s_paths_gdf = pd.concat(paths).reset_index(drop=True)
#s_paths_gdf.set_geometry('geometry')
#s_paths_gdf.head()
# print(list(s_paths_gdf['geometry']))

# SAVE EDGES TO FILE
# s_paths_gdf['oneway'] = s_paths_gdf['oneway'].astype('int')
# s_paths_gdf.to_file('data/PT_hub_analysis/shortest_paths.gpkg', layer='shortest_paths', driver="GPKG")

#%% SAVE PATHS TO FILE
s_paths_gdf = gpd.GeoDataFrame(data={'geometry': path_geoms}, crs=from_epsg(3879))
s_paths_gdf['route_dist'] = [geom.length for geom in s_paths_gdf['geometry']]
s_paths_gdf.to_file('data/PT_hub_analysis/shortest_paths.gpkg', layer='shortest_paths', driver="GPKG")
#%% SAVE LINES TO FILE
s_lines_gdf = gpd.GeoDataFrame(data={'geometry': lines}, crs=from_epsg(3879))
s_lines_gdf['route_dist'] = [geom.length for geom in s_lines_gdf['geometry']]
s_lines_gdf.to_file('data/PT_hub_analysis/shortest_paths.gpkg', layer='shortest_lines', driver="GPKG")


#%%
# edge_test = graph_proj.edges(34815882, 3005727061)
# geom = nx.get_edge_attributes(graph_proj, 'geometry')
print(graph_proj[34815882][3005727061])

#%%
s_paths_gdf.to_file('data/PT_hub_analysis/shortest_paths.gpkg', layer='shortest_paths', driver="GPKG")

#%%



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
