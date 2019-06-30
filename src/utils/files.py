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

def get_city_districts():
    return gpd.read_file('data/extents_grids.gpkg', layer='HSY_kaupunginosat_19')

def get_statfi_grid():
    return gpd.read_file('data/extents_grids.gpkg', layer='r250_hel_tyoalue')

def get_koskela_poly():
    koskela_rows = bboxes.loc[bboxes['name'] == 'koskela']
    poly = list(koskela_rows['geometry'])[0]
    return poly

def get_koskela_box():
    # return polygon of Koskela area in epsg:3879
    poly = get_koskela_poly()
    bounds = poly.bounds
    return box(*bounds)

def get_koskela_kumpula_box():
    # return polygon of Kumpula & Koskela area in epsg:3879
    rows = bboxes.loc[bboxes['name'] == 'koskela_kumpula']
    poly = list(rows['geometry'])[0]
    bounds = geom_utils.project_to_wgs(poly).bounds
    return box(*bounds)

def get_hel_poly():
    # return polygon of Helsinki in epsg:3879
    poly = list(hel['geometry'])[0]
    return poly

def get_update_test_walk_line():
    walk_proj = gpd.read_file('data/test/test_walk_line.shp')
    walk_proj['length'] = [int(round(geom.length)) for geom in walk_proj['geometry']]
    walk_proj['time'] = [round((geom.length/1.33)/60, 1) for geom in walk_proj['geometry']]
    # walk_proj.to_file('data/test/test_walk_line.shp')
    return walk_proj

def get_network_kumpula_dir():
    graph_proj = ox.load_graphml('kumpula_g.graphml', folder='graphs')
    return graph_proj

def get_network_kumpula():
    graph_undir = ox.load_graphml('kumpula_u_g.graphml', folder='graphs')
    return graph_undir

def get_network_kumpula_noise(version=1):
    if (version == 1):
        return load_graphml('kumpula_u_g_n_s.graphml', folder='graphs', directed=False)
    if (version == 2):
        return load_graphml('kumpula-v2_u_g_n2_f_s.graphml', folder='graphs', directed=False)
    return None

def get_network_full():
    graph = ox.load_graphml('hel_u_g.graphml', folder='graphs')
    return graph

def get_network_full_noise(directed=True):
    return load_graphml('hel_u_g_n_f_s.graphml', folder='graphs', directed=directed)

def get_network_full_noise_v2(directed=True):
    return load_graphml('hel_u_g_n2_f_s.graphml', folder='graphs', directed=directed)

def get_pois():
    pois = gpd.read_file('data/test/target_locations.geojson')
    pois = pois.to_crs(from_epsg(3879))
    return pois

def load_graphml(filename, folder=None, node_type=int, directed=None):
    # read the graph from disk
    path = os.path.join(folder, filename)

    # read as directed or undirected graph
    if (directed == True):
        print('loading directed graph')
        G = nx.MultiDiGraph(nx.read_graphml(path, node_type=node_type))
    else:
        print('loading undirected graph')
        G = nx.MultiGraph(nx.read_graphml(path, node_type=node_type))

    # convert graph crs attribute from saved string to correct dict data type
    G.graph['crs'] = ast.literal_eval(G.graph['crs'])

    if 'streets_per_node' in G.graph:
        G.graph['streets_per_node'] = ast.literal_eval(G.graph['streets_per_node'])

    # convert numeric node tags from string to numeric data types
    for _, data in G.nodes(data=True):
        data['x'] = float(data['x'])
        data['y'] = float(data['y'])

    # convert numeric, bool, and list node tags from string to correct data types
    for _, _, data in G.edges(data=True, keys=False):

        # first parse oneway to bool and length to float - they should always
        # have only 1 value each
        data['length'] = float(data['length'])
        data['noises'] = ast.literal_eval(data['noises'])

        # if geometry attribute exists, load the string as well-known text to
        # shapely LineString
        data['geometry'] = wkt.loads(data['geometry'])

    # remove node_default and edge_default metadata keys if they exist
    if 'node_default' in G.graph:
        del G.graph['node_default']
    if 'edge_default' in G.graph:
        del G.graph['edge_default']
    
    return G
