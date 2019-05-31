#%% 
import pandas as pd
import geopandas as gpd
import ast
import time
import numpy as np
import statistics as stats
import utils.path_stats as pstats
from statsmodels.stats.weightstats import DescrStatsW
from fiona.crs import from_epsg
import utils.geometry as geom_utils
import utils.files as files

#%% read grid for adding grid geometry to axyind level statistics
grid = files.get_statfi_grid()
# add centroid point geometry to grid
grid['grid_geom'] = [geometry.geoms[0] for geometry in grid['geometry']]
grid = grid.set_geometry('grid_geom')
grid['grid_centr'] = grid.apply(lambda row: geom_utils.get_point_from_xy({'x': row['x'], 'y': row['y']}), axis=1)
grid['xyind'] = [int(xyind) for xyind in grid['xyind']]
grid = grid[['xyind', 'grid_geom', 'grid_centr']]
grid.head()

#%% read data
paths =  gpd.read_file('outputs/YKR_commutes_output/home_paths_all.gpkg', layer='paths')
paths['noises'] = [ast.literal_eval(noises) for noises in paths['noises']]
paths['th_noises'] = [ast.literal_eval(th_noises) for th_noises in paths['th_noises']]
# count of all paths
print('read', len(paths.index), 'paths')
print('cols:', paths.columns)

#%% subset of short paths (filter out quiet paths)
s_paths = paths.query("type == 'short'")
print('short paths:', len(s_paths.index))
s_paths.head()

#%% add & extract th dB columns to gdf
s_paths = pstats.extract_th_db_cols(s_paths, ths=[55, 60, 65, 70])
s_paths.head()

#%% select paths to PT (filter out paths to destinations)
s_paths_to_pt = s_paths.query("to_pt_mode != 'WALK' and to_pt_mode != 'none'")
print('short paths to pt count:', len(s_paths_to_pt.index))

#%% reproject paths to epsg 3879 (to match epsg of Helsinki polygon)
s_paths_to_pt = s_paths_to_pt.to_crs(from_epsg(3879))
#%% add bool col for within hel = yes/no
s_paths_to_pt = pstats.add_bool_within_hel_poly(s_paths_to_pt)
s_paths_to_pt.head(2)

#%% print simple statistics of shortest paths to PT
# s short
# p path
# pt public transport (PT)
# l length
# sd standard deviation (SD)
# wp weighted with path probability
# wu weighted with path utilization rate
s_p_pt_lens = s_paths_to_pt['length']
s_p_pt_l_mean = round(np.mean(s_p_pt_lens), 3)
s_p_pt_l_median = round(np.median(s_p_pt_lens), 3)
s_p_pt_l_sd = round(np.std(s_p_pt_lens), 3)
print('simple mean length:', s_p_pt_l_mean)
print('simple median length:', s_p_pt_l_median)
print('simple length sd:', s_p_pt_l_sd)

#%% print weighted stats with DescrStatsW module
weighted_stats = DescrStatsW(s_p_pt_lens, weights=s_paths_to_pt['prob'], ddof=0)
print('weighted mean length:', round(weighted_stats.mean, 2))
print('weighted std length:', round(weighted_stats.std, 2))
quants = weighted_stats.quantile(probs=[0.5], return_pandas=True)
print(quants)

#%% print weighted statistics of all short paths to PT
pstats.calc_basic_stats(s_paths_to_pt, 'length', weight='prob', printing=True)

#%% group paths by origin (axyind)
axy_groups = s_paths_to_pt.groupby('from_axyind')

#%% calculate stats per origin (paths from axyind)
errors = []
stats = []
for key, group in axy_groups:
    in_paths = group.query("b_inside_hel == 'yes'")
    if (len(in_paths) > 0):
        paths_in_rat = round(len(in_paths)/(len(group))*100, 1)
    else:
        paths_in_rat = 0
    if (len(in_paths) != 0):
        d = { 'axyind': key }
        # calculate stats of path lengths
        len_stats = pstats.calc_basic_stats(group, 'length', weight='prob', col_prefix='len')
        d = { **d, **len_stats }
        # calculate stats of path exposures
        d['paths_in_rat'] = paths_in_rat
        stats.append(d)
    else:
        errors.append(key)
print('paths outside for:', len(errors), 'axyinds')

#%% combine stats to DF
stats_df = pd.DataFrame(stats, columns=stats[0].keys())
stats_df.head()

#%% merge grid geoometry to axyind stats
grid_stats = pd.merge(stats_df, grid, how='left', left_on='axyind', right_on='xyind')
print('merged:', len(grid_stats))
# drop rows without ykr grid cell geometry
grid_stats = grid_stats.dropna(subset=['grid_geom'])
print('after na drop:', len(grid_stats))
# convert to GeoDataFrame
grid_stats = gpd.GeoDataFrame(grid_stats, geometry='grid_geom', crs=from_epsg(3067))

#%% export axyind stats with grid geometry to file
grid_stats.drop(columns=['grid_centr']).to_file('outputs/YKR_commutes_output/axyind_stats.gpkg', layer='test', drive='GPKG')

#%%
