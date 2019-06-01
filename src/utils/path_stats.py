import pandas as pd
import geopandas as gpd
import numpy as np
import statistics as stats
import utils.files as files
import utils.geometry as geom_utils

def add_bool_within_hel_poly(gdf):
    # read city extent (polygon of Helsinki)
    hel_poly = files.get_hel_poly()
    hel_poly.buffer(30)
    # hel_poly = geom_utils.project_to_wgs(hel_poly)
    def inside_hel_extent(geometry):
        return 'yes' if geometry.within(hel_poly) else 'no'
    gdf['b_inside_hel'] = [inside_hel_extent(geom) for geom in gdf['geometry']]
    in_out_array = gdf['b_inside_hel']
    inside_count = len([x for x in in_out_array if x == 'yes'])
    outside_count = len([x for x in in_out_array if x == 'no'])
    print('count inside:', inside_count)
    print('count outside:', outside_count)
    return gdf
    
def extract_th_db_cols(paths_gdf, ths=[60, 65]):
    gdf = paths_gdf.copy()
    for th in ths:
        th_key = str(th)
        th_col = str(th)+'dB_len'
        gdf[th_col] = [th_noises[th_key] for th_noises in gdf['th_noises']]
    for th in ths:
        th_len_col = str(th)+'dB_len'
        th_rat_col = str(th)+'dB_rat'
        gdf[th_rat_col] = gdf.apply(lambda row: round((row[th_len_col]/row['length'])*100,2), axis=1)
    return gdf

def add_dt_length_diff_cols(paths_gdf):
    gdf = paths_gdf.copy()
    gdf['DT_len_diff'] = [-1 * diff for diff in gdf['DT_len_diff']]
    gdf['DT_len_diff_rat'] = gdf.apply(lambda row: round((row['DT_len_diff']/row['length'])*100,2), axis=1)
    return gdf

def explode_array_by_weights(df, var_col, weight_col):
    orig_array = df[var_col]
    weights = df[weight_col]
    if (len(orig_array) != len(weights)):
        print('length of weights does not match the length of values')
    expl_array = []
    for val, weight in zip(orig_array, weights):
        expl_array += [val] * int(round(weight*10))
    return expl_array

def calc_basic_stats(gdf, var_col, weight=None, percs=None, col_prefix='', printing=False):
    var_array = []
    if (weight is not None):
        if (printing == True): print('calculating weighted stats')
        var_array = explode_array_by_weights(gdf, var_col, weight)
    else:
        if (printing == True): print('calculating basic stats')
        var_array = gdf[var_col]

    mean = round(np.mean(var_array), 3)
    std = round(np.std(var_array), 3)
    median = round(np.median(var_array), 3)
    d = { col_prefix+'_mean': mean, col_prefix+'_median': median, col_prefix+'_std': std }

    if (percs is not None):
        for per in percs:
            d['p'+str(per)] = np.percentile(var_array, per)

    if (printing == True):
        print(d)

    return d
