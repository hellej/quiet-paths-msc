import geopandas as gpd
import osmnx as ox
from shapely.geometry import box
import utils.geometry as geom_utils
import utils.networks as nw
from fiona.crs import from_epsg

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
    graph_undir = ox.load_graphml('kumpula_u_g_n.graphml', folder='graphs')
    nw.delete_unused_edge_attrs(graph_undir)
    return graph_undir

def get_network_full():
    graph = ox.load_graphml('hel_u_g.graphml', folder='graphs')
    return graph

def get_network_full_noise():
    graph = ox.load_graphml('hel_u_g_n_s.graphml', folder='graphs')
    return graph

def get_pois():
    pois = gpd.read_file('data/input/target_locations.geojson')
    pois = pois.to_crs(from_epsg(3879))
    return pois
