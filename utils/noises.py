import pandas as pd
import geopandas as gpd
import utils.geometry as geo
import matplotlib.pyplot as plt
import numpy as np

def add_noises_to_split_lines(noise_polygons, split_lines):
    split_lines['geom_line'] = split_lines['geometry']
    split_lines['geom_point'] = [geo.get_line_middle_point(geom) for geom in split_lines['geometry']]
    split_lines['geometry'] = split_lines['geom_point']
    line_noises = gpd.sjoin(split_lines, noise_polygons, how='left', op='within')
    line_noises['geometry'] = line_noises['geom_line']
    return line_noises[['geometry', 'length', 'db_lo', 'db_hi', 'index_right']]

def get_cumulative_esposures(line_noises, thresholds):
    grouped = line_noises.groupby('db_lo')
    noise_dict = {}
    th1 = thresholds[0]
    th2 = thresholds[1]
    th3 = thresholds[2]
    th1_tot_len = 0
    th2_tot_len = 0
    th3_tot_len = 0

    for key, values in grouped:
        db_lo = int(key)
        tot_len = round(values['length'].sum(),2)
        noise_dict[db_lo] = tot_len
    
        if(db_lo > th1):
            th1_tot_len += tot_len
        if(db_lo > th2):
            th2_tot_len += tot_len
        if(db_lo > th3):
            th3_tot_len += tot_len
    
    th1_key = 'th_' + str(th1) + '_len'
    th2_key = 'th_' + str(th2) + '_len'
    th3_key = 'th_' + str(th3) + '_len'

    d = { 'noise_dict': [noise_dict], th1_key: [th1_tot_len], th2_key: [th2_tot_len], th3_key: [th3_tot_len] }
    line_cum_noises = pd.DataFrame(data=d)
    return line_cum_noises



def plot_cumulative_exposures(cum_noises):
    firstrow = cum_noises.iloc[0]
    noise_dict = firstrow['noise_dict']
    print(noise_dict)

    fig, ax = plt.subplots(figsize=(7,7))
    dbs = list(noise_dict.keys())
    lengths = list(noise_dict.values())

    ax.bar(dbs, lengths, width=3)
    yticks = np.arange(0, max(lengths)+10, 50)
    yticks = [int(tick) for tick in yticks]
    ax.st_yticks = yticks
    ax.set_yticklabels(yticks, fontsize=15)
    
    ax.set_xticklabels(np.arange(35, 85, 5), fontsize=15)
    ax.set_ylabel('Distance (m)')
    ax.set_xlabel('Traffic noise (dB)')

    ax.xaxis.label.set_size(16)
    ax.yaxis.label.set_size(16)

    ax.xaxis.labelpad = 10
    ax.yaxis.labelpad = 10
