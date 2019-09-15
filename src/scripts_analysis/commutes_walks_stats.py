#%%
import pandas as pd
import geopandas as gpd
import ast
import time
import numpy as np
import statistics as stats
from fiona.crs import from_epsg
import utils.path_stats as pstats
import utils.geometry as geom_utils
import utils.files as files
import utils.plots as plots
import utils.exposures as exps

walks_in_file = 'run_5_set_1'
problem_axyinds = [3933756673875]
axyind_stats_out_file = 'axyind_stats_v4'

#### READ & PROCESS WALKS & GRID ####
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
paths =  gpd.read_file('outputs/YKR_commutes_output/home_paths.gpkg', layer=walks_in_file)
paths['noises'] = [ast.literal_eval(noises) for noises in paths['noises']]
paths['th_noises'] = [ast.literal_eval(th_noises) for th_noises in paths['th_noises']]
paths['th_noises_diff'] = [ast.literal_eval(th_noises) for th_noises in paths['th_noises_diff']]
#%% count of all paths
print('read', len(paths.index), 'paths')
print('axyind count:', len(paths['from_axyind'].unique()))
print('paths per axyind:', round(len(paths.index)/len(paths['from_axyind'].unique())))
print(paths.columns)

#%% fix dt len diff ratio - only needed for run_5_set_1 and older (fixed routing script)
paths = pstats.fix_dt_len_diff(paths) # TODO disable for run_6 paths and newer
#%% mark path stats to -9999 for paths that are actually PT legs (origin happened to be exactly at the PT stop)
paths = pstats.map_pt_path_props_to_null(paths)


#### SHORTEST PATH LENGTH STATISTICS ####
#########################################

#%% subset of short paths (filter out quiet paths)
s_paths = paths.query("type == 'short'")
print('short paths count:', len(s_paths.index))

#%% add & extract dB exposure columnds to df
s_paths = pstats.extract_th_db_cols(s_paths, ths=[55, 60, 65, 70], valueignore=-9999)

#%% add bool col for within hel = yes/no
s_paths = pstats.add_bool_within_hel_poly(s_paths)
s_paths.head(2)

#%% select paths to PT (filter out paths to destinations)
count_before = len(s_paths)
s_paths_pt = s_paths.query("to_pt_mode != 'none'")
s_paths_work = s_paths.query("to_pt_mode == 'none'")
print('short paths to pt count:', len(s_paths_pt.index), '(of', str(count_before)+')')
print('short paths to work count:', len(s_paths_work.index), '(of', str(count_before)+')')

#%% calculate weighted statistics of path lengths
path_len_stats = []
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'length', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), axyindsignore=problem_axyinds, col_prefix='length_all', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths_pt, 'length', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), axyindsignore=problem_axyinds, col_prefix='length_pt', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths_work, 'length', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), axyindsignore=problem_axyinds, col_prefix='length_work', add_varname=True, add_n=True))
path_len_stats = pd.DataFrame(path_len_stats, columns=path_len_stats[0].keys())
path_len_stats.to_csv('outputs/path_stats/path_len_stats.csv')
path_len_stats

#%% print stats of lengths compared to reference lengths
path_len_stats = []
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'DT_len_diff', weight=None, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'DT_len_diff_rat', weight=None, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff_rat', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'DT_len_diff', weight=None, min_length=20, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff_filt', add_varname=True, add_n=True, printing=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'DT_len_diff_rat', weight=None, min_length=20, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='DT_lendiff_rat_filt', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'orig_offset', weight=None, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='orig_offset', add_varname=True, add_n=True))
path_len_stats.append(pstats.calc_basic_stats(s_paths, 'dest_offset', weight=None, percs=[5, 10, 15, 25, 75, 85, 90, 95], valueignore=-9999, col_prefix='dest_offset', add_varname=True, add_n=True))
path_len_stats = pd.DataFrame(path_len_stats, columns=path_len_stats[0].keys())
path_len_stats.to_csv('outputs/path_stats/path_len_diff_stats.csv')
path_len_stats

#%% plot DT len diff stats
s_paths_filt = pstats.filter_by_min_value(s_paths, 'length', 20)
s_paths_filt = pstats.filter_by_max_value(s_paths_filt, 'DT_len_diff', 7000)
fig = plots.scatterplot(s_paths_filt, xcol='length', ycol='DT_len', yignore=-9999, xlabel='Length (m)', ylabel='Ref. length (m)', line='xy')
fig.savefig('plots/paths_len_ref_len_scatter.png', format='png', dpi=300)
fig = plots.scatterplot(s_paths_filt, xcol='length', ycol='DT_len_diff', yignore=-9999, xlabel='Length (m)', ylabel='Ref. length diff. (m)')
fig.savefig('plots/paths_DT_len_diff_scatter.png', format='png', dpi=300)
fig = plots.boxplot(s_paths_filt, col='DT_len_diff', valignore=-9999, label='Ref. length diff. (m)')
fig.savefig('plots/paths_DT_len_diff_boxplot.png', format='png', dpi=300)
fig = plots.scatterplot(s_paths_filt, xcol='length', ycol='DT_len_diff_rat', yignore=-9999, xlabel='Length (m)', ylabel='Diff. to ref. length (%)', line='y0')
fig.savefig('plots/paths_DT_len_diff_rat_scatter.png', format='png', dpi=300)

