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
import utils.times as times
import utils.noises as nois
import utils.utils as utils
import utils.dt_routing as routing
import utils.ykr as ykr
import sys
# route params for testing
latlon_from = {'lat': 60.168992, 'lon': 24.932366 }
latLon_to = {'lat': 60.175294, 'lon': 24.684855 }
walkSpeed = '1.33'
maxWalkDistance = 6000
datetime = times.get_next_weekday_datetime(8, 30)

#%% build and run routing query for one test plan
itins = routing.get_route_itineraries(latlon_from, latLon_to, walkSpeed, maxWalkDistance, 3, datetime)
# parse geometry from Google Encoded Polyline Algorithm Format
itins_geom = routing.parse_itin_geom(itins)
#%% print route geometry (line) of the first itinerary
itin = itins_geom[0]
print(itin)
itin['line_geom']

#%% import test origin points & iterate over them
koskela_centers = ykr.get_koskela_centers()

row_count = len(list(koskela_centers.index))
for idx, row in koskela_centers.iterrows():
    if (idx == 3):
        break
    fromLatLon = utils.getLatLonFromGeom(row)
    sys.stdout.write(str(idx+1)+'/'+str(row_count)+' ')
    print(fromLatLon)
    sys.stdout.flush()

#%%
