import pypsa
import pandas as pd

co2_price = 75  # €/tCO2

network = pypsa.Network("sweden_gas_modelA.nc")

gas_bus_names = [b for b in network.buses.index if "Gas_" in b]

for link in network.links.index:
        bus0 = network.links.at[link, "bus0"]
        bus1 = network.links.at[link, "bus1"]
        
        if bus0 in gas_bus_names and bus1 in gas_bus_names:
            network.links.at[link, "carrier"] = "gas_transport"
        else:
            network.links.at[link, "carrier"] = "gas_fuel"

# set emissions
network.carriers.loc["gas_fuel", "co2_emissions"] = 0.2
network.carriers.loc["gas_transport", "co2_emissions"] = 0

# add CO2 price into marginal cost
for gen in network.generators.index:
    carrier = network.generators.loc[gen, "carrier"]
    if carrier in network.carriers.index:
        co2_intensity = network.carriers.loc[carrier, "co2_emissions"]
        network.generators.loc[gen, "marginal_cost"] += co2_price * co2_intensity

# solve without CO2 constraint
network.optimize(solver_name="highs")
co2_emissions = (
    network.generators_t.p
    .multiply(network.generators.carrier.map(network.carriers.co2_emissions), axis=1)
    .sum()
    .sum()
)

print("Implied CO2 emissions (cap):", co2_emissions)
# === revert carriers back to original ===

for link in network.links.index:
    if network.links.at[link, "carrier"] in ["gas_fuel", "gas_transport"]:
        network.links.at[link, "carrier"] = "gas"

# revert generator carrier
if "Gas_source_Norway" in network.generators.index:
    network.generators.at["Gas_source_Norway", "carrier"] = "gas"

# optional cleanup
network.carriers.drop(["gas_fuel", "gas_transport"], errors="ignore", inplace=True)
network.global_constraints.drop("CO2Limit", errors="ignore", inplace=True)

print(network.carriers)
network.export_to_netcdf("sweden_priceconstraint_model.nc")
