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
network.add("Link",
            "Gas_Sweden_Norway",
            bus0="Gas_Sweden",
            bus1="Gas_Norway",
            p_nom_extendable=True,
            p_min_pu=-1, #to make link is reversible
            capital_cost=15000,  # in €/MW
)
network.add("Link",
            "Gas_Sweden_Finland",
            bus0="Gas_Sweden",
            bus1="Gas_Finland",
            p_nom_extendable=True,
            p_min_pu=-1, #to make link is reversible
            capital_cost=15000,  # in €/MW
)        
network.add("Link",
            "Gas_Sweden_Denmark",
            bus0="Gas_Sweden",
            bus1="Gas_Denmark",
            p_nom_extendable=True,
            p_min_pu=-1, #to make link is reversible
            capital_cost=15000,  # in €/MW
)    
network.add("Link",
            "Gas_Norway_Denmark",
            bus0="Gas_Norway",
            bus1="Gas_Denmark",
            p_min_pu=-1, #to make link is reversible
            p_nom_extendable=True,
            capital_cost=15000,  # in €/MW
)    

#====run model=====
network.optimize(solver_name='gurobi')

#===Save the network to a NetCDF file===
network.export_to_netcdf("sweden_gas_model.nc")

#%%====print results====
print(f'Total Annualized System Cost: {network.objective/1000000:.2f} m€')
df_gen_capacity = network.generators.p_nom_opt.to_frame(name="capacity (MW_el or MW_th)")
print(df_gen_capacity.round(2))

#electricity line dispatch (positive means flow from bus0 to bus1, negative means flow from bus1 to bus0)
df_line_flows = network.lines_t.p0
print("Sweden - Norway line flows (first 5 hours):")
print(df_line_flows["Sweden - Norway"].head())

#the total gas flow
df_flow = network.links_t.p0.sum()
df_flow_table = df_flow.to_frame(name="Total flow (MWh)")
print(df_flow_table)
# %%===plot the gas flow between countries===
plt.figure(figsize=(10, 6))

# positive flow (export) in blue, negative flow (import) in red
colors = ['#1f77b4' if val >= 0 else '#d62728' for val in df_flow_table["Total flow (MWh)"]]

df_flow_table.plot(
    kind='bar', 
    y="Total flow (MWh)",   
    ax=plt.gca(),           
    color=colors,
    legend=False          
)

plt.title("Total Gas Flow per Link (1 Year)", fontsize=14, fontweight='bold')
plt.ylabel("Total Energy Transported (MWh_th)", fontsize=12)
plt.xlabel("Links", fontsize=12)
plt.xticks(rotation=45, ha='right')
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.show()
# %%
