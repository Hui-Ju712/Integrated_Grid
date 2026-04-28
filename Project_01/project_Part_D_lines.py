#%%
from pyexpat import model
import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
#impoert network, swedan case consider storage unit 
FILE_DIR = Path(__file__).parent
model_dir = FILE_DIR / 'sweden_storage_model.nc' 
Load_dir= FILE_DIR / 'data/electricity_demand.csv'
CF_onshore_dir = FILE_DIR / 'data/CF_onshore_wind_1979-2017.csv'
CF_offshore_dir = FILE_DIR / 'data/CF_offshore_wind_1979-2017.csv'
network = pypsa.Network(model_dir)

def annuity(n,r):
    """ Calculate the annuity factor for an asset with lifetime n years and
    discount rate  r """

    if r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n

#====add lines/nodes to neighboring countries====
network.add("Bus", 'Norway', v_nom=400)
network.add("Bus", 'Finland', v_nom=400)
network.add("Bus", 'Denmark', v_nom=400)

#===demande for neighbor ===
df_elec = pd.read_csv(Load_dir, sep=';', index_col=0) # in MWh
df_elec.index = pd.to_datetime(df_elec.index) #change index to datatime

denmark="DNK"
norway="NOR"
finland="FIN"
network.add("Load",
            "load_denmark",
            bus="Denmark",
            p_set=df_elec[denmark].values)
network.add("Load",
            "load_norway",
            bus="Norway",
            p_set=df_elec[norway].values)
network.add("Load",
            "load_finland",
            bus="Finland",
            p_set=df_elec[finland].values)
network.loads_t.p_set 

#===Transmission line data====
lengths = {
    "SE_NO": 530, #km
    "SE_FI": 450,
    "SE_DK": 160,
    "NO_DK": 480
}

'''
Data source: ENTSO-E Statistical Factsheet 2015
'''
capacity = {
    "SE_NO": 3685, #MW
    "SE_FI": 2300, #MW
    "SE_DK": 2415, #MW
    "NO_DK": 1632  #MW
}

network.add("Line",
             'Sweden - Norway',
             bus0="electricity bus",
             bus1="Norway",
             s_nom_extendable=False, 
             s_nom=capacity["SE_NO"], # in MW
             x=0.1*lengths["SE_NO"], # reactance in pu
             length=lengths["SE_NO"], # length (in km) between Sweden and Norway
             capital_cost=400*lengths["SE_NO"])

network.add("Line",
             'Sweden - Finland',
             bus0="electricity bus",
             bus1="Finland",
             s_nom_extendable=False, 
             s_nom=capacity["SE_FI"], # in MW
             x=0.1*lengths["SE_FI"], # reactance in pu
             length=lengths["SE_FI"], # length (in km) between Sweden and Finland
             capital_cost=400*lengths["SE_FI"]) 

network.add("Line",
             'Sweden - Denmark',
             bus0="electricity bus",
             bus1="Denmark",
             s_nom_extendable=False, 
             s_nom=capacity["SE_DK"], # in MW
             x=0.1*lengths["SE_DK"], # reactance in pu
             length=lengths["SE_DK"], # length (in km) between Sweden and Denmark
             capital_cost=400*lengths["SE_DK"]) 

network.add("Line",
             'Norway - Denmark',
             bus0="Norway",
             bus1="Denmark",
             s_nom_extendable=False, 
             s_nom=capacity["NO_DK"], # in MW
             v_nom=400, # voltage level in kV
             x=0.1*lengths["NO_DK"], # reactance in pu
             length=lengths["NO_DK"], # length (in km) between Norway and Denmark
             capital_cost=400*lengths["NO_DK"])  

#===add generators in neighboring countries====
'''
Norway: hydro
Finland: nuclear, onshore wind
Denmark: onshore wind, offshore wind
'''

#Finland (nuclear, onshore wind)
df_onshorewind = pd.read_csv(CF_onshore_dir, sep=';', index_col=0)
df_onshorewind.index = pd.to_datetime(df_onshorewind.index)
capital_cost_onshorewind = annuity(30,0.07)*910000*(1+0.033) # in €/MW
CF_wind_fin = df_onshorewind[finland][[hour.strftime("%Y-%m-%dT%H:%M:%SZ") for hour in network.snapshots]]
network.add("Generator",
            "onshorewind_Finland",
            bus="Finland",
            p_nom_extendable=True,
            carrier="onshorewind",
            capital_cost = capital_cost_onshorewind,
            marginal_cost = 0,
            p_max_pu = CF_wind_fin.values)

