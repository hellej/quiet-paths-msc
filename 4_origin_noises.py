#%% IMPORT MODULES FOR ORIGIN NOISE AGGREGATION
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

#%% READ PATH NOISES
path_noises = gpd.read_file('outputs/path_noises.gpkg', layer='path_noises')
path_noises.head(5)

#%% GROUP PATH NOISES BY ORIGIN
grouped = path_noises.groupby(by='from_id')

ths = [60, 56, 70]
for key, values in grouped:
    print(key)

    

#%%
