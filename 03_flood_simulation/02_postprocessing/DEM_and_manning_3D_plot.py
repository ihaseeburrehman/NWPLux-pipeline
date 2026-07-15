#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
3D rendering of DEM and Manning coefficient for research paper
Matching the reference style with proper 3D visualization
"""

import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import matplotlib.patches as mpatches

# Paths
base_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/10m/'
dem_path = os.path.join(base_dir, 'walferdange_dem_10m.asc')
manning_path = os.path.join(base_dir, 'manning_coefficients_10m.n.ascii')
output_dir = base_dir

# Manning coefficient mapping (from creating_manning_file_from_landcover.py)
manning_legend_dict = {
    'Bare soil': (0.02, '#D2B48C'),           # Tan
    'Other constructed area': (0.025, '#808080'),  # Grey
    'Water': (0.03, '#4682B4'),               # Steel blue
    'Permanent herbaceous vegetation': (0.035, '#9ACD32'),  # Yellow green
    'Seasonal herbaceous vegetation': (0.04, '#F0E68C'),    # Khaki
    'Bush': (0.07, '#6B8E23'),                # Olive drab
    'Tree': (0.1, '#228B22'),                 # Forest green
    'Building': (0.3, '#8B4513')              # Saddle brown
}

# Load DEM
with rasterio.open(dem_path) as dem_src:
    dem = dem_src.read(1).astype(float)
    dem[dem == dem_src.nodata] = np.nan
    bounds = dem_src.bounds
    transform = dem_src.transform

# Load Manning
with rasterio.open(manning_path) as man_src:
    manning = man_src.read(1).astype(float)
    manning[manning == man_src.nodata] = np.nan

# Downsample for 3D rendering (every 3rd point for better quality)
stride = 3
dem_3d = dem[::stride, ::stride]
manning_3d = manning[::stride, ::stride]

# Create coordinate grids
ny, nx = dem_3d.shape
x = np.linspace(bounds.left, bounds.right, nx)
y = np.linspace(bounds.bottom, bounds.top, ny)
X, Y = np.meshgrid(x, y)

# Set up figure for two-column paper
fig = plt.figure(figsize=(7.5, 9))

# ==================== (a) DEM 3D Plot ====================
ax1 = fig.add_subplot(2, 1, 1, projection='3d')

# Use terrain colormap for DEM
norm_dem = mcolors.Normalize(vmin=np.nanmin(dem_3d), vmax=np.nanmax(dem_3d))
colors_dem = cm.terrain(norm_dem(dem_3d))

# Create 3D surface with grid
surf1 = ax1.plot_surface(X, Y, dem_3d, facecolors=colors_dem,
                         linewidth=0.1, antialiased=True,
                         shade=True, alpha=1.0, rcount=200, ccount=200,
                         edgecolor='black', linewidths=0.05)

# Styling
ax1.set_xlabel('Longitude', fontsize=9, labelpad=8)
ax1.set_ylabel('Latitude', fontsize=9, labelpad=8)
ax1.set_zlabel('Elevation (m)', fontsize=9, labelpad=8)
ax1.set_title('(a) Digital Elevation Model', fontsize=11, weight='bold', pad=15)

# Set viewing angle to match reference
ax1.view_init(elev=25, azim=225)

# Grid styling
ax1.grid(True, linestyle='-', linewidth=0.3, alpha=0.3)
ax1.xaxis.pane.fill = False
ax1.yaxis.pane.fill = False
ax1.zaxis.pane.fill = False

# Tick styling
ax1.tick_params(axis='both', which='major', labelsize=8, pad=3)
ax1.tick_params(axis='z', which='major', labelsize=8, pad=3)

# Add colorbar for elevation
sm1 = cm.ScalarMappable(cmap=cm.terrain, norm=norm_dem)
sm1.set_array([])
cbar1 = fig.colorbar(sm1, ax=ax1, shrink=0.6, aspect=15, pad=0.08)
cbar1.set_label('Elevation (m)', fontsize=9, labelpad=10)
cbar1.ax.tick_params(labelsize=8)

# ==================== (b) Manning 3D Plot ====================
ax2 = fig.add_subplot(2, 1, 2, projection='3d')

# Create discrete colormap for Manning based on actual values
manning_values = sorted(set([v[0] for v in manning_legend_dict.values()]))
manning_colors = []
manning_labels = []

for label, (value, color) in sorted(manning_legend_dict.items(), key=lambda x: x[1][0]):
    manning_colors.append(color)
    manning_labels.append(f'{label} ({value:.3f})')

# Create discrete colormap
n_colors = len(manning_values)
cmap_manning = mcolors.ListedColormap(manning_colors)
bounds = manning_values + [manning_values[-1] + 0.01]
norm_manning = mcolors.BoundaryNorm(bounds, cmap_manning.N)

# Map Manning values to colors
colors_manning = cmap_manning(norm_manning(manning_3d))

# Create 3D surface with grid
surf2 = ax2.plot_surface(X, Y, dem_3d, facecolors=colors_manning,
                         linewidth=0.1, antialiased=True,
                         shade=True, alpha=1.0, rcount=200, ccount=200,
                         edgecolor='black', linewidths=0.05)

# Styling
ax2.set_xlabel('Longitude', fontsize=9, labelpad=8)
ax2.set_ylabel('Latitude', fontsize=9, labelpad=8)
ax2.set_zlabel('Elevation (m)', fontsize=9, labelpad=8)
ax2.set_title('(b) Manning Roughness Coefficient', fontsize=11, weight='bold', pad=15)

# Set viewing angle to match reference
ax2.view_init(elev=25, azim=225)

# Grid styling
ax2.grid(True, linestyle='-', linewidth=0.3, alpha=0.3)
ax2.xaxis.pane.fill = False
ax2.yaxis.pane.fill = False
ax2.zaxis.pane.fill = False

# Tick styling
ax2.tick_params(axis='both', which='major', labelsize=8, pad=3)
ax2.tick_params(axis='z', which='major', labelsize=8, pad=3)

# Create custom legend for Manning values
legend_elements = []
for label, (value, color) in sorted(manning_legend_dict.items(), key=lambda x: x[1][0]):
    legend_elements.append(mpatches.Patch(facecolor=color, edgecolor='black',
                                         linewidth=0.5, label=f'{label} ({value:.3f})'))

# Add legend to the right of the plot
ax2.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1.2, 0.5),
          fontsize=7.5, frameon=True, fancybox=False, shadow=False,
          title='Land Cover Type (n)', title_fontsize=8, edgecolor='black')

# Adjust layout
plt.tight_layout()

# Save high-resolution figure
output_path = os.path.join(output_dir, 'DEM_Manning_3D_research_paper.png')
fig.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white')
print(f"✅ High-quality 3D plots saved to: {output_path}")

plt.show()
