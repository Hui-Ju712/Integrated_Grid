#%% 
from pyexpat import model
import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
'''discuss the impact of increasing demand'''

FILE_DIR = Path(__file__).parent
model_dir = FILE_DIR / 'nordics_gas_transport_model.nc' 
network = pypsa.Network(model_dir)

growth_factors = {
    "load": 2,  
    "load_denmark":2,
    "load_norway": 2,
    "load_finland": 2
}

for load_name, factor in growth_factors.items():
    if load_name in network.loads.index:
        network.loads_t.p_set[load_name] *= factor
        print(f"{load_name} electricity demand has grown by {factor} times")
    else:
        print(f"No {load_name} Load")

nuclear_gens = network.generators[network.generators.carrier == 'nuclear'].index
for gen in nuclear_gens:
    network.generators.at[gen, 'p_min_pu'] = 0.75 

network.optimize(solver_name='gurobi')
#%%print capacity results
print(network.generators.p_nom_opt)
batt_power_mw = network.storage_units.at["SE storage", "p_nom_opt"]
batt_max_hours = network.storage_units.at["SE storage", "max_hours"]
total_energy_capacity = batt_power_mw * batt_max_hours
print(f'Total storage energy capacity: {total_energy_capacity:.2f} MWh')

#The capacity of OCGT in each country
# MW_th
gas_capacity_SWE = network.links.at["OCGT_Sweden", "p_nom_opt"]
gas_capacity_DKK= network.links.at["OCGT_Denmark", "p_nom_opt"]
gas_capacity_FIN= network.links.at["OCGT_Finland", "p_nom_opt"]

ocgt_efficiency = network.links.at["OCGT_Sweden", "efficiency"]

elec_output_capacity_SWE = gas_capacity_SWE * ocgt_efficiency
elec_output_capacity_DKK = gas_capacity_DKK * ocgt_efficiency
elec_output_capacity_FIN = gas_capacity_FIN * ocgt_efficiency

# print(f"Sweden OCGT gas capacity: {gas_capacity_SWE:.2f} MW_th")
# print(f"Denmark OCGT gas capacity: {gas_capacity_DKK:.2f} MW_th")
# print(f"Finland OCGT gas capacity: {gas_capacity_FIN:.2f} MW_th")
print(f"Sweden OCGT electric output capacity: {elec_output_capacity_SWE:.2f} MW_el")
print(f"Denmark OCGT electric output capacity: {elec_output_capacity_DKK:.2f} MW_el")
print(f"Finland OCGT electric output capacity: {elec_output_capacity_FIN:.2f} MW_el")

#%% plot the generation profile for the first four days
time_index = network.loads_t.p.index[0:96]

#source side
onshore = network.generators_t.p['onshorewind'][0:96].fillna(0)
solar = network.generators_t.p['solar'][0:96].fillna(0)
gas = (network.links_t.p0['OCGT_Sweden'][0:96] * 0.39).fillna(0)
nuclear = network.generators_t.p['nuclear'][0:96].fillna(0)

norway = network.lines_t.p1['Sweden - Norway'][0:96].fillna(0)
finland = network.lines_t.p1['Sweden - Finland'][0:96].fillna(0)
denmark = network.lines_t.p1['Sweden - Denmark'][0:96].fillna(0)
import_electricity = norway + finland + denmark

#storage_discharge = network.storage_units_t.p['SE storage'][0:96].fillna(0).clip(lower=0).values


source = [onshore, solar, gas, nuclear, import_electricity]
labels = ['Onshore Wind', 'Solar', 'Gas (OCGT)', 'Nuclear', 'Import Electricity']
colors = [
    "#4E79A7",  # blue
    "#F28E2B",  # orange
    "#59A14F",  # green
    "#76B7B2",  # teal
    "#B07AA1",  # purple
    # "#EDC948",  # mustard yellow
]

diagnostic_df = pd.DataFrame({
    'Onshore Wind': onshore,
    'Solar': solar,
    'Gas (OCGT)': gas,
    'Nuclear': nuclear,
    'Import Electricity': import_electricity
}, index=time_index)

plt.figure(figsize=(12, 6))

for col in diagnostic_df.columns:
    plt.plot(diagnostic_df.index, diagnostic_df[col], linewidth=2, label=col, alpha=0.8)

plt.xlabel('Time')
plt.ylabel('Power (MWh)')
plt.title('Diagnostic Plot: Individual Generation Profiles')
plt.legend(loc='upper right', bbox_to_anchor=(1.25, 1))
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.savefig(FILE_DIR /'graph/sweden_time_series_demand_2x.png', dpi=300, bbox_inches='tight')
plt.show()
#%% plot energy mix
import_no_total = network.lines_t.p1['Sweden - Norway'].clip(lower=0).sum()
import_fi_total = network.lines_t.p1['Sweden - Finland'].clip(lower=0).sum()
import_dk_total = network.lines_t.p1['Sweden - Denmark'].clip(lower=0).sum()

labels = [
    'Domestic Onshore Wind',
    'Domestic Solar',
    'Domestic Gas (OCGT)',
    'Domestic Nuclear', 
    'Import from Norway',
    'Import from Finland',
    'Import from Denmark',
]
sizes = [
    network.generators_t.p['onshorewind'].sum(),
    network.generators_t.p['solar'].sum(),
    elec_output_capacity_SWE,
    network.generators_t.p['nuclear'].sum(),
    import_no_total,
    import_fi_total,
    import_dk_total,
]

colors = [
    "#4E79A7",  # blue
    "#F28E2B",  # orange
    "#59A14F",  # green
    "#76B7B2",  # teal
    "#EDC948",   # mustard yellow
    "#76B7B2",   # teal
    "#FF9DA7",   # pink
    
]
        
patches, texts, autotexts = plt.pie(
    sizes,
    colors=colors,
    autopct='%1.1f%%',        
    textprops={'color': 'white', 'weight': 'bold'}, # Makes text white and bold
    wedgeprops={'linewidth': 0}
)

plt.axis('equal')
plt.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.savefig(FILE_DIR / "graph/sweden_energymix_demand_2x.png", dpi=300, bbox_inches='tight')
plt.show()
# %%
