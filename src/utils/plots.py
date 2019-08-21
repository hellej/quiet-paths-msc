import pandas as pd
import geopandas as gpd
import math
import ast
import numpy as np
from matplotlib import rcParams
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial']
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import matplotlib.transforms as mtransforms

def set_plot_style():
    plt.style.use('default')
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['Arial']

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

def abline(slope, intercept):
    '''Plot a line from slope and intercept'''
    axes = plt.gca()
    x_vals = np.array(axes.get_xlim())
    y_vals = intercept + slope * x_vals
    plt.plot(x_vals, y_vals, color='red', linestyle='dashed')

def scatterplot(data_df, xcol=None, ycol=None, yignore=None, line=None, xlabel=None, ylabel=None):
    if (yignore is not None):
        df = data_df.query(f'''{ycol} != {yignore}''')
        print('filtered:', len(data_df)-len(df), 'rows with y value:', yignore)
    else:
        df = data_df.copy()
    
    set_plot_style()

    fig, ax = plt.subplots(figsize=(8,5))

    ax.scatter(df[xcol], df[ycol], c='black', s=3)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    
    if (line is not None):
        if (line == 'xy'):
            abline(1, 0)
            # line = mlines.Line2D([0, 1], [0, 1], color='red')
            # transform = ax.transAxes
            # line.set_transform(transform)
            # ax.add_line(line)
        if (line == 'y0'): 
            abline(0, 0)

    ax.xaxis.label.set_size(18)
    ax.yaxis.label.set_size(18)
    ax.tick_params(axis='both', which='major', labelsize=15)

    ax.xaxis.labelpad = 10
    ax.yaxis.labelpad = 10

    fig.tight_layout()
    return fig

def boxplot(data_df, col=None, valignore=None, label=None):
    if (valignore is not None):
        df = data_df.query(f'''{col} != {valignore}''')
        print('filtered:', len(data_df)-len(df), 'rows with value:', valignore)
    else:
        df = data_df.copy()
    
    fig, ax = plt.subplots(figsize=(8,5))
    ax.boxplot(df[col], vert=False)
    ax.tick_params(axis='x', which='major', labelsize=15)

    ax.set_xlabel(label)
    y_axis = ax.axes.get_yaxis()
    y_axis.set_visible(False)
    ax.xaxis.label.set_size(18)
    ax.xaxis.labelpad = 10
    ax.yaxis.labelpad = 10
    fig.tight_layout()
    return fig
