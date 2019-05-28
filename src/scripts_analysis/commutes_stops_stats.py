#%% IMPORT MODULES FOR YKR COMMUTES PROCESSING
import pandas as pd
import geopandas as gpd
import time
import ast
from fiona.crs import from_epsg
import numpy as np
import statistics as stats
from shapely.geometry import Point
import utils.DT_API as DT_routing
import utils.DT_utils as DT_utils
import utils.geometry as geom_utils
import utils.times as times
import utils.files as files
import utils.utils as utils
import utils.commutes as commutes_utils
import utils.networks as nw

#%% read YKR work commute data
commutes = pd.read_csv('data/input/T06_tma_e_TOL2008_2016_hel.csv')
commutes['geom_home'] = commutes.apply(lambda row: Point(row['ax'], row['ay']), axis=1)
commutes['geom_work'] = commutes.apply(lambda row: Point(row['tx'], row['ty']), axis=1)
commutes['home_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in commutes['geom_home']]
commutes['work_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in commutes['geom_work']]
commutes = commutes[['axyind','txyind', 'geom_home', 'geom_work', 'home_latLon', 'work_latLon', 'yht']]
commutes.head()

#%% read grid
grid = files.get_statfi_grid()
# add centroid point geometry to grid
grid['grid_geom'] = [geometry.geoms[0] for geometry in grid['geometry']]
grid = grid.set_geometry('grid_geom')
grid['grid_centr'] = grid.apply(lambda row: geom_utils.get_point_from_xy({'x': row['x'], 'y': row['y']}), axis=1)
grid['xyind'] = [int(xyind) for xyind in grid['xyind']]
grid = grid[['xyind', 'grid_geom', 'grid_centr']]
grid.head()

#%% merge grid geometry to commutes by home & job xyind (just to make sure that the ids work for joining)
comm_homes = pd.merge(commutes, grid, how='left', left_on='axyind', right_on='xyind')
comm_workplaces = pd.merge(commutes, grid, how='left', left_on='txyind', right_on='xyind')
comm_workplaces = gpd.GeoDataFrame(comm_workplaces, geometry='geom_work', crs=from_epsg(3067))
# drop rows without ykr grid cell geometry
comm_workplaces = comm_workplaces.dropna(subset=['grid_geom'])
comm_homes = comm_homes.dropna(subset=['grid_geom'])

#%% print data stats
print('grid_cells:', len(grid.index))
print('ykr_commute rows:', len(commutes.index))
print('workplaces within area:', len(comm_workplaces.index))
print('commute origins within area:', len(comm_homes.index))
print('unique homes:', commutes['axyind'].nunique())
print('unique homes:', comm_homes['axyind'].nunique())

#%% get grid of the origin cells of the commutes
homes_grid = comm_homes.drop_duplicates(subset='axyind', keep='first')
print('homes:', len(homes_grid.index))
homes_grid = gpd.GeoDataFrame(homes_grid, geometry='grid_geom', crs=from_epsg(3067))
homes_grid = homes_grid[['axyind', 'grid_geom', 'grid_centr']]
homes_grid.head()

#%%
stats_files = 'outputs/YKR_commutes_output/home_workplaces_stats'
stops_files = 'outputs/YKR_commutes_output/home_stops'
axyfiles = commutes_utils.get_xyind_filenames(path=stops_files)
print(axyfiles[:1])

#%% read origin walks files: calculate origin commute counts that were included in origin walks analysis
axy_walks_stats = []
for idx, axy_walks_file in enumerate(axyfiles):
    # if (idx > 300):
    #     continue
    axyind = commutes_utils.get_xyind_from_filename(axy_walks_file)
    axy_stops = pd.read_csv(stops_files+'/'+axy_walks_file)
    util_sum = axy_stops['utilization'].sum()
    prob_sum = axy_stops['prob'].sum()
    axy_walks_stats.append({ 'axyind': axyind, 'util_sum': util_sum, 'prob_sum': prob_sum })

#%%
axy_walks_stats_df = pd.DataFrame(axy_walks_stats)
print(len(axy_walks_stats_df.index))

#%% calculate reference commute sums by origin from YKR commutes data
axy_commute_stats = []
grouped = comm_homes.groupby('axyind')
for key, values in grouped:
    commutes_sum = values['yht'].sum()
    axy_commute_stats.append({ 'axyind': key, 'commutes_sum': commutes_sum })
axy_commute_stats_df = pd.DataFrame(axy_commute_stats)

#%% join walks' utilization rates (grouped by origin) to YKR commutes (grouped by origin) for comparison
walks_comms_join = pd.merge(axy_commute_stats_df, axy_walks_stats_df, how='left', on='axyind')
walks_comms_join = walks_comms_join.fillna(0)
walks_comms_join.head()

#%% calculate inclusion of commuters in the routing analysis (walks from origins and their utilization rates)
walks_comms_join['comms_missing'] = walks_comms_join.apply(lambda row: row['commutes_sum'] - row['util_sum'], axis=1)
walks_comms_join['comms_inclusion'] = walks_comms_join.apply(lambda row: round((row['util_sum']/row['commutes_sum'])*100,2), axis=1)

ykr_comm_sum = walks_comms_join['commutes_sum'].sum()
incl_comm_sum = walks_comms_join['util_sum'].sum()
incl_ratio = round((incl_comm_sum/ykr_comm_sum)*100,2)
print('total number of origins:', len(walks_comms_join.index))
print('total sum of YKR commutes:', ykr_comm_sum)
print('total sum of included commutes:', incl_comm_sum)
print('commutes included ratio (%):', incl_ratio)
comms_inclusions = walks_comms_join['comms_inclusion']
# comms_inclusions = [prob for prob in comms_inclusions if prob > 0]
coms_incl_mean = stats.mean(comms_inclusions)
coms_incl_sd = np.std(comms_inclusions)
print('comms_inclusions mean:', stats.mean(comms_inclusions))
print('comms_inclusions SD:', np.std(comms_inclusions))
print('comms_inclusions CV:', coms_incl_sd/coms_incl_mean)

bad_cases = walks_comms_join.query('comms_inclusion < 50 and commutes_sum > 11')
bad_cases.head()

#%% plot all commutes vs included commutes (by origin)
fig = commutes_utils.plot_walk_stats(walks_comms_join)
fig.savefig('plots/commutes_incl.png', format='png', dpi=300)

#%% join grid geometry
walk_stats_grid = pd.merge(walks_comms_join, grid, how='left', left_on='axyind', right_on='xyind')
walk_stats_grid = gpd.GeoDataFrame(walk_stats_grid, geometry='grid_geom', crs=from_epsg(3067))

#%% 
walk_stats_grid.drop(columns=['grid_centr']).to_file('outputs/YKR_commutes_output/test.gpkg', layer='walk_stats_grid', drive='GPKG')

#%%
