#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
from shapely.geometry import Point
from shapely.ops import split, snap
import utils.geometry as geom
from matplotlib import pyplot as plt

#%% read traffic noise polygon layer
noise_polys = gpd.read_file('/Users/joose/Documents/gradu-pocs/data/pks_liikennemelu/pks_tieliikenne_LAeq_paiva.shp')
koskela_poly = gpd.read_file('data/koskela/koskela.shp')

#%% check data
print(noise_polys.crs)
print(koskela_poly.crs)
#%% reproject Koskela polygon
koskela_poly_proj = koskela_poly.to_crs(crs=noise_polys.crs)

#%% clip noises to Koskela
koskela_noises = geom.clip_polygon_with_polygon(noise_polys, koskela_poly_proj)
koskela_noises.plot()

#%% 
koskela_noises_proj = koskela_noises.to_crs(epsg=3879)
# koskela_noises_proj.to_file('data/Koskela/koskela_noises.shp')

#%%  READ WALK LINE AND NOISES POLYGONS
walk = gpd.read_file('data/Koskela/test_walk_line.shp')
walk_proj = walk.to_crs(epsg=3879)
#%%
ax = koskela_noises_proj.plot()
walk_proj.plot(ax=ax)
walk_geom = walk_proj.loc[0, 'geometry']


#%% explode multi polygons to polygons 
koskela_noise_polys = []
min_noises = []
max_noises = []
for idx, row in koskela_noises_proj.iterrows():
    geom = row['geometry'] 
    if (geom.geom_type == 'MultiPolygon'):
        polygons = list(geom.geoms)
        koskela_noise_polys += polygons
    else:
        koskela_noise_polys.append(geom)
koskela_noise_polygons = gpd.GeoDataFrame(geometry=koskela_noise_polys, crs=from_epsg(3879))
print(koskela_noise_polygons)

#%% FUNCTIONS FOR SPLITTING LINES AT POLYGON BOUNDARIES
def get_polygons_under_line(line_geom, polygons):
    intersects_mask = polygons.intersects(line_geom)
    polygons_under_line = polygons.loc[intersects_mask]
    return polygons_under_line

#%%
polygons_under_line = get_polygons_under_line(walk_geom, koskela_noise_polygons)
print(polygons_under_line)
polygons_under_line.to_file('data/Koskela/walk_noises.shp')

#%%
def get_inters_points(inters_line):
    inters_coords = inters_line.coords
    intersection_line = list(inters_coords)
    point_geoms = []
    for coords in intersection_line:
        point_geom = Point(coords)
        point_geoms.append(point_geom)
    return point_geoms

def split_line_with_polygon(line_geom, polygons):
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

#%% GET LINE SPLIT POINTS AT POLYGON BOUNDARIES
print('koskela_noises', koskela_noises_proj)
walk_geom = walk_proj.loc[0, 'geometry']
split_points = split_line_with_polygon(walk_geom, koskela_noise_polygons)
print(split_points)
uniq_split_points = filter_duplicate_split_points(split_points)
print(uniq_split_points)

#%% PLOT LINE SPLIT POINTS
ax = koskela_noises_proj.plot()
walk_proj.plot(ax=ax)
uniq_split_points.plot(ax=ax, color='red')
print(walk_proj.crs == uniq_split_points.crs)

#%%
# uniq_split_points.to_file('data/Koskela/split_points.shp')


#%% SPLIT LINE AT SPLIT POINTS
for idx, split_point in uniq_split_points.iterrows():
    point_geom = split_point['geometry']    
    point_line_distance = walk_geom.distance(point_geom)
    print(point_line_distance < 1e-8)   

    snap_point_geom = walk_geom.interpolate(walk_geom.project(point_geom))
    print(snap_point_geom.wkt)
    # print('snap_point', list(snap_line.coords))

    split_lines = split(walk_geom, snap_point_geom)
    print(split_lines)


#%%
def get_select_line_for_noise_polygon(lines, polygon):
    lines_under_poly = []
    points_under_polys = []
    for line in lines:
        # point_on_line = line.representative_point()
        point_on_line = line.interpolate(0.5, normalized = True)
        points_under_polys.append(point_on_line)
        if (point_on_line.within(polygon) or polygon.contains(point_on_line)):
            print('POINT IN POLYGON')
            lines_under_poly.append(line)
    return lines_under_poly

#%%
def split_line_with_polygon_with_split(line_geom, polygons):
    polygons_under_line = get_polygons_under_line(line_geom, polygons)
    print(polygons_under_line)
    all_split_lines = []
    for idx, row in polygons.iterrows():
        # print('idx', idx)
        poly_geom = row['geometry']
        split_line_geom = split(walk_geom, poly_geom)
        # explode geometry collection to list of geoms
        split_lines = list(split_line_geom.geoms)
        # print('split_lines', split_lines)
        lines_on_poly = get_select_line_for_noise_polygon(split_lines, poly_geom)
        # print('line_on_poly', line_on_poly)
        all_split_lines += lines_on_poly
    return all_split_lines

#%%
split_lines = split_line_with_polygon_with_split(walk_geom, koskela_noises_proj)
split_lines_gdf = gpd.GeoDataFrame(geometry=split_lines, crs=from_epsg(3879))
print(split_lines_gdf)

#%%
split_lines_gdf.to_file('data/Koskela/noise_walks.shp')
#%%
