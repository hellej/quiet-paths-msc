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

walks_in_file = 'run_6_set_1'
problem_axyinds = [3933756673875]

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
# axyinds = axyinds[:100]
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
    qp_stats = pstats.get_best_quiet_paths_of_max_len_diffs(od_id=key, df=qps, sp=sp, max_len_diffs=[100, 200, 300])
    qp_stats['count_qp'] = len(qps)
    all_od_stats.append({ **sp_stats, **qp_stats })
    # print('best_qp', od_stats)
    # print(qps[['path_id', 'len_sp', 'length', 'len_diff']])

#%% collect od stats
od_stats_df = pd.DataFrame(all_od_stats, columns=all_od_stats[0].keys())
print('od stats count:', len(od_stats_df))
# od stats count: 30097
od_stats_df.head()

#%%
od_stats_df['length_km'] = [length / 1000.0 for length in od_stats_df['length']]

#%% select subset of od stats based on path length ranges
# print(od_stats_df.columns)
od_stats_len_300_600 = od_stats_df.query('length > 300 and length < 600')
od_stats_len_700_1300 = od_stats_df.query('length > 700 and length < 1300')

#%% set quiet path names
qps = {'qp100': 'Diff. in dist. < 100 m', 'qp200': 'Diff. in dist. < 200 m', 'qp300': 'Diff. in dist. < 300 m'}

#%% path subsets
od_stats_p0_3000m = od_stats_df[(od_stats_df['length'] < 3000)]
od_stats_mdB_60_70 = od_stats_df[(od_stats_df['mdB'] > 60) & (od_stats_df['mdB'] < 70) & (od_stats_df['length'] < 3000)]

#%% qp counts regression
fig = plots.scatterplot(od_stats_p0_3000m, 'length_km', 'count_qp', linreg='topleft', xlabel='Shortest path length (km)', ylabel='Quiet path count',  large_text=True, yvaluemap=(-9999, 0), point_s=1)
fig.savefig('plots/quiet_path_plots/len-qp_count_linreg.png', format='png', dpi=300)

#%% OD distance - mdB diff qp 200
fig = plots.scatterplot(od_stats_mdB_60_70, 'length_km', 'mdB_diff_qp200', linreg=True, xlabel='Shortest path length (km)', ylabel='Diff. in mean dB',  title='Diff. in dist. < 200 m', large_text=True, yvaluemap=(-9999, 0), point_s=1)
fig.savefig('plots/quiet_path_plots/len-mdB_diff_qp200.png', format='png', dpi=300)

#%% qp count boxplots
fig = plots.boxplots_qp_counts(od_stats_p0_3000m, xlabel='Shortest path length (km)', ylabel='Quiet path count', large_text=True)
fig.savefig('plots/quiet_path_plots/len-qp_count_boxplot.png', format='png', dpi=300)

#%% db_diff histograms 300-600 m
for qp_name in qps.keys():
    fig = plots.plot_db_diff_histogram(od_stats_len_300_600, 'mdB_diff_'+ qp_name, yrange=5100, title=qps[qp_name],  xlabel='Diff. in mean dB', ylabel='Frequency', yvaluemap=(-9999, 0))
    fig.savefig(f'plots/quiet_path_plots/p300_600_mdB_diff_hist_{qp_name}.png', format='png', dpi=300)

#%% db_diff histograms 700-1300 m
for qp_name in qps.keys():
    fig = plots.plot_db_diff_histogram(od_stats_len_700_1300, 'mdB_diff_'+ qp_name, yrange=7100, title=qps[qp_name],  xlabel='Diff. in mean dB', ylabel='Frequency', yvaluemap=(-9999, 0))
    fig.savefig(f'plots/quiet_path_plots/p700_1300_mdB_diff_hist_{qp_name}.png', format='png', dpi=300)

