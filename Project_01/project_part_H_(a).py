import pypsa
import pandas as pd

co2_limits = [1e8, 5e7, 1e7, 5e6, 1e6, 5e5, 0]

results = []


for limit in co2_limits:

    network = pypsa.Network("sweden_gas_model.nc")

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


    network.generators.loc["Gas_source_Norway", "carrier"] = "gas_fuel"

    # add constraint
    network.add("GlobalConstraint",
                "CO2Limit",
                type="primary_energy",
                carrier_attribute="co2_emissions",
                sense="<=",
                constant=limit)

    network.optimize(solver_name="highs")

    results.append({
        "co2_limit": limit,
        "system_cost": network.objective,
        "co2_price": network.global_constraints.mu["CO2Limit"],
        "gas_use": network.generators_t.p["Gas_source_Norway"].sum(),
        "wind": network.generators.p_nom_opt.get("onshorewind", 0),
        "solar": network.generators.p_nom_opt.get("solar", 0),
        "nuclear": network.generators.p_nom_opt.get("nuclear", 0)
    })
total_emissions = (
    network.generators_t.p["Gas_source_Norway"].sum()
    * 0.2
)
for limit in limits:
    print(f"Limit: {limit}, Emissions: {total_emissions}")
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

network.export_to_netcdf("sweden_varyconstraint_model.nc")

df_results = pd.DataFrame(results)
print(df_results)
import matplotlib.pyplot as plt

df_plot = df_results.iloc[0:6]

plt.plot(df_plot["co2_limit"], -df_plot["co2_price"], marker='o')
plt.xlabel("CO2 limit (tCO2)")
plt.ylabel("CO2 price (€/tCO2)")
plt.title("CO2 Price vs CO2 Constraint")
plt.gca().invert_xaxis()
plt.grid()
plt.show()


plt.plot(df_plot["co2_limit"], df_plot["system_cost"]/1e6, marker='o')
plt.xlabel("CO2 limit (tCO2)")
plt.ylabel("System cost (M€)")
plt.title("System Cost vs CO2 Constraint")
plt.gca().invert_xaxis()
plt.grid()
plt.show()

hours = 8760  # or your simulation length
df_results["gas_capacity_equiv"] = df_results["gas_use"] / hours

plt.plot(df_results["co2_limit"], df_results["gas_capacity_equiv"], label="Gas (equiv)")
plt.plot(df_results["co2_limit"], df_results["nuclear"], label="Nuclear")
plt.plot(df_results["co2_limit"], df_results["wind"], label="Wind")
plt.plot(df_results["co2_limit"], df_results["solar"], label="Solar")


plt.xlabel("CO2 limit (tCO2)")
plt.ylabel("Installed capacity (MW)")
plt.title("Capacity vs CO2 Constraint")
plt.legend()
plt.gca().invert_xaxis()
plt.grid()
plt.show()
print(network.generators.p_nom_opt)
