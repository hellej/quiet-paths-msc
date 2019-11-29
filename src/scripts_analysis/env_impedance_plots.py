#%%
import utils.plots as plots
import utils.quiet_paths as qp

dbs = list(range(45, 85, 5))

db_costs_v2 = [qp.calc_db_cost_v2(db) for db in dbs]
db_costs_v3 = [qp.calc_db_cost_v3(db) for db in dbs]

#%%
fig = plots.plot_db_costs(dbs, db_costs_v2, db_costs_v3, xlabel='dB', ylabel='Cost coefficient')
fig.savefig('plots/noise_impedace_funcs.png', format='png', dpi=300)


#%%