life_nuclear = 60                    # years
cap_nuclear = 6000000               # €/MW_el
fom_nuclear = 0.025                 # 2.5%/year
capital_cost_nuclear = annuity(life_nuclear, 0.07) * cap_nuclear * (1 + fom_nuclear)
marginal_cost_nuclear = 10.0        # €/MWh_el (example stylized value)

network.add("Generator",
            "nuclear_Finland",
            bus="Finland",
            p_nom_extendable=True,
            carrier="nuclear",
            capital_cost=capital_cost_nuclear,
            marginal_cost=marginal_cost_nuclear)

#Denmark: onshore wind, offshore wind
df_offshorewind = pd.read_csv(CF_offshore_dir, sep=';', index_col=0)
df_offshorewind.index = pd.to_datetime(df_offshorewind.index)
CF_offwind_DNK = df_offshorewind[denmark][[hour.strftime("%Y-%m-%dT%H:%M:%SZ") for hour in network.snapshots]]
CF_onwind_DNK = df_onshorewind[denmark][[hour.strftime("%Y-%m-%dT%H:%M:%SZ") for hour in network.snapshots]]
capital_cost_offshorewind = annuity(25,0.07)*2506000*(1+0.03) # in €/MW

network.add("Generator",
            "onshorewind_Denmark",
            bus="Denmark",
            p_nom_extendable=True,
            carrier="onshorewind",
            capital_cost = capital_cost_onshorewind,
            marginal_cost = 0,
            p_max_pu = CF_onwind_DNK.values)

network.add("Generator",
            "offshorewind_Denmark",
            bus="Denmark",
            p_nom_extendable=True,
            carrier="offshorewind",
            #p_nom_max=1000, # maximum capacity can be limited due to environmental constraints
            capital_cost = capital_cost_offshorewind,
            marginal_cost = 0,
            p_max_pu = CF_offwind_DNK.values)

#Norway(hydro)
capital_cost_hydro = annuity(80,0.07)*2000000*(1+0.01) # in €/MW
marginal_cost_hydro = 0 # in €/MWh, assume 0 now, since water is free

network.add("Generator",
            "hydro_Norway",
            bus="Norway",
            p_nom_extendable=True,
            carrier="hydro",
            capital_cost=capital_cost_hydro,
            marginal_cost=marginal_cost_hydro)

#====run model=====
network.sanitize()
network.optimize(solver_name='gurobi')

#===Save the network to a NetCDF file===
network.export_to_netcdf("sweden_network_model.nc")

#====print results====
print(f'Total Annualized System Cost: {network.objective/1000000:.2f} m€')
print('========================================')
print(f'Optimal capacity for generators: {network.generators.p_nom_opt} MW')
batt_power_mw = network.storage_units.at["SE storage", "p_nom_opt"]
batt_max_hours = network.storage_units.at["SE storage", "max_hours"]
total_energy_capacity = batt_power_mw * batt_max_hours
print(f'Total storage energy capacity: {total_energy_capacity:.2f} MWh')

#%%===Plotting time series distribution =====
time_index = network.loads_t.p.index[0:96]

#source side
onshore=network.generators_t.p['onshorewind'][0:96]
solar=network.generators_t.p['solar'][0:96]
gas=network.generators_t.p['OCGT'][0:96]
norway = network.lines_t.p1['Sweden - Norway'][0:96].clip(lower=0) #export from Swedan turn into zero
finland = network.lines_t.p1['Sweden - Finland'][0:96].clip(lower=0)
denmark = network.lines_t.p1['Sweden - Denmark'][0:96].clip(lower=0)
import_electricity = norway + finland + denmark
storage_discharge=network.storage_units_t.p['SE storage'][0:96].clip(lower=0) #only consider discharge from storage

