# MSc thesis
## Assessing and minimizing pedestrians' exposure to traffic noise with spatial analysis and Web GIS (working title)
This repository contains (or is linked to) the main components of my master's thesis, including:
* Scripts for [construction, processing and analysis](https://github.com/DigitalGeographyLab/hope-green-path-server/blob/develop/src/graphs/graph_construction.py) of walkable street network (graph)
* [Analysis](https://github.com/hellej/quiet-paths-msc/tree/master/src/scripts_analysis) and [utilities](https://github.com/DigitalGeographyLab/hope-green-path-server/blob/develop/src/utils/noise_exposures.py) for assessing pedestrians exposure to traffic noise
* [Quiet path route optimization application](https://github.com/DigitalGeographyLab/hope-green-path-server)
* Quiet path route planner UI: [github.com/DigitalGeographyLab/hope-green-path-ui](https://github.com/DigitalGeographyLab/hope-green-path-ui) / [Live demo](https://quietpath.web.app/)

## Docs
* [Research plan (doc)](thesis/research_plan_doc.pdf)
* [Research plan (slides)](thesis/research_plan_slides.pdf)
* [Methods & results (slides)](thesis/methods_results.pdf)
* [Draft of the thesis](thesis/thesis.docx)

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
