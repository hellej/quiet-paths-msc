#%%
import geopandas as gpd
import osmnx as ox
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
graph_hel = ox.load_graphml('hel_u_g_n.graphml', folder='graphs')
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

#%% export filtered graph to file
ox.save_graphml(graph_hel, filename='hel_u_g_n_f_s.graphml', folder='graphs', gephi=False)

#%%
