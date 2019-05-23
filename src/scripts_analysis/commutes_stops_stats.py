#%% IMPORT MODULES FOR YKR COMMUTES PROCESSING
import pandas as pd
import geopandas as gpd
import time
import ast
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
edge_gdf = nw.get_edge_gdf(graph, attrs=['geometry', 'length', 'noises'])
node_gdf = nw.get_node_gdf(graph)
print('Network features extracted.')
edge_gdf = edge_gdf[['uvkey', 'geometry', 'noises']]
edges_sind = edge_gdf.sindex
nodes_sind = node_gdf.sindex
print('Spatial index built.')

#%% read YKR work commute data
commutes = pd.read_csv('data/input/T06_tma_e_TOL2008_2016_hel.csv')
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
grid['grid_centr'] = grid.apply(lambda row: geom_utils.get_point_from_xy({'x': row['x'], 'y': row['y']}), axis=1)
grid['xyind'] = [int(xyind) for xyind in grid['xyind']]
grid = grid[['xyind', 'grid_geom', 'grid_centr']]
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

#%% print data stats
print('districts:', len(districts_gdf))
print('grid_cells:', len(grid.index))
print('ykr_commute rows:', len(commutes.index))
print('workplaces within area:', len(workplaces.index))
print('workplaces with distr info:', len(workplaces_distr_join))
print('homes within area:', len(homes.index))
print('unique homes:', homes['axyind'].nunique())

#%% group commutes by homes
home_groups = commutes.groupby('axyind')

# routing params for Digitransit API
walk_speed = '1.16666'
datetime = times.get_next_weekday_datetime(8, 30, skipdays=4)
print('Datetime for routing:', datetime)
# Datetime for routing: 2019-05-27 08:30:00 !!!!

#%%
stats_files = 'outputs/YKR_commutes_output/home_workplaces_stats'
stops_files = 'outputs/YKR_commutes_output/home_stops'
axyfiles = commutes_utils.get_xyind_filenames(path=stops_files)
print(axyfiles[:1])

#%%
axyfiles_to_reprocess = commutes_utils.get_axyinds_to_reprocess(grid)

#%%


#%%
test_latLon = {'lat': 60.21168, 'lon': 24.87754}
adjusted_latLon = commutes_utils.get_valid_latLon_for_DT(test_latLon, distance=45, datetime=datetime, graph=graph, edge_gdf=edge_gdf, node_gdf=node_gdf)

#%%
