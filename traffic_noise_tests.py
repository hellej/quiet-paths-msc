#%%
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
import utils.noises as nois

#%% read traffic noise polygon layer
noise_polys = gpd.read_file('data/pks_liikennemelu/pks_tieliikenne_LAeq_paiva.shp')
koskela_poly = gpd.read_file('data/Koskela_input/koskela.shp')

#%% reproject Koskela polygon
koskela_poly_proj = koskela_poly.to_crs(crs=noise_polys.crs)

#%% clip noises to Koskela
koskela_noises = geom.clip_polygons_with_polygon(noise_polys, koskela_poly_proj)

#%% 
koskela_noises_proj = koskela_noises.to_crs(epsg=3879)
koskela_noise_polys = geom.explode_multipolygons_to_polygons(koskela_noises_proj)
koskela_noises_proj.to_file('data/Koskela_output/koskela_noises.shp')

#%%  read walk line
walk = gpd.read_file('data/Koskela_input/test_walk_line.shp')
walk_proj = walk.to_crs(epsg=3879)
walk_geom = walk_proj.loc[0, 'geometry']

#%% get noise polygons under the walk line
polygons_under_line = geom.get_polygons_under_line(walk_geom, koskela_noise_polys)
polygons_under_line.to_file('data/Koskela_output/walk_noises.shp')

#%% get line split points at polygon boundaries
split_points = geom.get_line_polygons_inters_points(walk_geom, koskela_noise_polys)
uniq_split_points = geom.filter_duplicate_split_points(split_points)
uniq_split_points.to_file('data/Koskela_output/split_points.shp')

#%% plot line, split points and noise polygons
ax = koskela_noises_proj.plot()
walk_proj.plot(ax=ax)
uniq_split_points.plot(ax=ax, color='red')

#%%
# split_lines_gdf = geom.split_line_with_polygons(walk_geom, koskela_noise_polys)
# split_lines_gdf.to_file('data/Koskela_output/noise_walks.shp')

#%% 
better_split_lines_gdf = geom.better_split_line_with_polygons(walk_geom, koskela_noise_polys)
better_split_lines_gdf.to_file('data/Koskela_output/better_split_lines_gdf.shp')

#%%
line_noises = nois.add_noises_to_split_lines(koskela_noise_polys, better_split_lines_gdf)

#%%
print(line_noises.head(5))
line_noises.to_file('data/Koskela_output/line_noises.shp')

#%%
