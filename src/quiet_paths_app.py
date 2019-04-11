
from flask import Flask
from flask_cors import CORS
from flask import jsonify
import json
import geopandas as gpd
import utils.files as files
import utils.routing as rt
import utils.geometry as geom_utils
import utils.networks as nw
import utils.exposures as exps
import utils.utils as utils
from fiona.crs import from_epsg
import time

app = Flask(__name__)
CORS(app)

# READ DATA
graph = files.get_kumpula_network()
edge_dicts = nw.get_all_edge_dicts(graph)
edge_gdf = nw.get_edge_gdf(edge_dicts, ['uvkey', 'geometry'])
node_gdf = nw.get_node_gdf(graph)

@app.route('/')
def hello_world():
    return 'Hello, World!'

@app.route('/shortestpath/<from_lat>,<from_lon>/<to_lat>,<to_lon>')
def get_shortest_path(from_lat, from_lon, to_lat, to_lon):
    from_latLon = {'lat': float(from_lat), 'lon': float(from_lon)}
    to_latLon = {'lat': float(to_lat), 'lon': float(to_lon)}
    print('from:', from_latLon)
    print('to:', to_latLon)
    from_xy = geom_utils.get_xy_from_lat_lon(from_latLon)
    to_xy = geom_utils.get_xy_from_lat_lon(to_latLon)
    print('from:', from_xy)
    print('to:', to_xy)
    orig_node = rt.get_nearest_node(graph, from_xy, edge_gdf, node_gdf, [])
    target_node = rt.get_nearest_node(graph, to_xy, edge_gdf, node_gdf, [])
    shortest_path = rt.get_shortest_path(graph, orig_node, target_node, 'length')
    path_geom = nw.get_edge_geometries(graph, shortest_path, 'length')
    feature = geom_utils.get_geojson_from_geom(path_geom['geometry'])
    feature['properties']['length'] = path_geom['total_length']
    feature['properties']['origin_node'] = orig_node
    feature['properties']['target_node'] = target_node
    print('feature', jsonify(feature))
    return jsonify(feature)

if __name__ == '__main__':
    app.run()
