from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pypsa

# %% ====Part C=====

FILE_DIR = Path(__file__).parent

# --- File paths ---
model_dir = FILE_DIR / "sweden_base_model.nc"
load_dir = FILE_DIR / "data/electricity_demand.csv"
cf_onshore_dir = FILE_DIR / "data/CF_onshore_wind_1979-2017.csv"
cf_offshore_dir = FILE_DIR / "data/CF_offshore_wind_1979-2017.csv"
cf_pv_dir = FILE_DIR / "data/CF_pv_optimal.csv"

# --- Load data ---
df_elec = pd.read_csv(load_dir, sep=";", index_col=0)  # in MWh
df_elec.index = pd.to_datetime(df_elec.index)

network = pypsa.Network(model_dir)


def annuity(n, r):
    """Calculate the annuity factor for an asset with lifetime n years and discount rate r."""
    return r / (1.0 - 1.0 / (1.0 + r) ** n) if r > 0 else 1 / n


# --- Load technology cost data ---
year = 2030
url = f"https://raw.githubusercontent.com/PyPSA/technology-data/v0.11.0/outputs/costs_{year}.csv"
costs = pd.read_csv(url, index_col=[0, 1])

# Convert costs from per-kW to per-MW
costs.loc[costs.unit.str.contains("/kW"), "value"] *= 1e3
costs.unit = costs.unit.str.replace("/kW", "/MW")

# Fill missing values with defaults
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

# Set fuel costs for gas technologies
costs.at["OCGT", "fuel"] = costs.at["gas", "fuel"]
costs.at["CCGT", "fuel"] = costs.at["gas", "fuel"]

# --- Compute capital and marginal costs ---
costs["marginal_cost"] = costs["VOM"] + costs["fuel"] / costs["efficiency"]
annuity_factor = costs.apply(lambda x: annuity(x["lifetime"], x["discount rate"]), axis=1)
costs["capital_cost"] = (annuity_factor + costs["FOM"] / 100) * costs["investment"]

capital_cost_storage = (
    costs.at["battery inverter", "capital_cost"]
    + 2 * costs.at["battery storage", "capital_cost"]  # 2 hours of storage
)
print(f"Battery storage capital cost: {capital_cost_storage:.2f} €/MW")

# --- Add battery storage to network ---
cost_reduction = 0.5

network.add("Carrier", "battery storage", co2_emissions=0)

network.add(
    "StorageUnit",
    "SE storage",
    bus="electricity bus",
    carrier="battery storage",
    max_hours=2,
    capital_cost=cost_reduction * capital_cost_storage,
    efficiency_store=costs.at["battery inverter", "efficiency"],
    efficiency_dispatch=costs.at["battery inverter", "efficiency"],
    p_nom_extendable=True,
    cyclic_state_of_charge=True,
)

# --- Optimise ---
network.optimize(solver_name="gurobi")

# --- Save network ---
network.export_to_netcdf(FILE_DIR / "sweden_storage_model.nc")


# %% ====Plotting====

def my_autopct(pct):
    """Only show percentage label if slice is non-zero."""
    return f"{pct:.1f}%" if pct > 0 else ""


# --- Energy Mix Pie Chart ---
labels = ["onshore wind", "offshore wind", "solar", "nuclear", "gas (OCGT)", "battery storage"]
colors = ["blue", "green", "orange", "purple", "brown", "green"]

sizes = [
    network.generators_t.p["onshorewind"].sum(),
    network.generators_t.p["offshorewind"].sum(),
    network.generators_t.p["solar"].sum(),
    network.generators_t.p["nuclear"].sum(),
    network.generators_t.p["OCGT"].sum(),
    network.storage_units_t.p["SE storage"].clip(lower=0).sum(),
]

fig, ax = plt.subplots()
patches, texts, autotexts = ax.pie(
    sizes,
    colors=colors,
    autopct=my_autopct,
    textprops={"color": "white", "weight": "bold"},
    wedgeprops={"linewidth": 0},
)
ax.axis("equal")
ax.set_title("Electricity mix", y=1.07)
ax.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
fig.savefig(FILE_DIR / "graph/sweden_storage_energy_mix.png", dpi=300, bbox_inches="tight")
plt.show()

# --- Installed Capacity Pie Chart ---
gen_caps = network.generators.groupby("carrier")["p_nom_opt"].sum()
storage_caps = network.storage_units.groupby("carrier")["p_nom_opt"].sum()
all_caps = pd.concat([gen_caps, storage_caps])
all_caps = all_caps[all_caps > 0]  # Drop zero-capacity entries

# Custom color mapping
color_map = {
    "onshorewind": "#0000FF",    # pure blue
    "offshorewind": "#87CEEB",   # light blue
    "solar": "#FF8C00",      # orange
    "nuclear": "#800080",    # purple
    "gas": "#A52A2A",        # brown
    "battery storage": "#228B22",    # green
}
colors = [color_map.get(carrier, "#999999") for carrier in all_caps.index]

fig, ax = plt.subplots()
patches, texts, autotexts = ax.pie(
    all_caps.values,
    labels=all_caps.index,
    autopct=my_autopct,
    colors=colors,
    textprops={"color": "white", "weight": "bold"},
)
ax.axis("equal")
ax.set_title("Installed Capacity Mix (MW)")
ax.legend(patches, all_caps.index, loc="center left", bbox_to_anchor=(1, 0.5))
fig.tight_layout()
fig.savefig(FILE_DIR / "graph/sweden_storage_capacity_mix.png", dpi=300, bbox_inches="tight")
plt.show()