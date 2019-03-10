import pandas as pd
import geopandas as gpd
import utils.geometry as geo
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
    split_lines['geom_point'] = [geo.get_line_middle_point(geom) for geom in split_lines['geometry']]
    split_lines['geometry'] = split_lines['geom_point']
    line_noises = gpd.sjoin(split_lines, noise_polygons, how='left', op='within')
    line_noises['geometry'] = line_noises['geom_line']
    return line_noises[['geometry', 'length', 'db_lo', 'db_hi', 'index_right']]

def get_line_noises(line_geom, noise_polys):
    split_lines = geom_utils.split_line_with_polys(line_geom, noise_polys)
    if (split_lines.empty):
        return gpd.GeoDataFrame()
    line_noises = add_noises_to_split_lines(noise_polys, split_lines)
    line_noises = line_noises.fillna(35)
    return line_noises

def get_cumulative_noises_dict(line_noises):
    noise_groups = line_noises.groupby('db_lo')
    noise_dict = {}
    for key, values in noise_groups:
        tot_len = round(values['length'].sum(),3)
        noise_dict[int(key)] = tot_len
    return noise_dict

def get_th_cols(ths):
    return ['th_'+str(th)+'_len' for th in ths]

def get_th_noises_dict(cum_noises_dict, ths):
    th_count = len(ths)
    th_lens = [0] * len(ths)
    for th in cum_noises_dict.keys():
        th_len = cum_noises_dict[th]
        for idx in range(th_count):
            if (th >= ths[idx]):
                th_lens[idx] = th_lens[idx] + th_len
    th_noises_dict = {}
    for idx in range(th_count):
        th_noises_dict[ths[idx]] = round(th_lens[idx],3)
    return th_noises_dict

def plot_cumulative_exposures(noises_dict):
    print(noises_dict)

    fig, ax = plt.subplots(figsize=(7,7))
    dbs = list(noises_dict.keys())
    lengths = list(noises_dict.values())

    ax.bar(dbs, lengths, width=3)
    # ax.set_xlim([30, 80])

    yticks = list(range(0, int(max(lengths)+10), 50))
    yticks = [int(tick) for tick in yticks]
    ax.set_yticks(yticks)
    ax.set_yticklabels(yticks, fontsize=15)
    
    xticks = np.arange(35, max(dbs)+5, step=5)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticks, fontsize=15)

    ax.set_ylabel('Distance (m)')
    ax.set_xlabel('Traffic noise (dB)')


    ax.xaxis.label.set_size(16)
    ax.yaxis.label.set_size(16)

    ax.xaxis.labelpad = 10
    ax.yaxis.labelpad = 10
