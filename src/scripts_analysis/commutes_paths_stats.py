#%%
import pandas as pd
import geopandas as gpd
import ast
import time
import numpy as np
import statistics as stats
from statsmodels.stats.weightstats import DescrStatsW
from fiona.crs import from_epsg
import utils.path_stats as pstats
import utils.geometry as geom_utils
import utils.files as files
import utils.plots as plots
import utils.exposures as exps

#### READ & PROCESS PATHS & GRID ####
##################################### 

#%% read statfi xy-grid
grid = files.get_statfi_grid()
# add centroid point geometry to grid
grid['grid_geom'] = [geometry.geoms[0] for geometry in grid['geometry']]
grid = grid.set_geometry('grid_geom')
grid['grid_centr'] = grid.apply(lambda row: geom_utils.get_point_from_xy({'x': row['x'], 'y': row['y']}), axis=1)
grid['xyind'] = [int(xyind) for xyind in grid['xyind']]
grid = grid[['xyind', 'grid_geom', 'grid_centr']]
grid.head()

#%% read all paths
paths =  gpd.read_file('outputs/YKR_commutes_output/home_paths.gpkg', layer='run_3_all')
paths['noises'] = [ast.literal_eval(noises) for noises in paths['noises']]
paths['th_noises'] = [ast.literal_eval(th_noises) for th_noises in paths['th_noises']]
#%% count of all paths
print('read', len(paths.index), 'paths')
print('axyind count:', len(paths['from_axyind'].unique()))
print('paths per axyind:', round(len(paths.index)/len(paths['from_axyind'].unique())))

#%% mark path stats to -9999 for paths that are actually PT legs (origin happened to be exactly at the PT stop)
paths = pstats.map_pt_path_props_to_null(paths)

#%% subset of short paths (filter out quiet paths)
s_paths = paths.query("type == 'short'")
print('short paths count:', len(s_paths.index))

#%% add & extract dB exposure columnds to df
s_paths = pstats.extract_th_db_cols(s_paths, ths=[55, 60, 65, 70], valueignore=-9999)
s_paths['mdB'] = s_paths.apply(lambda row: exps.get_mean_noise_level(row['length'], row['noises']) if type(row['noises']) == dict else -9999, axis=1)
s_paths.head(2)

#%% calculate path length statistics (compare lengths to reference lengths from DT)
s_paths = pstats.add_dt_length_diff_cols(s_paths, valueignore=-9999)
s_paths.head(2)

#%% add bool col for within hel = yes/no
s_paths = pstats.add_bool_within_hel_poly(s_paths)
s_paths.head(2)

#%% select paths to PT (filter out paths to destinations)
count_before = len(s_paths)
s_paths_to_pt = s_paths.query("to_pt_mode != 'none'")
s_paths_to_work = s_paths.query("to_pt_mode == 'none'")
print('short paths to pt count:', len(s_paths_to_pt.index), '(of', str(count_before)+')')
print('short paths to work count:', len(s_paths_to_work.index), '(of', str(count_before)+')')

#### PATH LENGTH STATISTICS ####
################################

#%% print unweighted statistics of shortest paths to PT
# s short
# p path
# pt public transport (PT)
# l length
# sd standard deviation (SD)
# wp weighted with path probability
# wu weighted with path utilization rate
# DT_len_diff_rat = [diff for diff in s_paths_to_pt['DT_len_diff_rat'] if diff != -9999]
# print(round(np.std(DT_len_diff_rat)))
#%%
s_p_pt_lens = s_paths_to_pt['length']
# -9999 means origin was already at the PT stop -> hence walk length was 0 m 
s_p_pt_lens = [length if length != -9999 else 0 for length in s_p_pt_lens]
s_p_pt_l_mean = round(np.mean(s_p_pt_lens), 3)
s_p_pt_l_median = round(np.median(s_p_pt_lens), 3)
s_p_pt_l_sd = round(np.std(s_p_pt_lens), 3)
print('simple mean length:', s_p_pt_l_mean)
print('simple median length:', s_p_pt_l_median)
print('simple length sd:', s_p_pt_l_sd)

#%% print weighted stats with DescrStatsW module
weighted_stats = DescrStatsW(s_p_pt_lens, weights=s_paths_to_pt['util'], ddof=0)
print('weighted mean length:', round(weighted_stats.mean, 2))
print('weighted std length:', round(weighted_stats.std, 2))
quants = weighted_stats.quantile(probs=[0.5], return_pandas=True)
print(quants)

#%% print weighted statistics of all short paths to PT
pstats.calc_basic_stats(s_paths, 'length', weight='util', percs=[10, 90], valuemap=(-9999, 0), printing=True)
pstats.calc_basic_stats(s_paths_to_pt, 'length', weight='util', percs=[10, 90], valuemap=(-9999, 0), printing=True)
pstats.calc_basic_stats(s_paths_to_work, 'length', weight='util', percs=[10, 90], valuemap=(-9999, 0), printing=True)

