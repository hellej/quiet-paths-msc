import pandas as pd
import geopandas as gpd
import math
import ast
import numpy as np
from matplotlib import rcParams
rcParams['font.family'] = 'sans-serif'
rcParams['font.sans-serif'] = ['Arial']
import matplotlib.pyplot as plt

def set_plot_style():
    plt.style.use('default')
    rcParams['font.family'] = 'sans-serif'
    rcParams['font.sans-serif'] = ['Arial']

def scatterplot(data_df, xcol=None, ycol=None, yignore=None, xlabel=None, ylabel=None):
    if (yignore is not None):
        df = data_df.query(f'''{ycol} != {yignore}''')
        print('filtered:', len(data_df)-len(df), 'rows with y value:', yignore)
    else:
        df = data_df.copy()
    
    set_plot_style()

    fig, ax = plt.subplots(figsize=(8,5))

    ax.scatter(df[xcol], df[ycol], c='black', s=6)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)

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
