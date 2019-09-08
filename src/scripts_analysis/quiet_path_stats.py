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
axyinds = axyinds[:20]
p = p[p['from_axyind'].isin(axyinds)]
print('filtered paths count:', len(p))

#%% add & extract dB exposure columnds to df
p = pstats.extract_th_db_cols(p, ths=[60, 65, 70], add_ratios=True)
# print(p.columns)
p = p[qp_cols]
p[['path_id', 'len_diff', 'len_diff_r', '60dBl', '60dBr']].head()

#%%
# group by od id (short and quiet paths of OD-pair are in the same group)
all_od_stats = []
print('OD count:', len(p['od_id'].unique()))
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
od_stats_df.head()

#%% divide od stats to length ranges
# print(od_stats_df.columns)
od_stats_len_600_1000 = od_stats_df.query('length > 600 and length < 1000')
od_stats_len_800_1500 = od_stats_df.query('length > 800 and length < 1500')


#%% create scatterplots

#%% mdB
fig = plots.scatterplot(od_stats_len_800_1500, 'mdB', 'mdB_diff_qp200', yvaluemap=(-9999, 0))

#%%
fig = plots.scatterplot(od_stats_len_800_1500, '60dBl', '60dB_diff_qp200', yvaluemap=(-9999, 0), line='-xy')
#%%
fig = plots.scatterplot(od_stats_len_800_1500, '65dBl', '65dB_diff_qp200', yvaluemap=(-9999, 0), line='-xy')

#%%
fig = plots.scatterplot(od_stats_len_800_1500, '65dBl', '65dB_diff_r_qp200', yvaluemap=(-9999, 0))

#%%
fig = plots.scatterplot(od_stats_len_600_1000, '60dBl', '60dB_diff_qp200', yvaluemap=(-9999, 0), line='-xy')

#%%
all_od_qp_stats = []
for min_lim in [0, 20, 40, 60, 80]:
    max_lim = min_lim + 20
    od_stats = od_stats_len_600_1000[(od_stats_len_600_1000['65dBr'] > min_lim) & (od_stats_len_600_1000['65dBr'] <= max_lim)]
    col_name = str(min_lim)+'_'+str(max_lim)
    od_qp_stats = pstats.calc_basic_stats(od_stats, '65dB_diff_r_qp200', col_prefix=col_name, add_varname=True, valuemap=(-9999, 0), add_n=True)
    all_od_qp_stats.append(od_qp_stats)
od_qp_stats_df = pd.DataFrame(all_od_qp_stats, columns=all_od_qp_stats[0].keys())
od_qp_stats_df

#%%
all_od_qp_stats = []
for min_lim in [0, 20, 40, 60, 80]:
    max_lim = min_lim + 20
    od_stats = od_stats_len_800_1500[(od_stats_len_800_1500['65dBr'] > min_lim) & (od_stats_len_800_1500['65dBr'] <= max_lim)]
    col_name = str(min_lim)+'_'+str(max_lim)
    od_qp_stats = pstats.calc_basic_stats(od_stats, '65dB_diff_r_qp300', col_prefix=col_name, add_varname=True, valuemap=(-9999, 0), add_n=True)
    all_od_qp_stats.append(od_qp_stats)
od_qp_stats_df = pd.DataFrame(all_od_qp_stats, columns=all_od_qp_stats[0].keys())
od_qp_stats_df

#%%
