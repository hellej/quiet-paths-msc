import geopandas as gpd
import osmnx as ox

def get_update_test_walk_line():
    walk_proj = gpd.read_file('data/input/test_walk_line.shp')
    walk_proj['length'] = [int(round(geom.length)) for geom in walk_proj['geometry']]
    walk_proj['time'] = [round((geom.length/1.33)/60, 1) for geom in walk_proj['geometry']]
    # walk_proj.to_file('data/input/test_walk_line.shp')
    return walk_proj

def get_network_graph():
    graph_proj = ox.load_graphml('koskela_kumpula_geom.graphml', folder='graphs')
    return graph_proj
