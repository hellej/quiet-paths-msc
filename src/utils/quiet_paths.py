import utils.geometry as geom_utils
import utils.exposures as exps

def get_noise_tolerances():
    return [ 0.1, 0.15, 0.25, 0.35, 0.5, 1, 1.5, 2, 4, 6, 10, 20, 40 ]

def calc_db_cost_v2(db):
    # Equation 3
    if (db <= 40): 
        return 0
    db_cost = (db-40) / (75-40)
    return round(db_cost, 2)

def calc_db_cost_v3(db):
    # Equation 4
    if (db <= 40): return 0
    db_cost = pow(10, (0.3 * db)/10)
    return round(db_cost / 100, 3)

def get_db_costs(version: int = 1):
    dbs = [45, 50, 55, 60, 65, 70, 75]
    if (version == 1):
        db_costs = { 50: 0.1, 55: 0.2, 60: 0.3, 65: 0.4, 70: 0.5, 75: 0.6 }
    elif (version == 2):
        db_costs = { db: calc_db_cost_v2(db) for db in dbs }
    elif (version == 3):
        db_costs = { db: calc_db_cost_v3(db) for db in dbs }
    else:
        raise ValueError('Parameter: version must be either 1, 2 or 3')
    print('Using dB costs v'+ str(version) + ': '+ str(db_costs))
    return db_costs

def get_path_overlay_candidates_by_len(by_path, all_paths: list, len_diff: int = 25) -> list:
    """Returns paths with length difference not greater or less than specified in [len_diff] (m)
    compared to the length of [path]. If [all_paths] contains [param_path], the latter is included in the returned list.
    """
    p_length = by_path['properties']['length']
    overlay_candidates = [path for path in all_paths if (abs(path['properties']['length'] - p_length) < len_diff)]
    return overlay_candidates

def get_overlapping_paths(by_path, compare_paths: list, buffer_m: int = None) -> list:
    """Returns [compare_paths] that are within a buffered geometry of [param_path].
    """
    overlapping_paths = [by_path]
    path_geom_buff = by_path['properties']['geometry'].buffer(buffer_m)
    for compare_path in [compare_path for compare_path in compare_paths if compare_path['properties']['id'] != by_path['properties']['id']]:
        bool_within = compare_path['properties']['geometry'].within(path_geom_buff)
        if (bool_within == True):
            overlapping_paths.append(compare_path)
    return overlapping_paths

def get_least_cost_path(paths, cost_attr):
    ordered = paths.copy()
    def get_score(path):
        return path['properties'][cost_attr]
    ordered.sort(key=get_score)
    # if (len(ordered) > 1):
    #     print('ordered (best=[0]):', [(path['properties']['id'], path['properties']['nei']) for path in ordered])
    return ordered[0]

def get_path_length(path):
    return path['properties']['length']

def remove_duplicate_geom_paths(paths, tolerance=None, remove_geom_prop=True, logging=True):
    filtered_paths = []
    filtered_paths_names = []
    paths_already_overlapped = []

    # function for returning better of two paths
    for path in paths:
        path_name = path['properties']['id']
        if (path_name not in filtered_paths_names and path_name not in paths_already_overlapped):
            overlay_candidates = get_path_overlay_candidates_by_len(path, paths, len_diff=tolerance)
            overlapping_paths = get_overlapping_paths(path, overlay_candidates, buffer_m=tolerance)
            best_overlapping_path = get_least_cost_path(overlapping_paths, cost_attr='nei')
            if (best_overlapping_path['properties']['id'] not in filtered_paths_names):
                filtered_paths_names.append(best_overlapping_path['properties']['id'])
                filtered_paths.append(best_overlapping_path)
            paths_already_overlapped += [path['properties']['id'] for path in overlapping_paths]

    filtered_paths.sort(key=get_path_length)

    if ('short_p' not in filtered_paths_names):
        filtered_paths[0]['properties']['id'] = 'short_p'
        filtered_paths[0]['properties']['type'] = 'short'

    # delete shapely geometries from path dicts
    if (remove_geom_prop == True):
        for path in filtered_paths:
            del path['properties']['geometry']
    if logging == True: 
        print('found', len(paths), 'of which returned', len(filtered_paths), 'unique paths.')
    return filtered_paths

def get_geojson_from_q_path_gdf(gdf):
    features = []
    for path in gdf.itertuples():
        feature_d = geom_utils.get_geojson_from_geom(getattr(path, 'geometry'))
        feature_d['properties']['type'] = getattr(path, 'type')
        feature_d['properties']['id'] = getattr(path, 'id')
        feature_d['properties']['length'] = getattr(path, 'total_length')
        feature_d['properties']['noises'] = getattr(path, 'noises')
        feature_d['properties']['noise_pcts'] = getattr(path, 'noise_pcts')
        feature_d['properties']['th_noises'] = getattr(path, 'th_noises')
        feature_d['properties']['mdB'] = getattr(path, 'mdB')
        feature_d['properties']['nei'] = getattr(path, 'nei')
        feature_d['properties']['nei_norm'] = getattr(path, 'nei_norm')
        feature_d['properties']['geometry'] = getattr(path, 'geometry')
        features.append(feature_d)
    return features
