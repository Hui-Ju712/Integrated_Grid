# Connect electricity sector with transport sector using synthetic EV demand
# Assumption: all passenger cars are replaced by EVs

import matplotlib.pyplot as plt
import pandas as pd
import pypsa
from pathlib import Path
import numpy as np

FILE_DIR = Path(__file__).parent
base_model_path = FILE_DIR / "sweden_gas_model.nc"
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

# Approximate passenger car stock
# Interpreted as: existing EVs + petrol/diesel cars all become EVs
number_cars = {
    "Sweden": 5_000_000,
    "Denmark": 2_700_000,
    "Finland": 2_800_000,
    "Norway": 2_900_000,
}

km_per_year = {
    "Sweden": 11_300,
    "Denmark": 11_300,
    "Finland": 11_300,
    "Norway": 11_300,
}

ev_consumption = 0.18      # kWh/km
bev_energy = 0.05          # MWh/car = 50 kWh
bev_charger_rate = 0.011   # MW/car = 11 kW
charger_efficiency = 0.90

# =========================
# Synthetic EV demand profile
# =========================

snapshots = network.snapshots
hour = pd.Series(snapshots.hour, index=snapshots)

# Driving energy demand shape:
# morning + evening driving peaks
daily_profile = (
    np.exp(-0.5 * ((hour - 8) / 2) ** 2)
    + np.exp(-0.5 * ((hour - 17) / 3) ** 2)
)

# Normalize over the full model period
daily_profile = daily_profile / daily_profile.sum()

# Charging availability:
# most cars are available at night and evening
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

    # Check electricity bus exists
    if elec_bus not in network.buses.index:
        raise KeyError(
            f"Electricity bus '{elec_bus}' for {country} not found. "
            f"Available buses are: {list(network.buses.index)}"
        )

    # Annual EV demand in MWh/year
    annual_ev_demand_MWh = (
        number_cars[country]
        * km_per_year[country]
        * ev_consumption
        / 1000
    )

    # Hourly EV driving demand in MW
    ev_demand = daily_profile * annual_ev_demand_MWh

    network.add(
        "Bus",
        ev_bus,
        carrier="EV",
    )

    network.add(
        "Load",
        f"EV demand {country}",
        bus=ev_bus,
        p_set=ev_demand.values,
        carrier="EV demand",
    )

    network.add(
        "Link",
        f"EV charger {country}",
        bus0=elec_bus,
        bus1=ev_bus,
        p_nom=number_cars[country] * bev_charger_rate,
        p_max_pu=availability.values,
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
        p_max_pu=availability.values,
        efficiency=charger_efficiency,
        carrier="V2G",
    )

# =========================
# Optimise
# =========================

network.optimize(solver_name="gurobi")
network.export_to_netcdf("nordics_gas_transport_model.nc")

# =========================
# Results
# =========================


print(network.generators.p_nom_opt)


print(f"Total annualized system cost: {network.objective/1e6:.2f} million €")

print("\nEV annual demand by country, TWh:")
ev_loads = [f"EV demand {c}" for c in countries]
print(network.loads_t.p_set[ev_loads].sum().div(1e6).round(3))

print("\nOptimised generator capacities:")
print(network.generators.p_nom_opt.round(2))

print("\nOptimised link capacities:")
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
        network.loads_t.p_set[f"EV demand {country}"].loc[date].rename("EV driving demand"),
        network.links_t.p0[f"EV charger {country}"].loc[date].rename("EV charging from grid"),
        network.links_t.p1[f"V2G {country}"].loc[date].rename("V2G to grid"),
        network.stores_t.e[f"EV battery {country}"].loc[date].rename("EV battery SOC"),
    ],
    axis=1,
)

plot_df.plot(figsize=(10, 5))
plt.title(f"EV sector operation in {country} on {date}")
plt.ylabel("MW or MWh")
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()