#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg

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
