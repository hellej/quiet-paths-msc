import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
from shapely.geometry import Point, MultiPolygon
from shapely.ops import split, snap
from matplotlib import pyplot as plt
import utils.geometry as geom_utils
import utils.times as times
import utils.noises as nois
import utils.dt_routing as routing

koskela_poly = gpd.read_file('data/Koskela_input/koskela.shp')
grid_gdf = gpd.read_file('data/hsy_vaesto_2017/Vaestoruudukko_2017.shp')


def filter_only_inhabitet_features(df):
    filterd_df = df.loc[df['ASUKKAITA'] > 0]
    return filterd_df

def get_koskela_centers():
    # extract center points of population grid
    points_gdf = grid_gdf.copy()
    points_gdf['geometry'] = [geom.centroid for geom in points_gdf['geometry']]
    # reproject to WGS 84
    points_gdf = points_gdf.to_crs(from_epsg(4326))
    # add latLon coordinates as dictionary column
    points_gdf['from_latLon'] = points_gdf.apply(lambda row: geom_utils.get_lat_lon_from_geom(row), axis=1)
    # select only points inside AOI (Koskela-polygon)
    point_mask = points_gdf.intersects(koskela_poly.loc[0, 'geometry'])
    points_gdf = points_gdf.loc[point_mask].reset_index(drop=True)
    # filter only features with residents
    inhabited_points_gdf = points_gdf.loc[points_gdf['ASUKKAITA'] > 0]
    return inhabited_points_gdf

def get_target_locations():
    target_locations = gpd.read_file('data/PT_Hub_analysis/routing_inputs.gpkg', layer='target_locations')
    target_locations['to_latLon'] = target_locations.apply(lambda row: geom_utils.get_lat_lon_from_geom(row), axis=1)
    return target_locations
