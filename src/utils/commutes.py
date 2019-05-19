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
import utils.geometry as geom_utils
import utils.times as times
import utils.routing as rt
import utils.networks as nw

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

def get_workplaces_distr_join(workplaces, districts):
    # districts['distr_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in districts['geom_distr_point']]
    workplaces = workplaces.reset_index(drop=True)
    
    print('count workplaces:', len(workplaces.index))
    # join district id to workplaces based on point polygon intersection
    workplaces_distr_join = gpd.sjoin(workplaces, districts, how='left', op='intersects')
    # drop workplaces that are outside the districts
    workplaces_distr_join = workplaces_distr_join.dropna(subset=['id_distr'])
    print('count workplaces:', len(workplaces_distr_join.index))
    print(workplaces_distr_join.head())
    workplaces_distr_join = workplaces_distr_join[['txyind', 'yht', 'geom_work', 'grid_geom', 'id_distr']]

    return workplaces_distr_join

def get_valid_distr_geom(districts, workplaces_distr_join):
    workplace_distr_g = workplaces_distr_join.groupby('id_distr')

    district_dicts = []

    for idx, distr in districts.iterrows():
        # if (distr['id_distr'] != '091_OULUNKYLÄ'):
        #     continue
        d = { 'id_distr': distr['id_distr'], 'geom_distr_poly': distr['geom_distr_poly'] }
        try:
            distr_works = workplace_distr_g.get_group(distr['id_distr'])
            distr_works = gpd.GeoDataFrame(distr_works, geometry='geom_work', crs=from_epsg(3067))
            works_convex_poly = distr_works['geom_work'].unary_union.convex_hull
            # print(works_convex_poly)
            works_convex_poly_buffer = works_convex_poly.buffer(20)
            works_center_point = works_convex_poly_buffer.centroid
            # print(works_center_point)
            distr_works['work_center_dist'] = [round(geom.distance(works_center_point)) for geom in distr_works['geom_work']]
            distr_works = distr_works.sort_values(by='work_center_dist')
            # print(distr_works.head(70))
            center_work = distr_works.iloc[0]
            d['work_center'] = center_work['geom_work']
            d['has_works'] = 'yes'
        except Exception:
            d['work_center'] = distr['geom_distr_poly'].centroid
            d['has_works'] = 'no'
        district_dicts.append(d)

    districts_gdf = gpd.GeoDataFrame(district_dicts, geometry='geom_distr_poly', crs=from_epsg(3067))
    districts_gdf['distr_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in districts_gdf['work_center']]
    return districts_gdf

def get_home_district(geom_home, districts):
    for idx, distr in districts.iterrows():
        if (geom_home.within(distr['geom_distr_poly'])):
            # print('District of the origin', distr['id_distr'])
            return { 'id_distr': distr['id_distr'], 'geom_distr_poly': distr['geom_distr_poly'] }

def test_distr_centers_with_DT(districts_gdf):
    datetime = times.get_next_weekday_datetime(8, 30, skipdays=7)
    test_latLon = {'lat': 60.23122, 'lon': 24.83998}

    distr_valids = {}
    districts_gdf = districts_gdf.copy()
    for idx, distr in districts_gdf.iterrows():
        utils.print_progress(idx, len(districts_gdf), percentages=False)
        try:
            itins = DT_routing.get_route_itineraries(test_latLon, distr['distr_latLon'], '1.6666', datetime, itins_count=3, max_walk_distance=6000)
        except Exception:
            itins = []
        valid = 'yes' if (len(itins) > 0) else 'no'
        distr_valids[distr['id_distr']] = valid

    districts_gdf['DT_valid'] = [distr_valids[id_distr] for id_distr in districts_gdf['id_distr']]
    return districts_gdf

def get_work_targets_gdf(geom_home, districts, axyind=None, work_rows=None, logging=True):
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
    home_work_stats[['axyind', 'total_dests_count', 'close_dests_count', 'distr_dests_count', 'total_works_count', 'dest_works_count', 'missing_works_count', 'outside_ratio', 'work_count_match']]
    return { 'targets': targets, 'home_work_stats': home_work_stats }

def get_adjusted_routing_location(latLon, graph=None, edge_gdf=None, node_gdf=None):
    wgs_point = geom_utils.get_point_from_lat_lon(latLon)
    etrs_point = geom_utils.project_to_etrs(wgs_point)
    point_xy = geom_utils.get_xy_from_geom(etrs_point)
    try:
        node = rt.get_nearest_node(graph, point_xy, edge_gdf, node_gdf, [], False, logging=False)
        node_geom = nw.get_node_geom(graph, node['node'])
        node_distance = round(node_geom.distance(etrs_point))
        node_geom_wgs = geom_utils.project_to_wgs(node_geom)
        node_latLon = geom_utils.get_lat_lon_from_geom(node_geom_wgs)
        if (node_distance < 300):
            return node_latLon
    except Exception:
        return latLon
    return latLon

def get_home_work_walks(axyind=None, work_rows=None, districts=None, datetime=None, walk_speed=None, subset=True, logging=True, graph=None, edge_gdf=None, node_gdf=None):
    stats_path='outputs/YKR_commutes_output/home_workplaces_stats/'
    geom_home = work_rows['geom_home'].iloc[0]
    home_latLon = work_rows['home_latLon'].iloc[0]
    targets = get_work_targets_gdf(geom_home, districts, axyind=axyind, work_rows=work_rows, logging=logging)
    work_targets = targets['targets']
    home_work_stats = targets['home_work_stats']
    if (logging == True):
        print('Routing to', len(work_targets.index), 'targets')
    # filter rows of work_targets for testing
    work_targets = work_targets[:14] if subset == True else work_targets
    # print('WORK_TARGETS', work_targets)
    # filter out target if it's the same as origin
    work_targets = work_targets[work_targets.apply(lambda x: str(x['id_target']) != str(axyind), axis=1)]
    total_origin_workers_flow = work_targets['yht'].sum()
    # get routes to all workplaces of the route
    home_walks_all = []
    for idx, target in work_targets.iterrows():
        utils.print_progress(idx, len(work_targets.index)+1, percentages=False)
        # execute routing request to Digitransit API
        try:
            itins = DT_routing.get_route_itineraries(home_latLon, target['to_latLon'], walk_speed, datetime, itins_count=3, max_walk_distance=2500)
        except Exception:
            print('Error in DT routing request between:', axyind, 'and', target['id_target'])
            itins = []
        # if no itineraries got, try adjusting the origin & target by snapping them to network
        if (len(itins) == 0):
            print('No itineraries got -> try adjusting origin & target')
            adj_origin = get_adjusted_routing_location(home_latLon, graph=graph, edge_gdf=edge_gdf, node_gdf=node_gdf)
            adj_target = get_adjusted_routing_location(target['to_latLon'], graph=graph, edge_gdf=edge_gdf, node_gdf=node_gdf)
            try:
                itins = DT_routing.get_route_itineraries(adj_origin, adj_target, walk_speed, datetime, itins_count=3, max_walk_distance=2500)
                print('Found', len(itins), 'with adjusted origin & target locations')
            except Exception:
                itins = []

        od_itins_count = len(itins)
        od_workers_flow = target['yht']
        if (od_itins_count > 0):
            # calculate utilization of the itineraries for identifying the probability of using the itinerary from the origin
            # based on number of commuters and number of alternative itineraries to the destination
            # if only one itinerary is got for origin-destination (commute flow), utilization equals the number of commutes between the OD pair
            utilization = round(od_workers_flow/od_itins_count, 6)
            od_walk_dicts = DT_routing.parse_itin_attributes(itins, axyind, target['id_target'], utilization=utilization)
            home_walks_all += od_walk_dicts
        else:
            print('No DT itineraries got between:', axyind, 'and', target['id_target'])
            error_df = pd.DataFrame([{ 'axyind': axyind, 'target_type': target['target_type'], 'target_id': target['id_target'], 'target_yht': target['yht'] }])
            error_df.to_csv('outputs/YKR_commutes_output/home_stops_errors/axyind_'+str(axyind)+'_to_'+str(target['id_target'])+'.csv')

    # print(home_walks_all)
    # collect walks to stops/targets to GDF
    home_walks_all_df = pd.DataFrame(home_walks_all)
    home_walks_all_df['uniq_id'] = home_walks_all_df.apply(lambda row: DT_utils.get_walk_uniq_id(row), axis=1)
    # group similar walks and calculate realtive utilization rates of them
    home_walks_g = DT_utils.group_home_walks(home_walks_all_df)
    # check that no commute data was lost in the analysis (flows match)
    total_utilization_sum = round(home_walks_g['utilization'].sum())
    total_probs = round(home_walks_g['prob'].sum())
    works_misings_routing = total_origin_workers_flow - total_utilization_sum
    if (works_misings_routing != 0 or total_probs != 100):
        print('Error: utilization sum of walks does not match the total flow of commuters')
        error_df = pd.DataFrame([{ 'axyind': axyind, 'total_origin_workers_flow': total_origin_workers_flow, 'total_utilization_sum': total_utilization_sum, 'total_probs': total_probs }])
        error_df.to_csv('outputs/YKR_commutes_output/home_stops_errors/axyind_'+str(axyind)+'_no_flow_match.csv')
    home_work_stats['works_misings_routing'] = works_misings_routing
    home_work_stats['works_misings_routing_rat'] = round((works_misings_routing/total_origin_workers_flow)*100, 1)
    home_work_stats['total_probs'] = total_probs
    home_work_stats.to_csv(stats_path+'axyind_'+str(axyind)+'.csv')
    return home_walks_g

def validate_home_stops(home_walks_g):
    df = home_walks_g.dropna(subset=['DT_origin_latLon'])
    df = df.reset_index(drop=True)
    stops_count = len(df.index)
    if (stops_count < 1):
        return '\nNo stops found!!'
