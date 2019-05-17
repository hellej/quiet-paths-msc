import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
from shapely.geometry import Point
import utils.geometry as geom_utils
import utils.utils as utils

koskela_poly = gpd.read_file('data/extents_grids.gpkg', layer='koskela_poly')

def filter_only_inhabitet_features(df):
    filterd_df = df.loc[df['ASUKKAITA'] > 0]
    return filterd_df

def get_koskela_centers():
    # extract center points of population grid
    points_gdf = utils.get_grid().copy()
    points_gdf['geometry'] = [geom.centroid for geom in points_gdf['geometry']]
    # reproject grid points to WGS
    points_gdf = points_gdf.to_crs(from_epsg(4326))
    # add latLon coordinates as dictionary column
    points_gdf['from_latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in points_gdf['geometry']]
    points_gdf['from_xy'] = [geom_utils.get_xy_from_lat_lon(latLon) for latLon in points_gdf['from_latLon']]
    # reproject back to GK25
    points_gdf = points_gdf.to_crs(from_epsg(3879))
    # select only points inside AOI (Koskela-polygon)
    point_mask = points_gdf.intersects(koskela_poly.loc[0, 'geometry'])
    points_gdf = points_gdf.loc[point_mask].reset_index(drop=True)
    # filter only features with residents
    inhabited_points_gdf = points_gdf.loc[points_gdf['ASUKKAITA'] > 0]
    # reproject to ETRS
    inhabited_points_gdf = inhabited_points_gdf.to_crs(from_epsg(3879))
    return inhabited_points_gdf[:4]

def get_target_locations():
    target_locations = gpd.read_file('data/input/target_locations.geojson')
    # CRS OF THIS IS WGS 84
    target_locations['to_latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in target_locations['geometry']]
    # reproject to ETRS
    target_locations = target_locations.to_crs(from_epsg(3879))
    return target_locations[:3]

def group_home_walks(df):
    # calculate probability of taking particular walk from home location based on aggregated utilizations of walks
    grouped_dfs = []
    # group by uniq_id (which is either axyind + PT stop id or axyind + txyind)
    grouped = df.groupby('uniq_id')
    total_utilization_sum = df['utilization'].sum()
    for key, values in grouped:
        firstrow = values.iloc[0]
        g_gdf = pd.DataFrame([firstrow])
        # number of walks
        g_gdf['count'] = len(values.index)
        walk_utilization = values['utilization'].sum()
        g_gdf['utilization'] = round(walk_utilization, 2)
        g_gdf['prob'] = round((walk_utilization/total_utilization_sum)*100, 2)
        grouped_dfs.append(g_gdf)
    origin_stop_groups = pd.concat(grouped_dfs).reset_index(drop=True)
    return origin_stop_groups

def merge_origin_target_attrs_to_walks(gdf, origins, targets):
    # print('walks columns', list(gdf))
    origins['from_Point'] = origins['geometry']
    targets['to_Point'] = targets['geometry']
    origins_join = origins[['INDEX', 'ASUKKAITA', 'from_xy', 'from_Point']]
    targets_join = targets[[ 'name', 'name_en', 'to_Point']]
    origins_join = origins_join.rename(index=str, columns={'INDEX': 'from_id', 'ASUKKAITA': 'from_pop'})
    targets_join = targets_join.rename(index=str, columns={'name': 'to_id', 'name_en': 'to_name_en'})
    # print('origin columns', list(origins_join))
    # print('targets columns', list(targets_join))
    origins_joined = pd.merge(gdf, origins_join, how='inner', on='from_id')
    targets_joined = pd.merge(origins_joined, targets_join, how='inner', on='to_id')
    print('\nMerged columns', list(targets_joined))
    return targets_joined

def get_walk_uniq_id(row):
    if (row['to_pt_mode'] == 'none'):
        uniq_id = f'''{row['from_axyind']}_{row['to_id']}'''
        return uniq_id
    else:
        uniq_id = f'''{row['from_axyind']}_{row['stop_id']}'''
        return uniq_id
