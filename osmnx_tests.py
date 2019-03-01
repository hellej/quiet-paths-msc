#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
import utils.networks as nw
import ast

#%% GET BOUNDING BOX POLYGONS
koskela_box = nw.get_koskela_box()
koskela_kumpula_box = nw.get_koskela_kumpula_box()
data = {'name': ['Koskela', 'Koskela_Kumpula']}
box_gdf = gpd.GeoDataFrame(data=data, geometry=[koskela_box, koskela_kumpula_box], crs=from_epsg(4326))
box_gdf.to_file('data/PT_hub_analysis/routing_inputs.gpkg', layer='bboxes')

#%% DEFINE FILTER FOR WALKABLE ROADS
cust_filter = ox.get_osm_filter('walk')
# ["area"!~"yes"]["highway"!~"cycleway|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]
cust_filter = '["area"!~"yes"]["highway"!~"trunk_link|motor|proposed|construction|abandoned|platform|raceway"]["foot"!~"no"]["service"!~"private"]["access"!~"private"]'

#%% GET NETWORK GRAPH
#graph = ox.graph_from_polygon(koskela_box, network_type='all')
graph = ox.graph_from_polygon(koskela_box, custom_filter=cust_filter)
fig, ax = ox.plot_graph(graph)

#%% GRAPH TO PROJECTED GRAPH
graph_proj = ox.project_graph(graph, from_epsg(3879))
fig, ax = ox.plot_graph(graph_proj)

#%% GRAPH TO GDFS
nodes, edges = ox.graph_to_gdfs(graph_proj, nodes=True, edges=True, node_geometry=True, fill_edge_geometry=True)
print('NODES', list(nodes))
print('EDGES', list(edges))

#%% GDFS TO FILES NOT WORKING
# nodes.to_file('data/PT_hub_analysis/networks.gpkg', layer='koskela_nodes')
# edges['oneway'] = edges['oneway'].astype('int')
# edges.to_file('data/PT_hub_analysis/networks.gpkg', layer='koskela_edges')

#%% READ ORIGIN TARGET DATA
dt_paths = gpd.read_file('data/PT_hub_analysis/walks_test.gpkg', layer='paths_g')

for idx, row in dt_paths.iterrows():
    if (idx == 0):
        from_latLon = ast.literal_eval(row['from_latLon'])
        to_latLon = ast.literal_eval(row['to_latLon'])
        print(from_latLon['lat'])







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
