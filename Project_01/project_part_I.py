# Connect electricity sector with transport sector using EV demand profile from CSV
# Assumption: all passenger cars are replaced by EVs

import matplotlib.pyplot as plt
import pandas as pd
import pypsa
from pathlib import Path
import numpy as np

FILE_DIR = Path(__file__).parent
DATA_DIR = FILE_DIR / "data"

base_model_path = FILE_DIR / "sweden_priceconstraint_model.nc"
ev_profile_path = DATA_DIR / "ev_profile_path.csv"

network = pypsa.Network(base_model_path)

# =========================
# Main assumptions
# =========================

electricity_buses = {
    "Sweden": "electricity bus",
    "Denmark": "Denmark",
    "Finland": "Finland",
    "Norway": "Norway",
}

countries = ["Sweden", "Denmark", "Finland", "Norway"]

number_cars = {
    "Sweden": 5_000_000,
    "Denmark": 2_700_000,
    "Finland": 2_800_000,
    "Norway": 2_900_000,
}

bev_energy = 0.05          # MWh/car = 50 kWh
bev_charger_rate = 0.011   # MW/car = 11 kW
charger_efficiency = 0.90

# =========================
# Load EV demand profile from CSV
# =========================

ev_df = pd.read_csv(ev_profile_path)

ev_df["utc_time"] = pd.to_datetime(ev_df["utc_time"], utc=True)
ev_df = ev_df.set_index("utc_time")

# Match PyPSA snapshots
model_snapshots_utc = pd.to_datetime(network.snapshots, utc=True)
ev_df = ev_df.reindex(model_snapshots_utc)

# Check for missing values after matching snapshots
if ev_df.isna().any().any():
    missing_times = ev_df[ev_df.isna().any(axis=1)].index[:10]
    raise ValueError(
        "EV demand profile does not fully match the model snapshots. "
        f"First missing timestamps: {missing_times}"
    )

# Use original PyPSA snapshot index
ev_df.index = network.snapshots

# Check all required countries exist in CSV
missing_countries = [c for c in countries if c not in ev_df.columns]
if missing_countries:
    raise KeyError(
        f"Missing countries in EV demand CSV: {missing_countries}. "
        f"Available columns are: {list(ev_df.columns)}"
    )

# =========================
# Charging availability profile
# =========================

snapshots = network.snapshots
hour = pd.Series(snapshots.hour, index=snapshots)

availability = pd.Series(0.30, index=snapshots)

availability[(hour >= 0) & (hour <= 6)] = 0.90
availability[(hour >= 18) & (hour <= 23)] = 0.80
availability[(hour >= 8) & (hour <= 16)] = 0.20

# =========================
# Add EV sector
# =========================

for country in countries:

    ev_bus = f"EV_{country}"
    elec_bus = electricity_buses[country]

    if elec_bus not in network.buses.index:
        raise KeyError(
            f"Electricity bus '{elec_bus}' for {country} not found. "
            f"Available buses are: {list(network.buses.index)}"
        )

    # Hourly EV electricity demand from CSV, assumed MW
    ev_demand = ev_df[country]

    network.add(
        "Bus",
        ev_bus,
        carrier="EV",
    )

    network.add(
        "Load",
        f"EV demand {country}",
        bus=ev_bus,
        p_set=ev_demand,
        carrier="EV demand",
    )

    network.add(
        "Link",
        f"EV charger {country}",
        bus0=elec_bus,
        bus1=ev_bus,
        p_nom=number_cars[country] * bev_charger_rate,
        p_max_pu=availability,
        efficiency=charger_efficiency,
        carrier="EV charger",
    )

    network.add(
        "Store",
        f"EV battery {country}",
        bus=ev_bus,
        e_nom=number_cars[country] * bev_energy,
        e_cyclic=True,
        carrier="EV battery",
    )

    network.add(
        "Link",
        f"V2G {country}",
        bus0=ev_bus,
        bus1=elec_bus,
        p_nom=number_cars[country] * bev_charger_rate,
        p_max_pu=availability,
        efficiency=charger_efficiency,
        carrier="V2G",
    )

# =========================
# Optimise
# =========================

network.optimize(solver_name="gurobi")

network.export_to_netcdf(FILE_DIR / "nordics_gas_transport_model.nc")

# =========================
# Results
# =========================

print(network.generators.p_nom_opt)

print(f"Total annualized system cost: {network.objective / 1e6:.2f} million €")

print("\nEV annual demand by country, TWh:")
ev_loads = [f"EV demand {c}" for c in countries]
print(network.loads_t.p_set[ev_loads].sum().div(1e6).round(3))

print("\nOptimised generator capacities, MW:")
print(network.generators.p_nom_opt.round(2))

print("\nOptimised link capacities, MW:")
print(network.links.p_nom_opt.round(2))

print("\nEV charger electricity use, TWh:")
ev_chargers = [f"EV charger {c}" for c in countries]
print(network.links_t.p0[ev_chargers].sum().div(1e6).round(3))

# =========================
# Plot one country
# =========================

date = "2015-07-01"
country = "Sweden"

plot_df = pd.concat(
    [
        network.loads_t.p_set[f"EV demand {country}"]
        .loc[date]
        .rename("EV driving demand"),

        network.links_t.p0[f"EV charger {country}"]
        .loc[date]
        .rename("EV charging from grid"),

        (-network.links_t.p1[f"V2G {country}"])
        .loc[date]
        .rename("V2G to grid"),

        network.stores_t.e[f"EV battery {country}"]
        .loc[date]
        .rename("EV battery SOC"),
    ],
    axis=1,
)

plot_df.plot(figsize=(10, 5))
plt.title(f"EV sector operation in {country} on {date}")
plt.ylabel("MW or MWh")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()