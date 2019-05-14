#%% IMPORT MODULES FOR NOISE EXTRACTION
import pandas as pd
import geopandas as gpd
import utils.geometry as geom_utils
import utils.exposures as exps
import utils.utils as utils
import utils.files as files

walkspeed = 1.16666

#%% read traffic noise polygons
noise_polys = files.get_noise_polygons()

#%%  read walk line
walk_proj = files.get_update_test_walk_line()
walk_geom = walk_proj.loc[1, 'geometry']
walk_proj
walk_geom

#%% SPLIT LINE WITH NOISE POLYGON BOUNDARIES
split_lines = geom_utils.get_split_lines_gdf(walk_geom, noise_polys)

#%% JOIN NOISE LEVELS TO SPLIT LINES
noise_lines = exps.add_noises_to_split_lines(noise_polys, split_lines)
noise_lines = noise_lines.fillna(35)
noise_lines.head(4)

#%% EXPORT NOISE LINES TO FILE
noise_lines.to_file('outputs/path_noises.gpkg', layer='noise_lines_test', driver='GPKG')

#%% AGGREGATE CUMULATIVE EXPOSURES
exp_lens = exps.get_exposures(noise_lines)
exp_times = exps.get_exposure_times(exp_lens, walkspeed, True)
exp_lens

#%% PLOT CUMULATIVE EXPOSURES
fig_len = exps.plot_exposure_lengths(exp_lens)
fig_time = exps.plot_exposure_times(exp_times)
# fig_len.savefig('plots/noise_exp_len.eps', format='eps', dpi=500)
# fig_time.savefig('plots/noise_exp_time.eps', format='eps', dpi=500)


#%% EXTRACT NOISES FOR ALL SHORTEST PATHS
shortest_paths = gpd.read_file('outputs/shortest_paths.gpkg', layer='shortest_paths_undir')

noise_lines_all = []
noise_exps_dfs = []
path_count = len(shortest_paths.index)
for idx, shortest_path in shortest_paths.iterrows():
    if (idx < 0):
        break
    utils.print_progress(idx, path_count, False)
    path_geom = shortest_path['geometry']
    path_id = shortest_path['uniq_id']

    noise_lines = exps.get_exposure_lines(path_geom, noise_polys)
    noise_dict = exps.get_exposures(noise_lines)
    th_noise_dict = exps.get_th_exposures(noise_dict, [55, 60, 65, 70])

    noise_lines_all.append(noise_lines)
    noise_exps_dfs.append(pd.DataFrame({'uniq_id': path_id, 'noises': [noise_dict], 'th_noises': [th_noise_dict], **th_noise_dict}, index=[0]))

#%% EXPORT NOISE LINES & PATHS TO FILES
noise_lines_gdf = pd.concat(noise_lines_all).reset_index(drop=True)
noise_lines_gdf.to_file('outputs/path_noises.gpkg', layer='noise_lines', driver='GPKG')

noise_exposures = pd.concat(noise_exps_dfs).reset_index(drop=True)
path_noises = pd.merge(shortest_paths, noise_exposures, how='inner', on='uniq_id')
path_noises = path_noises.rename(index=str, columns={55: 'th_55', 60: 'th_60', 65: 'th_65', 70: 'th_70'})
path_noises.to_file('outputs/path_noises.gpkg', layer='path_noises', driver='GPKG')

#%%
noise_lines_gdf.head(5)
path_noises.head(5)

#%%