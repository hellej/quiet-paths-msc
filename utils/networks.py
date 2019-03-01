#%%
import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx
import json
from fiona.crs import from_epsg
from shapely.geometry import box

extents = gpd.read_file('data/PT_hub_analysis/routing_inputs.gpkg', layer='extents')

def get_koskela_poly():
    koskela_rows = extents.loc[extents['info'] == 'Koskela']
    poly = list(koskela_rows['geometry'])[0]
    return poly

def get_koskela_box():
    poly = get_koskela_poly()
    bounds = poly.bounds
    return box(*bounds)

def get_koskela_kumpula_box():
    rows = extents.loc[extents['info'] == 'kumpula_koskela_poly']
    poly = list(rows['geometry'])[0]
    bounds = poly.bounds
    return box(*bounds)
