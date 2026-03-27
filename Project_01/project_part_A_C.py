# %%
# conda install pandas=2.2

# %%
import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path
# %%
network = pypsa.Network()
hours_in_2015 = pd.date_range('2015-01-01 00:00Z',
                              '2015-12-31 23:00Z',
                              freq='h')

network.set_snapshots(hours_in_2015.values)

network.add("Bus",
            "electricity bus",v_nom=400)

network.snapshots

# %%
# load electricity demand data
FILE_DIR = Path(__file__).parent
model_dir = FILE_DIR / 'sweden_storage_model.nc' 
Load_dir= FILE_DIR / 'data/electricity_demand.csv'
CF_onshore_dir = FILE_DIR / 'data/CF_onshore_wind_1979-2017.csv'
CF_offshore_dir = FILE_DIR / 'data/CF_offshore_wind_1979-2017.csv'
CF_pv_dir = FILE_DIR / 'data/CF_pv_optimal.csv'
df_elec = pd.read_csv(Load_dir, sep=';', index_col=0) # in MWh
df_elec.index = pd.to_datetime(df_elec.index) #change index to datatime
country='SWE'
print(df_elec[country].head())

# %%
# network.set_snapshots(df_elec.index)
# network.snapshots

# %%
# add load to the bus
network.add("Load",
            "load",
            bus="electricity bus",
            p_set=df_elec[country].values,
            v_nom=400)

# %%
network.loads_t.p_set

# %%


def annuity(n, r):
    """ Calculate the annuity factor for an asset with lifetime n years and
    discount rate  r """

    if r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n

# %%
# We add the different carries: nuclear, gas, solar and wind


network.add("Carrier", "onshorewind")
network.add("Carrier", "offshorewind")
network.add("Carrier", "solar")
network.add("Carrier", "nuclear")
network.add("Carrier", "gas", co2_emissions=0.19)  # in t_CO2/MWh_th
country = 'SWE'

# add onshore wind generator
df_onshorewind = pd.read_csv(CF_onshore_dir, sep=';', index_col=0)
df_onshorewind.index = pd.to_datetime(df_onshorewind.index)
CF_wind = df_onshorewind[country][[hour.strftime(
    "%Y-%m-%dT%H:%M:%SZ") for hour in network.snapshots]]
capital_cost_onshorewind = annuity(30, 0.07)*910000*(1+0.033)  # in €/MW
network.add("Generator",
            "onshorewind",
            bus="electricity bus",
            p_nom_extendable=True,
            carrier="onshorewind",
            # p_nom_max=1000, # maximum capacity can be limited due to environmental constraints
            capital_cost=capital_cost_onshorewind,
            marginal_cost=0,
            p_max_pu=CF_wind.values)


# add offshore wind generator
df_offshorewind = pd.read_csv(CF_offshore_dir, sep=';', index_col=0)
df_offshorewind.index = pd.to_datetime(df_offshorewind.index)
CF_offwind = df_offshorewind[country][[hour.strftime(
    "%Y-%m-%dT%H:%M:%SZ") for hour in network.snapshots]]
'''
the overnight cost, lifetime, opex is changed based on reference table 2
'''
capital_cost_offshorewind = annuity(25, 0.07)*2506000*(1+0.03)  # in €/MW
network.add("Generator",
            "offshorewind",
            bus="electricity bus",
            p_nom_extendable=True,
            carrier="offshorewind",
            # p_nom_max=1000, # maximum capacity can be limited due to environmental constraints
            capital_cost=capital_cost_offshorewind,
            marginal_cost=0,
            p_max_pu=CF_offwind.values)


# add solar PV generator
df_solar = pd.read_csv(CF_pv_dir, sep=';', index_col=0)
df_solar.index = pd.to_datetime(df_solar.index)
CF_solar = df_solar[country][[hour.strftime(
    "%Y-%m-%dT%H:%M:%SZ") for hour in network.snapshots]]
capital_cost_solar = annuity(25, 0.07)*425000*(1+0.03)  # in €/MW
network.add("Generator",
            "solar",
            bus="electricity bus",
            p_nom_extendable=True,
            carrier="solar",
            # p_nom_max=1000, # maximum capacity can be limited due to environmental constraints
            capital_cost=capital_cost_solar,
            marginal_cost=0,
            p_max_pu=CF_solar.values)


