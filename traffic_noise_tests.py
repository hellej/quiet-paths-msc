#%% IMPORT MODULES FOR NOISE EXTRACTION
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
from shapely.geometry import Point, MultiPolygon
from shapely.ops import split, snap
from matplotlib import pyplot as plt
import utils.noises as nois
import utils.networks as nw
import utils.geometry as geom_utils

#%% read traffic noise polygon layer and extent
noise_polys = gpd.read_file('data/data.gpkg', layer='2017_alue_01_tieliikenne_L_Aeq_paiva')
koskela_kumpula_box = nw.get_koskela_kumpula_box()

#%% clip noises to Koskela / Kumpula
koskela_noises = geom_utils.clip_polygons_with_polygon(noise_polys, koskela_kumpula_box)
koskela_noises.head(2)

#%% explode multipolygons to polygons (noises)
koskela_noise_polys = geom_utils.explode_multipolygons_to_polygons(koskela_noises)

#%%  read walk line
walk = gpd.read_file('data/input/test_walk_line.shp')
walk_proj = walk.to_crs(epsg=3879)
walk_geom = walk_proj.loc[0, 'geometry']

#%% get noise polygons under the walk line
polygons_under_line = geom_utils.get_polygons_under_line(walk_geom, koskela_noise_polys)

#%% get line split points at polygon boundaries
split_points = geom_utils.get_line_polygons_inters_points(walk_geom, koskela_noise_polys)
uniq_split_points = geom_utils.filter_duplicate_split_points(split_points)
uniq_split_points.to_file('outputs/noises.gpkg', layer='line_split_points', driver='GPKG')

#%% plot line, split points and noise polygons
ax = koskela_noise_polys.plot()
walk_proj.plot(ax=ax)
uniq_split_points.plot(ax=ax, color='red')

#%% SPLIT LINE WITH NOISE POLYGON BOUNDARIES
better_split_lines_gdf = geom_utils.better_split_line_with_polygons(walk_geom, koskela_noise_polys)
better_split_lines_gdf.to_file('outputs/noises.gpkg', layer='split_lines', driver='GPKG')

#%% JOIN NOISE LEVELS TO SPLIT LINES
line_noises = nois.add_noises_to_split_lines(koskela_noise_polys, better_split_lines_gdf)

#%%
line_noises.to_file('outputs/noises.gpkg', layer='noise_lines', driver='GPKG')

#%%
    