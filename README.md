# MSc thesis
## Quiet paths for people: developing routing analysis and Web GIS application
This repository features (and is linked to) the main components of my master's thesis, including:
* [Quiet path routing application](https://github.com/DigitalGeographyLab/hope-green-path-server)
* [Quiet path route planner UI](https://github.com/DigitalGeographyLab/hope-green-path-ui) / [Live demo](https://green-paths.web.app/)
* [Research plan (pdf)](thesis/research_plan_doc.pdf)
* [Methods & results (slides / pdf)](thesis/helle_msc_slides.pdf)
* [Draft of the thesis (pdf)](thesis/helle_msc_draft.pdf)

## Tech
* Python (3.6)
* Shapely
* GeoPandas
* NetworkX (+ OSMnx)
* igraph
* Flask
* Gunicorn

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
