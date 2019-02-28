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
targets = pt_hub_routing.get_target_locations()
targets_count = len(list(targets.index))

#%% build and run routing query for one test plan
itins = routing.get_route_itineraries(latlon_from, latLon_to, walkSpeed, maxWalkDistance, 3, datetime)
# parse walk geometries
walks = routing.parse_walk_geoms(itins, 'FROMID', 'TOID')
# print route geometry (line) of the first itinerary
walk_cols = ['from_id', 'to_id', 'to_pt_mode', 'stop_id', 'stop_desc', 'stop_p_id', 'stop_p_name', 'stop_c_id', 'stop_c_name']
walk_lines = walks[['geometry'] + walk_cols]
walk_lines.to_file('data/walk_test_output/walks_test.gpkg', layer='paths_test', driver="GPKG")

#%% import test origin points & iterate over them
origins = pt_hub_routing.get_koskela_centers()
origins_count = len(list(origins.index))
#%%
all_walks = []
for origin_idx, origin in origins.iterrows():
    if (origin_idx == 3):
        break
    utils.print_progress(origin_idx, origins_count)
    for target_idx, target in targets.iterrows():
        utils.print_progress(target_idx, targets_count)
        itins = routing.get_route_itineraries(origin['from_latLon'], target['to_latLon'], walkSpeed, maxWalkDistance, 3, datetime)
        walks = routing.parse_walk_geoms(itins, origin['INDEX'], target['name'])
        all_walks.append(walks)

#%%
walks_gdf = pd.concat(all_walks).reset_index(drop=True)
walk_cols = ['from_id', 'to_id', 'to_pt_mode', 'stop_id', 'stop_desc', 'stop_p_id', 'stop_p_name', 'stop_c_id', 'stop_c_name']

# select walks to targets (filter out walks to PT stations)
walks_to_targets = walks_gdf.loc[walks_gdf['to_pt_mode'] == 'none']
walks_to_targets_g = pt_hub_routing.group_by_origin_stop(walks_to_targets)

# select walks to PT stations (filter out walks to targets)
walks_to_stops = walks_gdf.loc[walks_gdf['to_pt_mode'] != 'none']
walks_to_stops_g = pt_hub_routing.group_by_origin_stop(walks_to_stops)

# combine walks to PT stations and walks to targets to one GeoDataFrame
all_walk_groups = pd.concat([walks_to_stops_g, walks_to_targets_g]).reset_index(drop=True) 

#%% EXPORT TO GEOPACKAGE
# save grouped walks
walk_groups = all_walk_groups.set_geometry('line_geom')
walk_groups = walk_groups[['line_geom', 'count'] + walk_cols]
walk_groups.to_file('data/walk_test_output/walks_test.gpkg', layer='walk_groups', driver="GPKG")
# save walk lines
walk_lines = walks_gdf.set_geometry('line_geom')
walk_lines = walk_lines[['line_geom'] + walk_cols]
walk_lines.to_file('data/walk_test_output/walks_test.gpkg', layer='paths', driver="GPKG")
# save walk origins
walk_origins = walks_gdf.set_geometry('first_point')
walk_origins = walk_origins[['first_point'] + walk_cols]
walk_origins.to_file('data/walk_test_output/walks_test.gpkg', layer='origins', driver="GPKG")
# save walk origins
walk_targets = walks_gdf.set_geometry('stop_point')
walk_targets = walk_targets[['stop_point'] + walk_cols]
walk_targets.to_file('data/walk_test_output/walks_test.gpkg', layer='pt_hubs', driver="GPKG")

#%%