# add nuclear generator
life_nuclear = 60                    # years
cap_nuclear = 6000000               # €/MW_el
fom_nuclear = 0.025                 # 2.5%/year
capital_cost_nuclear = annuity(
    life_nuclear, 0.07) * cap_nuclear * (1 + fom_nuclear)

marginal_cost_nuclear = 10.0        # €/MWh_el (example stylized value)

network.add("Generator",
            "nuclear",
            bus="electricity bus",
            p_nom_extendable=True,
            carrier="nuclear",
            capital_cost=capital_cost_nuclear,
            marginal_cost=marginal_cost_nuclear)


# add OCGT (Open Cycle Gas Turbine) generator
capital_cost_OCGT = annuity(25, 0.07)*560000*(1+0.033)  # in €/MW
fuel_cost = 21.6  # in €/MWh_th
efficiency = 0.39  # MWh_elec/MWh_th
marginal_cost_OCGT = fuel_cost/efficiency  # in €/MWh_el
network.add("Generator",
            "OCGT",
            bus="electricity bus",
            p_nom_extendable=True,
            carrier="gas",
            # p_nom_max=1000,
            capital_cost=capital_cost_OCGT,
            marginal_cost=marginal_cost_OCGT)

# Save the network to a NetCDF file
network.export_to_netcdf("sweden_base_model.nc")


# %%
network.generators_t.p_max_pu

# %%
network.optimize(solver_name='gurobi')

# %%
# Total Annualized System Cost in 10^6 €
print(network.objective/1000000)

# %%
# The cost per MWh electricity (LCOE)
print(network.objective/network.loads_t.p.sum())  # EUR/MWh

# %%
# optimal capacity for generators
network.generators.p_nom_opt  # in MW

# %%
print(f"cost for onshore wind: {capital_cost_onshorewind:,.2f} €/MW")
print(f"cost for offshore wind: {capital_cost_offshorewind:,.2f} €/MW")
print(f"cost for solar: {capital_cost_solar:,.2f} €/MW")
print(f"cost for nuclear: {capital_cost_nuclear:,.2f} €/MW")
print(f"cost for OCGT: {capital_cost_OCGT:,.2f} €/MW")

# %%
# Plot the generation and demand profiles for the first 4 days in January (96 hours)

plt.figure(figsize=(10, 5))
plt.plot(network.loads_t.p['load'][0:96], color='black', label='demand')
plt.plot(network.generators_t.p['onshorewind']
         [0:96], color='blue', label='onshore wind')
plt.plot(network.generators_t.p['offshorewind']
         [0:96], color='green', label='offshore wind')
plt.plot(network.generators_t.p['solar'][0:96], color='orange', label='solar')
plt.plot(network.generators_t.p['nuclear']
         [0:96], color='purple', label='nuclear')
plt.plot(network.generators_t.p['OCGT'][0:96],
         color='brown', label='gas (OCGT)')
plt.xlabel('Time (Day/hours)')
plt.ylabel('Power (MWh)')
plt.legend(fancybox=True, shadow=True, loc='best')
plt.savefig(FILE_DIR / "graph/sweden_base_time_series.png", dpi=300, bbox_inches='tight')
plt.tight_layout()

# %%
labels = ['onshore wind',
          'offshore wind',
          'solar',
          'nuclear',
          'gas (OCGT)']
sizes = [network.generators_t.p['onshorewind'].sum(),
         network.generators_t.p['offshorewind'].sum(),
         network.generators_t.p['solar'].sum(),
         network.generators_t.p['nuclear'].sum(),
         network.generators_t.p['OCGT'].sum()]
colors = ['blue', 'green', 'orange', 'purple', 'brown']


def my_autopct(pct):
    # Only show the text if the percentage is greater than 0%
    return f'{pct:.1f}%' if pct > 0 else ''


patches, texts, autotexts = plt.pie(
    sizes,
    colors=colors,
    autopct=my_autopct,
    # Makes text white and bold
    textprops={'color': 'white', 'weight': 'bold'},
    wedgeprops={'linewidth': 0}
)

plt.axis('equal')
plt.title('Electricity mix', y=1.07)
plt.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.savefig(FILE_DIR / "graph/sweden_base_energy_mix.png", dpi=300, bbox_inches='tight')
plt.show()

# %%
'''This is part 2 of the project, we can fix problem later'''

