#%%
from pyexpat import model
import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path
#impoert network 
FILE_DIR = Path(__file__).parent
model_dir = FILE_DIR / 'sweden_base_model.nc'
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

#====print results====
print(f'Total Annualized System Cost: {network.objective/1000000:.2f} m€')
print('========================================')
print(f'Optimal capacity for generators: {network.generators.p_nom_opt} MW')

#%%===Plotting=====
time_index = network.loads_t.p.index[0:96]

onshore=network.generators_t.p['onshorewind'][0:96]
#offshore=network.generators_t.p['offshorewind'][0:96]
solar=network.generators_t.p['solar'][0:96]
#nuclear=network.generators_t.p['nuclear'][0:96]
gas=network.generators_t.p['OCGT'][0:96]
norway = network.lines_t.p1['Sweden - Norway'][0:96].clip(lower=0) #export from Swedan turn into zero
finland = network.lines_t.p1['Sweden - Finland'][0:96].clip(lower=0)
denmark = network.lines_t.p1['Sweden - Denmark'][0:96].clip(lower=0)

# export_no = network.lines_t.p1['Sweden - Norway'][0:96].clip(upper=0)
# export_fi = network.lines_t.p1['Sweden - Finland'][0:96].clip(upper=0)
# export_dk = network.lines_t.p1['Sweden - Denmark'][0:96].clip(upper=0)
# export_source = [export_no, export_fi, export_dk]
# export_labels = ['Export to Norway', 'Export to Finland', 'Export to Denmark']
# export_colors = ["#A8D0CB", "#D4B9CD", "#F0A3A4"] 

source=[onshore, solar, gas, norway, finland, denmark]
labels = ['Onshore Wind', 'Solar', 'Gas (OCGT)', 'Import Norway', 'Import Finland', 'Import Denmark']
colors = [
    "#4E79A7",  # blue
    "#F28E2B",  # orange
    "#59A14F",  # green
    "#E15759",  # red
    "#B07AA1",  # purple
    "#76B7B2"   # teal
]

plt.figure(figsize=(12, 6))
plt.stackplot(time_index, source, labels=labels, colors=colors)
#plt.stackplot(time_index, export_source, labels=export_labels, colors=export_colors)
plt.plot(time_index, network.loads_t.p['load'][0:96], 
         color='black', linewidth=2.5, linestyle='--', label='Demand (Sweden)')
plt.xlabel('Time (Day/hours)')
plt.ylabel('Power (MWh)')
plt.title('Generation and Import Profiles (First 4 days of January)')
plt.legend(loc='upper left')
plt.tight_layout()
plt.savefig(FILE_DIR /'graph/sweden_generation_stackplot.png', dpi=300, bbox_inches='tight')
plt.show()

#===Plot energy mix pie chart===
import_no_total = network.lines_t.p1['Sweden - Norway'].clip(lower=0).sum()
import_fi_total = network.lines_t.p1['Sweden - Finland'].clip(lower=0).sum()
import_dk_total = network.lines_t.p1['Sweden - Denmark'].clip(lower=0).sum()

labels_pie_sweden = [
    'Domestic Onshore Wind',
    'Domestic Solar',  
    'Domestic Gas (OCGT)',
    'Import from Norway',
    'Import from Finland',
    'Import from Denmark'
]
sizes = [
    network.generators_t.p['onshorewind'].sum(),
    network.generators_t.p['solar'].sum(),
    network.generators_t.p['OCGT'].sum(),
    import_no_total,
    import_fi_total,
    import_dk_total
]

colors = [
    "#4E79A7",  # blue
    "#F28E2B",  # orange
    "#59A14F",  # green
    "#E15759",  # red
    "#B07AA1",  # purple
    "#76B7B2"   # teal
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
plt.title('Electricity mix', y=1.07)
plt.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.savefig(FILE_DIR / "graph/sweden_energymix_import.png", dpi=300, bbox_inches='tight')
plt.show()
# %%