#%% print stats of lengths compared to reference lengths
pstats.calc_basic_stats(s_paths, 'DT_len_diff', weight=None, min_length=20, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff', printing=True)
pstats.calc_basic_stats(s_paths, 'DT_len_diff_rat', weight=None, min_length=20, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff_rat', printing=True)

#%% plot DT len diff stats
s_paths_filt = pstats.filter_by_min_value(s_paths, 'length', 20)
s_paths_filt = pstats.filter_by_max_value(s_paths_filt, 'DT_len_diff', 7000)
fig = plots.scatterplot(s_paths_filt, xcol='length', ycol='DT_len', yignore=-9999, xlabel='Length (m)', ylabel='Ref. length (m)')
fig.savefig('plots/paths_len_ref_len_scatter.png', format='png', dpi=300)
fig = plots.scatterplot(s_paths_filt, xcol='length', ycol='DT_len_diff', yignore=-9999, xlabel='Length (m)', ylabel='Ref. length diff. (m)')
fig.savefig('plots/paths_DT_len_diff_scatter.png', format='png', dpi=300)
fig = plots.boxplot(s_paths_filt, col='DT_len_diff', valignore=-9999, label='Ref. length diff. (m)')
fig.savefig('plots/paths_DT_len_diff_boxplot.png', format='png', dpi=300)
fig = plots.scatterplot(s_paths_filt, xcol='length', ycol='DT_len_diff_rat', yignore=-9999, xlabel='Length (m)', ylabel='Ref. length diff. (%)')
fig.savefig('plots/paths_DT_len_diff_rat_scatter.png', format='png', dpi=300)

#%% export paths with stats to file
s_paths.to_file('outputs/YKR_commutes_output/home_paths.gpkg', layer='run_3_stats', driver='GPKG')

#### STATFI GRID LEVEL NOISE STATISTICS ####
############################################

#%% #### group paths to PT by origin (axyind)
axy_groups = s_paths_to_pt.groupby('from_axyind')
print('paths to PT count', len(s_paths_to_pt))
print(len(s_paths_to_pt.query('DT_len_diff == -9999')))

#%% calculate stats per origin (paths from axyind)
errors = []
stats = []
for key, group in axy_groups:
    # if (key != 3863756670125):
    #     continue
    in_paths = group.query("b_inside_hel == 'yes'")
    filt_paths = pstats.filter_out_problem_paths(in_paths)
    if (len(in_paths) > 0):
        paths_incl_ratio = round(len(filt_paths)/(len(group))*100, 1)
    else:
        paths_incl_ratio = 0
    if (len(filt_paths) != 0):
        d = { 'axyind': key }
        d['probsum'] = round(filt_paths['prob'].sum(),2)
        d['paths_incl_ratio'] = paths_incl_ratio
        # calculate stats of path lengths
        len_stats = pstats.calc_basic_stats(filt_paths, 'length', weight='prob', valuemap=(-9999, 0), col_prefix='len')
        # calculate stats of path noise exposures
        db55l_stats = pstats.calc_basic_stats(filt_paths, '55dBl', weight='prob', valuemap=(-9999, 0), col_prefix='dB55l')
        db60l_stats = pstats.calc_basic_stats(filt_paths, '60dBl', weight='prob', valuemap=(-9999, 0), col_prefix='dB60l')
        db65l_stats = pstats.calc_basic_stats(filt_paths, '65dBl', weight='prob', valuemap=(-9999, 0), col_prefix='dB65l')
        db70l_stats = pstats.calc_basic_stats(filt_paths, '70dBl', weight='prob', valuemap=(-9999, 0), col_prefix='dB70l')
        db55r_stats = pstats.calc_basic_stats(filt_paths, '55dBr', weight='prob', valueignore=-9999, col_prefix='dB55r')
        db60r_stats = pstats.calc_basic_stats(filt_paths, '60dBr', weight='prob', valueignore=-9999,col_prefix='dB60r')
        db65r_stats = pstats.calc_basic_stats(filt_paths, '65dBr', weight='prob', valueignore=-9999,col_prefix='dB65r')
        db70r_stats = pstats.calc_basic_stats(filt_paths, '70dBr', weight='prob', valueignore=-9999,col_prefix='dB70r')
        nei_stats = pstats.calc_basic_stats(filt_paths, 'nei', weight='prob', valuemap=(-9999, 0), col_prefix='nei')
        nei_norm_stats = pstats.calc_basic_stats(filt_paths, 'nei_norm', weight='prob', valueignore=-9999, col_prefix='nei_n')
        mdB_stats = pstats.calc_basic_stats(filt_paths, 'mdB', weight='prob', valueignore=-9999, col_prefix='mdB')
        d = { **d, **len_stats, **db55l_stats, **db60l_stats, **db65l_stats, **db70l_stats, **db55r_stats, 
            **db60r_stats, **db65r_stats, **db70r_stats, **nei_stats, **nei_norm_stats, **mdB_stats }
        stats.append(d)
    else:
        errors.append(key)
print('stats got for:', len(stats), 'axyinds')
print('all paths filtered out for:', len(errors), 'axyinds')

#%% combine stats to DF
stats_df = pd.DataFrame(stats, columns=stats[0].keys())
stats_df.head()

#%% merge grid geoometry to axyind stats
grid_stats = pd.merge(stats_df, grid, how='left', left_on='axyind', right_on='xyind')
print('merged:', len(grid_stats))
# convert to GeoDataFrame
grid_stats = gpd.GeoDataFrame(grid_stats, geometry='grid_geom', crs=from_epsg(3067))

#%% export axyind stats with grid geometry to file
grid_stats.drop(columns=['grid_centr']).to_file('outputs/YKR_commutes_output/axyind_stats.gpkg', layer='axyind_stats_v3', drive='GPKG')

#### PATH NOISE STATS #####
###########################

