# MSc thesis scripts & POCs
This repository contains the main components of my master's thesis, including:
* Walkable street network (graph) [construction, processing and analysis](src/utils/networks.py)
* [Scripts](https://github.com/hellej/gradu-pocs/tree/master/src/batch_jobs) (for CSC's Taito supercluster) for extracting traffic noises to all edges of the network 
* [Analysis](src/3_path_noises.py) and [utilities](src/utils/exposures.py) for assessing pedestrians exposure to traffic noise (under development)
* [Quiet path route optimization application](src/quiet_paths_app.py) (under development)
* Quiet path route planner UI: [github.com/hellej/quiet-path-ui](https://github.com/hellej/quiet-path-ui)

## Tech
* Python (3.6)
* Shapely
* GeoPandas
* NetworkX (+ OSMnx)
* Flask

## Materials
* [Traffic noise zones in Helsinki 2017](https://hri.fi/data/en_GB/dataset/helsingin-kaupungin-meluselvitys-2017)
* [OpenStreetMap](https://www.openstreetmap.org/about/)

## Installation
```
$ git clone git@github.com:hellej/gradu-pocs.git
$ cd gradu-pocs/src

$ conda env create -f env-gis-flask.yml
$ conda activate gis
```
