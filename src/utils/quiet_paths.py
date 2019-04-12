import utils.geometry as geom_utils

def get_geojson_from_q_path_gdf(gdf):
    features = []
    for path in gdf.itertuples():
        feature_d = geom_utils.get_geojson_from_geom(getattr(path, 'geometry'))
        feature_d['properties']['type'] = getattr(path, 'type')
        feature_d['properties']['length'] = getattr(path, 'total_length')
        feature_d['properties']['min_nt'] = getattr(path, 'min_nt')
        feature_d['properties']['max_nt'] = getattr(path, 'max_nt')
        feature_d['properties']['diff_len'] = getattr(path, 'diff_len')
        feature_d['properties']['diff_rat'] = getattr(path, 'diff_rat')
        # feature_d['properties']['noises'] = getattr(path, 'noises')
        # feature_d['properties']['th_noises'] = getattr(path, 'th_noises')
        feature_d['properties']['diff_55db'] = getattr(path, 'diff_55_dB')
        feature_d['properties']['diff_60db'] = getattr(path, 'diff_60_dB')
        feature_d['properties']['diff_65db'] = getattr(path, 'diff_65_dB')
        features.append(feature_d)
    
    return features