#%% export paths with stats to file
s_paths.to_file('outputs/YKR_commutes_output/home_paths.gpkg', layer=walks_in_file+'_stats', driver='GPKG')


#### FILTER OUT PATHS FROM PROBLEMATIC AXYINDS ####
###################################################

#%% filter out paths from specific axyinds
count_before = len(s_paths)

paths = paths[~paths['from_axyind'].isin(problem_axyinds)]
s_paths = s_paths[~s_paths['from_axyind'].isin(problem_axyinds)]
s_paths_pt = s_paths_pt[~s_paths_pt['from_axyind'].isin(problem_axyinds)]
s_paths_work = s_paths_work[~s_paths_work['from_axyind'].isin(problem_axyinds)]

count_after = len(s_paths)
print('Filtered out:', count_before-count_after, 'shortest paths')
print('s_paths count:', len(s_paths))


#### STATFI GRID LEVEL NOISE STATISTICS ####
############################################

#%% #### group paths to PT by origin (axyind)
axy_groups = s_paths_pt.groupby('from_axyind')
print('paths to PT count:', len(s_paths_pt))
print('paths with null length count:', len(s_paths_pt.query('DT_len_diff == -9999')))

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
grid_stats.drop(columns=['grid_centr']).to_file('outputs/YKR_commutes_output/axyind_stats.gpkg', layer=axyind_stats_out_file, driver='GPKG')


#### PATH NOISE STATS #####
###########################

#%% print column names
print(s_paths.columns)

#%% filter out paths outside hel
s_paths = s_paths.query("b_inside_hel == 'yes'")
s_paths_pt = s_paths_pt.query("b_inside_hel == 'yes'")

#%%# ALL SHORTEST PATHS ###
sp_stats = []
sp_stats.append(pstats.calc_basic_stats(s_paths, 'nei', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, 'nei_norm', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, 'mdB', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '60dBl', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '65dBl', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '70dBl', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '60dBr', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '65dBr', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats.append(pstats.calc_basic_stats(s_paths, '70dBr', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_stats = pd.DataFrame(sp_stats, columns=sp_stats[0].keys())
sp_stats.to_csv('outputs/path_stats/sp_noise_stats.csv')

print(sp_stats)
# name      n     mean  median      std    p10    p25     p75     p90
# 0       nei  30160   99.659   73.50   93.015  14.60  35.30  135.10  220.70
# 1  nei_norm  30097    0.361    0.34    0.218   0.07   0.19    0.53    0.66
# 2       mdB  30097   57.545   57.46    7.450  47.49  52.19   63.32   67.37
# 3     60dBl  30160  210.138  142.32  214.735  12.89  63.96  292.65  496.86
# 4     65dBl  30160  135.926   75.36  175.588   0.00  21.61  179.49  342.39
# 5     70dBl  30160   52.591    8.31  101.213   0.00   0.00   64.26  150.49
# 6     60dBr  30097   46.221   40.76   32.729   4.10  18.40   73.97   99.99
# 7     65dBr  30097   29.929   20.51   29.753   0.00   5.12   47.19   79.38
# 8     70dBr  30097   11.683    1.90   20.244   0.00   0.00   14.17   37.18

#%%# SHORTEST PATHS TO PT STOPS ###
sp_pt_stats = []
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, 'nei', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, 'nei_norm', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, 'mdB', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '60dBl', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '65dBl', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '70dBl', weight='util', percs=[10, 25, 75, 90], valuemap=(-9999, 0), printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '60dBr', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '65dBr', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats.append(pstats.calc_basic_stats(s_paths_pt, '70dBr', weight='util', percs=[10, 25, 75, 90], valueignore=-9999, printing=False, add_varname=True, add_n=True))
sp_pt_stats = pd.DataFrame(sp_pt_stats, columns=sp_pt_stats[0].keys())
sp_pt_stats.to_csv('outputs/path_stats/sp_pt_noise_stats.csv')

print(sp_pt_stats)
# name      n     mean  median      std    p10    p25     p75     p90
# 0       nei  17892   96.193   71.80   87.263  14.70  34.90  131.10  212.00
# 1  nei_norm  17829    0.363    0.34    0.218   0.08   0.19    0.53    0.66
# 2       mdB  17829   57.633   57.55    7.435  47.61  52.28   63.36   67.43
# 3     60dBl  17892  203.155  139.65  203.464  14.81  63.63  283.49  474.97
# 4     65dBl  17892  130.214   73.85  164.957   0.00  21.61  172.85  330.34
# 5     70dBl  17892   49.868    7.91   94.374   0.00   0.00   62.74  141.91
# 6     60dBr  17829   46.584   41.19   32.805   4.47  18.63   74.53   99.99
# 7     65dBr  17829   30.058   20.70   29.857   0.00   5.17   47.30   79.78
# 8     70dBr  17829   11.700    1.86   20.357   0.00   0.00   14.14   37.23

#%%
