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

#%% read city districts
districts = files.get_city_districts()
districts['id_distr'] = districts.apply(lambda row: str(row['kunta'] +'_'+ row['nimi']), axis=1)
districts = districts.to_crs(epsg=3067)
districts['geom_distr_poly'] = [geometry.geoms[0] for geometry in districts['geometry']]
districts['geom_distr_point'] = [geometry.centroid for geometry in districts['geometry']]
districts['distr_latLon'] = [geom_utils.get_lat_lon_from_geom(geom_utils.project_to_wgs(geom, epsg=3067)) for geom in districts['geom_distr_point']]
districts = districts.set_geometry('geom_distr_poly')
districts = districts[['id_distr', 'geom_distr_poly', 'distr_latLon']]
print('districts', districts['id_distr'].nunique())
districts.head()

#%% merge grid geometry to commutes by home & job xyind
homes = pd.merge(commutes, grid, how='left', left_on='axyind', right_on='xyind')
workplaces = pd.merge(commutes, grid, how='left', left_on='txyind', right_on='xyind')
# drop rows without ykr grid cell geometry
workplaces = workplaces.dropna(subset=['grid_geom'])
homes = homes.dropna(subset=['grid_geom'])

#%% print data stats
print('ykr_commute rows:', len(commutes.index))
print('grid_cells:', len(grid.index))
print('workplaces', len(workplaces.index))
print('homes', len(homes.index))
print('unique homes', homes['axyind'].nunique())

#%% group workplaces by homes
home_groups = commutes.groupby('axyind')
# collect axyinds to process
axyinds = commutes['axyind'].unique()
axyinds_processed = commutes_utils.get_processed_home_walks()
axyinds = [axyind for axyind in axyinds if axyind not in axyinds_processed]
axyinds = [3873756677375, 3866256677375, 3863756676625, 3876256675875, 3838756674875]

# routing params for Digitransit API
walk_speed = '1.16666'
datetime = times.get_next_weekday_datetime(8, 30, skipdays=7)
print('Datetime for routing:', datetime)

# function that returns home_walks
def get_home_walk_gdf(axyind):
    start_time = time.time()
    work_rows = home_groups.get_group(axyind)
    home_walks_g = commutes_utils.get_home_work_walks(axyind=axyind, work_rows=work_rows, districts=districts, datetime=datetime, walk_speed=walk_speed, subset=True, logging=False)
    home_walks_g_to_file = home_walks_g.drop(columns=['stop_Point', 'DT_geom'])
    home_walks_g_to_file.to_csv('outputs/YKR_commutes_output/home_stops/axyind_'+str(axyind)+'.csv')
    utils.print_duration(start_time, 'home stops got for: '+str(axyind)+'.')
    return home_walks_g

#%% process origins
# with pool
pool = Pool(processes=4)
all_home_walks_dfs = pool.map(get_home_walk_gdf, axyinds)
# without pool (one by one)
# all_home_walks_dfs = [get_home_walk_gdf(axyind) for axyind in axyinds]

#%% export to GDF for debugging
all_home_walks_df = pd.concat(all_home_walks_dfs, ignore_index=True)
all_home_walks_gdf = gpd.GeoDataFrame(all_home_walks_df, geometry='DT_geom', crs=from_epsg(4326))
# all_home_walks_gdf.drop(columns=['stop_Point']).to_file('outputs/YKR_commutes_output/test.gpkg', layer='dt_paths', driver='GPKG')
all_home_walks_gdf = gpd.GeoDataFrame(all_home_walks_df, geometry='stop_Point', crs=from_epsg(4326))
# all_home_walks_gdf.drop(columns=['DT_geom']).to_file('outputs/YKR_commutes_output/test.gpkg', layer='dt_stops', driver='GPKG')

#%%
# this should be exactly 100:
print('sum prob', all_home_walks_gdf['prob'].sum())
all_home_walks_gdf.plot()
all_home_walks_gdf.head(50)

#%%