source=[onshore, solar, gas, import_electricity, storage_discharge]
labels = ['Onshore Wind', 'Solar', 'Gas (OCGT)', 'Import Electricity', 'Storage_Discharge']
colors = [
    "#4E79A7",  # blue
    "#F28E2B",  # orange
    "#59A14F",  # green
    "#B07AA1",  # purple
    "#EDC948",   # mustard yellow
   # "#E15759",  # red
   # "#76B7B2",   # teal
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
plt.savefig(FILE_DIR /'graph/sweden_generation_stackplot.png', dpi=300, bbox_inches='tight')
plt.show()

#%%===Plot energy mix pie chart===
import_no_total = network.lines_t.p1['Sweden - Norway'].clip(lower=0).sum()
import_fi_total = network.lines_t.p1['Sweden - Finland'].clip(lower=0).sum()
import_dk_total = network.lines_t.p1['Sweden - Denmark'].clip(lower=0).sum()

labels = [
    'Domestic Onshore Wind',
    'Domestic Solar',  
    'Domestic Gas (OCGT)',
    'Import from Norway',
    'Import from Finland',
    'Import from Denmark',
    'Storage Discharge'
]
sizes = [
    network.generators_t.p['onshorewind'].sum(),
    network.generators_t.p['solar'].sum(),
    network.generators_t.p['OCGT'].sum(),
    import_no_total,
    import_fi_total,
    import_dk_total,
    network.storage_units_t.p['SE storage'].clip(lower=0).sum()
]

colors = [
    "#4E79A7",  # blue
    "#F28E2B",  # orange
    "#59A14F",  # green
    "#E15759",  # red
    "#B07AA1",  # purple
    "#76B7B2",   # teal
    "#EDC948"   # mustard yellow
]

def my_autopct(pct):
    # Only show the text if the percentage is greater than 0%
    return f'{pct:.1f}%' if pct > 0 else ''
        
patches, texts, autotexts = plt.pie(
    sizes,
    colors=colors,
    autopct=my_autopct,        
    textprops={'color': 'white', 'weight': 'bold'}, # Makes text white and bold
    wedgeprops={'linewidth': 0}
)

plt.axis('equal')
#plt.title('Electricity mix', y=1.07)
plt.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.savefig(FILE_DIR / "graph/sweden_energymix_import.png", dpi=300, bbox_inches='tight')
plt.show()
# %% ====get actual flow result from pypsa====
t = network.snapshots[10]
injections = []
countries = ['electricity bus', 'Norway', 'Finland', 'Denmark']
for country in countries:
    gen_total = network.generators_t.p.loc[t, network.generators.bus == country].sum()
    load_total = network.loads_t.p.loc[t, network.loads.bus == country].sum()
    if country == 'electricity bus':
        storage_total = network.storage_units_t.p.loc[t, 'SE storage']
    else:
        storage_total = 0 
        
    net_inject = gen_total - load_total + storage_total
    injections.append(net_inject)

#transform into column vector
injections_array = np.array(injections).reshape(-1, 1)

lines_order = ['Sweden - Norway', 'Sweden - Finland', 'Sweden - Denmark', 'Norway - Denmark'] # 確保順序與 K 矩陣的 Row 一致！
pypsa_flows = network.lines_t.p0.loc[t, lines_order].values
print("Power flow on each line from PyPSA:\n", np.round(pypsa_flows, 2))

# %% ===PTDF calculation ===
K=np.array([
    [1,1,1,0],
    [-1,0,0,1],
    [0,-1,0,0],
    [0,0,-1,-1]
]
)
L=K@K.T
print("Laplacian matrix L:\n", L)

x=0.1
Lengths=np.array([530,450,160,480])
X_line=0.1*Lengths
B=np.diag(1/X_line) 
print("Susceptance matrix B:\n", B)

L_weighted = K @ B @ K.T
L_inv = np.linalg.pinv(L_weighted)
print("Inverse of weighted Laplacian:\n", L_inv)
PTDF = B @ K.T @ L_inv
print("=== PTDF ===")
print(np.round(PTDF, 4))

calculated_flows = PTDF @ injections_array
print("Calculated power flow on each line:\n", np.round(calculated_flows.flatten(), 2))
#%%
# 1. 提取每小時實際流量 
actual_flow_Nor = network.lines_t.p0['Sweden - Norway']
actual_flow_Fin= network.lines_t.p0['Sweden - Finland']
actual_flow_DK = network.lines_t.p0['Sweden - Denmark']

plt.figure(figsize=(10, 4))
plt.plot(actual_flow_Nor[:96], label='Actual Power Flow (Sweden - Norway)', color='blue')
plt.plot(actual_flow_Fin[:96], label='Actual Power Flow (Sweden - Finland)', color='green')
plt.plot(actual_flow_DK[:96], label='Actual Power Flow (Sweden - Denmark)', color='orange')
plt.axhline(y=0, color='gray', linestyle='--')
plt.axhline(y=2300, color='green', linestyle='--', label='Capacity (Sweden - Finland)')
plt.axhline(y=-2415, color='orange', linestyle='--', label='Capacity (Sweden - Denmark)')
plt.title(f"Congestion Analysis")
plt.ylabel("Power Flow (MW)")
plt.xlabel("Time (Hours)")
plt.legend()
plt.tight_layout()
plt.savefig(FILE_DIR / "graph/sweden_import_congestion.png", dpi=300, bbox_inches='tight')
plt.show()
# %%
