#%% IMPORT MODULES FOR ORIGIN NOISE AGGREGATION
import pandas as pd
import geopandas as gpd
import utils.utils as utils

#%% READ PATH NOISES
path_noises = gpd.read_file('outputs/path_noises.gpkg', layer='path_noises')
path_noises.head(5)

#%% GROUP PATH NOISES BY ORIGIN
grouped = path_noises.groupby(by='from_id')

# CALCULATE MEAN EXPOSURES ABOVE THREE THRESHOLDS
ths = [60, 65, 70]
th_len_cols = [str(th)+'dB_avg_len' for th in ths]
th_ratio_cols = [str(th)+'dB_avg_ratio' for th in ths]
dfs = []
for key, values in grouped:
    path_count = values['count'].sum()
    len_sum = 0
    th_sum_lens = [0, 0, 0]
    for idx, row in values.iterrows():
        len_sum += row['total_length'] * row['count']
        for idx, val in enumerate(ths):
            th_column = 'th_' + str(ths[idx]) + '_len'
            th_sum_lens[idx] = th_sum_lens[idx] + row['count'] * row[th_column]
    avg_total_len = int(round(len_sum / path_count))
    # calculate average lengths of above threshold exposures (m) to noises
    th_avg_lens = [int(round(th_sum/path_count)) for th_sum in th_sum_lens]
    # calculate average ratios of above threshold exposures (m) to total path lengths (%)
    th_avg_ratios = [int(round(th_len/avg_total_len,2)*100) for th_len in th_avg_lens]
    # collect results to dictionaries -> DF
    d1 = {'from_id': key, th_len_cols[0]: th_avg_lens[0], th_len_cols[1]: th_avg_lens[1], th_len_cols[2]: th_avg_lens[2]}
    d2 = {'avg_total_len': avg_total_len, th_ratio_cols[0]: th_avg_ratios[0], th_ratio_cols[1]: th_avg_ratios[1], th_ratio_cols[2]: th_avg_ratios[2]}
    dfs.append(pd.DataFrame({**d1, **d2}, index=[0]))

from_path_noise_avgs = pd.concat(dfs)
from_path_noise_avgs

#%% JOIN PATH NOISE AVERAGES TO ORIGINAL GRID
grid = utils.get_grid()
grid_noise_avgs = pd.merge(grid, from_path_noise_avgs, how='inner', left_on='INDEX', right_on='from_id')
grid_noise_avgs

#%% EXPORT TO FILE
grid_noise_avgs.to_file('outputs/grid_noises.gpkg', layer='avg_noise_exps', driver='GPKG')

#%%
