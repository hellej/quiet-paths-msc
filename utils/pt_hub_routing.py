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
    points_gdf['from_latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in points_gdf['geometry']]
    # select only points inside AOI (Koskela-polygon)
    point_mask = points_gdf.intersects(koskela_poly.loc[0, 'geometry'])
    points_gdf = points_gdf.loc[point_mask].reset_index(drop=True)
    # filter only features with residents
    inhabited_points_gdf = points_gdf.loc[points_gdf['ASUKKAITA'] > 0]
    return inhabited_points_gdf

def get_target_locations():
    target_locations = gpd.read_file('data/PT_hub_analysis/routing_inputs.gpkg', layer='target_locations')
    # CRS OF THIS IS WGS 84
    target_locations['to_latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in target_locations['geometry']]
    return target_locations

def group_by_origin_stop(df):
    grouped_dfs = []
    grouped = df.groupby(['from_id', 'stop_id'])
    for key, values in grouped:
        firstrow = values.iloc[0]
        count = len(values.index)
        g_gdf = gpd.GeoDataFrame([firstrow], crs=from_epsg(4326))
        g_gdf['count'] = count
        grouped_dfs.append(g_gdf)
    origin_stop_groups = pd.concat(grouped_dfs).reset_index(drop=True)
    return origin_stop_groups

def group_by_origin_target(df):
    grouped_dfs = []
    grouped = df.groupby(['from_id', 'to_id'])
    for key, values in grouped:
        firstrow = values.iloc[0]
        count = len(values.index)
        g_gdf = gpd.GeoDataFrame([firstrow], crs=from_epsg(4326))
        g_gdf['count'] = count
        grouped_dfs.append(g_gdf)
    origin_target_groups = pd.concat(grouped_dfs).reset_index(drop=True)
    return origin_target_groups

def merge_origin_target_attrs_to_walks(gdf, origins, targets):
    print('Rows before join:', len(list(gdf.index)))
    # print('walks columns', list(gdf))
    origins['from_Point'] = origins['geometry']
    targets['to_Point'] = targets['geometry']
    origins_join = origins[['INDEX', 'ASUKKAITA', 'from_latLon', 'from_Point']]
    targets_join = targets[[ 'name', 'name_en', 'to_latLon', 'to_Point']]
    origins_join = origins_join.rename(index=str, columns={'INDEX': 'from_id', 'ASUKKAITA': 'from_pop'})
    targets_join = targets_join.rename(index=str, columns={'name': 'to_id', 'name_en': 'to_name_en'})
    # print('origin columns', list(origins_join))
    # print('targets columns', list(targets_join))
    origins_joined = pd.merge(gdf, origins_join, how='inner', on='from_id')
    targets_joined = pd.merge(origins_joined, targets_join, how='inner', on='to_id')
    print('Rows after join:', len(list(targets_joined.index)))
    print('\nMerged columns', list(targets_joined))
    return targets_joined

def get_walk_target_point(row):
    if (row['to_pt_mode'] == 'none'):
        return row['to_Point']
    else:
        return row['stop_Point']