# co2_limit=1000000 #tonCO2
# network.add("GlobalConstraint",
#             "co2_limit",
#             type="primary_energy",
#             carrier_attribute="co2_emissions",
#             sense="<=",
#             constant=co2_limit)
# network.optimize(solver_name='gurobi')


# network.generators.p_nom_opt #in MW

# #plot the generation and demand profiles for the first 4 days in January (96 hours)
# plt.plot(network.loads_t.p['load'][0:96], color='black', label='demand')
# plt.plot(network.generators_t.p['onshorewind'][0:96], color='blue', label='onshore wind')
# plt.plot(network.generators_t.p['offshorewind'][0:96], color='green', label='offshore wind')
# plt.plot(network.generators_t.p['solar'][0:96], color='orange', label='solar')
# plt.plot(network.generators_t.p['nuclear'][0:96], color='purple', label='nuclear')
# plt.plot(network.generators_t.p['OCGT'][0:96], color='brown', label='gas (OCGT)')
# plt.legend(fancybox=True, shadow=True, loc='best')

# #plot the generation mix
# labels = ['onshore wind', 'offshore wind', 'solar', 'nuclear', 'gas (OCGT)' ]
# sizes = [network.generators_t.p['onshorewind'].sum(),
#          network.generators_t.p['offshorewind'].sum(),
#          network.generators_t.p['solar'].sum(),
#          network.generators_t.p['nuclear'].sum(),
#          network.generators_t.p['OCGT'].sum()]

# colors = ['blue', 'green', 'orange', 'purple', 'brown']

# plt.pie(sizes,
#         colors=colors,
#         labels=labels,
#         wedgeprops={'linewidth':0})
# plt.axis('equal')

# plt.title('Electricity mix', y=1.07)


# %% [markdown]
# ## Part A

# choose a different country/region/city/system and calculate the optimal capacities for renewable and non-renewable generators. 
# You can add as many technologies as you want. Remember to provide a reference for the cost assumptions. Plot the dispatch time series for a week in summer and winter. Plot the annual electricity mix. Use the duration curves or the capacity factor to investigate the contribution of different technologies.

# %%
# Winter week and summer week


def plot_dispatch_week(network, start_date, end_date, title):
    dispatch = network.generators_t.p.loc[start_date:end_date, [
        "onshorewind", "offshorewind", "solar", "nuclear", "OCGT"]]
    demand = network.loads_t.p.loc[start_date:end_date, "load"]

    plt.figure(figsize=(14, 5))
    plt.plot(demand.index, demand, color="black", linewidth=2, label="demand")
    plt.stackplot(dispatch.index,
                  dispatch["onshorewind"],
                  dispatch["offshorewind"],
                  dispatch["solar"],
                  dispatch["nuclear"],
                  dispatch["OCGT"],
                  labels=["onshore wind", "offshore wind",
                          "solar", "nuclear", "gas (OCGT)"],
                  alpha=0.85)
    plt.title(title)
    plt.ylabel("Power [MW]")
    plt.legend(loc="upper left", ncol=3)
    plt.tight_layout()
    plt.show()


plot_dispatch_week(network,
                   "2015-01-02 00:00:00",
                   "2015-01-08 23:00:00",
                   "Dispatch - Winter week")
plot_dispatch_week(network,
                   "2015-07-03 00:00:00",
                   "2015-07-09 23:00:00",
                   "Dispatch - Summer week")

# %%
# Annual energy mix
annual_generation = network.generators_t.p.sum().sort_values(ascending=False)
print("Annual generation by technology (MWh):")
print(annual_generation.round(0))

labels = ["onshore wind", "offshore wind", "solar", "nuclear", "gas (OCGT)"]
sizes = [
    network.generators_t.p["onshorewind"].sum(),
    network.generators_t.p["offshorewind"].sum(),
    network.generators_t.p["solar"].sum(),
    network.generators_t.p["nuclear"].sum(),
    network.generators_t.p["OCGT"].sum()
]

colors = ['blue', 'green', 'orange', 'purple', 'brown']

plt.figure(figsize=(7, 7))
patches, texts, autotexts = plt.pie(sizes,
                                    colors=colors,
                                    autopct=my_autopct,
                                    textprops={'color': 'white',
                                               'weight': 'bold'},
                                    wedgeprops={"linewidth": 0})

