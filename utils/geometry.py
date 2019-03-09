import pandas as pd
import geopandas as gpd
import requests
import json
from urllib.parse import urlparse, urlencode
from shapely.geometry import Point, LineString, MultiPolygon
from shapely.ops import split, snap, transform
from functools import partial
import pyproj
from fiona.crs import from_epsg
import glob

def get_lat_lon_from_geom(geom):
    return {'lat': geom.y, 'lon': geom.x }

def get_lat_lon_from_row(row):
    return {'lat': row['geometry'].y, 'lon': row['geometry'].x }

def get_coords_from_lat_lon(latLon):
    return [latLon['lon'], latLon['lat']]

def get_point_from_lat_lon(latLon):
    return Point(get_coords_from_lat_lon(latLon))

def project_to_etrs(geom):
    project = partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:4326'), # source coordinate system
        pyproj.Proj(init='epsg:3879')) # destination coordinate system
    geom_proj = transform(project, geom)
    return geom_proj

def project_to_wgs(geom):
    project = partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:3879'), # source coordinate system
        pyproj.Proj(init='epsg:4326')) # destination coordinate system
    geom_proj = transform(project, geom)
    return geom_proj

def get_xy_from_geom(geom):
    return { 'x': geom.x, 'y': geom.y }    

def get_coords_from_xy(xy):
    return (xy['x'], xy['y'])

def get_xy_from_lat_lon(latLon):
    point = get_point_from_lat_lon(latLon)
    point_proj = project_to_etrs(point)
    return get_xy_from_geom(point_proj)

def clip_polygons_with_polygon(clippee, clipper):
    poly = clipper
    poly_bbox = poly.bounds

    spatial_index = clippee.sindex
    sidx = list(spatial_index.intersection(poly_bbox))
    clippee_sub = clippee.iloc[sidx]

    clipped = clippee_sub.copy()
    clipped['geometry'] = clippee_sub.intersection(poly)
    clipped_final = clipped[clipped.geometry.notnull()]

    return clipped_final

def get_polygons_under_line(line_geom, polygons):
    intersects_mask = polygons.intersects(line_geom)
    polygons_under_line = polygons.loc[intersects_mask]
    return polygons_under_line

def get_inters_points(inters_line):
    inters_coords = inters_line.coords
    intersection_line = list(inters_coords)
    point_geoms = []
    for coords in intersection_line:
        point_geom = Point(coords)
        point_geoms.append(point_geom)
    return point_geoms

def get_line_polygons_inters_points(line_geom, polygons):
    polygons_under_line = get_polygons_under_line(line_geom, polygons)
    point_geoms = []
    for idx, row in polygons_under_line.iterrows():
        poly_geom = row['geometry']
        inters_geom = poly_geom.intersection(line_geom)
        if (inters_geom.geom_type == 'MultiLineString'):
            for inters_line in inters_geom:
                point_geoms += get_inters_points(inters_line)
        else:
            inters_line = inters_geom
            point_geoms += get_inters_points(inters_line)
    return gpd.GeoDataFrame(geometry=point_geoms, crs=from_epsg(3879))

def filter_duplicate_split_points(split_points):
    split_points['geom_str'] = [str(geom) for geom in split_points['geometry']]
    grouped = split_points.groupby('geom_str')
    point_geoms = []
    for key, values in grouped:
        point_geom = list(values['geometry'])[0]
        point_geoms.append(point_geom)
    return gpd.GeoDataFrame(geometry=point_geoms, crs=from_epsg(3879))

# THIS DOESN'T WORK
def split_line_at_points(line_geom, points_gdf):
    split_lines = []
    for idx, split_point in points_gdf.iterrows():
        point_geom = split_point['geometry']    
        # point_line_distance = line_geom.distance(point_geom)
        # print(point_line_distance < 1e-8)   
        snap_point_geom = line_geom.interpolate(line_geom.project(point_geom))
        print(snap_point_geom.wkt)
        # print('snap_point', list(snap_line.coords))
        split_geoms = split(line_geom, snap_point_geom)
        print(split_geoms)
        split_lines += split_geoms
    return split_lines

def get_select_line_for_noise_polygon(lines, polygon):
    lines_under_poly = []
    # points_under_polys = []
    for line in lines:
        # get center point in the middle of the line
        point_on_line = line.interpolate(0.5, normalized = True)
        # points_under_polys.append(point_on_line)
        if (point_on_line.within(polygon) or polygon.contains(point_on_line)):
            print('POINT IN POLYGON')
            lines_under_poly.append(line)
    return lines_under_poly

def split_line_with_polygons(line_geom, polygons):
    polygons_under_line = get_polygons_under_line(line_geom, polygons)
    print(polygons_under_line)
    all_split_lines = []
    for idx, row in polygons.iterrows():
        # print('idx', idx)
        poly_geom = row['geometry']
        split_line_geom = split(line_geom, poly_geom)
        # explode geometry collection to list of geoms
        split_lines = list(split_line_geom.geoms)
        # print('split_lines', split_lines)
        lines_on_poly = get_select_line_for_noise_polygon(split_lines, poly_geom)
        # print('line_on_poly', line_on_poly)
        all_split_lines += lines_on_poly
    split_lines_gdf = gpd.GeoDataFrame(geometry=all_split_lines, crs=from_epsg(3879))
    return split_lines_gdf

def better_split_line_with_polygons(line_geom, polygons):
    polygons_under_line = get_polygons_under_line(line_geom, polygons)
    multi_polygon = MultiPolygon(list(polygons_under_line['geometry']))
    split_line_geom = split(line_geom, multi_polygon)
    line_geoms = list(split_line_geom.geoms)
    lengths = [round(line_geom.length, 3) for line_geom in line_geoms]
    all_split_lines_gdf = gpd.GeoDataFrame(data={'length': lengths}, geometry=line_geoms, crs=from_epsg(3879))
    return all_split_lines_gdf

def explode_multipolygons_to_polygons(polygons_gdf):
    all_polygons = []
    db_lows = []
    db_highs = []
    for idx, row in polygons_gdf.iterrows():
        geom = row['geometry'] 
        db_low = row['db_lo'] 
        db_high = row['db_hi'] 
        if (geom.geom_type == 'MultiPolygon'):
            polygons = list(geom.geoms)
            all_polygons += polygons
            db_lows += [db_low] * len(polygons)
            db_highs += [db_high] * len(polygons)
        else:
            all_polygons.append(geom)
            db_lows.append(db_low)
            db_highs.append(db_high)
    data = {'db_lo': db_lows, 'db_hi': db_highs}
    all_polygons_gdf = gpd.GeoDataFrame(data=data, geometry=all_polygons, crs=from_epsg(3879))
    return all_polygons_gdf

def create_line_geom(point_coords):
    '''
    Function for building line geometries from list of coordinate tuples [(x,y), (x,y)].
    Returns
    -------
    <LineString>
    '''
    try:
        return LineString([point for point in point_coords])
    except:
        return

def get_line_middle_point(line_geom):
    return line_geom.interpolate(0.5, normalized = True)

def get_simple_line(row, from_col, to_col):
    return LineString([row[from_col], row[to_col]])
