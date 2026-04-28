# %%
import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path

FILE_DIR = Path(__file__).parent

# Load the connected Sweden-Norway-Finland-Denmark model
base_model_path = FILE_DIR / "sweden_network_model.nc"
network = pypsa.Network(base_model_path)

# -----------------------------
# Cap Swedish onshore wind
# -----------------------------
gen_name = "onshorewind"

if gen_name not in network.generators.index:
    raise KeyError(f"{gen_name} not found in network.generators.index")

network.generators.loc[gen_name, "p_nom_extendable"] = True
network.generators.loc[gen_name, "p_nom_max"] = 5400.0
network.generators.loc[gen_name, "p_nom_min"] = 0.0

# Re-optimize
network.optimize(solver_name="gurobi")

# Save modified case
output_path = FILE_DIR / "sweden_connecting_onshore5400.nc"
network.export_to_netcdf(output_path)

print("Saved:", output_path)
print()
print(network.generators[["bus", "carrier", "p_nom_opt"]])

# Comparision

# %%

base = pypsa.Network(FILE_DIR / "sweden_network_model.nc")
capped = pypsa.Network(FILE_DIR / "sweden_connecting_onshore5400.nc")

# Build comparison dataframe
cap_compare = pd.DataFrame({
    "base_MW": base.generators.p_nom_opt,
    "capped_MW": capped.generators.p_nom_opt
})

cap_compare["carrier"] = base.generators.carrier
cap_grouped = cap_compare.groupby("carrier").sum()

# Plot
ax = cap_grouped.plot(kind="bar", figsize=(10, 6))

plt.ylabel("Installed Capacity (MW)")
plt.title("Capacity by Technology (Base vs Onshore Wind Cap)")
plt.xticks(rotation=45)
plt.grid(axis="y")
plt.tight_layout()
plt.show()


cap_grouped["difference_MW"] = cap_grouped["capped_MW"] - \
    cap_grouped["base_MW"]
cap_grouped["difference_MW"].plot(kind="bar", figsize=(8, 5))

plt.ylabel("Change in Capacity (MW)")
plt.title("Capacity Change After Wind Cap")
plt.axhline(0)
plt.grid(axis="y")
plt.tight_layout()
plt.show()

# Build comparison dataframe (aligned index)
cap_compare = pd.DataFrame(index=base.generators.index)
cap_compare["base_MW"] = base.generators.p_nom_opt
cap_compare["capped_MW"] = capped.generators.p_nom_opt

# Optional: sort by base capacity for nicer visual order
cap_compare = cap_compare.sort_values("base_MW", ascending=False)

# Plot grouped bars
ax = cap_compare.plot(kind="bar", figsize=(12, 6), width=0.8)

plt.ylabel("Installed Capacity (MW)")
plt.title("Optimal Generator Capacity: Base vs Onshore Wind Cap")
plt.xticks(rotation=45, ha="right")
plt.grid(axis="y")

plt.legend(["Base", "Capped"])

plt.tight_layout()
plt.show()
