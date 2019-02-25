
def get_lat_lon_from_geom(row):
    return {'lat': row['geometry'].y, 'lon': row['geometry'].x }