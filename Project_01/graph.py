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

sizes = [46.5, 34.8, 10.1, 5.6,1.8, 0.8, 0.6]
colors = ['blue', 'green', 'orange', 'purple', 'brown']

def my_autopct(pct):
    # Only show the text if the percentage is greater than 0%
    return f'{pct:.1f}%' if pct > 1 else ''
        
patches, texts, autotexts = plt.pie(
    sizes,
    colors=colors,
    autopct=my_autopct,        
    textprops={'color': 'white', 'weight': 'bold'}, # Makes text white and bold
    wedgeprops={'linewidth': 0}
)

plt.axis('equal')
plt.title('Electricity mix real', y=1.07)
plt.legend(patches, labels, loc="center left", bbox_to_anchor=(1, 0.5))
plt.show()