#%% mdB - paths 300-600 m
for qp_name in qps.keys():
    fig = plots.scatterplot(od_stats_len_300_600, 'mdB', 'mdB_diff_'+ qp_name, linreg=True, yrange=(0, -20), xlabel='Mean dB', ylabel='Diff. in mean dB', title=qps[qp_name], large_text=True, yvaluemap=(-9999, 0), point_s=2)
    fig.savefig('plots/quiet_path_plots/p300_600_mdB_'+ qp_name +'.png', format='png', dpi=300)

#%% 60 dBl - paths 300-600 m
for qp_name in qps.keys():
    fig = plots.scatterplot(od_stats_len_300_600, '60dBl', '60dB_diff_'+ qp_name, linreg=True, xlabel='> 60 dB dist. (m)', ylabel='Diff. in > 60 dB dist. (m)', title=qps[qp_name], large_text=True, yvaluemap=(-9999, 0), ylims=(133, -650), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p300_600_60dBl_'+ qp_name +'.png', format='png', dpi=300)

#%% 65 dBl - paths 300-600 m
for qp_name in qps.keys():
    fig = plots.scatterplot(od_stats_len_300_600, '65dBl', '65dB_diff_'+ qp_name, linreg=True, xlabel='> 65 dB dist. (m)', ylabel='Diff. in > 65 dB dist. (m)', title=qps[qp_name], large_text=True, yvaluemap=(-9999, 0), ylims=(133, -650), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p300_600_65dBl_'+ qp_name +'.png', format='png', dpi=300)

#%% nei - paths 300-600 m
for qp_name in qps.keys():
    fig = plots.scatterplot(od_stats_len_300_600, 'nei', 'nei_diff_'+ qp_name, linreg=True, xlabel='Noise exposure index', ylabel='Diff. in noise exposure index', title=qps[qp_name], large_text=True, yvaluemap=(-9999, 0), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p300_600_nei_'+ qp_name +'.png', format='png', dpi=300)

#%% mdB - paths 700-1300 m
for qp_name in qps.keys():
    fig = plots.scatterplot(od_stats_len_700_1300, 'mdB', 'mdB_diff_'+ qp_name, linreg=True, xlabel='Mean dB', ylabel='Diff. in mean dB', title=qps[qp_name], large_text=True, yvaluemap=(-9999, 0), point_s=2)
    fig.savefig('plots/quiet_path_plots/p700_1300_mdB_'+ qp_name +'.png', format='png', dpi=300)

#%% 60 dBl - paths 700-1300 m
for qp_name in qps.keys():
    fig = plots.scatterplot(od_stats_len_700_1300, '60dBl', '60dB_diff_'+ qp_name, linreg=True, xlabel='> 60 dB dist. (m)', ylabel='Diff. in > 60 dB dist. (m)', title=qps[qp_name], large_text=True, yvaluemap=(-9999, 0), ylims=(238, -1430), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p700_1300_60dBl_'+ qp_name +'.png', format='png', dpi=300)

#%% 65 dBl - paths 700-1300 m
for qp_name in qps.keys():
    fig = plots.scatterplot(od_stats_len_700_1300, '65dBl', '65dB_diff_'+ qp_name, linreg=True, xlabel='> 65 dB dist. (m)', ylabel='Diff. in > 65 dB dist. (m)', title=qps[qp_name], large_text=True, yvaluemap=(-9999, 0), ylims=(238, -1430), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p700_1300_65dBl_'+ qp_name +'.png', format='png', dpi=300)

#%% nei - paths 700-1300 m
for qp_name in qps.keys():
    fig = plots.scatterplot(od_stats_len_700_1300, 'nei', 'nei_diff_'+ qp_name, linreg=True, xlabel='Noise exposure index', ylabel='Diff. in noise exposure index', title=qps[qp_name], large_text=True, yvaluemap=(-9999, 0), line='-xy', point_s=2)
    fig.savefig('plots/quiet_path_plots/p700_1300_nei_'+ qp_name +'.png', format='png', dpi=300)

#%% print quiet path length stats
def print_quiet_path_length_diff_stats(paths_subset, qps):
    for qp_name in qps.keys():
        len_diff_col = 'len_diff_'+ qp_name
        qp_len_diff_stats = pstats.calc_basic_stats(paths_subset, len_diff_col, valuemap=(-9999, 0), add_n=True)
        print('Stats of:', len_diff_col +':', qp_len_diff_stats)


### LONGER PATHS (700-1300 M) ###

#%% qp stats in terms of noise attribute 65dBr
noise_col = '65dBr'
od_subset = od_stats_len_700_1300[(od_stats_len_700_1300[noise_col] >= 10) & (od_stats_len_700_1300[noise_col] <= 100)]
print('path subset length stats:', pstats.calc_basic_stats(od_subset, 'length', valuemap=(-9999, 0), add_n=True), '\n')
print_quiet_path_length_diff_stats(od_subset, qps)
for qp_name in qps.keys():
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

# path subset length stats: {'n': 7842, 'mean': 981.758, 'median': 973.075, 'std': 170.217} 

# Stats of: len_diff_qp100: {'n': 7842, 'mean': 31.226, 'median': 20.8, 'std': 32.438}
# Stats of: len_diff_qp200: {'n': 7842, 'mean': 74.267, 'median': 64.1, 'std': 63.97}
# Stats of: len_diff_qp300: {'n': 7842, 'mean': 116.962, 'median': 103.4, 'std': 94.689}

# qp name: qp100 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp100
# name       10_40     40_70    70_100
# n       4358.000  2347.000  1137.000
# mean     -22.219   -35.032   -32.040
# median     0.000   -33.000   -28.000
# std       30.187    31.746    29.704

# qp name: qp200 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp200
# name       10_40     40_70    70_100
# n       4358.000  2347.000  1137.000
# mean     -29.368   -48.513   -47.749
# median   -20.000   -53.000   -54.000
# std       32.646    30.539    29.816

# qp name: qp300 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp300
# name       10_40     40_70    70_100
# n       4358.000  2347.000  1137.000
# mean     -32.236   -55.576   -56.675
# median   -26.000   -60.000   -64.000
# std       33.375    28.005    26.710

#%% qp stats in terms of noise attribute dBmean
noise_col = 'mdB'
od_subset = od_stats_len_700_1300[(od_stats_len_700_1300[noise_col] >= 55) & (od_stats_len_700_1300[noise_col] <= 80)]
print('path subset length stats:', pstats.calc_basic_stats(od_subset, 'length', valuemap=(-9999, 0), add_n=True), '\n')
print_quiet_path_length_diff_stats(od_subset, qps)
for qp_name in qps.keys():
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

# path subset length stats: {'n': 6925, 'mean': 979.177, 'median': 969.82, 'std': 169.547} 

# Stats of: len_diff_qp100: {'n': 6925, 'mean': 31.796, 'median': 21.5, 'std': 32.691}
# Stats of: len_diff_qp200: {'n': 6925, 'mean': 77.398, 'median': 70.1, 'std': 64.435}
# Stats of: len_diff_qp300: {'n': 6925, 'mean': 122.474, 'median': 113.1, 'std': 94.368}

# qp name: qp100 noise col: mdB qp_noise_diff_col: mdB_diff_qp100
# name       55_60     60_65     65_80
# n       2901.000  2379.000  1654.000
# mean      -2.401    -3.876    -4.972
# median    -1.410    -2.780    -3.590
# std        2.831     4.093     4.995

# qp name: qp200 noise col: mdB qp_noise_diff_col: mdB_diff_qp200
# name       55_60     60_65     65_80
# n       2901.000  2379.000  1654.000
# mean      -3.555    -5.883    -7.782
# median    -3.040    -5.560    -7.870
# std        3.229     4.450     5.459

# qp name: qp300 noise col: mdB qp_noise_diff_col: mdB_diff_qp300
# name       55_60     60_65     65_80
# n       2901.000  2379.000  1654.000
# mean      -4.224    -7.151    -9.593
# median    -3.870    -7.270   -10.220
# std        3.424     4.461     5.371


### SHORTER PATHS (300-400 M) ###

#%% qp stats in terms of noise attribute 65dBr
noise_col = '65dBr'
od_subset = od_stats_len_300_600[(od_stats_len_300_600[noise_col] >= 10) & (od_stats_len_300_600[noise_col] <= 100)]
print('path subset length stats:', pstats.calc_basic_stats(od_subset, 'length', valuemap=(-9999, 0), add_n=True), '\n')
print_quiet_path_length_diff_stats(od_subset, qps)
for qp_name in qps.keys():
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

# path subset length stats: {'n': 4338, 'mean': 447.577, 'median': 444.83, 'std': 85.929} 

# Stats of: len_diff_qp100: {'n': 4338, 'mean': 18.127, 'median': 0.0, 'std': 28.386}
# Stats of: len_diff_qp200: {'n': 4338, 'mean': 40.928, 'median': 5.8, 'std': 55.887}
# Stats of: len_diff_qp300: {'n': 4338, 'mean': 60.299, 'median': 16.6, 'std': 80.83}

# qp name: qp100 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp100
# name       10_40     40_70   70_100
# n       2442.000  1108.000  788.000
# mean     -12.433   -23.836  -21.551
# median     0.000     0.000    0.000
# std       26.053    31.444   27.622

# qp name: qp200 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp200
# name       10_40     40_70   70_100
# n       2442.000  1108.000  788.000
# mean     -15.687   -32.868  -32.501
# median     0.000   -28.500  -29.500
# std       28.558    33.445   29.946

# qp name: qp300 noise col: 65dBr qp_noise_diff_col: 65dB_diff_r_qp300
# name       10_40     40_70   70_100
# n       2442.000  1108.000  788.000
# mean     -16.760   -36.801  -37.905
# median     0.000   -36.000  -40.000
# std       29.328    33.738   30.313

#%% qp stats in terms of noise attribute dBmean
noise_col = 'mdB'
od_subset = od_stats_len_300_600[(od_stats_len_300_600[noise_col] >= 55) & (od_stats_len_300_600[noise_col] <= 80)]
print('path subset length stats:', pstats.calc_basic_stats(od_subset, 'length', valuemap=(-9999, 0), add_n=True), '\n')
print_quiet_path_length_diff_stats(od_subset, qps)
for qp_name in qps.keys():
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

# path subset length stats: {'n': 4103, 'mean': 444.218, 'median': 439.18, 'std': 86.212} 

# Stats of: len_diff_qp100: {'n': 4103, 'mean': 18.537, 'median': 0.0, 'std': 28.642}
# Stats of: len_diff_qp200: {'n': 4103, 'mean': 42.512, 'median': 8.1, 'std': 56.663}
# Stats of: len_diff_qp300: {'n': 4103, 'mean': 63.612, 'median': 20.9, 'std': 82.688}

# qp name: qp100 noise col: mdB qp_noise_diff_col: mdB_diff_qp100
# name       55_60     60_65     65_80
# n       1616.000  1404.000  1092.000
# mean      -1.622    -2.614    -3.040
# median     0.000     0.000     0.000
# std        2.664     3.997     4.269

# qp name: qp200 noise col: mdB qp_noise_diff_col: mdB_diff_qp200
# name       55_60     60_65     65_80
# n       1616.000  1404.000  1092.000
# mean      -2.321    -4.063    -5.111
# median     0.000    -2.255    -3.790
# std        3.185     4.674     5.308

# qp name: qp300 noise col: mdB qp_noise_diff_col: mdB_diff_qp300
# name       55_60     60_65     65_80
# n       1616.000  1404.000  1092.000
# mean      -2.689    -4.885    -6.428
# median     0.000    -3.785    -5.750
# std        3.425     5.033     5.808

#%%
