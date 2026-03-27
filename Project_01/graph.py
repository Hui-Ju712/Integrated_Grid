import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

labels = [
    "Hydropower",
    "Nuclear",
    "Wind",
    "Biofuels",
    "Waste",
    "Coal",
    "Others"
]

sizes = [46.5, 34.8, 10.1, 5.6, 1.8, 0.8, 0.6]
colors = ['blue', 'green', 'orange', 'purple', 'brown']


def my_autopct(pct):
    # Only show the text if the percentage is greater than 0%
    return f'{pct:.1f}%' if pct > 1 else ''


patches, texts, autotexts = plt.pie(
    sizes,
    colors=colors,
    autopct=my_autopct,
    # Makes text white and bold
    textprops={'color': 'white', 'weight': 'bold'},
    wedgeprops={'linewidth': 0}
)

plt.axis('equal')
plt.title('Electricity mix real', y=1.07)
plt.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.show()


# Create dataframe (you can skip this if df_sensitivity already exists)
data = {
    "year": [2001, 2002, 2003, 2005, 2006, 2007, 2009, 2010, 2011, 2013, 2014, 2015, 2017],
    "onshorewind": [30481.19, 34043.86, 30590.02, 34462.18, 30479.39, 36301.02, 27235.44, 31272.73, 32939.90, 26725.68, 34174.13, 37648.23, 37332.71],
    "solar": [15065.14, 16046.46, 17242.94, 14805.20, 19845.30, 5650.63, 17635.30, 16730.35, 15765.95, 20649.61, 14908.48, 6334.37, 6632.64],
    "OCGT": [21661.05, 21936.77, 21403.22, 21280.27, 22318.18, 21937.96, 22049.94, 21103.64, 22454.90, 21958.26, 21388.07, 22373.15, 20946.71]
}

df = pd.DataFrame(data).set_index("year")

# X positions
x = np.arange(len(df.index))
width = 0.25

# Plot
plt.figure(figsize=(12, 6))

plt.bar(x - width, df["onshorewind"], width, label="Onshore Wind")
plt.bar(x, df["solar"], width, label="Solar")
plt.bar(x + width, df["OCGT"], width, label="OCGT")

# Labels and formatting
plt.xticks(x, df.index, rotation=45)
plt.ylabel("Capacity (MW)")
plt.xlabel("Year")
plt.title("Optimal Capacity by Weather Year")
plt.legend()
plt.tight_layout()

plt.show()


# Create dataframe
data = {
    "Technology": ["Onshore wind", "Solar", "OCGT"],
    "mean": [32591.27, 14408.65, 21754.78],
    "relative_variability": [10.77, 34.71, 2.28]
}

df = pd.DataFrame(data)

# Positions
x = np.arange(len(df))
width = 0.38

# Figure
fig, ax1 = plt.subplots(figsize=(9, 5.5))
ax2 = ax1.twinx()

# Bars
bars1 = ax1.bar(
    x - width/2,
    df["mean"],
    width=width,
    color=["steelblue"],
    edgecolor="black",
    linewidth=0.8,
    label="Mean capacity"
)

bars2 = ax2.bar(
    x + width/2,
    df["relative_variability"],
    width=width,
    color=["darkorange"],
    edgecolor="black",
    linewidth=0.8,
    label="Relative variability"
)

# Labels
ax1.set_ylabel("Mean capacity (MW)", fontsize=11)
ax2.set_ylabel("Relative variability (%)", fontsize=11)
ax1.set_xticks(x)
ax1.set_xticklabels(df["Technology"], fontsize=10)

# Title
ax1.set_title(
    "Average Capacity and Relative Variability by Technology", fontsize=13, pad=12)

# Grid
ax1.grid(axis="y", linestyle="--", alpha=0.4)
ax1.set_axisbelow(True)

# Remove top spines for cleaner look
ax1.spines["top"].set_visible(False)
ax2.spines["top"].set_visible(False)

# Optional: soften right spine a bit
ax2.spines["right"].set_linewidth(0.8)
ax1.spines["left"].set_linewidth(0.8)
ax1.spines["bottom"].set_linewidth(0.8)

# Value labels
for bar in bars1:
    h = bar.get_height()
    ax1.text(
        bar.get_x() + bar.get_width()/2,
        h + max(df["mean"]) * 0.015,
        f"{h:,.0f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

for bar in bars2:
    h = bar.get_height()
    ax2.text(
        bar.get_x() + bar.get_width()/2,
        h + max(df["relative_variability"]) * 0.03,
        f"{h:.1f}%",
        ha="center",
        va="bottom",
        fontsize=9
    )

# Combined legend
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper right", fontsize=10)

plt.tight_layout()
plt.show()
