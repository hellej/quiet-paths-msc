#%% IMPORT MODULES FOR NOISE EXTRACTION
import pandas as pd
import geopandas as gpd
import utils.geometry as geom_utils
import utils.noise_overlays as noise_utils
import utils.utils as utils

#%% read traffic noise polygons
noise_polys = noise_utils.get_noise_polygons()

#%%  read walk line
walk = gpd.read_file('data/input/test_walk_line.shp')
walk_proj = walk.to_crs(epsg=3879)
walk_geom = walk_proj.loc[0, 'geometry']

#%% SPLIT LINE WITH NOISE POLYGON BOUNDARIES
split_lines = geom_utils.split_line_with_polys(walk_geom, noise_polys)

#%% JOIN NOISE LEVELS TO SPLIT LINES
line_noises = noise_utils.add_noises_to_split_lines(noise_polys, split_lines)
line_noises = line_noises.fillna(35)
line_noises.head(4)

#%% EXPORT NOISE LINES TO FILE
line_noises.to_file('outputs/path_noises.gpkg', layer='line_noises_test', driver='GPKG')

#%% AGGREGATE CUMULATIVE EXPOSURES
exp_lens = noise_utils.get_cumulative_noises_dict(line_noises)
exp_times = noise_utils.get_exposure_times(exp_lens, 1.33, True)
exp_times

#%% PLOT CUMULATIVE EXPOSURES
fig_len = noise_utils.plot_exposure_lengths(exp_lens)
fig_time = noise_utils.plot_exposure_times(exp_times)
fig_len.savefig('outputs/plots/noise_exp_len.eps', format='eps', dpi=500)
fig_time.savefig('outputs/plots/noise_exp_time.eps', format='eps', dpi=500)


#%% READ ALL SHORTEST PATHS
shortest_paths = gpd.read_file('outputs/shortest_paths.gpkg', layer='shortest_paths_g')

#%% EXTRACT NOISES FOR ALL SHORTEST PATHS
line_noises_gdfs = []
cum_noises_dfs = []
path_count = len(shortest_paths.index)
for idx, shortest_path in shortest_paths.iterrows():
    if (idx < 0):
        break
    utils.print_progress(idx, path_count)
    path_geom = shortest_path['geometry']
    path_id = shortest_path['uniq_id']

    line_noises = noise_utils.get_line_noises(path_geom, noise_polys)
    noises_dict = noise_utils.get_cumulative_noises_dict(line_noises)
    th_noises_dict = noise_utils.get_th_noises_dict(noises_dict, [55, 60, 65, 70])

    line_noises_gdfs.append(line_noises)
    cum_noises_dfs.append(pd.DataFrame({'uniq_id': path_id, 'noises': [noises_dict], 'th_noises': [th_noises_dict], **th_noises_dict}, index=[0]))

#%% EXPORT NOISE LINES & PATHS TO FILES
line_noises_gdf = pd.concat(line_noises_gdfs).reset_index(drop=True)
line_noises_gdf.to_file('outputs/path_noises.gpkg', layer='line_noises', driver='GPKG')

cum_noises_df = pd.concat(cum_noises_dfs).reset_index(drop=True)
path_noises = pd.merge(shortest_paths, cum_noises_df, how='inner', on='uniq_id')
path_noises = path_noises.rename(index=str, columns={55: 'th_55', 60: 'th_60', 65: 'th_65', 70: 'th_70'})
path_noises.to_file('outputs/path_noises.gpkg', layer='path_noises', driver='GPKG')

#%%
line_noises_gdf.head(5)
path_noises.head(5)

#%%