plt.axis("equal")
plt.title("Annual electricity mix")
plt.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.savefig(FILE_DIR / "graph/sweden_base_annual_energy_mix.png", dpi=300, bbox_inches='tight')
plt.show()


# %%
# Duration curves
plt.figure(figsize=(10, 5))

for tech in ["onshorewind", "offshorewind", "solar", "nuclear", "OCGT"]:
    sorted_dispatch = network.generators_t.p[tech].sort_values(
        ascending=False).reset_index(drop=True)
    plt.plot(sorted_dispatch, label=tech)

plt.xlabel("Hour rank")
plt.ylabel("Dispatch [MW]")
plt.title("Duration curves by technology")
plt.legend()
plt.tight_layout()
plt.savefig(FILE_DIR / "graph/sweden_base_duration_curves.png", dpi=300, bbox_inches='tight')
plt.show()

# %% [markdown]
# ## Part B
#
# Investigate how sensitive your results are to the interannual variability of solar and wind generation.
# Plot the average capacity and variability obtained for every generator using different weather years.

weather_years = range(2000, 2018)
results = []

country = "SWE"

# fixed demand series: use one non-leap-year demand profile
fixed_load = df_elec[country].values   # should be 8760 long

for year in weather_years:
    print(f"Running weather year {year}...")

    snapshots = pd.date_range(
        f"{year}-01-01 00:00", f"{year}-12-31 23:00", freq="h")

    # skip leap years if fixed load has 8760 hours
    if len(snapshots) != len(fixed_load):
        print(
            f"Skipping {year}: snapshot length {len(snapshots)} != load length {len(fixed_load)}")
        continue

    # get weather-year profiles
    onshore_year = df_onshorewind.loc[df_onshorewind.index.year == year, country]
    offshore_year = df_offshorewind.loc[df_offshorewind.index.year == year, country]
    solar_year = df_solar.loc[df_solar.index.year == year, country]

    if not (len(onshore_year) == len(offshore_year) == len(solar_year) == len(snapshots)):
        print(f"Skipping {year}: mismatch in renewable profile lengths")
        continue

    # create fresh network
    n = pypsa.Network()
    n.set_snapshots(snapshots)

    n.add("Bus", "electricity bus")

    n.add("Load",
          "load",
          bus="electricity bus",
          p_set=fixed_load)

    # carriers
    n.add("Carrier", "onshorewind")
    n.add("Carrier", "offshorewind")
    n.add("Carrier", "solar")
    n.add("Carrier", "nuclear")
    n.add("Carrier", "gas", co2_emissions=0.19)

    # generators
    n.add("Generator",
          "onshorewind",
          bus="electricity bus",
          p_nom_extendable=True,
          carrier="onshorewind",
          capital_cost=capital_cost_onshorewind,
          marginal_cost=0,
          p_max_pu=onshore_year.values)

    n.add("Generator",
          "offshorewind",
          bus="electricity bus",
          p_nom_extendable=True,
          carrier="offshorewind",
          capital_cost=capital_cost_offshorewind,
          marginal_cost=0,
          p_max_pu=offshore_year.values)

    n.add("Generator",
          "solar",
          bus="electricity bus",
          p_nom_extendable=True,
          carrier="solar",
          capital_cost=capital_cost_solar,
          marginal_cost=0,
          p_max_pu=solar_year.values)

    n.add("Generator",
          "nuclear",
          bus="electricity bus",
          p_nom_extendable=True,
          carrier="nuclear",
          capital_cost=capital_cost_nuclear,
          marginal_cost=marginal_cost_nuclear)

    n.add("Generator",
          "OCGT",
          bus="electricity bus",
          p_nom_extendable=True,
          carrier="gas",
          capital_cost=capital_cost_OCGT,
          marginal_cost=marginal_cost_OCGT)

    # optimize
    status, condition = n.optimize(solver_name="gurobi")
    print(status, condition)

    if status != "ok":
        print(f"Skipping {year}: optimization failed")
        continue

    # store capacities
    opt_caps = n.generators.p_nom_opt.copy()
    opt_caps["year"] = year
    results.append(opt_caps)

df_sensitivity = pd.DataFrame(results).set_index("year")
print(df_sensitivity)

