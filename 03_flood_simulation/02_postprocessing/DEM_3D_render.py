#!/usr/bin/env python3
"""
3D DEM visualization - vibrant colorful rendering
"""

import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import matplotlib.colors as mcolors

# Paths
base_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/ready_for_simulation'
dem_path = os.path.join(base_dir, 'Alzette_sub_basin_10m_bridge_burn.asc')
output_dir = base_dir

# Load DEM
with rasterio.open(dem_path) as dem_src:
    dem = dem_src.read(1).astype(float)
    dem[dem == dem_src.nodata] = np.nan
    bounds = dem_src.bounds

# Downsample for smooth rendering (use stride=1 for best quality, 2 for faster rendering)
stride = 1
dem_3d = dem[::stride, ::stride]

# Mask NaN values properly
dem_masked = np.ma.masked_invalid(dem_3d)

# Create coordinate grids
ny, nx = dem_3d.shape
x = np.linspace(bounds.left, bounds.right, nx)
y = np.linspace(bounds.top, bounds.bottom, ny)  # Top to bottom (north to south)
X, Y = np.meshgrid(x, y)

# Create natural terrain colormap (green -> brown)
from pyproj import Transformer

# Create terrain colormap: Low (Dark Green) -> Medium (Light Green/Yellow) -> High (Brown/Dark Brown)
# This represents valleys/rivers in green and hills/mountains in brown
colors_list = [
    '#1a5f1a',  # Dark green (lowest elevation - river valleys)
    '#2d8b2d',  # Medium green
    '#4db84d',  # Light green
    '#7fcc7f',  # Very light green
    '#9dd99d',  # Pale green
    '#c2e6c2',  # Very pale green
    '#d4cc9a',  # Yellow-green transition
    '#c9a86a',  # Tan
    '#b5914d',  # Light brown
    '#9a7b3d',  # Medium brown
    '#806030',  # Brown
    '#664d26',  # Dark brown (highest elevation)
]
n_bins = 256
cmap_terrain = mcolors.LinearSegmentedColormap.from_list('terrain', colors_list, N=n_bins)

# Create figure
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='3d')

# Transform coordinates to Lat/Lon (EPSG:2169 -> EPSG:4326)
# Assuming input is LUREF (Luxembourg), EPSG:2169
transformer = Transformer.from_crs("EPSG:2169", "EPSG:4326", always_xy=True)
Lon, Lat = transformer.transform(X, Y)

# Plot 3D surface with masked data
# Using Lon, Lat for X, Y coordinates
surf = ax.plot_surface(Lon, Lat, dem_masked, cmap=cmap_terrain,
                       linewidth=0, antialiased=True,
                       shade=True, alpha=1.0, rcount=400, ccount=400,
                       vmin=np.nanmin(dem_3d), vmax=np.nanmax(dem_3d))

# Set viewing angle (azim=-90 makes north point up)
ax.view_init(elev=40, azim=-90)

# Calculate Metric aspect ratio for realistic scaling (from original metric bounds)
x_range_m = bounds.right - bounds.left
y_range_m = bounds.top - bounds.bottom
z_range_m = np.nanmax(dem_3d) - np.nanmin(dem_3d)

# Set box aspect ratio based on METRIC dimensions
# Increase vertical exaggeration to 15x for better visibility
ax.set_box_aspect((x_range_m, y_range_m, z_range_m * 15))

# Set Z-axis limits
ax.set_zlim(np.nanmin(dem_3d), np.nanmax(dem_3d))

# Reduce Z-axis tick density to prevent overlapping
from matplotlib.ticker import MaxNLocator
ax.zaxis.set_major_locator(MaxNLocator(nbins=3))

# Axis labels - positioned in front of tick labels
ax.set_xlabel('Longitude (°)', labelpad=25, fontsize=16)
ax.set_ylabel('Latitude (°)', labelpad=40, rotation=0, fontsize=16)  # rotation=0 to face viewer
ax.set_zlabel('Elevation (m)', labelpad=30, rotation=0, fontsize=16)  # rotation=0 to face viewer

# Push tick labels (numbers) away from axis lines
ax.tick_params(axis='x', which='major', pad=10, labelsize=16)
ax.tick_params(axis='y', which='major', pad=15, labelsize=16)  # More padding for latitude
ax.tick_params(axis='z', which='major', pad=10, labelsize=16)  # More padding for elevation

# Enable grid lines on all three axes with custom styling
ax.xaxis._axinfo['grid'].update({'color': 'grey', 'linewidth': 0.3, 'linestyle': '--'})
ax.yaxis._axinfo['grid'].update({'color': 'grey', 'linewidth': 0.3, 'linestyle': '--'})
ax.zaxis._axinfo['grid'].update({'color': 'grey', 'linewidth': 0.3, 'linestyle': '--'})

# Make panes completely transparent so grid shows through
ax.xaxis.pane.fill = False
ax.yaxis.pane.fill = False
ax.zaxis.pane.fill = False
ax.xaxis.pane.set_alpha(0)
ax.yaxis.pane.set_alpha(0)
ax.zaxis.pane.set_alpha(0)
fig.patch.set_facecolor('white')

# Adjust layout
# Remove white space - adjust subplot to fill figure
plt.subplots_adjust(left=0, right=1, top=1, bottom=0)

# Save high-resolution figure with tight cropping
output_path = os.path.join(output_dir, 'DEM_3D.png')
fig.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white', pad_inches=0.1)
print(f"✅ 3D DEM saved to: {output_path}")

plt.show()
