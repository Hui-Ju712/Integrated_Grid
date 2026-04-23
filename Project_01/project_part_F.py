from pathlib import Path
import numpy as np
import pandas as pd
import pypsa
import matplotlib.pyplot as plt

from project_part_C import FILE_DIR, costs, capital_cost_storage_3, cost_reduction

# CO2 limits to sweep [tonnes/year]
co2_limits = [0.1e6, 0.5e6, 1e6, 2e6, 5e6, 10e6, 20e6, 40e6]

tech_labels = ["Onshore Wind", "Offshore Wind", "Solar PV", "Nuclear", "Gas (OCGT)", "Battery"]
tech_colors = ["#4C9BE8", "#1A5FA8", "#F5A623", "#9B59B6", "#C0392B", "#2ECC71"]
cap_cols    = ["cap_onshore", "cap_offshore", "cap_solar", "cap_nuclear", "cap_ocgt", "cap_battery"]

results = []

for co2_limit in co2_limits:
    print(f"Solving CO2 limit = {co2_limit/1e6:.1f} Mt ...")

    network = pypsa.Network(FILE_DIR / 'sweden_storage_model.nc')

    network.add(
        "GlobalConstraint",
        "CO2Limit",
        carrier_attribute="co2_emissions",
        sense="<=",
        constant=co2_limit, #MtCO2
    )

    network.optimize(solver_name="gurobi")

    results.append({
        "co2_Mt":       co2_limit / 1e6,
        "cap_onshore":  network.generators.loc["onshorewind",  "p_nom_opt"] / 1e3,
        "cap_offshore": network.generators.loc["offshorewind", "p_nom_opt"] / 1e3,
        "cap_solar":    network.generators.loc["solar",        "p_nom_opt"] / 1e3,
        "cap_nuclear":  network.generators.loc["nuclear",      "p_nom_opt"] / 1e3,
        "cap_ocgt":     network.generators.loc["OCGT",         "p_nom_opt"] / 1e3,
        "cap_battery":  network.storage_units.loc["SE storage", "p_nom_opt"] / 1e3,
    })

df = pd.DataFrame(results)

# Plot
fig, ax = plt.subplots(figsize=(14, 6))
x_labels = df["co2_Mt"].apply(lambda v: f"{v:.1f}" if v < 1 else f"{int(v)}").tolist()
total = df[cap_cols].sum(axis=1).values
bottom = np.zeros(len(df))

for col, label, color in zip(cap_cols, tech_labels, tech_colors):
    vals = df[col].values
    bars = ax.bar(x_labels, vals, bottom=bottom,
                  label=label, color=color, edgecolor="white", linewidth=0.5)
    for i, (bar, val) in enumerate(zip(bars, vals)):
        if val >= 0.015 * total[i]:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bottom[i] + val / 2,
                f"{val:.1f}",
                ha="center", va="center",
                fontsize=7, color="white", fontweight="bold"
            )
    bottom += vals

ax.set_xlabel("CO₂ Limit (Mt CO₂/year)", fontsize=12)
ax.set_ylabel("Optimal Installed Capacity (GW)", fontsize=12)
ax.set_title("Optimal Capacity Mix vs. CO₂ Constraint", fontsize=13, fontweight="bold")
ax.legend(loc="upper left", fontsize=10, framealpha=0.85)
ax.grid(axis="y", linestyle="--", alpha=0.4)

plt.tight_layout()
plt.savefig(FILE_DIR / "graph/co2_sensitivity_capacity.png", dpi=300, bbox_inches="tight")
plt.show()