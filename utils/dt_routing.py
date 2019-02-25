import requests
import json
import polyline
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
                    transitLeg
                    legGeometry {{
                        length
                        points
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

def parse_itin_geom(itins):
    '''
    Function for parsing route geometries got from Digitransit Routing API. 
    Coordinates are decoded from Google Encoded Polyline Algorithm Format.
    Returns
    -------
    <list of dictionaries>
        List of itineraries as dictionaries
    '''
    for itin in itins:
        itin_coords = []
        legs = itin['legs']
        for leg in legs:
            geom = leg['legGeometry']['points']
            # parse coordinates from Google Encoded Polyline Algorithm Format
            decoded = polyline.decode(geom)
            # swap coordinates (y, x) -> (x, y)
            coords = [point[::-1] for point in decoded]
            leg['line_geom'] = create_line_geom(coords)
            leg['first_point'] = Point(coords[0])
            leg['last_point'] = Point(coords[len(coords)-1])
            itin_coords += coords
            del leg['legGeometry']
        itin['line_geom'] = create_line_geom(itin_coords)
    return itins

