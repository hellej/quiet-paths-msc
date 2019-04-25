import geopandas as gpd
import osmnx as ox
from shapely import wkt
from shapely.geometry import box
import utils.geometry as geom_utils
import utils.networks as nw
from fiona.crs import from_epsg
import os
import networkx as nx
import ast

bboxes = gpd.read_file('data/extents_grids.gpkg', layer='bboxes')
hel = gpd.read_file('data/extents_grids.gpkg', layer='hel')

def get_noise_polygons():
    noise_data = gpd.read_file('data/data.gpkg', layer='2017_alue_01_tieliikenne_L_Aeq_paiva')
    noise_polys = geom_utils.explode_multipolygons_to_polygons(noise_data)
    return noise_polys

def get_koskela_poly():
    koskela_rows = bboxes.loc[bboxes['name'] == 'koskela']
    poly = list(koskela_rows['geometry'])[0]
    return poly

def get_koskela_box():
    poly = get_koskela_poly()
    bounds = poly.bounds
    return box(*bounds)

def get_koskela_kumpula_box():
    rows = bboxes.loc[bboxes['name'] == 'koskela_kumpula']
    poly = list(rows['geometry'])[0]
    bounds = poly.bounds
    return box(*bounds)

def get_hel_poly():
    poly = list(hel['geometry'])[0]
    return poly

def get_update_test_walk_line():
    walk_proj = gpd.read_file('data/input/test_walk_line.shp')
    walk_proj['length'] = [int(round(geom.length)) for geom in walk_proj['geometry']]
    walk_proj['time'] = [round((geom.length/1.33)/60, 1) for geom in walk_proj['geometry']]
    # walk_proj.to_file('data/input/test_walk_line.shp')
    return walk_proj

def get_network_kumpula_dir():
    graph_proj = ox.load_graphml('kumpula_g.graphml', folder='graphs')
    return graph_proj

def get_network_kumpula():
    graph_undir = ox.load_graphml('kumpula_u_g.graphml', folder='graphs')
    return graph_undir

def get_network_kumpula_noise():
    graph_undir = load_graphml('kumpula_u_g_n.graphml', folder='graphs')
    nw.delete_unused_edge_attrs(graph_undir)
    return graph_undir

def get_network_full():
    graph = ox.load_graphml('hel_u_g.graphml', folder='graphs')
    return graph

def get_network_full_noise():
    graph = load_graphml('hel_u_g_n_s.graphml', folder='graphs')
    return graph

def get_pois():
    pois = gpd.read_file('data/input/target_locations.geojson')
    pois = pois.to_crs(from_epsg(3879))
    return pois

def load_graphml(filename, folder=None, node_type=int):

    # read the graph from disk
    path = os.path.join(folder, filename)
    G = nx.MultiDiGraph(nx.read_graphml(path, node_type=node_type))

    # convert graph crs attribute from saved string to correct dict data type
    G.graph['crs'] = ast.literal_eval(G.graph['crs'])

    if 'streets_per_node' in G.graph:
        G.graph['streets_per_node'] = ast.literal_eval(G.graph['streets_per_node'])

    # convert numeric node tags from string to numeric data types
    for _, data in G.nodes(data=True):
        data['osmid'] = node_type(data['osmid'])
        data['x'] = float(data['x'])
        data['y'] = float(data['y'])

    # convert numeric, bool, and list node tags from string to correct data types
    for _, _, data in G.edges(data=True, keys=False):

        # first parse oneway to bool and length to float - they should always
        # have only 1 value each
        data['noises'] = ast.literal_eval(data['noises'])
        data['length'] = float(data['length'])

        # these attributes might have a single value, or a list if edge's
        # topology was simplified
        for attr in ['highway', 'name', 'bridge', 'tunnel', 'lanes', 'ref', 'maxspeed', 'service', 'access', 'area', 'landuse', 'width', 'est_width']:
            # if this edge has this attribute, and it starts with '[' and ends
            # with ']', then it's a list to be parsed
            if attr in data and data[attr][0] == '[' and data[attr][-1] == ']':
                # try to convert the string list to a list type, else leave as
                # single-value string (and leave as string if error)
                try:
                    data[attr] = ast.literal_eval(data[attr])
                except:
                    pass

        # osmid might have a single value or a list
        if 'osmid' in data:
            if data['osmid'][0] == '[' and data['osmid'][-1] == ']':
                # if it's a list, eval the list then convert each element to node_type
                data['osmid'] = [node_type(i) for i in ast.literal_eval(data['osmid'])]
            else:
                # if it's not a list, convert it to the node_type
                data['osmid'] = node_type(data['osmid'])

        # if geometry attribute exists, load the string as well-known text to
        # shapely LineString
        if 'geometry' in data:
            data['geometry'] = wkt.loads(data['geometry'])

    # remove node_default and edge_default metadata keys if they exist
    if 'node_default' in G.graph:
        del G.graph['node_default']
    if 'edge_default' in G.graph:
        del G.graph['edge_default']
    
    return G
