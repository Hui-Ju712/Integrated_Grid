'''Run part g of the project, creating gas network
Assumption: Norway providing gas, Denamrk and Finland add gas generators 
'''
from pyexpat import model
import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
#impoert network, swedan case consider storage unit 
FILE_DIR = Path(__file__).parent
model_dir = FILE_DIR / 'sweden_network_model.nc' 
network = pypsa.Network(model_dir)

#===Add gas network===
# Add gas buses
network.add("Bus", "Gas_Norway", carrier="gas")
network.add("Bus", "Gas_Denmark", carrier="gas")
network.add("Bus", "Gas_Finland", carrier="gas")
network.add("Bus", "Gas_Sweden", carrier="gas") #need to say carrier? 

def annuity(n,r):
    """ Calculate the annuity factor for an asset with lifetime n years and
    discount rate  r """

    if r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n

#add Norway as gas supplier 
fuel_cost = 21.6  # in €/MWh_th
network.add("Generator",
            "Gas_source_Norway",
            bus="Gas_Norway", #add in gas bus
            p_nom_extendable=True,
            carrier="gas",
            marginal_cost=fuel_cost)

#Add gas generators. make sure the gas in pipeline can be used as the source of OCGT in Sweden, Denmark and Finland
capital_cost_OCGT = annuity(25, 0.07)*560000*(1+0.033)  # in €/MW
efficiency = 0.39  # MWh_elec/MWh_th
marginal_cost_OCGT = fuel_cost/efficiency  # in €/MWh_el
network.add("Link",
            "OCGT_Finland",
            bus0="Gas_Finland",   
            bus1="Finland",      
            p_nom_extendable=True,
            carrier="gas",
            efficiency=efficiency,             
            capital_cost=capital_cost_OCGT,    
            marginal_cost=0)                   #marginal cost is 0 because the cost of fuel is already included in the gas source (Norway)

network.add("Link",
            "OCGT_Denmark",
            bus0="Gas_Denmark",   
            bus1="Denmark",      
            p_nom_extendable=True,
            carrier="gas",
            efficiency=efficiency,             
            capital_cost=capital_cost_OCGT,    
            marginal_cost=0)                   #marginal cost is 0 because the cost of fuel is already included in the gas source (Norway)

#remove the original OCGT generator in Sweden, and replace it with a link from gas bus to Sweden bus
network.remove("Generator", "OCGT") 
network.add("Link",
            "OCGT_Sweden",
            bus0="Gas_Sweden",   
            bus1="electricity bus",      
            p_nom_extendable=True,
            carrier="gas",
            efficiency=efficiency,             
            capital_cost=capital_cost_OCGT,    
            marginal_cost=0)                   #marginal cost is 0 because the cost of fuel is already included in the gas source (Norway)


#add gas links between countries
lengths = {
    "SE_NO": 530, #km
    "SE_FI": 450,
    "SE_DK": 160,
    "NO_DK": 480
}
'''From https://github.com/PyPSA/technology-data/blob/v0.11.0/outputs/costs_2030.csv, 
CH4 (g) pipeline FOM 1.5 %/yr
investment 87.22 EUR/MW/km
lifetime 50 yr'''

capital_cost_unit = (annuity(50,0.07)+0.015)*87.22  # in €/MW/km, including FOM and investment cost

