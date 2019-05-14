#%% IMPORT MODULES FOR YKR COMMUTES PROCESSING
import pandas as pd
import geopandas as gpd
import numpy as np
import time
from fiona.crs import from_epsg
from shapely.geometry import Point
import utils.DT_API as DT_routing
import utils.DT_utils as DT_utils
import utils.geometry as geom_utils
import utils.times as times
import utils.files as files
import utils.utils as utils

#%% read YKR work commute data
commutes = pd.read_csv('data/input/T06_tma_e_12_TOL2008.csv')
commutes['axyind'] = [int(xyind) for xyind in commutes['axyind']]
commutes['txyind'] = [int(xyind) for xyind in commutes['txyind']]
commutes = commutes.loc[commutes['akunta'] == 91]
commutes = commutes.loc[commutes['sp'] == 0]
commutes['geom_home'] = commutes.apply(lambda row: Point(row['ax'], row['ay']), axis=1)
commutes['geom_work'] = commutes.apply(lambda row: Point(row['tx'], row['ty']), axis=1)
commutes['home_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in commutes['geom_home']]
commutes['work_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in commutes['geom_work']]
commutes = commutes[['txyind','axyind', 'geom_home', 'geom_work', 'home_latLon', 'work_latLon', 'yht']]
commutes.head()

#%% read grid
grid = files.get_statfi_grid()
# add centroid point geometry to grid
grid['grid_geom'] = [geometry.geoms[0] for geometry in grid['geometry']]
grid = grid.set_geometry('grid_geom')
grid['xyind'] = [int(xyind) for xyind in grid['xyind']]
grid = grid[['xyind', 'grid_geom']]
grid.head()

#%% read city districts
distrs = files.get_city_districts()
distrs['id_distr'] = distrs.apply(lambda row: str(row['kunta'] +'_'+ row['nimi']), axis=1)
distrs = distrs.to_crs(epsg=3067)
distrs['geom_distr_poly'] = [geometry.geoms[0] for geometry in distrs['geometry']]
distrs['geom_distr_point'] = [geometry.centroid for geometry in distrs['geometry']]
distrs['distr_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in distrs['geom_distr_point']]
distrs = distrs.set_geometry('geom_distr_poly')
distrs = distrs[['id_distr', 'geom_distr_poly', 'distr_latLon']]
print('districts', distrs['id_distr'].nunique())
distrs.head()

#%% merge grid geometry to commutes by home & job xyind
homes = pd.merge(commutes, grid, how='left', left_on='axyind', right_on='xyind')
workplaces = pd.merge(commutes, grid, how='left', left_on='txyind', right_on='xyind')
print(homes.head())
print(workplaces.head())

#%% drop rows without ykr grid cell geometry
workplaces = workplaces.dropna(subset=['grid_geom'])
homes = homes.dropna(subset=['grid_geom'])

#%%
print('ykr_commute rows:', len(commutes.index))
print('grid_cells:', len(grid.index))
print('workplaces', len(workplaces.index))
print('homes', len(homes.index))
print('unique homes', homes['axyind'].nunique())

#%% group workplaces by homes

def get_home_district(geom_home):
    for idx, distr in distrs.iterrows():
        if (geom_home.within(distr['geom_distr_poly'])):
            print('District of the origin', distr['id_distr'])
            return { 'id_distr': distr['id_distr'], 'geom_distr_poly': distr['geom_distr_poly'] }

def get_work_targets_gdf(geom_home, values):
    home_distr = get_home_district(geom_home)
    # turn values (workplaces) into GDF
    works = gpd.GeoDataFrame(values, geometry='geom_work', crs=from_epsg(3067))
    # convert txyind to string to be used as id
    works['txyind'] = [str(txyind) for txyind in works['txyind']]
    # add distance from home to works table
    works['home_dist'] = [round(geom_home.distance(geometry)) for geometry in works['geom_work']]
    # divide works to remote and close works based on home district and 4 km threshold 
    works['within_home_distr'] = [geom.within(home_distr['geom_distr_poly']) for geom in works['geom_work']]
    close_works = works.query('within_home_distr == True or home_dist < 3000')
    remote_works = works.query('within_home_distr == False and home_dist >= 3000')
    # join remote workplaces to distrcits by spatial intersection
    distr_works_join = gpd.sjoin(distrs, remote_works, how='left', op='intersects')
    # count works per district
    distr_works_grps = pd.pivot_table(distr_works_join, index='id_distr', values='yht', aggfunc=np.sum)
    # filter out districts without works
    distr_works_grps = distr_works_grps.loc[distr_works_grps['yht'] > 0]
    # join district geometry back to works per districts table
    distr_works = pd.merge(distr_works_grps, distrs, how='left', on='id_distr')
    distr_works['yht'] = [int(round(yht)) for yht in distr_works['yht']]
    # rename work_latLon and distr_latLon to "to_latLon"
    close_works = close_works.rename(index=str, columns={'work_latLon': 'to_latLon', 'txyind': 'id_target'})
    distr_works = distr_works.rename(index=str, columns={'distr_latLon': 'to_latLon', 'id_distr': 'id_target'})
    # filter out unused columns
    close_works = close_works[['yht', 'to_latLon', 'id_target']]
    distr_works = distr_works[['yht', 'to_latLon', 'id_target']]
    close_works['target_type'] = 'gridcell'
    distr_works['target_type'] = 'district'
    print('found', len(close_works.index), 'close work locations')
    print('found', len(distr_works.index), 'remote work locations')
    # combine dataframes
    targets = pd.concat([close_works, distr_works], ignore_index=True)

    # print stats about works inside and outside the districts
    all_works_count = works['yht'].sum()
    print('all works:', all_works_count)
    all_included_works_count = targets['yht'].sum()
    # calculate reference sum of all included works
    distr_works_join = gpd.sjoin(distrs, works, how='left', op='intersects')
    all_included_works_count_reference = distr_works_join['yht'].sum()
    print('work count match?:', 'yes' if all_included_works_count == all_included_works_count_reference else 'no')
    outside_ratio = round(((all_works_count - all_included_works_count)/all_works_count)*100)
    print('missing:', all_works_count - all_included_works_count, '-', outside_ratio, '%')
    return targets

#%%
# routing params for Digitransit API
walk_speed = '1.16666'
datetime = times.get_next_weekday_datetime(8, 30, skipdays=7)
print('Datetime for routing:', datetime)

#%% process one origin at a time
home_groups = commutes.groupby('axyind')
for key, values in home_groups:
    axyind = key
    home_stops_all = []
    if (axyind == 3873756677375 or axyind == 3866256677375):
        start_time = time.time()
        geom_home = values['geom_home'].iloc[0]
        home_latLon = values['home_latLon'].iloc[0]
        work_targets = get_work_targets_gdf(geom_home, values)
        print('Got', len(work_targets.index), 'targets')
        # filter rows of work_targets for testing
        work_targets = work_targets[:10]
        # print('WORK_TARGETS', work_targets)
        # get routes to all workplaces of the route
        for target_idx, target in work_targets.iterrows():
            # print('Target ', target_idx, 'yht:', target['yht'], target['to_latLon'])
            utils.print_progress(target_idx, len(work_targets.index), percentages=False)
            itins = DT_routing.get_route_itineraries(home_latLon, target['to_latLon'], walk_speed, datetime, itins_count=3, max_walk_distance=6000)
            if (len(itins) > 0):
                stop_dicts = DT_routing.parse_itin_attributes(itins, axyind, target['id_target'], weight=target['yht'])
                home_stops_all += stop_dicts
            else:
                print('Error in DT routing to target:', target)
        print(home_stops_all)
        # collect walks to stops/targets to GDF
        home_walks_all = pd.DataFrame(home_stops_all)
        home_walks_all['uniq_id'] = home_walks_all.apply(lambda row: DT_utils.get_walk_uniq_id(row), axis=1)
        # group similar walks and calculate realtive utilization rates of them
        home_walks_g = DT_utils.group_home_walks(home_walks_all)
        utils.print_duration(start_time, 'Origin walks got.')
        home_walks_g.drop(columns=['stop_Point']).to_csv('outputs/YKR_commutes_output/home_walks/axyind_'+str(axyind)+'.csv')

#%%
home_walks_g_gdf = gpd.GeoDataFrame(home_walks_g, geometry='stop_Point', crs=from_epsg(4326))
print('sum prob', home_walks_g_gdf['prob'].sum())
home_walks_g_gdf.plot()
home_walks_g_gdf.head(50)
# this should be exactly 100

#%%
home_walks_g_gdf.to_file('outputs/YKR_commutes_output/test.gpkg', layer='stops_test', driver='GPKG')
# walk_targets_g.to_file('outputs/DT_output_test.gpkg', layer='targets_g', driver="GPKG")

#%%
