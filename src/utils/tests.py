import pandas as pd
import geopandas as gpd
import utils.geometry as geom_utils

def get_origin_lat_lon():
    # read locations for routing tests (in WGS)
    locations = gpd.read_file('data/test/test_locations_qp_tests.geojson')
    locations['latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in locations['geometry']]
    origin = locations.query("name == 'Koskela'").copy()
    return list(origin['latLon'])[0]

def get_target_locations():
    # read target locations for routing tests (in WGS)
    locations = gpd.read_file('data/test/test_locations_qp_tests.geojson')
    target_locations = locations.query("type == 'target'").copy()
    target_locations['latLon'] = [geom_utils.get_lat_lon_from_geom(geom) for geom in target_locations['geometry']]
    return target_locations
