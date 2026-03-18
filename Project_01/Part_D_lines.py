from pyexpat import model

import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path
#impoert network 

FILE_DIR = Path(__file__).parent
model_dir = FILE_DIR / 'sweden_base_model.nc'
network = pypsa.Network(model_dir)

network.add("Bus", 'Norway', v_nom=400)
network.add("Bus", 'Finland', v_nom=400)
network.add("Bus", 'Denmark', v_nom=400)

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
             v_nom=400, # voltage level in kV
             x=0.1*lengths["SE_NO"], # reactance in pu
             length=lengths["SE_NO"], # length (in km) between Sweden and Norway
             capital_cost=400*lengths["SE_NO"])

network.add("Line",
             'Sweden - Finland',
             bus0="electricity bus",
             bus1="Finland",
             s_nom_extendable=False, 
             s_nom=capacity["SE_FI"], # in MW
             v_nom=400, # voltage level in kV
             x=0.1*lengths["SE_FI"], # reactance in pu
             length=lengths["SE_FI"], # length (in km) between Sweden and Finland
             capital_cost=400*lengths["SE_FI"]) 

network.add("Line",
             'Sweden - Denmark',
             bus0="electricity bus",
             bus1="Denmark",
             s_nom_extendable=False, 
             s_nom=capacity["SE_DK"], # in MW
             v_nom=400, # voltage level in kV
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


'''
Add Generation for the neighboring countries, refernece from ENTSOE STATISTICAL FACTSHEET 2015
the MC of countreis are electricity price, but probably is not reasonable?
https://www.nordpoolgroup.com/en/message-center-container/newsroom/exchange-message-list/2016/q1/no.-42016---nord-pool-spot-2015-traded-volumes---new-all-time-high-in-the-nordicbaltic-market/

'''

network.add("Generator", "Norway_elec",
            bus="Norway",
            p_nom=33692,
            p_nom_extendable=False,
            marginal_cost=21)

network.add("Generator", "Finland_elec",
            bus="Finland",
            p_nom=17681,
            p_nom_extendable=False,
            marginal_cost=21)

network.add("Generator", "Denmark_elec",
            bus="Denmark",
            p_nom=13922,
            p_nom_extendable=False,
            marginal_cost=21)

#====run model=====
network.optimize(solver_name='gurobi')

#====print results====
print(f'Total Annualized System Cost: {network.objective/1000000:.2f} m€')
print(f'LCOE: {network.objective/network.loads_t.p.sum()} €/MWh') 
print(f'Optimal capacity for generators: {network.generators.p_nom_opt} MW')

#%%
#===Plotting=====
time_index = network.loads_t.p.index[0:96]

onshore=network.generators_t.p['onshorewind'][0:96]
#offshore=network.generators_t.p['offshorewind'][0:96]
solar=network.generators_t.p['solar'][0:96]
#nuclear=network.generators_t.p['nuclear'][0:96]
gas=network.generators_t.p['OCGT'][0:96]
norway=network.lines_t.p1['Sweden - Norway'][0:96]
finland=network.lines_t.p1['Sweden - Finland'][0:96]
denmark=network.lines_t.p1['Sweden - Denmark'][0:96]

source=[onshore, solar, gas, norway, finland, denmark]
labels = ['Onshore Wind', 'Solar', 'Gas (OCGT)', 'Import Finland', 'Import Norway', 'Import Denmark']
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
plt.plot(time_index, network.loads_t.p['load'][0:96], 
         color='black', linewidth=2.5, linestyle='--', label='Demand')
plt.xlabel('Time (Day/hours)')
plt.ylabel('Power (MWh)')
plt.title('Generation and Import Profiles (First 4 days of January)')
plt.legend(loc='upper left')
plt.tight_layout()
plt.show()

#===Plot energy mix pie chart===
labels = ['onshore wind',
          'solar',  
          'gas (OCGT)',
          'Norway import',
          'Finland import',
          'Denmark import']

sizes = [network.generators_t.p['onshorewind'].sum(),
         #network.generators_t.p['offshorewind'].sum(),
         network.generators_t.p['solar'].sum(),
         #network.generators_t.p['nuclear'].sum(),
         network.generators_t.p['OCGT'].sum(),
         network.generators_t.p['Norway_elec'].sum(),
         network.generators_t.p['Finland_elec'].sum(),
         network.generators_t.p['Denmark_elec'].sum()]

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
plt.show()
# %%
