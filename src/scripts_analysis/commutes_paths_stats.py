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
paths['th_noises_diff'] = [ast.literal_eval(th_noises) for th_noises in paths['th_noises_diff']]
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
s_paths_pt = s_paths.query("to_pt_mode != 'none'")
s_paths_work = s_paths.query("to_pt_mode == 'none'")
print('short paths to pt count:', len(s_paths_pt.index), '(of', str(count_before)+')')
print('short paths to work count:', len(s_paths_work.index), '(of', str(count_before)+')')

#### PATH LENGTH STATISTICS ####
################################

#%% calculate weighted statistics of path lengths
path_len_stats = []
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'length', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), col_prefix='length_all', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths_pt, 'length', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), col_prefix='length_pt', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths_work, 'length', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), col_prefix='length_work', add_varname=True, add_n=True))
path_len_stats = pd.DataFrame(path_len_stats, columns=path_len_stats[0].keys())
path_len_stats.to_csv('outputs/path_stats/path_len_stats.csv')
path_len_stats

#%% print stats of lengths compared to reference lengths
path_len_stats = []
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'DT_len_diff', weight=None, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'DT_len_diff_rat', weight=None, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff_rat', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'DT_len_diff', weight=None, min_length=20, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff_filt', add_varname=True, add_n=True, printing=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'DT_len_diff_rat', weight=None, min_length=20, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff_rat_filt', add_varname=True, add_n=True))
path_len_stats = pd.DataFrame(path_len_stats, columns=path_len_stats[0].keys())
path_len_stats.to_csv('outputs/path_stats/path_len_diff_stats.csv')
path_len_stats

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

#### FILTER OUT PATHS FROM PROBLEMATIC AXYINDS ####
###################################################

#%% filter out paths from specific axyinds
count_before = len(s_paths)
skip_axyinds = [3933756673875, 3863756670125]

paths = paths[~paths['from_axyind'].isin(skip_axyinds)]
s_paths = s_paths[~s_paths['from_axyind'].isin(skip_axyinds)]
s_paths_pt = s_paths_pt[~s_paths_pt['from_axyind'].isin(skip_axyinds)]
s_paths_work = s_paths_work[~s_paths_work['from_axyind'].isin(skip_axyinds)]

count_after = len(s_paths)
print('Filtered out:', count_before-count_after, 'shortest paths')

#### STATFI GRID LEVEL NOISE STATISTICS ####
############################################

#%% #### group paths to PT by origin (axyind)
axy_groups = s_paths_pt.groupby('from_axyind')
print('paths to PT count', len(s_paths_pt))
print(len(s_paths_pt.query('DT_len_diff == -9999')))

#%% calculate stats per origin (paths from axyind)
errors = []
stats = []
for key, group in axy_groups:
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
        db60r_stats = pstats.calc_basic_stats(filt_paths, '60dBr', weight='prob', valueignore=-9999, col_prefix='dB60r')
        db65r_stats = pstats.calc_basic_stats(filt_paths, '65dBr', weight='prob', valueignore=-9999, col_prefix='dB65r')
        db70r_stats = pstats.calc_basic_stats(filt_paths, '70dBr', weight='prob', valueignore=-9999, col_prefix='dB70r')
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

#%% print column names
print(s_paths.columns)

