import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path

# %% ====Part C=====
FILE_DIR = Path(__file__).parent
model_dir = FILE_DIR / 'sweden_base_model.nc' 
Load_dir= FILE_DIR / 'data/electricity_demand.csv'
CF_onshore_dir = FILE_DIR / 'data/CF_onshore_wind_1979-2017.csv'
CF_offshore_dir = FILE_DIR / 'data/CF_offshore_wind_1979-2017.csv'
CF_pv_dir = FILE_DIR / 'data/CF_pv_optimal.csv'
df_elec = pd.read_csv(Load_dir, sep=';', index_col=0) # in MWh
df_elec.index = pd.to_datetime(df_elec.index) #change index to datatime
network = pypsa.Network(model_dir)

def annuity(n, r):
    """ Calculate the annuity factor for an asset with lifetime n years and
    discount rate  r """

    if r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n

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

def my_autopct(pct):
    # Only show the text if the percentage is greater than 0%
    return f'{pct:.1f}%' if pct > 0 else ''

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
print("", capital_cost_nuclear, "Nuclear")
print("", capital_cost_solar, "Solar")
print("", capital_cost_onshorewind, "Onshore Wind")
print("", capital_cost_storage_3, "Storage 3")