network.add("Link",
            "Gas_Sweden_Norway",
            bus0="Gas_Sweden",
            bus1="Gas_Norway",
            p_nom_extendable=True,
            p_min_pu=-1, #to make link is reversible
            capital_cost=capital_cost_unit * lengths["SE_NO"],  # in €/MW
)
network.add("Link",
            "Gas_Sweden_Finland",
            bus0="Gas_Sweden",
            bus1="Gas_Finland",
            p_nom_extendable=True,
            p_min_pu=-1, #to make link is reversible
            capital_cost=capital_cost_unit * lengths["SE_FI"],  # in €/MW
)        
network.add("Link",
            "Gas_Sweden_Denmark",
            bus0="Gas_Sweden",
            bus1="Gas_Denmark",
            p_nom_extendable=True,
            p_min_pu=-1, #to make link is reversible
            capital_cost=capital_cost_unit * lengths["SE_DK"],  # in €/MW
)    
network.add("Link",
            "Gas_Norway_Denmark",
            bus0="Gas_Norway",
            bus1="Gas_Denmark",
            p_min_pu=-1, #to make link is reversible
            p_nom_extendable=True,
            capital_cost=capital_cost_unit * lengths["NO_DK"],  # in €/MW
)    

#====run model=====
network.optimize(solver_name='gurobi')

#===Save the network to a NetCDF file===
network.export_to_netcdf(FILE_DIR /"sweden_gas_model.nc")

#%%====print results====
print(f'Total Annualized System Cost: {network.objective/1000000:.2f} m€')
df_gen_capacity = network.generators.p_nom_opt.to_frame(name="capacity (MW_el or MW_th)")
print(df_gen_capacity.round(2))
batt_power_mw = network.storage_units.at["SE storage", "p_nom_opt"]
batt_max_hours = network.storage_units.at["SE storage", "max_hours"]
total_energy_capacity = batt_power_mw * batt_max_hours
print(f'Total storage energy capacity: {total_energy_capacity:.2f} MWh')

# %% The capacity of OCGT in each country
# MW_th
gas_capacity_SWE = network.links.at["OCGT_Sweden", "p_nom_opt"]
gas_capacity_DKK= network.links.at["OCGT_Denmark", "p_nom_opt"]
gas_capacity_FIN= network.links.at["OCGT_Finland", "p_nom_opt"]

ocgt_efficiency = network.links.at["OCGT_Sweden", "efficiency"]

elec_output_capacity_SWE = gas_capacity_SWE * ocgt_efficiency
elec_output_capacity_DKK = gas_capacity_DKK * ocgt_efficiency
elec_output_capacity_FIN = gas_capacity_FIN * ocgt_efficiency

print(f"Sweden OCGT gas capacity: {gas_capacity_SWE:.2f} MW_th")
print(f"Denmark OCGT gas capacity: {gas_capacity_DKK:.2f} MW_th")
print(f"Finland OCGT gas capacity: {gas_capacity_FIN:.2f} MW_th")
print(f"Sweden OCGT electric output capacity: {elec_output_capacity_SWE:.2f} MW_el")
print(f"Denmark OCGT electric output capacity: {elec_output_capacity_DKK:.2f} MW_el")
print(f"Finland OCGT electric output capacity: {elec_output_capacity_FIN:.2f} MW_el")

#%% calculate the capacity factor of nuclear in Sweden
nuclear_total_gen = network.generators_t.p["nuclear"].sum()
nuclear_capacity = network.generators.at["nuclear", "p_nom_opt"]

cf_nuclear = nuclear_total_gen / (nuclear_capacity * 8760)

print(f"CF of nuclear in sweden: {cf_nuclear:.2%}")

#%% get the gas pipline capacity
target_links = ["Gas_Sweden_Norway", "Gas_Sweden_Finland", "Gas_Sweden_Denmark", "Gas_Norway_Denmark"]
pipeline_results = {
    "Pipeline Name": target_links,
    "Optimal Capacity (MW_th)": [network.links.at[link, "p_nom_opt"] for link in target_links],
    "Unit Capital Cost (€/MW)": [
        network.links.at[link, "capital_cost"] 
        for link in target_links
    ]
}

df_pipelines = pd.DataFrame(pipeline_results)

print("\n=== Optimized Gas Pipeline Capacities ===")
print(df_pipelines)

