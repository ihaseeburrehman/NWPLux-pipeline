# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# Provided data
data = {
    "Station Name": ["Breidfeld", "Echternach", "Ettelbruck", "Obercorn", "Remerchen", "Findel", "Roodt"],
    "Observed 24 hr accumulation 2021 July 14": [70.1, 85.2, 75.9, 68.2, 63.4, 79.4, 64.6],
    "GFS without DA 0600hr": [41, 67, 47, 66, 71, 66, 49],
    "GFS with DA (GFS + ZTD+ Radiosonde)0600hr": [74, 58, 73, 56, 72, 67, 49],
    "ds083.2 without DA 0600hr": [39, 87, 48, 67, 77, 76, 40],
    "ds083.2 With DA (ds083.2 + ZTD + Radiosonde) 0600hr": [88, 57, 95, 95, 65, 78, 75],
    "GFS without DA 0000hr": [85, 47, 78, 76, 44, 55, 69],
    "GFS with DA (GFS + ZTD) 0000hr": [34, 16, 31, 23, 9, 15, 40],
    "ds083.2 without DA 0000hr": [74, 51, 84, 83, 43, 59, 61],
    "ds083.2 With DA (ds083.2 + ZTD + Radiosonde) 0000hr": [33, 126, 51, 79, 157, 127, 39],
    "NASA-GPM": [50.47, 69.91, 75.12, 74.09, 56.26, 67.18, 63.77],
}

# Convert the data into a DataFrame
df = pd.DataFrame(data)

# Define a traditional scientific color palette
colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:cyan']

# Plotting the grouped bar chart with adjusted bar width, spacing, and styles
fig, ax = plt.subplots(figsize=(14, 7))

# Set positions for the groups
bar_width = 0.08  # Adjusted bar width for spacing
num_bars = len(df.columns) - 1  # Number of bars per station
group_width = bar_width * num_bars  # Total width of a group
space_width = 0.1  # Additional space between groups

# Calculate positions for each group
index = np.linspace(0, (len(df) - 1) * (group_width + space_width), len(df))

# Plotting each group of bars with the defined colors and styles
for i, column in enumerate(df.columns[1:], start=1):
    bar_positions = index + bar_width * (i - 1) - (group_width / 2)
    if "Observed" in column:
        ax.bar(bar_positions, df[column], width=bar_width, label=column, color=colors[i - 1], hatch='//', edgecolor='black', alpha=0.7)
    elif "NASA" in column:
        ax.bar(bar_positions, df[column], width=bar_width, label=column, hatch='-', color=colors[i - 1], alpha=0.7)
    elif "0600hr" in column:
        ax.bar(bar_positions, df[column], width=bar_width, label=column, color=colors[i - 1], alpha=0.7)
    elif "0000hr" in column:
        ax.bar(bar_positions, df[column], width=bar_width, label=column, color=colors[i - 1], hatch='xx', edgecolor='black', alpha=0.7)

# Create legends for each column
legends = []
for i, column in enumerate(df.columns[1:], start=1):
    if "Observed" in column:
        legends.append(ax.bar(0, 0, color=colors[i - 1], label=column, hatch='//', edgecolor='black', alpha=0.7))
    elif "0600hr" in column:
        legends.append(ax.bar(0, 0, color=colors[i - 1], label=column, alpha=0.7))
    elif "0000hr" in column:
        legends.append(ax.bar(0, 0, color=colors[i - 1], label=column, hatch='xx', edgecolor='black', alpha=0.7))
    elif "NASA-GPM" in column:
        legends.append(ax.bar(0, 0, color=colors[i - 1], label=column, hatch='-', edgecolor='black', alpha=0.7))

# Adding labels and title
ax.set_xlabel('Station Name', fontweight='bold')
ax.set_ylabel('Precipitation (mm)', fontweight='bold')
ax.set_title('Comparison of Observed and Predicted 24 hr Precipitation', fontsize=14, fontweight='bold')
ax.set_xticks(index)
ax.set_xticklabels(df["Station Name"])

# Create a legend with all the legends created earlier
ax.legend(handles=legends, title='Methods', bbox_to_anchor=(1.05, 1), loc='upper left')

# Rotate the x-axis labels for better readability
plt.setp(ax.get_xticklabels(), rotation=45)

# Specify the path to the folder where you want to save the PNG file
output_folder = '/Users/haseeb.rehman/Desktop/For_Animation'

# Save the plot as PNG with the same name as the NetCDF file
output_file = os.path.join(output_folder, 'precipitation_comparison.png')
plt.savefig(output_file, dpi=400, bbox_inches='tight')  # Adjusted bbox_inches

# Adjust layout and show the plot
plt.tight_layout()
plt.show()
