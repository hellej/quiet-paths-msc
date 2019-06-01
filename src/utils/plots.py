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

def scatterplot(df, xcol=None, ycol=None, xlabel=None, ylabel=None):
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

def boxplot(df, col=None, label=None):
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
