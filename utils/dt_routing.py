import requests
import json
import polyline
import pandas as pd
import geopandas as gpd
from fiona.crs import from_epsg
from shapely.geometry import Point, LineString

def build_plan_query(latlon_from, latlon_to, walkSpeed, maxWalkDistance, itins_count, datetime):
    '''
    Function for combining query string for route plan using Digitransit Routing API. 
    Returns
    -------
    <string>
        Digitransit Routing API compatible GraphQL query for querying route plan.
    '''
    return f'''
    plan(
        from: {{lat: {latlon_from['lat']}, lon: {latlon_from['lon']}}}
        to: {{lat: {latlon_to['lat']}, lon: {latlon_to['lon']}}}
        numItineraries: {itins_count},
        walkSpeed: {walkSpeed},
        maxWalkDistance: {maxWalkDistance},
        date: "{str(datetime.strftime("%Y-%m-%d"))}",
        time: "{str(datetime.strftime("%H:%M:%S"))}",
    )
    '''

def build_full_route_query(latlon_from, latlon_to, walkSpeed, maxWalkDistance, itins_count, datetime):
    '''
    Function for combining query string for full route plan using Digitransit Routing API. 
    Returns
    -------
    <string>
        Digitransit Routing API compatible GraphQL query for querying full route plan.
    '''
    return f'''
    {{
    {build_plan_query(latlon_from, latlon_to, walkSpeed, maxWalkDistance, itins_count, datetime)}
        {{
            itineraries {{
                duration
                legs {{
                    mode
                    duration
                    distance
                    legGeometry {{
                        length
                        points
                    }}
                    to {{
                        stop {{
                            gtfsId
                            desc
                            lat
                            lon
                            parentStation {{
                                gtfsId
                                name
                                lat
                                lon
                            }}
                            cluster {{
                                gtfsId
                                name
                                lat
                                lon
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    '''

def run_query(query):
    '''
    Function for running Digitransit Routing API query in the API. 
    Returns
    -------
    <dictionary>
        Results of the query as a dictionary.
    '''
    dt_routing_endpoint = 'https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql' 
    headers = {'Content-Type': 'application/json'}
    request = requests.post(dt_routing_endpoint, json={'query': query}, headers=headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception('Query failed to run by returning code of {}. {}'.format(request.status_code, query))

def get_route_itineraries(latlon_from, latlon_to, walkSpeed, maxWalkDistance, itins_count, datetime):
    '''
    Function for building and running routing query in Digitransit API.
    Returns
    -------
    <list of dictionaries>
        Results of the routing request as list of itineraries
    '''
    query = build_full_route_query(latlon_from, latlon_to, walkSpeed, maxWalkDistance, itins_count, datetime)
    # print(query)
    response = run_query(query)
    itineraries = response['data']['plan']['itineraries']
    return itineraries

def create_line_geom(point_coords):
    '''
    Function for building line geometries from list of coordinate tuples [(x,y), (x,y)].
    Returns
    -------
    <LineString>
    '''
    try:
        return LineString([point for point in point_coords])
    except:
        return

def parse_walk_geoms(itins, from_id, to_id):
    '''
    Function for parsing route geometries got from Digitransit Routing API. 
    Coordinates are decoded from Google Encoded Polyline Algorithm Format.
    Returns
    -------
    <list of dictionaries>
        List of itineraries as dictionaries
    '''
    walk_gdfs = []
    for itin in itins:
        walk_leg = itin['legs'][0]
        try:
            pt_leg = itin['legs'][1]
        except IndexError:
            pt_leg = {'mode': 'none'}
        geom = walk_leg['legGeometry']['points']
        # parse coordinates from Google Encoded Polyline Algorithm Format
        decoded = polyline.decode(geom)
        # swap coordinates (y, x) -> (x, y)
        coords = [point[::-1] for point in decoded]
        walk = {}
        walk['from_id'] = [from_id]
        walk['to_id'] = [to_id]
        walk['to_pt_mode'] = [pt_leg['mode']]
        walk['line_geom'] = [create_line_geom(coords)]
        walk['first_point'] = [Point(coords[0])]
        walk['last_point'] = [Point(coords[len(coords)-1])]
        to_stop = walk_leg['to']['stop']
        walk['stop_id'] = [to_stop['gtfsId']] if to_stop != None else ['']
        walk['stop_desc'] = [to_stop['desc']] if to_stop != None else ['']
        walk['stop_point'] = [Point(to_stop['lon'], to_stop['lat'])] if to_stop != None else ['']
        parent_station = to_stop['parentStation'] if to_stop != None else None
        walk['stop_p_id'] = [parent_station['gtfsId']] if parent_station != None else ['']
        walk['stop_p_name'] = [parent_station['name']] if parent_station != None else ['']
        walk['stop_p_point'] = [Point(parent_station['lon'], parent_station['lat'])] if parent_station != None else ['']
        cluster = to_stop['cluster'] if to_stop != None else None
        walk['stop_c_id'] = [cluster['gtfsId']] if cluster != None else ['']
        walk['stop_c_name'] = [cluster['name']] if cluster != None else ['']
        walk['stop_c_point'] = [Point(cluster['lon'], cluster['lat'])] if cluster != None else ['']
        # convert walk dictionary to GeoDataFrame
        walk_gdf = gpd.GeoDataFrame(data=walk, geometry=walk['line_geom'], crs=from_epsg(4326))
        walk_gdfs.append(walk_gdf)
    walk_gdf = pd.concat(walk_gdfs).reset_index(drop=True)
    return walk_gdf

