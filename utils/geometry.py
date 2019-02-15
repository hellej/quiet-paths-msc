import pandas as pd
import geopandas as gpd
import requests
import json
from urllib.parse import urlparse, urlencode
from shapely.geometry import Point
from fiona.crs import from_epsg
import glob

def clip_polygon_with_polygon(clippee, clipper):

    poly = clipper.geometry.unary_union
    poly_bbox = poly.bounds

    spatial_index = clippee.sindex
    sidx = list(spatial_index.intersection(poly_bbox))
    clippee_sub = clippee.iloc[sidx]

    clipped = clippee_sub.copy()
    clipped['geometry'] = clippee_sub.intersection(poly)
    clipped_final = clipped[clipped.geometry.notnull()]

    return clipped_final
