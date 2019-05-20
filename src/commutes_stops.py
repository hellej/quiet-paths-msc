#%% IMPORT MODULES FOR YKR COMMUTES PROCESSING
import pandas as pd
import geopandas as gpd
import time
from fiona.crs import from_epsg
from shapely.geometry import Point
from multiprocessing import current_process, Pool
import utils.DT_API as DT_routing
import utils.DT_utils as DT_utils
import utils.geometry as geom_utils
import utils.times as times
import utils.files as files
import utils.utils as utils
import utils.commutes as commutes_utils
import utils.networks as nw

#%% read graph
graph = files.get_network_full_noise()
print('Graph of', graph.size(), 'edges read.')
edge_gdf = nw.get_edge_gdf(graph)
node_gdf = nw.get_node_gdf(graph)
print('Network features extracted.')
edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Spatial index built.')

#%% read YKR work commute data
commutes = pd.read_csv('data/input/T06_tma_e_TOL2008_2016_hel.csv')
# commutes['axyind'] = [int(xyind) for xyind in commutes['axyind']]
# commutes['txyind'] = [int(xyind) for xyind in commutes['txyind']]
# commutes = commutes.loc[commutes['akunta'] == 91]
# commutes = commutes.loc[commutes['sp'] == 0]
# commutes.to_csv('data/input/T06_tma_e_TOL2008_2016_hel.csv')
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

#%% read city extent (polygon of Helsinki)
hel_poly = files.get_hel_poly()
hel_poly = geom_utils.project_to_wgs(hel_poly)
def outside_hel_extent(geometry):
    return 'no' if geometry.within(hel_poly) else 'yes'

#%% merge grid geometry to commutes by home & job xyind (just to make sure that the ids work for joining)
homes = pd.merge(commutes, grid, how='left', left_on='axyind', right_on='xyind')
workplaces = pd.merge(commutes, grid, how='left', left_on='txyind', right_on='xyind')
workplaces = gpd.GeoDataFrame(workplaces, geometry='geom_work', crs=from_epsg(3067))
# drop rows without ykr grid cell geometry
workplaces = workplaces.dropna(subset=['grid_geom'])
homes = homes.dropna(subset=['grid_geom'])

#%% read city districts
districts = files.get_city_districts()
districts['id_distr'] = districts.apply(lambda row: str(row['kunta'] +'_'+ row['nimi']), axis=1)
districts['geom_distr_poly'] = [geometry.geoms[0] for geometry in districts['geometry']]
districts = districts.set_geometry('geom_distr_poly')
districts = districts[['id_distr','geom_distr_poly']]
districts = districts.to_crs(epsg=3067)
districts['geom_distr_point'] = [geometry.centroid for geometry in districts['geom_distr_poly']]
# join district info to workplaces
workplaces_distr_join = commutes_utils.get_workplaces_distr_join(workplaces, districts)
#%% add valid district center geometries (in central workplace are of the district)
districts_gdf = commutes_utils.get_valid_distr_geom(districts, workplaces_distr_join)
districts_gdf.head()
# validate district center points with DT Api
# districts_gdf = commutes_utils.test_distr_centers_with_DT(districts_gdf)
# save district work center to file
# districts_gdf.set_geometry('work_center').drop(columns=['geom_distr_poly']).to_file('outputs/YKR_commutes_output/test.gpkg', layer='district_centers', driver='GPKG')

#%% print data stats
print('districts:', len(districts_gdf))
print('grid_cells:', len(grid.index))
print('ykr_commute rows:', len(commutes.index))
print('workplaces within area:', len(workplaces.index))
print('workplaces with distr info:', len(workplaces_distr_join))
print('homes within area:', len(homes.index))
print('unique homes:', homes['axyind'].nunique())

#%% group workplaces by homes
home_groups = commutes.groupby('axyind')

# routing params for Digitransit API
walk_speed = '1.16666'
datetime = times.get_next_weekday_datetime(8, 30, skipdays=7)
print('Datetime for routing:', datetime)
# Datetime for routing: 2019-05-27 08:30:00 !!!!

