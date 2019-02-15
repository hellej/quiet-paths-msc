#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
from shapely.geometry import Point
import utils.geometry as geom


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
koskela_noises_proj.to_file('data/Koskela/koskela_noises.shp')

#%%  READ WALK LINE AND NOISES POLYGONS
walk = gpd.read_file('data/Koskela/test_walk_line.shp')
walk_proj = walk.to_crs(epsg=3879)
print(walk_proj.crs)
print(koskela_noises_proj.crs)
#%%
ax = koskela_noises_proj.plot()
walk_proj.plot(ax=ax)


#%% FUNCTIONS FOR SPLITTING LINES AT POLYGON BOUNDARIES
def get_polygons_under_line(line_geom, polygons):
    intersects_mask = polygons.intersects(line_geom)
    polygons_under_line = polygons.loc[intersects_mask]
    return polygons_under_line

def get_inters_coords(inters_line):
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
                point_geoms += get_inters_coords(inters_line)
        else:
            inters_line = inters_geom
            point_geoms += get_inters_coords(inters_line)
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
walk_geom = walk_proj.loc[0, 'geometry']
split_points = split_line_with_polygon(walk_geom, koskela_noises_proj)
print(split_points)
uniq_split_points = filter_duplicate_split_points(split_points)
print(uniq_split_points)

#%% PLOT LINE SPLIT POINTS
ax = koskela_noises_proj.plot()
walk_proj.plot(ax=ax)
uniq_split_points.plot(ax=ax, color='red')
#%%
uniq_split_points.to_file('data/Koskela/split_points.shp')


#%% SPLIT LINE AT SPLIT POINTS



