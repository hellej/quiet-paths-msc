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
import utils.noise_overlays as noise_utils
import utils.networks as nw
import utils.geometry as geom_utils

#%% read traffic noise polygon layer and extent
noise_polys = gpd.read_file('data/data.gpkg', layer='2017_alue_01_tieliikenne_L_Aeq_paiva')
koskela_kumpula_box = nw.get_koskela_kumpula_box()

#%% clip noises to Koskela / Kumpula
noise_polys_clip = geom_utils.clip_polygons_with_polygon(noise_polys, koskela_kumpula_box)
noise_polys_clip.head(2)

#%% explode multipolygons to polygons (noises)
koskela_noise_polys = geom_utils.explode_multipolygons_to_polygons(noise_polys_clip)

#%%  read walk line
walk = gpd.read_file('data/input/test_walk_line.shp')
walk_proj = walk.to_crs(epsg=3879)
walk_geom = walk_proj.loc[0, 'geometry']

#%% get line split points at polygon boundaries
split_points = geom_utils.get_line_polygons_inters_points(walk_geom, koskela_noise_polys)
uniq_split_points = geom_utils.filter_duplicate_split_points(split_points)
# uniq_split_points.to_file('outputs/noises.gpkg', layer='line_split_points', driver='GPKG')

#%% SPLIT LINE WITH NOISE POLYGON BOUNDARIES
split_lines = geom_utils.better_split_line_with_polygons(walk_geom, koskela_noise_polys)
# split_lines.to_file('outputs/noises.gpkg', layer='split_lines', driver='GPKG')

#%% JOIN NOISE LEVELS TO SPLIT LINES
line_noises = noise_utils.add_noises_to_split_lines(koskela_noise_polys, split_lines)
line_noises = line_noises.fillna(39)

#%% EXPORT NOISE LINES TO FILE
line_noises.to_file('outputs/path_noises.gpkg', layer='line_noises', driver='GPKG')

#%% AGGREGATE CUMULATIVE EXPOSURES
cum_noises = noise_utils.aggregate_cumulative_esposures(line_noises, [60, 65, 70], 'test_line_1')
cum_noises

#%% PLOT CUMULATIVE EXPOSURES
noise_utils.plot_cumulative_exposures(cum_noises)

#%% READ ALL SHORTEST PATHS
shortest_paths = gpd.read_file('outputs/shortest_paths.gpkg', layer='shortest_paths_g')

#%% EXTRACT NOISES FOR ALL SHORTEST PATHS
cum_noises = []
line_noises = []
for idx, shortest_path in shortest_paths.iterrows():
    if (idx < 0):
        break
    line_geom = shortest_path['geometry']
    line_id = shortest_path['uniq_id']
    noises_dict = noise_utils.get_cumulative_noise_exposures(line_geom, koskela_noise_polys, line_id)
    cum_noises.append(noises_dict['cum_noises'])
    line_noises.append(noises_dict['line_noises'])

#%% EXPORT NOISE LINES & PATHS TO FILES
line_noises_gdf = pd.concat(line_noises).reset_index(drop=True)
line_noises_gdf.to_file('outputs/path_noises.gpkg', layer='line_noises', driver='GPKG')

cum_noises_gdf = pd.concat(cum_noises).reset_index(drop=True)
path_noises = pd.merge(shortest_paths, cum_noises_gdf, how='inner', left_on='uniq_id', right_on='id')
path_noises.to_file('outputs/path_noises.gpkg', layer='path_noises', driver='GPKG')

#%%
line_noises_gdf.head(5)
path_noises.head(5)

#%%
