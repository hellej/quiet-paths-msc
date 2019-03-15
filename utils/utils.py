import pandas as pd
import geopandas as gpd
from time import sleep
import sys

grid_gdf = gpd.read_file('data/extents_grids.gpkg', layer='HSY_vaesto_250m_2017')

def get_grid():
    return grid_gdf

def print_progress(idx, count, percentages: bool):
    if (percentages):
        sys.stdout.write('\r{0} %'.format(int(round(((idx/count)*100)))))
    else:
        sys.stdout.write('\r')
        sys.stdout.write(str(idx+1)+'/'+str(count)+' ')
    sys.stdout.flush()
    sleep(0.02)
