import utils.geometry as geom_utils

def get_geojson_from_q_path_gdf(gdf):
    features = []
    for path in gdf.itertuples():
        feature_d = geom_utils.get_geojson_from_geom(getattr(path, 'geometry'))
        feature_d['properties']['type'] = getattr(path, 'type')
        feature_d['properties']['id'] = getattr(path, 'id')
        feature_d['properties']['length'] = getattr(path, 'total_length')
        feature_d['properties']['min_nt'] = getattr(path, 'min_nt')
        feature_d['properties']['max_nt'] = getattr(path, 'max_nt')
        feature_d['properties']['len_diff'] = getattr(path, 'len_diff')
        feature_d['properties']['len_diff_rat'] = getattr(path, 'len_diff_rat')
        feature_d['properties']['noises'] = getattr(path, 'noises')
        feature_d['properties']['noises_diff'] = getattr(path, 'noises_diff')
        feature_d['properties']['th_noises'] = getattr(path, 'th_noises')
        feature_d['properties']['th_noises_diff'] = getattr(path, 'th_noises_diff')
        feature_d['properties']['nei'] = getattr(path, 'nei')
        feature_d['properties']['nei_norm'] = getattr(path, 'nei_norm')
        feature_d['properties']['nei_diff_rat'] = getattr(path, 'nei_diff_rat')
        features.append(feature_d)
    
    return features
