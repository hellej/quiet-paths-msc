# MSc thesis
## Assessing and minimizing pedestrians' exposure to traffic noise with spatial analysis and Web GIS (working title)
This repository contains the main components of my master's thesis, including:
* Scripts for [construction, processing and analysis](src/scripts_analysis/network_full_processing.py) of walkable street network (graph)
* [Scripts](https://github.com/hellej/quiet-paths-msc/tree/master/src/batch_jobs) for extracting traffic noises to all network edges (in CSC's Taito supercluster) 
* [Analysis](https://github.com/hellej/quiet-paths-msc/tree/master/src/scripts_analysis) and [utilities](src/utils/exposures.py) for assessing pedestrians exposure to traffic noise
* [Quiet path route optimization application](src/quiet_paths_app.py) (POC)
* Quiet path route planner UI: [github.com/hellej/quiet-path-ui](https://github.com/hellej/quiet-path-ui) / [Live demo](https://quietpath.web.app/)

## Docs
* [Draft of the thesis](thesis/thesis.docx)
* [Research plan (doc)](thesis/research_plan_doc.pdf)
* [Research plan (slides)](thesis/research_plan_slides.pdf)
* [Methods & results (slides)](thesis/methods_results.pdf)

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
$ git clone git@github.com:hellej/quiet-paths-msc.git
$ cd quiet-paths-msc/src

$ conda env create -f env-gis-flask.yml
$ conda activate gis-flask
```
