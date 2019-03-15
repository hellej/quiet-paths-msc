#%% IMPORT MODULES FOR PT STATION/HUB ANALYSIS
import pandas as pd
import geopandas as gpd
import utils.DT_API as routing
import utils.DT_utils as DT_utils
import utils.geometry as geom_utils
import utils.times as times
import utils.utils as utils

# routing params for Digitransit API
walkSpeed = '1.33'
maxWalkDistance = 6000
datetime = times.get_next_weekday_datetime(8, 30)

# import test origin points
origins = DT_utils.get_koskela_centers()
origins_count = len(list(origins.index))
print('Origins:', origins_count)
# import test target points
targets = DT_utils.get_target_locations()
targets_count = len(list(targets.index))
print('Targets:', targets_count)

#%% RUN DIGITRANSIT ROUTING QUERIES
all_walks = []
for origin_idx, origin in origins.iterrows():
    utils.print_progress(origin_idx, origins_count, False)
    for target_idx, target in targets.iterrows():
        # utils.print_progress(target_idx, targets_count, False)
        itins = routing.get_route_itineraries(origin['from_latLon'], target['to_latLon'], walkSpeed, maxWalkDistance, 3, datetime)
        walks = routing.parse_walk_geoms(itins, origin['INDEX'], target['name'])
        all_walks.append(walks)

#%% GATHER ALL WALKS AND MERGE COLUMNS OF ORIGINS & TARGETS
walks_gdf = pd.concat(all_walks).reset_index(drop=True)
walks_gdf.plot()
walks_gdf = DT_utils.merge_origin_target_attrs_to_walks(walks_gdf, origins, targets)
walk_cols = ['from_id', 'to_id', 'path_dist', 'to_pt_mode', 'stop_id', 'stop_desc', 'stop_p_id', 'stop_p_name', 'stop_c_id', 'stop_c_name']

#%% GROUP IDENTICAL WALKS
# select & group walks to targets (filter out walks to PT stations)
walks_to_targets = walks_gdf.loc[walks_gdf['to_pt_mode'] == 'none']
walks_to_targets_g = DT_utils.group_by_origin_target(walks_to_targets)
# select & group walks to PT stations (filter out walks to targets)
walks_to_stops = walks_gdf.loc[walks_gdf['to_pt_mode'] != 'none']
walks_to_stops_g = DT_utils.group_by_origin_stop(walks_to_stops)
# combine walks to PT stations and walks to targets to one GeoDataFrame
all_walk_groups = pd.concat([walks_to_stops_g, walks_to_targets_g]).reset_index(drop=True)
# select either target Point or stop Point as last walk Point
all_walk_groups['walk_target_Point'] = all_walk_groups.apply(lambda row: DT_utils.get_walk_target_point(row), axis=1)
all_walk_groups['uniq_id'] = all_walk_groups.apply(lambda row: DT_utils.get_walk_uniq_id(row), axis=1)
all_walk_groups['line_geom'] = all_walk_groups.apply(lambda row: geom_utils.get_simple_line(row, 'from_Point', 'walk_target_Point'), axis=1)
all_walk_groups['to_xy'] = [geom_utils.get_xy_from_geom(geom) for geom in all_walk_groups['walk_target_Point']]
walk_group_cols = ['uniq_id', 'count', 'from_pop', 'from_xy', 'to_xy', 'to_name_en']

#%% EXPORT TO GEOPACKAGE
# save all walk paths
walk_paths = walks_gdf.set_geometry('path_geom')
walk_paths = walk_paths[['path_geom'] + walk_cols]
walk_paths.to_file('outputs/DT_output_test.gpkg', layer='paths_all', driver="GPKG")
# save grouped walk paths
walk_paths_g = all_walk_groups.set_geometry('path_geom')
walk_paths_g = walk_paths_g[['path_geom'] + walk_cols + walk_group_cols]
walk_paths_g.to_file('outputs/DT_output_test.gpkg', layer='paths_g', driver="GPKG")
# save grouped walk lines
walk_lines_g = all_walk_groups.set_geometry('line_geom')
walk_lines_g = walk_lines_g[['line_geom'] + walk_cols + walk_group_cols]
walk_lines_g.to_file('outputs/DT_output_test.gpkg', layer='lines_g', driver="GPKG")
# save grouped walk origins
walk_origins_g = all_walk_groups.set_geometry('from_Point')
walk_origins_g = walk_origins_g[['from_Point'] + walk_cols + walk_group_cols]
walk_origins_g.to_file('outputs/DT_output_test.gpkg', layer='origins_g', driver="GPKG")
# save grouped walk targets
walk_targets_g = all_walk_groups.set_geometry('walk_target_Point')
walk_targets_g = walk_targets_g[['walk_target_Point'] + walk_cols + walk_group_cols]
walk_targets_g.to_file('outputs/DT_output_test.gpkg', layer='targets_g', driver="GPKG")

#%%
