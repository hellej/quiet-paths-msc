import pandas as pd
import geopandas as gpd
import utils.geometry as geo

def add_noises_to_split_lines(noise_polygons, split_lines):
    split_lines['geom_line'] = split_lines['geometry']
    split_lines['geom_point'] = [geo.get_line_middle_point(geom) for geom in split_lines['geometry']]
    split_lines['geometry'] = split_lines['geom_point']
    line_noises = gpd.sjoin(split_lines, noise_polygons, how='left', op='within')
    line_noises['geometry'] = line_noises['geom_line']
    return line_noises[['geometry', 'length', 'db_lo', 'db_hi', 'index_right']]