#%% plot total gas flow for a year
#the total gas flow
flow_data = {
    "Sweden - Norway": network.links_t.p0["Gas_Sweden_Norway"].sum(),
    "Sweden - Finland": network.links_t.p0["Gas_Sweden_Finland"].sum(),
    "Sweden - Denmark": network.links_t.p0["Gas_Sweden_Denmark"].sum(),
    "Norway - Denmark": network.links_t.p0["Gas_Norway_Denmark"].sum()
}

df_flow_table = pd.Series(flow_data, name="Total flow (MWh)")

plt.figure(figsize=(10, 6))

# positive flow (export) in blue, negative flow (import) in red
colors = ['#1f77b4' if val >= 0 else '#d62728' for val in df_flow_table.values]

df_flow_table.plot(
    kind='bar', 
    ax=plt.gca(),           
    color=colors
)

plt.title("Total Gas Flow per Link in 2015", fontsize=14, fontweight='bold')
plt.ylabel("Total Energy Transported (MWh_th)", fontsize=12)
plt.xlabel("Links", fontsize=12)
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(FILE_DIR / "graph/gas_flows.png", dpi=300, bbox_inches='tight')
plt.show()

#%% plot the generation profile for the first four days
time_index = network.loads_t.p.index[0:96]

#source side
onshore=network.generators_t.p['onshorewind'][0:96]
solar=network.generators_t.p['solar'][0:96]
gas=network.links_t.p0['OCGT_Sweden'][0:96] * 0.39
nuclear=network.generators_t.p['nuclear'][0:96]
norway = network.lines_t.p1['Sweden - Norway'][0:96].clip(lower=0) #export from Swedan turn into zero
finland = network.lines_t.p1['Sweden - Finland'][0:96].clip(lower=0)
denmark = network.lines_t.p1['Sweden - Denmark'][0:96].clip(lower=0)
import_electricity = norway + finland + denmark
storage_discharge=network.storage_units_t.p['SE storage'][0:96].clip(lower=0) #only consider discharge from storage

source=[onshore, solar, gas, nuclear, import_electricity, storage_discharge]
labels = ['Onshore Wind', 'Solar', 'Gas (OCGT)', 'Nuclear', 'Import Electricity', 'Storage_Discharge']
colors = [
    "#4E79A7",  # blue
    "#F28E2B",  # orange
    "#59A14F",  # green
    "#76B7B2",   # teal
    "#B07AA1",  # purple
    "#EDC948",   # mustard yellow
   # "#E15759",  # red
   
]
#demand side
storage_charge = -network.storage_units_t.p['SE storage'][0:96].clip(upper=0) #consider charge from storage, turn into positive value
norway_ex = network.lines_t.p0['Sweden - Norway'][0:96].clip(lower=0) 
finland_ex = network.lines_t.p0['Sweden - Finland'][0:96].clip(lower=0)
denmark_ex = network.lines_t.p0['Sweden - Denmark'][0:96].clip(lower=0)
export_electricity=norway_ex + finland_ex + denmark_ex
curve_demand = network.loads_t.p['load'][0:96]
curve_demand_plus_export = curve_demand + export_electricity
curve_total_sink = curve_demand_plus_export + storage_charge

plt.figure(figsize=(12, 6))
plt.stackplot(time_index, source, labels=labels, colors=colors)
plt.plot(time_index, curve_demand, 
         color='black', linewidth=2.5, linestyle='--', zorder=5, 
         label='Demand (Sweden)')

plt.plot(time_index, curve_total_sink, 
         color='#8B0000', linewidth=2.5, linestyle='--', zorder=5, 
         label='Demand + Export + Charge')


plt.xlabel('Time (Day/hours)')
plt.ylabel('Power (MWh)')
plt.title('Generation and Import Profiles (First 4 days of January)')
plt.legend(loc='upper left')
plt.tight_layout()
plt.savefig(FILE_DIR /'graph/sweden_time_series_gas_network.png', dpi=300, bbox_inches='tight')
plt.show()

# %%
