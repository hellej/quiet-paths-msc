#%%
import geopandas as gpd
import osmnx as ox
import networkx as nx
import time
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.quiet_paths as qp
import utils.exposures as exps
import utils.utils as utils

#%% GET GRAPH OF UNWALKABLE STREETS (TUNNELS / SERVICE ROADS ETC)
# define extent
hel_poly = files.get_hel_poly()
hel_poly_buff = hel_poly.buffer(1500)
extent = geom_utils.project_to_wgs(hel_poly_buff)
# get graph
graph_filt = nw.get_unwalkable_network(extent)
# add missing edge geoms
filt_edge_dicts = nw.get_all_edge_dicts(graph_filt)
nw.add_missing_edge_geometries(filt_edge_dicts, graph_filt)
# get edge gdf
filt_edge_gdf = nw.get_edge_gdf(graph_filt)
len(filt_edge_dicts)
print(filt_edge_gdf.head(2))
#%% add osmid as string to unwalkable (filter) edge gdfs
filt_edge_gdf['osmid_str'] = [nw.osmid_to_string(osmid) for osmid in filt_edge_gdf['osmid'] ]
filt_edge_gdf.head(3)
# save edge gdf to file
filt_edges_file = filt_edge_gdf.drop(['oneway', 'access', 'osmid', 'uvkey', 'service', 'junction', 'lanes'], axis=1)
print(filt_edges_file.head(2))
filt_edges_file.to_file('data/networks.gpkg', layer='tunnel_edges', driver="GPKG")
# export graph of unwalkable edges
ox.save_graphml(graph_filt, filename='city_tunnels.graphml', folder='graphs', gephi=False)

#%% read full graph
graph_hel = files.load_graphml('hel_u_g_n.graphml', folder='graphs', directed=True)
print('loaded graph of type:', type(graph_hel))
#%% get edge gdf
edge_gdf = nw.get_edge_gdf(graph_hel, attrs=['geometry', 'length', 'osmid'])
#%% add osmid as string to edge gdfs
edge_gdf['osmid_str'] = [nw.osmid_to_string(osmid) for osmid in edge_gdf['osmid'] ]
edge_gdf.head(3)

#%% find matching edges from full graph to remove 
print('matching', len(filt_edge_gdf), 'edges to remove')
edges_to_rm = []
for idx, filt_edge in filt_edge_gdf.iterrows():
    # if idx > 2:
    #     continue
    edges_found = edge_gdf.loc[edge_gdf['osmid_str'] == filt_edge['osmid_str']].copy()
    # print(idx, '-', filt_edge['osmid_str'])
    # print('found', len(edges_found), 'matches')
    if (len(edges_found) > 0):
        edges_found['filter_match'] = [geom_utils.lines_overlap(filt_edge['geometry'], geom) for geom in edges_found['geometry']]
        edges_match = edges_found.loc[edges_found['filter_match'] == True].copy()
        # print('of which', len(edges_match), 'matches')
        rm_edges = list(edges_match['uvkey'])
        edges_to_rm += rm_edges

print('found', len(edges_to_rm), 'to remove')

#%% remove found and matched edges
removed = 0
errors = 0
for uvkey in edges_to_rm:
    try:
        graph_hel.remove_edge(uvkey[0], uvkey[1], key=uvkey[2])
        removed += 1
    except Exception:
        errors += 1
print('removed', removed, 'edges')
print('could not remove', errors, 'edges')

#%% remove unnecessary attributes from the graph 
nw.delete_unused_edge_attrs(graph_hel)

#%% remove isolated nodes from the graph
isolate_nodes = list(nx.isolates(graph_hel))
graph_hel.remove_nodes_from(isolate_nodes)
print('removed', len(isolate_nodes), 'isolated nodes')

#%% convert graph to udirected graph
print('graph type:', type(graph_hel))
#%% if type is directed, convert to undirected
graph_hel_u = graph_hel.to_undirected()
print('graph type after conversion:', type(graph_hel_u))
#%% find subgraphs and remove them
sub_graphs = nx.connected_component_subgraphs(graph_hel_u)
# find subgraphs (nodes) to remove
rm_nodes = []
for sb in sub_graphs:
    sub_graph = sb.copy()
    print(f'subgraph has {sub_graph.number_of_nodes()} nodes')
    if (len(sub_graph.nodes) < 30):
        rm_nodes += list(sub_graph.nodes)
print('nodes to remove:', len(rm_nodes))
#%% remove subgraphs (by nodes)
for rm_node in rm_nodes:
    try:
        graph_hel_u.remove_node(rm_node)
        print('removed node', rm_node)
        removed += 1
    except Exception:
        print('removed node before', rm_node)

#%% export filtered graph to file
ox.save_graphml(graph_hel_u, filename='hel_u_g_n_f_s.graphml', folder='graphs', gephi=False)

#%% try if the saved undirected graph loads as undirected
graph_hel_test = files.get_network_full_noise(directed=False)
print('loaded graph should be undirected multigraph:', type(graph_hel_test))

#%%