#%%# ALL SHORTEST PATHS ###
sp_stats = []
sp_stats.append(pstats.calc_basic_stats(s_paths, 'nei', weight='util', percs=[5, 10, 90, 95], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, 'nei_norm', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, 'mdB', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '60dBl', weight='util', percs=[5, 10, 90, 95], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '65dBl', weight='util', percs=[5, 10, 90, 95], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '70dBl', weight='util', percs=[5, 10, 90, 95], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '60dBr', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '65dBr', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '70dBr', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats = pd.DataFrame(sp_stats, columns=sp_stats[0].keys())
sp_stats.to_csv('outputs/path_stats/sp_noise_stats.csv')
sp_stats

#%%# SHORTEST PATHS TO PT STOPS ###
sp_pt_stats = []
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, 'nei', weight='util', percs=[5, 10, 90, 95], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, 'nei_norm', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, 'mdB', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '60dBl', weight='util', percs=[5, 10, 90, 95], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '65dBl', weight='util', percs=[5, 10, 90, 95], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '70dBl', weight='util', percs=[5, 10, 90, 95], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '60dBr', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '65dBr', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '70dBr', weight='util', percs=[5, 10, 90, 95], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats = pd.DataFrame(sp_pt_stats, columns=sp_pt_stats[0].keys())
sp_pt_stats.to_csv('outputs/path_stats/sp_pt_noise_stats.csv')
sp_pt_stats

#### QUIET PATH NOISE STATS #####
#################################
#%% set & rename columns
print(paths.columns)
qp_cols = ['od_id', 'path_id', 'len_diff', 'len_diff_r', 'length', 'nei',
       'nei_diff', 'nei_diff_r', 'nei_norm', 'noises', 'noises_diff', 'th_noises', 
       'th_noises_diff', 'util', 'mdB', '60dBl', '65dBl', '70dBl']

#%% filter out null paths & rename id columns
p = paths.query('length != -9999').copy()
p['od_id'] = p['path_id']
p['path_id'] = p['id']
p['nei_diff_r'] = p['nei_diff_rat']
p['len_diff_r'] = p['len_diff_rat']
print(p[['od_id', 'path_id']].head())

#%% select subset of paths
axyinds = grid_stats['axyind'].unique()
axyinds = axyinds[:10]
p = p[p['from_axyind'].isin(axyinds)]
print('filtered paths count:', len(p))

#%% add & extract dB exposure columnds to df
p['mdB'] = p.apply(lambda row: exps.get_mean_noise_level(row['length'], row['noises']), axis=1)
p = pstats.extract_th_db_cols(p, ths=[60, 65, 70], add_ratios=False)
print(p.columns)
p = p[qp_cols]
p.head()

#%%
# group by path id (short and quiet paths of OD-pair are in the same group)
# all_qps = []
all_od_stats = []
print('OD count:', len(p['od_id'].unique()))
grouped = p.groupby('od_id')
for key, group in grouped:
    # if (key != '3801256680625_HSL:1320224' and key != '3801256680875_HSL:1320111'):
    #     continue
    sp = group.query("path_id == 'short_p'").to_dict(orient='records')[0]
    qps = group.query("path_id != 'short_p'")[qp_cols]
    # qps['len_sp'] = sp['length']
    qps['mdB_diff'] = [mdB - sp['mdB'] for mdB in qps['mdB']]
    # db len diffs
    qps['60dB_diff'] = [round(dblen - sp['60dBl'], 1) for dblen in qps['60dBl']]
    qps['65dB_diff'] = [round(dblen - sp['65dBl'], 1) for dblen in qps['65dBl']]
    # qps['70dB_diff'] = [round(dblen - sp['70dBl'], 1)  for dblen in qps['70dBl']]
    # db len diff ratios
    qps['60dB_diff_r'] = [ round((dblendiff/sp['60dBl'])*100) if sp['60dBl'] != 0 else 0 for dblendiff in qps['60dB_diff']]
    qps['65dB_diff_r'] = [ round((dblendiff/sp['65dBl'])*100) if sp['65dBl'] != 0 else 0 for dblendiff in qps['65dB_diff']]
    # qps['70dB_diff_r'] = [ round((dblendiff/sp['70dBl'])*100) if sp['70dBl'] != 0 else 0 for dblendiff in qps['70dB_diff']]
    # all_qps.append(qps)

    all_od_stats.append(pstats.get_best_quiet_paths_of_max_len_diffs(od_id=key, df=qps, sp=sp, max_len_diffs=[30, 100, 150, 200, 300]))
    # print('best_qp', od_stats)
    # print(qps[['path_id', 'len_sp', 'length', 'len_diff']])

#%% collect od stats
od_stats_df = pd.DataFrame(all_od_stats, columns=all_od_stats[0].keys())
od_stats_df.head()

#%% collect quiet paths
# qps_df = pd.concat(all_qps, ignore_index=True)
# print('quiet paths count:', len(qps_df))
# print(qps_df.columns)
# qps_df_500_1000 = qps_df.query('len_sp > 600 and len_sp < 1000')

#%%
