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

#%% filter out paths with -9999 values
p = pstats.filter_out_null_paths(paths)
#%% filter out paths from problematic axyinds
p = pstats.filter_out_paths_from_axyinds(p, problem_axyinds)
#%% filter out paths outside Helsinki
p = pstats.filter_out_paths_outside_hel(p)


#### QUIET PATH NOISE STATS #####
#%%
print(paths.columns)
qp_cols = ['od_id', 'path_id', 'len_diff', 'len_diff_r', 'length', 'nei',
       'nei_diff', 'nei_diff_r', 'nei_norm', 'noises', 'noises_diff', 'th_noises', 
       'th_noises_diff', 'util', 'mdB', '60dBl', '65dBl', '70dBl', '60dBr', '65dBr', '70dBr']

#%% rename columns
p['path_id'] = p['id']
p['nei_diff_r'] = p['nei_diff_rat']
p['len_diff_r'] = p['len_diff_rat']
print(p[['od_id', 'path_id']].head())

#%% select subset of paths
axyinds = p['from_axyind'].unique()
axyinds = axyinds[:100]
p = p[p['from_axyind'].isin(axyinds)]
print('filtered paths count:', len(p))

#%% add & extract dB exposure columnds to df
p = pstats.extract_th_db_cols(p, ths=[60, 65, 70], add_ratios=True)
p = p[qp_cols]
p[['path_id', 'len_diff', 'len_diff_r', '60dBl', '60dBr']].head()

#%% Calculate quiet path stats per od
# group by od id (short and quiet paths of OD-pair are in the same group)
all_od_stats = []
print('OD count:', len(p['od_id'].unique()))
# OD count: 30100
grouped = p.groupby('od_id')
for key, group in grouped:
    # if (key != '3801256680625_HSL:1320224' and key != '3801256680875_HSL:1320111'):
    #     continue
    sps = group.query("path_id == 'short_p'").to_dict(orient='records')
    sp = sps[0] if len(sps) > 0 else None
    if (sp is None):
        continue
    qps = group.query("path_id != 'short_p'")[qp_cols]
    # qps['len_sp'] = sp['length']
    qps['mdB_diff'] = [mdB - sp['mdB'] for mdB in qps['mdB']]
    # db len diffs
    qps['60dB_diff'] = [round(dblen - sp['60dBl'], 1) for dblen in qps['60dBl']]
    qps['65dB_diff'] = [round(dblen - sp['65dBl'], 1) for dblen in qps['65dBl']]
    # db len diff ratios
    qps['60dB_diff_r'] = [ round((dblendiff/sp['60dBl'])*100) if sp['60dBl'] != 0 else 0 for dblendiff in qps['60dB_diff']]
    qps['65dB_diff_r'] = [ round((dblendiff/sp['65dBl'])*100) if sp['65dBl'] != 0 else 0 for dblendiff in qps['65dB_diff']]
    # collect
    sp_stats = {'od_id': key, 'length': sp['length'], 'mdB': sp['mdB'], 'nei': sp['nei'], 'nei_norm': sp['nei_norm'], 'util': sp['util'], '60dBl': sp['60dBl'], '65dBl': sp['65dBl'], '60dBr': sp['60dBr'], '65dBr': sp['65dBr'] }
    qp_stats = pstats.get_best_quiet_paths_of_max_len_diffs(od_id=key, df=qps, sp=sp, max_len_diffs=[30, 100, 150, 200, 300, 500])
    all_od_stats.append({ **sp_stats, **qp_stats })
    # print('best_qp', od_stats)
    # print(qps[['path_id', 'len_sp', 'length', 'len_diff']])

#%% collect od stats
od_stats_df = pd.DataFrame(all_od_stats, columns=all_od_stats[0].keys())
print('od stats count:', len(od_stats_df))
# od stats count: 30097
od_stats_df.head()

#%% select subset of od stats based on path length ranges
# print(od_stats_df.columns)
od_stats_len_300_600 = od_stats_df.query('length > 300 and length < 600')
od_stats_len_700_1300 = od_stats_df.query('length > 700 and length < 1300')

