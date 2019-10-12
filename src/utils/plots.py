import pandas as pd
import geopandas as gpd
import math
import ast
import numpy as np
from scipy import stats
from matplotlib import rcParams
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial']
import matplotlib.pyplot as plt

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

def abline(x_vals, slope, intercept, color='green'):
    '''Plot a line from slope and intercept'''
    y_vals = intercept + slope * x_vals
    plt.plot(x_vals, y_vals, color=color, linewidth=1, linestyle='dashed')

def scatterplot(data_df, xcol=None, ycol=None, linreg=False, yrange=None, ylims=None, yignore=None, yvaluemap=None, point_s=3, line=None, xlabel=None, ylabel=None, title=None, large_text=False):
    # filter out null values (e.g. -9999)
    if (yignore is not None):
        # df = data_df.query(f'''{ycol} != {yignore}''')
        df = data_df[data_df[ycol] != yignore]
        print('filtered:', len(data_df)-len(df), 'rows with y value:', yignore, round((len(data_df)-len(df))*100/len(data_df)), '%')
    else:
        df = data_df.copy()

    xvals = list(df[xcol])
    yvals = list(df[ycol])
    
    if (yvaluemap is not None):
        print('mapped:', yvals.count(yvaluemap[0]), 'rows with y value:', yvaluemap[0], 'to', yvaluemap[1], round(yvals.count(yvaluemap[0])*100/len(yvals)), '%')
        yvals = [value if value != yvaluemap[0] else yvaluemap[1] for value in yvals]
    
    set_plot_style()
    fig, ax = plt.subplots(figsize=(7,7))

    # set y ticks
    if (yrange == (0, -20)):
        yticks = list(range(0, -25, -5))
        yticks = [int(tick) for tick in yticks]
        ax.set_yticks(yticks)
        ax.set_yticklabels(yticks, fontsize=15)
        ax.set_ylim(top=5, bottom=-25)

    ax.scatter(xvals, yvals, c='black', s=point_s)
    ax.set_ylabel(ylabel if ylabel is not None else ycol)
    ax.set_xlabel(xlabel if xlabel is not None else xcol)

    # get x vals for plotting ablines
    x_vals = np.array(ax.get_xlim())

    def get_p_string(p_value):
        if p_value < 0.001: return 'p < 0.001'
        if p_value < 0.01: return 'p < 0.01'
        if p_value < 0.1: return 'p < 0.1'
        return 'p = '+ str(round(p_value, 2))

    if (linreg == True):
        slope, intercept, r_value, p_value, std_err = stats.linregress(xvals, yvals)
        print('slope:', slope, 'intercept:', intercept, 'r_value:', r_value, 'p_value:', p_value, 'std_err:', std_err)
        abline(x_vals, slope, intercept, color='red')
        func_string = 'y = '+ str(round(intercept,1)) + ' + '+ str(round(slope, 2)) +'x'
        ax.text(0.06, 0.05, 'R = '+ str(round(r_value, 2)) +'\n'+ get_p_string(p_value)+ '\n'+ func_string,
                verticalalignment='bottom', horizontalalignment='left',
                transform=ax.transAxes,
                color='black', fontsize=13, linespacing=1.5)
    
    # plot abline
    if (line is not None):
        if (line == 'xy'):
            abline(x_vals, 1, 0)
        if (line == '-xy'):
            abline(x_vals, -1, 0)
        if (line == 'y0'):
            abline(x_vals, 0, 0)

    y_lims = np.array(ax.get_ylim())
    print('y_lims:', y_lims)

    if (ylims is not None):
        ax.set_ylim(top=ylims[0], bottom=ylims[1])

    label_font_size = 18 if large_text == False else 23
    tick_font_size = 15 if large_text == False else 20

    if (title is not None):
        ax.set_title(title, fontsize=25, y = 1.04)

    ax.xaxis.label.set_size(label_font_size)
    ax.yaxis.label.set_size(label_font_size)
    ax.tick_params(axis='both', which='major', labelsize=tick_font_size)

    ax.xaxis.labelpad = 10
    ax.yaxis.labelpad = 10

    fig.tight_layout()
    return fig

def boxplots_qp_counts(od_stats_df, large_text = True, xlabel=None, ylabel=None, title=None):

    qp_counts = range(0, 9)

    qp_count_groups = []
    for i in qp_counts:
        ed_stats_qp_i = od_stats_df[od_stats_df['count_qp'] == i]
        qp_count_groups.append(ed_stats_qp_i['length_km'])

    # Create a figure instance
    fig = plt.figure(1, figsize=(9, 8))

    # Create an axes instance
    ax = fig.add_subplot(111)

    # Create the boxplot
    ax.boxplot(qp_count_groups, labels=qp_counts, vert=False)

    ax.set_ylabel(ylabel if ylabel is not None else '')
    ax.set_xlabel(xlabel if xlabel is not None else '')

    label_font_size = 18 if large_text == False else 23
    tick_font_size = 15 if large_text == False else 18

    if (title is not None):
        ax.set_title(title, fontsize=25, y = 1.04)

    ax.xaxis.label.set_size(label_font_size)
    ax.yaxis.label.set_size(label_font_size)
    ax.tick_params(axis='both', which='major', labelsize=tick_font_size)

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
