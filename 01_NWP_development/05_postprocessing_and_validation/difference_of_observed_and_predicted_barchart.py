# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np

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
}

# Convert the data into a DataFrame
df = pd.DataFrame(data)

# Calculate the differences between predicted values and observed values for both "0600hr" and "0000hr" columns
for i, column in enumerate(df.columns[2:], start=2):
    if "0600hr" in column or "0000hr" in column:
        df[column] = df[column] - df["Observed 24 hr accumulation 2021 July 14"]

# Define a traditional scientific color palette
colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive']

# Plotting the grouped bar chart with a smaller figsize
fig, ax = plt.subplots(figsize=(14, 7))

# Set positions for the groups
bar_width = 0.1
index = np.arange(len(df))

# Plotting each group of bars with the defined colors
for i, column in enumerate(df.columns[1:], start=1):
    if "Observed" in column:
        ax.bar(index + bar_width * (i - 1), df[column], width=bar_width, label=column, color=colors[i - 1], hatch='//', edgecolor='black', alpha=0.7)
    elif "0600hr" in column:
        ax.bar(index + bar_width * (i - 1), df[column], width=bar_width, label=column + " (0600hr)", color=colors[i - 1], alpha=0.7)  # Solid bars for "0600hr" data
    elif "0000hr" in column:
        ax.bar(index + bar_width * (i - 1), df[column], width=bar_width, label=column + " (0000hr)", color=colors[i - 1], hatch='xx', edgecolor='black', alpha=0.7)  # Specify the hatch pattern for "0000hr" data

# Adding labels and title
ax.set_xlabel('Station Name', fontweight='bold')
ax.set_ylabel('Precipitation Difference (mm)', fontweight='bold')
ax.set_title('Comparison of Observed and Predicted 24 hr Precipitation Differences', fontsize=14, fontweight='bold')
ax.set_xticks(index + bar_width * (len(df.columns) / 2 - 1))
ax.set_xticklabels(df["Station Name"])

# Creating legend & ensuring it's not overlapping
ax.legend(title='Methods', bbox_to_anchor=(1.05, 1), loc='upper left')

# Rotate the x-axis labels for better readability
plt.setp(ax.get_xticklabels(), rotation=45)

# Specify the path to the folder where you want to save the PNG file
output_folder = '/Users/haseeb.rehman/Desktop/For_Animation'

# Save the plot as PNG with the same name as the NetCDF file
output_file = os.path.join(output_folder, 'precipitation_difference_comparison.png')
plt.savefig(output_file, dpi=400, bbox_inches='tight')  # Adjusted bbox_inches

# Show the plot
plt.tight_layout()
plt.show()
