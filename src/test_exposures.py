import pytest
import geopandas as gpd
import utils.geometry as geom_utils
import utils.noise_overlays as noise_utils

# read data
walk = gpd.read_file('data/input/test_walk_line.shp')
walk_proj = walk.to_crs(epsg=3879)
walk_geom = walk_proj.loc[0, 'geometry']
noise_polys = noise_utils.get_noise_polygons()

def test_split_lines():
    split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
    count_split_lines = len(split_lines.index)
    mean_split_line_len = round(split_lines['length'].mean(),1)
    assert (count_split_lines, mean_split_line_len) == (19, 32.5)

def test_add_noises_to_split_lines():
    split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
    noise_lines = noise_utils.add_noises_to_split_lines(noise_polys, split_lines)
    mean_noise =  round(noise_lines['db_lo'].mean(),1)
    min_noise = noise_lines['db_lo'].min()
    max_noise = noise_lines['db_lo'].max()
    assert (mean_noise, min_noise, max_noise) == (60.6, 45.0, 75.0)

def test_get_exposure_lens():
    split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
    noise_lines = noise_utils.add_noises_to_split_lines(noise_polys, split_lines)
    noise_dict = noise_utils.get_exposures(noise_lines)
    assert noise_dict == {45: 14.356, 50: 4.96, 55: 344.866, 60: 107.11, 65: 62.58, 70: 40.678, 75: 18.673}

def test_get_th_exposure_lens():
    split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)
    noise_lines = noise_utils.add_noises_to_split_lines(noise_polys, split_lines)
    noise_dict = noise_utils.get_exposures(noise_lines)
    th_noise_dict = noise_utils.get_th_exposures(noise_dict, [55, 60, 65, 70])
    assert th_noise_dict == {55: 573.907, 60: 229.041, 65: 121.931, 70: 59.351}

def test_get_exposure_lines():
    noise_lines = noise_utils.get_exposure_lines(walk_geom, noise_polys)
    mean_noise =  round(noise_lines['db_lo'].mean(),1)
    min_noise = noise_lines['db_lo'].min()
    max_noise = noise_lines['db_lo'].max()
    assert (mean_noise, min_noise, max_noise) == (59.5, 40.0, 75.0)