#%% set quiet path names
qp_names = ['qp100', 'qp200', 'qp300']

#%% mdB - paths 300-600 m
for qp_name in qp_names:
    fig = plots.scatterplot(od_stats_len_300_600, 'mdB', 'mdB_diff_'+ qp_name, xlabel='Mean dB', ylabel='Diff. in mean dB', yvaluemap=(-9999, 0), point_s=2)
    fig.savefig('plots/quiet_path_plots/p300_600_mdB_'+ qp_name +'.png', format='png', dpi=300)

#%% 60 dBl - paths 300-600 m
for qp_name in qp_names:
    fig = plots.scatterplot(od_stats_len_300_600, '60dBl', '60dB_diff_'+ qp_name, xlabel='> 60 dB dist. (m)', ylabel='Diff. in > 60 dB dist. (m)', yvaluemap=(-9999, 0), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p300_600_60dBl_'+ qp_name +'.png', format='png', dpi=300)

#%% 65 dBl - paths 300-600 m
for qp_name in qp_names:
    fig = plots.scatterplot(od_stats_len_300_600, '65dBl', '65dB_diff_'+ qp_name, xlabel='> 65 dB dist. (m)', ylabel='Diff. in > 65 dB dist. (m)', yvaluemap=(-9999, 0), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p300_600_65dBl_'+ qp_name +'.png', format='png', dpi=300)

#%% nei - paths 300-600 m
for qp_name in qp_names:
    fig = plots.scatterplot(od_stats_len_300_600, 'nei', 'nei_diff_'+ qp_name, xlabel='Noise exposure (index)', ylabel='Diff. in noise exposure (index)', yvaluemap=(-9999, 0), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p300_600_nei_'+ qp_name +'.png', format='png', dpi=300)

#%% mdB - paths 700-1300 m
for qp_name in qp_names:
    fig = plots.scatterplot(od_stats_len_700_1300, 'mdB', 'mdB_diff_'+ qp_name, xlabel='Mean dB', ylabel='Diff. in mean dB', yvaluemap=(-9999, 0), point_s=2)
    fig.savefig('plots/quiet_path_plots/p700_1300_mdB_'+ qp_name +'.png', format='png', dpi=300)

#%% 60 dBl - paths 700-1300 m
for qp_name in qp_names:
    fig = plots.scatterplot(od_stats_len_700_1300, '60dBl', '60dB_diff_'+ qp_name, xlabel='> 60 dB dist. (m)', ylabel='Diff. in > 60 dB dist. (m)', yvaluemap=(-9999, 0), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p700_1300_60dBl_'+ qp_name +'.png', format='png', dpi=300)

#%% 65 dBl - paths 700-1300 m
for qp_name in qp_names:
    fig = plots.scatterplot(od_stats_len_700_1300, '65dBl', '65dB_diff_'+ qp_name, xlabel='> 65 dB dist. (m)', ylabel='Diff. in > 65 dB dist. (m)', yvaluemap=(-9999, 0), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p700_1300_65dBl_'+ qp_name +'.png', format='png', dpi=300)

#%% nei - paths 700-1300 m
for qp_name in qp_names:
    fig = plots.scatterplot(od_stats_len_700_1300, 'nei', 'nei_diff_'+ qp_name, xlabel='Noise exposure (index)', ylabel='Diff. in noise exposure (index)', yvaluemap=(-9999, 0), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p700_1300_nei_'+ qp_name +'.png', format='png', dpi=300)

#%% print quiet path length stats
def print_quiet_path_length_diff_stats(paths_subset, qp_names):
    for qp_name in qp_names:
        len_diff_col = 'len_diff_'+ qp_name
        qp_len_diff_stats = pstats.calc_basic_stats(paths_subset, len_diff_col, valuemap=(-9999, 0), add_n=True)
        print('Stats of:', len_diff_col +':', qp_len_diff_stats)


### LONGER PATHS (700-1300 M) ###

#%% qp stats in terms of noise attribute 65dBr
noise_col = '65dBr'
od_subset = od_stats_len_700_1300[(od_stats_len_700_1300[noise_col] >= 10) & (od_stats_len_700_1300[noise_col] <= 100)]
print('path subset length stats:', pstats.calc_basic_stats(od_subset, 'length', valuemap=(-9999, 0), add_n=True), '\n')
print_quiet_path_length_diff_stats(od_subset, qp_names)
for qp_name in qp_names:
    # qp_name = 'qp100'
    qp_noise_diff_col = '65dB_diff_r_'+qp_name
    qp_len_diff_col = 'len_diff_'+qp_name
    all_od_qp_stats = []
    for min_lim in [10, 40, 70]:
        max_lim = min_lim + 30
        od_stats = od_stats_len_700_1300[(od_stats_len_700_1300[noise_col] >= min_lim) & (od_stats_len_700_1300[noise_col] <= max_lim)]
        col_name = str(min_lim)+'_'+str(max_lim)
        od_qp_stats = pstats.calc_basic_stats(od_stats, qp_noise_diff_col, col_prefix=col_name, add_varname=True, valuemap=(-9999, 0), add_n=True)
        all_od_qp_stats.append(od_qp_stats)
    od_qp_stats_df = pd.DataFrame(all_od_qp_stats, columns=all_od_qp_stats[0].keys())
    od_qp_stats_df = od_qp_stats_df.set_index('name').transpose()
    print('\nqp name:', qp_name, 'noise col:', noise_col, 'qp_noise_diff_col:', qp_noise_diff_col)
    print(od_qp_stats_df)

# path subset length stats: {'n': 7780, 'mean': 981.686, 'median': 973.065, 'std': 170.272} 

# Stats of: len_diff_qp100: {'n': 7780, 'mean': 30.369, 'median': 19.1, 'std': 32.207}
# Stats of: len_diff_qp200: {'n': 7780, 'mean': 74.653, 'median': 66.7, 'std': 63.338}
# Stats of: len_diff_qp300: {'n': 7780, 'mean': 117.032, 'median': 107.0, 'std': 93.031}

# qp name: qp100 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp100
# name       10_40     40_70    70_100
# n       4455.000  2216.000  1109.000
# mean     -21.146   -31.932   -29.655
# median     0.000   -28.000   -25.000
# std       29.483    31.022    29.416

# qp name: qp200 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp200
# name       10_40     40_70    70_100
# n       4455.000  2216.000  1109.000
# mean     -28.999   -46.272   -45.674
# median   -20.000   -49.000   -51.000
# std       32.351    30.740    30.412

# qp name: qp300 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp300
# name       10_40     40_70    70_100
# n       4455.000  2216.000  1109.000
# mean     -32.203   -53.467   -55.326
# median   -27.000   -58.500   -62.000
# std       33.291    28.922    27.439

#%% qp stats in terms of noise attribute dBmean
noise_col = 'mdB'
od_subset = od_stats_len_700_1300[(od_stats_len_700_1300[noise_col] >= 55) & (od_stats_len_700_1300[noise_col] <= 80)]
print('path subset length stats:', pstats.calc_basic_stats(od_subset, 'length', valuemap=(-9999, 0), add_n=True), '\n')
print_quiet_path_length_diff_stats(od_subset, qp_names)
for qp_name in qp_names:
    # qp_name = 'qp100'
    qp_noise_diff_col = 'mdB_diff_'+qp_name
    qp_len_diff_col = 'len_diff_'+qp_name
    all_od_qp_stats = []
    for db_range in [(55, 60), (60, 65), (65, 80)]:
        od_stats = od_stats_len_700_1300[(od_stats_len_700_1300[noise_col] >= db_range[0]) & (od_stats_len_700_1300[noise_col] <= db_range[1])]
        col_name = str(db_range[0])+'_'+str(db_range[1])
        od_qp_stats = pstats.calc_basic_stats(od_stats, qp_noise_diff_col, col_prefix=col_name, add_varname=True, valuemap=(-9999, 0), add_n=True)
        all_od_qp_stats.append(od_qp_stats)
    od_qp_stats_df = pd.DataFrame(all_od_qp_stats, columns=all_od_qp_stats[0].keys())
    od_qp_stats_df = od_qp_stats_df.set_index('name').transpose()
    print('\nqp name:', qp_name, 'noise col:', noise_col, 'qp_noise_diff_col:', qp_noise_diff_col)
    print(od_qp_stats_df)

# path subset length stats: {'n': 6742, 'mean': 978.106, 'median': 968.32, 'std': 169.195} 

# Stats of: len_diff_qp100: {'n': 6742, 'mean': 31.376, 'median': 21.0, 'std': 32.478}
# Stats of: len_diff_qp200: {'n': 6742, 'mean': 78.985, 'median': 74.7, 'std': 63.502}
# Stats of: len_diff_qp300: {'n': 6742, 'mean': 126.094, 'median': 121.6, 'std': 92.84}

# qp name: qp100 noise col: mdB qp_noise_diff_col: mdB_diff_qp100
# name       55_60     60_65     65_80
# n       2907.000  2259.000  1582.000
# mean      -2.261    -3.499    -4.542
# median    -1.300    -2.360    -3.125
# std        2.682     3.890     4.795

# qp name: qp200 noise col: mdB qp_noise_diff_col: mdB_diff_qp200
# name       55_60     60_65     65_80
# n       2907.000  2259.000  1582.000
# mean      -3.461    -5.597    -7.468
# median    -3.000    -5.320    -7.695
# std        3.046     4.260     5.370

# qp name: qp300 noise col: mdB qp_noise_diff_col: mdB_diff_qp300
# name       55_60     60_65     65_80
# n       2907.000  2259.000  1582.000
# mean      -4.138    -6.893    -9.398
# median    -3.880    -7.040   -10.115
# std        3.204     4.301     5.351


### SHORTER PATHS (300-400 M) ###

#%% qp stats in terms of noise attribute 65dBr
noise_col = '65dBr'
od_subset = od_stats_len_300_600[(od_stats_len_300_600[noise_col] >= 10) & (od_stats_len_300_600[noise_col] <= 100)]
print('path subset length stats:', pstats.calc_basic_stats(od_subset, 'length', valuemap=(-9999, 0), add_n=True), '\n')
print_quiet_path_length_diff_stats(od_subset, qp_names)
for qp_name in qp_names:
    # qp_name = 'qp100'
    qp_noise_diff_col = '65dB_diff_r_'+qp_name
    qp_len_diff_col = 'len_diff_'+qp_name
    all_od_qp_stats = []
    for min_lim in [10, 40, 70]:
        max_lim = min_lim + 30
        od_stats = od_stats_len_300_600[(od_stats_len_300_600[noise_col] >= min_lim) & (od_stats_len_300_600[noise_col] <= max_lim)]
        col_name = str(min_lim)+'_'+str(max_lim)
        od_qp_stats = pstats.calc_basic_stats(od_stats, qp_noise_diff_col, col_prefix=col_name, add_varname=True, valuemap=(-9999, 0), add_n=True)
        all_od_qp_stats.append(od_qp_stats)
    od_qp_stats_df = pd.DataFrame(all_od_qp_stats, columns=all_od_qp_stats[0].keys())
    od_qp_stats_df = od_qp_stats_df.set_index('name').transpose()
    print('\nqp name:', qp_name, 'noise col:', noise_col, 'qp_noise_diff_col:', qp_noise_diff_col)
    print(od_qp_stats_df)

# path subset length stats: {'n': 4353, 'mean': 447.379, 'median': 444.03, 'std': 86.149} 

# Stats of: len_diff_qp100: {'n': 4353, 'mean': 18.119, 'median': 0.0, 'std': 28.083}
# Stats of: len_diff_qp200: {'n': 4353, 'mean': 43.53, 'median': 12.4, 'std': 57.537}
# Stats of: len_diff_qp300: {'n': 4353, 'mean': 64.796, 'median': 20.9, 'std': 83.026}

# qp name: qp100 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp100
# name       10_40     40_70   70_100
# n       2452.000  1101.000  801.000
# mean     -12.487   -22.567  -20.469
# median     0.000     0.000    0.000
# std       25.845    30.900   27.331

# qp name: qp200 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp200
# name       10_40     40_70   70_100
# n       2452.000  1101.000  801.000
# mean     -16.175   -32.321  -31.236
# median     0.000   -26.000  -28.000
# std       28.611    33.331   30.078

# qp name: qp300 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp300
# name       10_40     40_70   70_100
# n       2452.000  1101.000  801.000
# mean     -17.554   -36.409  -38.187
# median     0.000   -36.000  -41.000
# std       29.596    33.740   30.593

#%% qp stats in terms of noise attribute dBmean
noise_col = 'mdB'
od_subset = od_stats_len_300_600[(od_stats_len_300_600[noise_col] >= 55) & (od_stats_len_300_600[noise_col] <= 80)]
print('path subset length stats:', pstats.calc_basic_stats(od_subset, 'length', valuemap=(-9999, 0), add_n=True), '\n')
print_quiet_path_length_diff_stats(od_subset, qp_names)
for qp_name in qp_names:
    # qp_name = 'qp100'
    qp_noise_diff_col = 'mdB_diff_'+qp_name
    qp_len_diff_col = 'len_diff_'+qp_name
    all_od_qp_stats = []
    for db_range in [(55, 60), (60, 65), (65, 80)]:
        od_stats = od_stats_len_300_600[(od_stats_len_300_600[noise_col] >= db_range[0]) & (od_stats_len_300_600[noise_col] <= db_range[1])]
        col_name = str(db_range[0])+'_'+str(db_range[1])
        od_qp_stats = pstats.calc_basic_stats(od_stats, qp_noise_diff_col, col_prefix=col_name, add_varname=True, valuemap=(-9999, 0), add_n=True)
        all_od_qp_stats.append(od_qp_stats)
    od_qp_stats_df = pd.DataFrame(all_od_qp_stats, columns=all_od_qp_stats[0].keys())
    od_qp_stats_df = od_qp_stats_df.set_index('name').transpose()
    print('\nqp name:', qp_name, 'noise col:', noise_col, 'qp_noise_diff_col:', qp_noise_diff_col)
    print(od_qp_stats_df)

# path subset length stats: {'n': 4077, 'mean': 443.856, 'median': 438.53, 'std': 86.273} 

# Stats of: len_diff_qp100: {'n': 4077, 'mean': 18.938, 'median': 0.0, 'std': 28.514}
# Stats of: len_diff_qp200: {'n': 4077, 'mean': 47.321, 'median': 15.8, 'std': 59.381}
# Stats of: len_diff_qp300: {'n': 4077, 'mean': 72.22, 'median': 31.6, 'std': 86.285}

# qp name: qp100 noise col: mdB qp_noise_diff_col: mdB_diff_qp100
# name       55_60     60_65     65_80
# n       1624.000  1357.000  1107.000
# mean      -1.565    -2.562    -2.758
# median     0.000     0.000     0.000
# std        2.542     3.921     3.976

# qp name: qp200 noise col: mdB qp_noise_diff_col: mdB_diff_qp200
# name       55_60     60_65     65_80
# n       1624.000  1357.000  1107.000
# mean      -2.364    -4.285    -4.959
# median    -0.500    -2.970    -3.550
# std        3.095     4.590     5.228

# qp name: qp300 noise col: mdB qp_noise_diff_col: mdB_diff_qp300
# name       55_60     60_65     65_80
# n       1624.000  1357.000  1107.000
# mean      -2.815    -5.156    -6.417
# median    -1.170    -4.960    -5.940
# std        3.348     4.862     5.769

#%%
