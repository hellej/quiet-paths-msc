## Gradu POCs & tests

## Installation
```
$ git clone git@github.com:hellej/gradu-pocs.git
$ cd gradu-pocs/src
```
```
$ conda create -n gis -c conda-forge python=3.6.5 jupyterlab geopandas geoplot osmnx pysal pylint pytest
$ conda activate gis
$ pip install pycrs
$ pip install requests
$ pip install polyline
```
Or:
```
$ conda env create -f env-gis-flask.yml
$ conda activate gis
```
