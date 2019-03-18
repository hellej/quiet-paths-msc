import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import utils.geometry as geom_utils

def get_noise_polygons():
    noise_data = gpd.read_file('data/data.gpkg', layer='2017_alue_01_tieliikenne_L_Aeq_paiva')
    # explode multipolygons to polygons (noises)
    noise_polys = geom_utils.explode_multipolygons_to_polygons(noise_data)
    return noise_polys

def add_noises_to_split_lines(noise_polygons, split_lines):
    split_lines['geom_line'] = split_lines['geometry']
    split_lines['geom_point'] = [geom_utils.get_line_middle_point(geom) for geom in split_lines['geometry']]
    split_lines['geometry'] = split_lines['geom_point']
    line_noises = gpd.sjoin(split_lines, noise_polygons, how='left', op='within')
    line_noises['geometry'] = line_noises['geom_line']
    return line_noises[['geometry', 'length', 'db_lo', 'db_hi', 'index_right']]

def get_exposure_lines(line_geom, noise_polys):
    split_lines = geom_utils.split_line_with_polys(line_geom, noise_polys)
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
