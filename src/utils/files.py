import geopandas as gpd
import osmnx as ox
from shapely.geometry import box
import utils.geometry as geom_utils
from fiona.crs import from_epsg

bboxes = gpd.read_file('data/extents_grids.gpkg', layer='bboxes')

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

def get_update_test_walk_line():
    walk_proj = gpd.read_file('data/input/test_walk_line.shp')
    walk_proj['length'] = [int(round(geom.length)) for geom in walk_proj['geometry']]
    walk_proj['time'] = [round((geom.length/1.33)/60, 1) for geom in walk_proj['geometry']]
    # walk_proj.to_file('data/input/test_walk_line.shp')
    return walk_proj

def get_network_graph():
    graph_proj = ox.load_graphml('kumpula_g.graphml', folder='graphs')
    return graph_proj

def get_undirected_network_graph():
    # graph_proj = ox.load_graphml('kumpula_g.graphml', folder='graphs')
    # graph_undir = ox.get_undirected(graph_proj)
    graph_undir = ox.load_graphml('kumpula_u_g.graphml', folder='graphs')
    return graph_undir

def get_noise_network_graph():
    graph_undir = ox.load_graphml('kumpula_u_g_n.graphml', folder='graphs')
    return graph_undir

def get_pois():
    pois = gpd.read_file('data/input/target_locations.geojson')
    pois = pois.to_crs(from_epsg(3879))
    return pois
