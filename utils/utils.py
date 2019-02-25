
def getLatLonFromGeom(row):
    return {'lat': row['geometry'].y, 'lon': row['geometry'].x }