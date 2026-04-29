import pypsa
import pandas as pd

co2_price = 75  # €/tCO2

network = pypsa.Network("sweden_gas_model.nc")

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
network.export_to_netcdf("sweden_priceconstraint_model.nc")
