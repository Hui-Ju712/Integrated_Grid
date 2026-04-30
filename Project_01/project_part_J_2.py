#%% 
from pyexpat import model
import pandas as pd
import pypsa
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
'''the nc. model may be changed'''
FILE_DIR = Path(__file__).parent
model_dir = FILE_DIR / 'nordics_gas_transport_model.nc' 
network = pypsa.Network(model_dir)

network.optimize(solver_name='gurobi')
#%%
def annuity(n, r):
    """ Calculate the annuity factor for an asset with lifetime n years and
    discount rate  r """

    if r > 0:
        return r/(1. - 1./(1.+r)**n)
    else:
        return 1/n
    
#nuclear origial cost
# add nuclear generator
life_nuclear = 60                    # years
cap_nuclear = 6000000               # €/MW_el
fom_nuclear = 0.025                 # 2.5%/year
capital_cost_nuclear = annuity(
    life_nuclear, 0.07) * cap_nuclear * (1 + fom_nuclear)

marginal_cost_nuclear = 10.0        # €/MWh_el (example stylized value)

cost_multipliers = [1.0, 0.8, 0.6, 0.4] 
scenario_names = ["100% (Base)", "80% Cost", "60% Cost", "40% Cost"]
sensitivity_results = {}
generation_profile_results = {}

'''problem for the base case!!!'''

for mult, name in zip(cost_multipliers, scenario_names):
    # a. new capital_cost
    new_capital_cost = (annuity(life_nuclear, 0.07) + fom_nuclear) * (cap_nuclear * mult)
    network.generators.loc["nuclear", "capital_cost"] = new_capital_cost
    
    # b. optimize the network with the new cost
    network.optimize(solver_name='gurobi')
    
    # c. extract generators capacity in swedan (MW)
    sweden_capacities = {
        "Nuclear": network.generators.at["nuclear", "p_nom_opt"],
        "Onshore Wind": network.generators.at["onshorewind", "p_nom_opt"],
        "offshore Wind": network.generators.at["offshorewind", "p_nom_opt"],
        "Solar": network.generators.at["solar", "p_nom_opt"],
        "OCGT (Gas)": network.links.at["OCGT_Sweden", "p_nom_opt"] * 0.39 
    }

    sweden_generation_profile= {"Nuclear": network.generators_t.p['nuclear'][0:96], 
                                "Onshore Wind": network.generators_t.p['onshorewind'][0:96], 
                                "offshore Wind": network.generators_t.p['offshorewind'][0:96], 
                                "Solar": network.generators_t.p['solar'][0:96], 
                                "OCGT (Gas)": network.links_t.p0['OCGT_Sweden'][0:96] * 0.39}

    sensitivity_results[name] = sweden_capacities
    generation_profile_results[name] = sweden_generation_profile

df_results = pd.DataFrame(sensitivity_results).T
df_generation_profiles = pd.concat({k: pd.DataFrame(v) for k, v in generation_profile_results.items()}, axis=0)

#%% Print the results
print("\n Nuclear Sensitivity Analysis (MW):")
print(df_results)
print(df_generation_profiles)

#%% plot the sensitivity analysis
colors = ["#B07AA1", "#4E79A7", "#E15759", "#F28E2B", "#59A14F"]

ax = df_results.plot(kind="bar", stacked=True, figsize=(10, 6), color=colors, alpha=0.85)

plt.title("Impact of Nuclear Cost Reduction on Sweden's Capacity Mix", fontsize=14, fontweight="bold")
plt.xlabel("Nuclear Capital Cost Scenarios", fontsize=12)
plt.ylabel("Optimized Installed Capacity (MW_el)", fontsize=12)
plt.xticks(rotation=0)
plt.legend(title="Technologies", loc='center left', bbox_to_anchor=(1.0, 0.5))
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()

plt.savefig(FILE_DIR / "graph/nuclear_sensitivity.png", dpi=300, bbox_inches='tight')
plt.show()
# %% Plot first 4 days of generation profiles for each scenario
demand_96h = network.loads_t.p['load'][0:96]
# 2. 設定畫布：2 列 x 2 欄的子圖矩陣，並讓它們共享 X 軸和 Y 軸刻度以便對比
fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(16, 10), sharex=True, sharey=True)
axes = axes.flatten() # 把 2x2 矩陣攤平成一維陣列，方便用 for 迴圈讀取

# 確保顏色與你的長條圖對應
colors = ["#B07AA1", "#4E79A7", "#E15759", "#F28E2B", "#59A14F"]

# 3. 跑迴圈畫出 4 個情境
for i, (name, profile_dict) in enumerate(generation_profile_results.items()):
    
    # 將字典轉換為 DataFrame
    df_gen = pd.DataFrame(profile_dict)
    
    # a. 畫出堆疊面積圖 (Pandas 內建神技)
    df_gen.plot.area(ax=axes[i], color=colors, alpha=0.85, linewidth=0)
    
    # b. 疊加上黑色的 Demand 虛線
    axes[i].plot(df_gen.index, demand_96h, color='black', linestyle='--', linewidth=2, label='Demand')
    
    # c. 設定每張小圖的標題與標籤
    axes[i].set_title(f"Scenario: {name}", fontsize=13, fontweight='bold')
    axes[i].set_ylabel("Power Generation (MW)")
    
    # d. 整理圖例：我們只需要在右上角那張圖顯示一次圖例就好，免得畫面太亂
    if i == 1:
        # 把圖例放在圖的外面
        axes[i].legend(loc='center left', bbox_to_anchor=(1.05, 0.5))
    else:
        axes[i].get_legend().remove() # 移除其他三張圖的圖例

plt.suptitle("96-Hour Dispatch Profiles: Impact of Nuclear Cost Reduction", fontsize=18, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(FILE_DIR / "graph/nuclear_dispatch_profiles_2x2.png", dpi=300, bbox_inches='tight')
plt.show()


# %%
