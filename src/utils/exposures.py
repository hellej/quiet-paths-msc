import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import ast
import utils.geometry as geom_utils

def add_noises_to_split_lines(noise_polygons, split_lines):
    split_lines['geom_line'] = split_lines['geometry']
    split_lines['geom_point'] = [geom_utils.get_line_middle_point(geom) for geom in split_lines['geometry']]
    split_lines['geometry'] = split_lines['geom_point']
    line_noises = gpd.sjoin(split_lines, noise_polygons, how='left', op='within')
    line_noises['geometry'] = line_noises['geom_line']
    return line_noises[['geometry', 'length', 'db_lo', 'db_hi', 'index_right']]

def get_exposure_lines(line_geom, noise_polys):
    split_lines = geom_utils.get_split_lines_gdf(line_geom, noise_polys)
    if (split_lines.empty):
        return gpd.GeoDataFrame()
    line_noises = add_noises_to_split_lines(noise_polys, split_lines)
    line_noises = line_noises.fillna(40)
    return line_noises

def get_exposures(line_noises):
    noise_groups = line_noises.groupby('db_lo')
    noise_dict = {}
    for key, values in noise_groups:
        tot_len = round(values['length'].sum(),3)
        noise_dict[int(key)] = tot_len
    return noise_dict

def get_exposures_for_geom(line_geom, noise_polys):
    line_noises = get_exposure_lines(line_geom, noise_polys)
    return get_exposures(line_noises)

def get_exposure_times(d: 'dict of db: length', speed: 'float: m/s', minutes: bool):
    exp_t_d = {}
    for key in d.keys():
        exp_t_d[key] = round((d[key]/speed)/(60 if minutes else 1), (4 if minutes else 1))
    return exp_t_d

def get_th_exposures(noise_dict, ths):
    th_count = len(ths)
    th_lens = [0] * len(ths)
    for th in noise_dict.keys():
        th_len = noise_dict[th]
        for idx in range(th_count):
            if (th >= ths[idx]):
                th_lens[idx] = th_lens[idx] + th_len
    th_noise_dict = {}
    for idx in range(th_count):
        th_noise_dict[ths[idx]] = round(th_lens[idx],3)
    return th_noise_dict

def plot_exposure_lengths(exp_lens):
    plt.style.use('default')

    fig, ax = plt.subplots(figsize=(7,7))
    dbs = list(exp_lens.keys())
    lengths = list(exp_lens.values())

    ax.bar(dbs, lengths, width=3)
    # ax.set_xlim([30, 80])

    yticks = list(range(0, int(max(lengths)+10), 50))
    yticks = [int(tick) for tick in yticks]
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticks, fontsize=15)

    if (max(dbs)>85):
        raise Exception('Adjust xticks to show high dB exposures!!')
    xticks = np.arange(40, 90, step=5)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticks, fontsize=15)

    ax.set_ylabel('Distance (m)')
    ax.set_xlabel('Traffic noise (dB)')


    ax.xaxis.label.set_size(16)
    ax.yaxis.label.set_size(16)

    ax.xaxis.labelpad = 10
    ax.yaxis.labelpad = 10

    return fig

def plot_exposure_times(exp_times):
    plt.style.use('default')

    fig, ax = plt.subplots(figsize=(7,7))
    dbs = list(exp_times.keys())
    times = list(exp_times.values())

    ax.bar(dbs, times, width=3)
    # ax.set_xlim([30, 80])

    if (max(times)>5):
        raise Exception('Adjust yticks to show long exposures!!')
    yticks = list(range(0, 6, 1))
    yticks = [int(tick) for tick in yticks]
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticks, fontsize=15)

    if (max(dbs)>85):
        raise Exception('Adjust xticks to show high dB exposures!!')
    xticks = np.arange(40, 90, step=5)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticks, fontsize=15)

    ax.set_ylabel('Duration (min)')
    ax.set_xlabel('Traffic noise (dB)')

    ax.xaxis.label.set_size(16)
    ax.yaxis.label.set_size(16)

    ax.xaxis.labelpad = 10
    ax.yaxis.labelpad = 10

    return fig

def get_noise_attrs_to_split_lines(gdf, noise_polys):
    gdf['geometry'] = gdf['mid_point']
    split_line_noises = gpd.sjoin(gdf, noise_polys, how='left', op='within')
    return split_line_noises

def get_noise_dict_for_geom(geom, noise_polys):
    noise_lines = get_exposure_lines(geom, noise_polys)
    if (noise_lines.empty):
        return {}
    else:
        return get_exposures(noise_lines)

def aggregate_line_noises(split_line_noises, uniq_id):
    row_accumulator = []
    grouped = split_line_noises.groupby(uniq_id)
    for key, values in grouped:
        row_d = {uniq_id: key}
        row_d['noises'] = get_exposures(values)
        row_accumulator.append(row_d)
    return pd.DataFrame(row_accumulator)

def add_noise_exposures_to_gdf(line_gdf, uniq_id, noise_polys):
    # add noises to lines as list
    line_gdf['split_lines'] = [geom_utils.get_split_lines_list(line_geom, noise_polys) for line_geom in line_gdf['geometry']]
    # explode new rows from split lines column
    split_lines = geom_utils.explode_lines_to_split_lines(line_gdf, uniq_id)
    # join noises to split lines
    split_line_noises = get_noise_attrs_to_split_lines(split_lines, noise_polys)
    # aggregate noises back to segments
    line_noises = aggregate_line_noises(split_line_noises, uniq_id)
    line_gdf = line_gdf.drop(['split_lines'], axis=1)
    return pd.merge(line_gdf, line_noises, how='inner', on=uniq_id)

def get_th_exp_diff(dB, th_noises, s_th_noises):
    return round(th_noises[dB]-s_th_noises[dB],1)

def aggregate_exposures(exp_list):
    exps = {}
    for exp_d_value in exp_list:
        exp_d = ast.literal_eval(exp_d_value) if type(exp_d_value) == str else exp_d_value
        for db in exp_d.keys():
            if db in exps.keys():
                exps[db] += exp_d[db]
            else:
                exps[db] = exp_d[db]
    for db in exps.keys():
        exps[db] = round(exps[db], 2)
    return exps

def get_noises_diff(s_noises, q_noises):
    dbs = [40, 45, 50, 55, 60, 65, 70, 75]
    diff_dict = {}
    for db in dbs:
        s_noise = s_noises[db] if db in s_noises.keys() else 0
        q_noise = q_noises[db] if db in q_noises.keys() else 0
        noise_diff = q_noise - s_noise
        diff_dict[db] = round(noise_diff, 2)
    return diff_dict
