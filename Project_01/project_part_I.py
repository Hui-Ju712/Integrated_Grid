import matplotlib.pyplot as plt
import pandas as pd
import pypsa

# Load EV demand data
data_el_EV = pd.read_csv("data/EV_electricity_demand.csv", sep=";")
data_el_EV.index = pd.DatetimeIndex(data_el_EV["utc_time"])

ev_country_codes = {
    "Sweden": "SWE",
    "Denmark": "DNK",
    "Finland": "FIN",
    "Norway": "NOR",
}

electricity_buses = {
    "Sweden": "electricity bus",
    "Denmark": "Denmark",
    "Finland": "Finland",
    "Norway": "Norway",
}

# ERIFY number
number_cars = {
    "Sweden": 5_000_000,
    "Denmark": 2_700_000,
    "Finland": 2_800_000,
    "Norway": 2_900_000,
}

bev_charger_rate = 0.011   # MW per car
bev_energy = 0.05          # MWh per car
charger_efficiency = 0.90

for country, code in ev_country_codes.items():

    ev_bus = f"EV_{country}"
    elec_bus = electricity_buses[country]

    ev_demand = data_el_EV[code].reindex(network.snapshots).fillna(0)

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

    # Optional V2G
    network.add(
        "Link",
        f"V2G {country}",
        bus0=ev_bus,
        bus1=elec_bus,
        p_nom=number_cars[country] * bev_charger_rate,
        efficiency=charger_efficiency,
        carrier="V2G",
    )