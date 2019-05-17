import pandas as pd
import geopandas as gpd
import time
from os import listdir
from os.path import isfile, join
from fiona.crs import from_epsg
import numpy as np
import utils.utils as utils
import utils.DT_API as DT_routing
import utils.DT_utils as DT_utils


def get_axyind_filenames(path='outputs/YKR_commutes_output/home_stops'):
    files = [f for f in listdir(path) if isfile(join(path, f))]
    files_filtered = [f for f in files if 'DS_Store' not in f]
    return files_filtered

def parse_axyinds_from_filenames(filenames):
    axyinds = []
    for filename in filenames:
        name = filename.replace('axyind_', '')
        name = name.replace('.csv', '')
        xyind = int(name)
        axyinds.append(xyind)
    return axyinds

def get_processed_home_walks():
    filenames = get_axyind_filenames()
    return parse_axyinds_from_filenames(filenames)

def get_home_district(geom_home, districts):
    for idx, distr in districts.iterrows():
        if (geom_home.within(distr['geom_distr_poly'])):
            # print('District of the origin', distr['id_distr'])
            return { 'id_distr': distr['id_distr'], 'geom_distr_poly': distr['geom_distr_poly'] }

def get_work_targets_gdf(geom_home, districts, axyind=None, work_rows=None, logging=True, stats_path='outputs/YKR_commutes_output/home_workplaces_stats/'):
    home_distr = get_home_district(geom_home, districts)
    # turn work_rows (workplaces) into GDF
    works = gpd.GeoDataFrame(work_rows, geometry='geom_work', crs=from_epsg(3067))
    # convert txyind to string to be used as id
    works['txyind'] = [str(txyind) for txyind in works['txyind']]
    # add distance from home to works table
    works['home_dist'] = [round(geom_home.distance(geometry)) for geometry in works['geom_work']]
    # divide works to remote and close works based on home district and 4 km threshold 
    works['within_home_distr'] = [geom.within(home_distr['geom_distr_poly']) for geom in works['geom_work']]
    close_works = works.query('within_home_distr == True or home_dist < 3000')
    remote_works = works.query('within_home_distr == False and home_dist >= 3000')
    # join remote workplaces to distrcits by spatial intersection
    distr_works_join = gpd.sjoin(districts, remote_works, how='left', op='intersects')
    # count works per district
    distr_works_grps = pd.pivot_table(distr_works_join, index='id_distr', values='yht', aggfunc=np.sum)
    # filter out districts without works
    distr_works_grps = distr_works_grps.loc[distr_works_grps['yht'] > 0]
    # join district geometry back to works per districts table
    distr_works = pd.merge(distr_works_grps, districts, how='left', on='id_distr')
    distr_works['yht'] = [int(round(yht)) for yht in distr_works['yht']]
    # rename work_latLon and distr_latLon to "to_latLon"
    close_works = close_works.rename(index=str, columns={'work_latLon': 'to_latLon', 'txyind': 'id_target'})
    distr_works = distr_works.rename(index=str, columns={'distr_latLon': 'to_latLon', 'id_distr': 'id_target'})
    # filter out unused columns
    close_works = close_works[['yht', 'to_latLon', 'id_target']]
    distr_works = distr_works[['yht', 'to_latLon', 'id_target']]
    close_works['target_type'] = 'gridcell'
    distr_works['target_type'] = 'district'
    if (logging == True):
        print('found', len(close_works.index), 'close work locations')
        print('found', len(distr_works.index), 'remote work locations')
    # combine dataframes
    targets = pd.concat([close_works, distr_works], ignore_index=True)

    # print stats about works inside and outside the districts
    total_works_count = works['yht'].sum()
    if (logging == True):
        print('all works:', total_works_count)
    all_included_works_count = targets['yht'].sum()
    distr_works_join = gpd.sjoin(districts, works, how='left', op='intersects')
    all_included_works_count_reference = distr_works_join['yht'].sum()
    work_count_match = 'yes' if all_included_works_count == all_included_works_count_reference  else 'no'
    missing_works = total_works_count - all_included_works_count
    outside_ratio = round(((missing_works)/total_works_count)*100)
    if (logging == True):
        print('work count match?:', work_count_match)
    if (logging == True):
        print('missing:', missing_works, '-', outside_ratio, '%')
    home_work_stats = pd.DataFrame([{'axyind': axyind, 'total_dests_count': len(targets.index), 'close_dests_count': len(close_works.index), 'distr_dests_count': len(distr_works.index), 'total_works_count': total_works_count, 'dest_works_count': all_included_works_count, 'missing_works_count': missing_works, 'outside_ratio': outside_ratio, 'work_count_match': work_count_match }])
    home_work_stats[['axyind', 'total_dests_count', 'close_dests_count', 'distr_dests_count', 'total_works_count', 'dest_works_count', 'missing_works_count', 'outside_ratio', 'work_count_match']].to_csv(stats_path+'axyind_'+str(axyind)+'.csv')
    return targets

def get_home_work_walks(axyind=None, work_rows=None, districts=None, datetime=None, walk_speed=None, subset=True, logging=True):
    home_stops_all = []
    start_time = time.time()
    geom_home = work_rows['geom_home'].iloc[0]
    home_latLon = work_rows['home_latLon'].iloc[0]
    work_targets = get_work_targets_gdf(geom_home, districts, axyind=axyind, work_rows=work_rows, logging=logging)
    if (logging == True):
        print('Got', len(work_targets.index), 'targets')
    # filter rows of work_targets for testing
    work_targets = work_targets[:6] if subset == True else work_targets
    # print('WORK_TARGETS', work_targets)
    # get routes to all workplaces of the route
    for target_idx, target in work_targets.iterrows():
        # print('Target ', target_idx, 'yht:', target['yht'], target['to_latLon'])
        # utils.print_progress(target_idx, len(work_targets.index), percentages=False)
        itins = DT_routing.get_route_itineraries(home_latLon, target['to_latLon'], walk_speed, datetime, itins_count=3, max_walk_distance=6000)
        if (len(itins) > 0):
            stop_dicts = DT_routing.parse_itin_attributes(itins, axyind, target['id_target'], weight=target['yht'])
            home_stops_all += stop_dicts
        else:
            print('Error in DT routing to target:', target)
    # print(home_stops_all)
    # collect walks to stops/targets to GDF
    home_walks_all = pd.DataFrame(home_stops_all)
    home_walks_all['uniq_id'] = home_walks_all.apply(lambda row: DT_utils.get_walk_uniq_id(row), axis=1)
    # group similar walks and calculate realtive utilization rates of them
    home_walks_g = DT_utils.group_home_walks(home_walks_all)
    if (logging == True):
        utils.print_duration(start_time, 'Home walks got.')
    return home_walks_g