#%% function that returns home_walks
def get_home_walk_gdf(axyind):
    start_time = time.time()
    work_rows = home_groups.get_group(axyind)
    home_walks_g = commutes_utils.get_home_work_walks(axyind=axyind, work_rows=work_rows, districts=districts_gdf, datetime=datetime, walk_speed=walk_speed, subset=False, logging=True, graph=graph, edge_gdf=edge_gdf, node_gdf=node_gdf)
    if (not isinstance(home_walks_g, pd.DataFrame)):
        if (home_walks_g == None):
            print('No work destinations found for:', axyind, 'skipping...')
            return None
    error = commutes_utils.validate_home_stops(home_walks_g)
    if (error != None):
        print(error)
    # add column that tells if the stop geometry is outside of the extent of Helsinki
    home_walks_g['outside_hel'] = [outside_hel_extent(geom) for geom in home_walks_g['DT_dest_Point']]
    home_walks_g_to_file = home_walks_g.drop(columns=['DT_geom', 'DT_dest_Point'])
    home_walks_g_to_file.to_csv('outputs/YKR_commutes_output/home_stops/axyind_'+str(axyind)+'.csv')
    utils.print_duration(start_time, str(len(home_walks_g)) +' home stops got for: '+str(axyind)+'.\n')
    return home_walks_g

while True:
    print('\nHow many origins to process: ', end='')
    to_process_count = int(input())
    if (to_process_count == 0):
        break

    #%% process origins
    # collect axyinds to process
    axyinds = commutes['axyind'].unique()
    # axyinds = [3803756679125, 3873756677375, 3866256677375, 3863756676625, 3876256675875, 3838756674875]
    axyinds_toskip = [4026256685375, 9999999999999, 3841256675125]
    axyinds_processed = commutes_utils.get_processed_home_walks()
    print('Previously processed', len(axyinds_processed), 'axyinds')
    axyinds = [axy for axy in axyinds if axy not in axyinds_processed]
    axyinds = [axy for axy in axyinds if axy not in axyinds_toskip]
    axyinds = axyinds[:to_process_count]
    print('Start processing', len(axyinds), 'axyinds')

    #%% one by one
    start_time = time.time()
    all_home_walks_dfs = []
    for idx, axyind in enumerate(axyinds):
        utils.print_progress(idx, len(axyinds), False)
        print('\nStart processing:', axyind)
        if (axyind == 9999999999999):
            print('skip 9999999999999')
            continue
        all_home_walks_dfs.append(get_home_walk_gdf(axyind))
    # print time stats
    time_elapsed = round(time.time() - start_time)
    avg_origin_time = round(time_elapsed/len(axyinds))
    print('--- %s min --- %s' % (round(time_elapsed/60,1), 'processed: '+ str(len(axyinds)) +' origins'))
    print('Average origin processing time:', avg_origin_time, 's')

print('\nFinished routing.')


#%% export to GDF for debugging
# all_home_walks_df = pd.concat(all_home_walks_dfs, ignore_index=True)
# all_home_walks_gdf = gpd.GeoDataFrame(all_home_walks_df, geometry='DT_geom', crs=from_epsg(4326))
# all_home_walks_gdf.drop(columns=['DT_dest_Point']).to_file('outputs/YKR_commutes_output/test.gpkg', layer='dt_paths', driver='GPKG')
# all_home_walks_gdf = gpd.GeoDataFrame(all_home_walks_df, geometry='DT_dest_Point', crs=from_epsg(4326))
# all_home_walks_gdf.drop(columns=['DT_geom']).to_file('outputs/YKR_commutes_output/test.gpkg', layer='dt_stops', driver='GPKG')

#%%
# this should be exactly 100:
# print('sum prob', all_home_walks_gdf['prob'].sum())
# all_home_walks_gdf.plot()
# all_home_walks_gdf.head(50)