summary = pd.DataFrame({
    "mean": df_sensitivity.mean(),
    "std": df_sensitivity.std(),
    "relative_variability_%": df_sensitivity.std() / df_sensitivity.mean() * 100
})

print(summary)

summary["mean"].plot(kind="bar", yerr=summary["std"], capsize=5)


plt.scatter(df_sensitivity["onshorewind"], df_sensitivity["solar"])
plt.xlabel("Wind capacity")
plt.ylabel("Solar capacity")
plt.title("Wind–Solar trade-off")
plt.show()

# %% ====Part C=====
network

# Storage Costs
year = 2030
url = f"https://raw.githubusercontent.com/PyPSA/technology-data/v0.11.0/outputs/costs_{year}.csv"
costs = pd.read_csv(url, index_col=[0, 1])

costs.loc[costs.unit.str.contains("/kW"), "value"] *= 1e3
costs.unit = costs.unit.str.replace("/kW", "/MW")

defaults = {
    "FOM": 0,
    "VOM": 0,
    "efficiency": 1,
    "fuel": 0,
    "investment": 0,
    "lifetime": 25,
    "discount rate": 0.07,
}
costs = costs.value.unstack().fillna(defaults)

costs.at["OCGT", "fuel"] = costs.at["gas", "fuel"]
costs.at["CCGT", "fuel"] = costs.at["gas", "fuel"]

# --- Storage Units Cost Calculation 1---

capital_cost_storage_1 = annuity(10, 0.07) * costs.at["battery inverter", "investment"] + 2 * annuity(
    25, 0.07) * costs.at["battery storage", "investment"]
# ^ this is 2 hours of storage
capital_cost_storage_1


# --- Storage Units Cost Calculation 3---

costs["marginal_cost"] = costs["VOM"] + costs["fuel"] / costs["efficiency"]
# annuity = costs.apply(lambda x: annuity(x["discount rate"], x["lifetime"]), axis=1)
# changed discount rate and lifetime order ^
annuity = costs.apply(lambda x: annuity(
    x["lifetime"], x["discount rate"]), axis=1)

costs["capital_cost"] = (annuity + costs["FOM"] / 100) * costs["investment"]

capital_cost_storage_3 = costs.at["battery inverter",
                                  "capital_cost"] + 2 * costs.at["battery storage", "capital_cost"]
print(capital_cost_storage_3)

# We add another carrier: battery storage

network.add("Carrier", "battery", co2_emissions=0)

# --- Storage Units ---
network.add(
    "StorageUnit",
    "SE storage",
    bus="electricity bus",
    carrier="battery storage",

    max_hours=2,
    capital_cost=capital_cost_storage_3,
    efficiency_store=costs.at["battery inverter", "efficiency"],
    efficiency_dispatch=costs.at["battery inverter", "efficiency"],
    p_nom_extendable=True,
    cyclic_state_of_charge=True,
)

network.optimize(solver_name="gurobi") # Solve the optimization problem with the new storage unit
# add this if doesnt work , assign_all_duals=False

#Save the network to a NetCDF file
network.export_to_netcdf("sweden_storage_model.nc")


labels = ['onshore wind',
          'offshore wind',
          'solar',
          'nuclear',
          'gas (OCGT)',
          'battery storage']

sizes = [network.generators_t.p['onshorewind'].sum(),
         network.generators_t.p['offshorewind'].sum(),
         network.generators_t.p['solar'].sum(),
         network.generators_t.p['nuclear'].sum(),
         network.generators_t.p['OCGT'].sum(),
         network.storage_units_t.p['SE storage'].clip(lower=0).sum()]

colors = ['blue', 'green', 'orange', 'purple', 'brown', 'red']

patches, texts, autotexts = plt.pie(
    sizes,
    colors=colors,
    autopct=my_autopct,
    textprops={'color': 'white', 'weight': 'bold'},
    wedgeprops={'linewidth': 0}
)

plt.axis('equal')
plt.title('Electricity mix', y=1.07)
plt.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.savefig(FILE_DIR / "graph/sweden_storage_energy_mix.png", dpi=300, bbox_inches='tight')
plt.show()
# Print the capital costs for each technology
print("", capital_cost_OCGT, "OCGT")
print(capital_cost_nuclear, "Nuclear")
print("", capital_cost_solar, "Solar")
print("", capital_cost_onshorewind, "Onshore Wind")
print("", capital_cost_storage_3, "Storage 3")
