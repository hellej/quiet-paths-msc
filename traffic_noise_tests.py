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
noise_polys = gpd.read_file('data/pks_liikennemelu/pks_tieliikenne_LAeq_paiva.shp')
koskela_poly = gpd.read_file('data/koskela/koskela.shp')

#%% reproject Koskela polygon
koskela_poly_proj = koskela_poly.to_crs(crs=noise_polys.crs)

#%% clip noises to Koskela
koskela_noises = geom.clip_polygons_with_polygon(noise_polys, koskela_poly_proj)

#%% 
koskela_noises_proj = koskela_noises.to_crs(epsg=3879)
koskela_noise_polys = geom.explode_multipolygons_to_polygons(koskela_noises_proj)
print('polygons count', len(koskela_noises_proj.index))
print('polygons exploded count', len(koskela_noise_polys.index))
# koskela_noises_proj.to_file('data/Koskela/koskela_noises.shp')

#%%  read walk line
walk = gpd.read_file('data/Koskela/test_walk_line.shp')
walk_proj = walk.to_crs(epsg=3879)
walk_geom = walk_proj.loc[0, 'geometry']
#%% plot noise polygons and walk
ax = koskela_noises_proj.plot()
walk_proj.plot(ax=ax)

#%% get noise polygons under the walk line
polygons_under_line = geom.get_polygons_under_line(walk_geom, koskela_noise_polys)
polygons_under_line.to_file('data/Koskela/walk_noises.shp')

#%% get line split points at polygon boundaries
split_points = geom.get_line_polygons_inters_points(walk_geom, koskela_noise_polys)
uniq_split_points = geom.filter_duplicate_split_points(split_points)
print('split_points count', len(split_points.index))
print('uniq_split_points count', len(uniq_split_points.index))
uniq_split_points.to_file('data/Koskela/split_points.shp')

#%% plot line, split points and noise polygons
ax = koskela_noises_proj.plot()
walk_proj.plot(ax=ax)
uniq_split_points.plot(ax=ax, color='red')

#%%
split_lines_gdf = geom.split_line_with_polygons(walk_geom, koskela_noise_polys)
print(split_lines_gdf)

#%%
split_lines_gdf.to_file('data/Koskela/noise_walks.shp')
#%%
