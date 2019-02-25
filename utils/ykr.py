import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
from shapely.geometry import Point, MultiPolygon
from shapely.ops import split, snap
from matplotlib import pyplot as plt
import utils.geometry as geom
import utils.times as times
import utils.noises as nois
import utils.dt_routing as routing


koskela_poly = gpd.read_file('data/Koskela_input/koskela.shp')
pop_poly = gpd.read_file('data/hsy_vaesto_2017/Vaestoruudukko_2017.shp')

def get_koskela_centers():
    # extract center points of population grid
    pop_point = pop_poly.copy()
    pop_point['geometry'] = [geom.centroid for geom in pop_point['geometry']]
    pop_point = pop_point.to_crs(from_epsg(4326))
    # select only points inside AOI (Koskela-polygon)
    point_mask = pop_point.intersects(koskela_poly.loc[0, 'geometry'])
    pop_koskela = pop_point.loc[point_mask].reset_index(drop=True)
    return pop_koskela

