import pypsa
import numpy as np
import matplotlib.pyplot as plt
from project_part_C import FILE_DIR, costs, capital_cost_storage
            #   1.    2.    4.     8.     16.    32.
REDUCTIONS  = [0.00, 0.25, 0.50, 0.75, 0.80, 0.85, 0.90]
TECHS       = ['onshorewind', 'offshorewind', 'solar', 'nuclear', 'OCGT', 'SE storage']
LABELS      = ['Onshore Wind', 'Offshore Wind', 'Solar', 'Nuclear', 'Gas (OCGT)', 'Battery Storage']
COLORS      = ['blue', 'green', 'orange', 'purple', 'brown', 'red']

def run_scenario(reduction):
    net = pypsa.Network(FILE_DIR / 'sweden_base_model.nc')
    if "battery" not in net.carriers.index:
        net.add("Carrier", "battery", co2_emissions=0)
    net.add("StorageUnit", "SE storage", bus="electricity bus", carrier="battery storage",
            max_hours=2, capital_cost=capital_cost_storage * (1 - reduction),
            efficiency_store=costs.at["battery inverter", "efficiency"],
            efficiency_dispatch=costs.at["battery inverter", "efficiency"],
            p_nom_extendable=True, cyclic_state_of_charge=True)
    net.optimize(solver_name="gurobi")
    caps = [net.generators.loc[t, 'p_nom_opt'] for t in TECHS[:-1]]
    caps += [net.storage_units.loc['SE storage', 'p_nom_opt']]
    return caps

# Run all scenarios
scenario_labels = [f"-{int(r*100)}%" for r in REDUCTIONS]
data = np.array([run_scenario(r) for r in REDUCTIONS])  # (n_scenarios, n_techs)

# Export to text file
cap_path = FILE_DIR / "sensitivity_installed_capacity.txt"
with open(cap_path, "w") as f:
    f.write(f"{'Scenario':<12}" + "".join(f"{l:>18}" for l in LABELS) + "\n")
    f.write("-" * (12 + 18 * len(LABELS)) + "\n")
    for label, row in zip(scenario_labels, data):
        f.write(f"{label:<12}" + "".join(f"{v:>18,.1f}" for v in row) + "\n")

# Plot
fig, ax = plt.subplots(figsize=(16, 8))
bottoms = np.zeros(len(scenario_labels))
x = np.arange(len(scenario_labels))

for i, (label, color) in enumerate(zip(LABELS, COLORS)):
    ax.bar(x, data[:, i], 0.5, bottom=bottoms, color=color, label=label, edgecolor='white', linewidth=0.5)
    for j in range(len(scenario_labels)):
        val = data[j, i]
        if val > 0:
            ax.text(x[j], bottoms[j] + val / 2, f"{val:,.0f}",
                    ha='center', va='center', fontsize=7, color='black', fontweight='bold')
    bottoms += data[:, i]

ax.set_xticks(x)
ax.set_xticklabels(scenario_labels, fontsize=10)
ax.set_xlabel('Battery Storage Cost Reduction', fontsize=12)
ax.set_ylabel('Installed Capacity (MW)', fontsize=12)
ax.set_title('Sensitivity Analysis – Installed Capacity per Scenario', fontsize=13, fontweight='bold')
ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=10)
ax.yaxis.grid(True, linestyle='--', alpha=0.5)
ax.set_axisbelow(True)
plt.tight_layout()

out_path = FILE_DIR / "graph" / "sensitivity_battery_cost.png"
out_path.parent.mkdir(parents=True, exist_ok=True)
plt.savefig(out_path, dpi=300, bbox_inches='tight')
plt.show()