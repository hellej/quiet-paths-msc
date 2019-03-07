import sys
import pandas as pd
import geopandas as gpd

grid_gdf = gpd.read_file('data/extents_grids.gpkg', layer='HSY_vaesto_250m_2017')

def get_grid():
    return grid_gdf

def print_progress(idx, count):
    sys.stdout.write(str(idx+1)+'/'+str(count)+' ')
    sys.stdout.flush()
