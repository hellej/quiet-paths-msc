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
import utils.geometry as geom_utils
import utils.times as times
import utils.utils as utils
import utils.noises as nois
import utils.dt_routing as routing
import utils.pt_hub_routing as pt_hub_routing
import sys

# route params for testing
latlon_from = {'lat': 60.168992, 'lon': 24.932366 }
latLon_to = {'lat': 60.175294, 'lon': 24.684855 }
latLon_steissi = { 'lat': 60.170435, 'lon': 24.940673 }
walkSpeed = '1.33'
maxWalkDistance = 6000
datetime = times.get_next_weekday_datetime(8, 30)
target_locations = pt_hub_routing.get_target_locations()

#%% build and run routing query for one test plan
itins = routing.get_route_itineraries(latlon_from, latLon_to, walkSpeed, maxWalkDistance, 3, datetime)

#%% parse geometry from Google Encoded Polyline Algorithm Format
from_id = 'FROMID'
to_id = 'TOID'
walks = routing.parse_walk_geoms(itins, from_id, to_id)
# print route geometry (line) of the first itinerary
print(walks)
walk_cols = ['from_id', 'to_id', 'to_pt_mode', 'stop_id', 'stop_desc', 'stop_p_id', 'stop_p_name', 'stop_c_id', 'stop_c_name']
walks_file = walks[['geometry'] + walk_cols]
walks_file.to_file('data/walk_test_output/walks_test.gpkg', layer='asdf', driver="GPKG")

#%% import test origin points & iterate over them
origins = pt_hub_routing.get_koskela_centers()
origins_count = len(list(origins.index))
#%%
from_walks = []
for idx, row in origins.iterrows():
    if (idx == 3):
        break
    itins = routing.get_route_itineraries(row['from_latLon'], latLon_steissi, walkSpeed, maxWalkDistance, 3, datetime)
    to_id = 'steissi'
    walks = routing.parse_walk_geoms(itins, row['INDEX'], to_id)
    from_walks.append(walks)
    utils.print_progress(idx, origins_count)

#%%
walk_cols = ['from_id', 'to_id', 'to_pt_mode', 'stop_id', 'stop_desc', 'stop_p_id', 'stop_p_name', 'stop_c_id', 'stop_c_name']
walk_gdf = pd.concat(from_walks).reset_index(drop=True)
walks_file = walks[['geometry'] + walk_cols]
walks_file.to_file('data/walk_test_output/walks_test.gpkg', layer='koskela_walks', driver="GPKG")

#%%
