#!/usr/bin/env python3
"""
2D Manning coefficient map from ASCII grid - Optimized
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.patches import Rectangle
from matplotlib.colors import ListedColormap, BoundaryNorm
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling

# Paths
manning_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/ready_for_simulation/manning.n.ascii'
output_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/ready_for_simulation/plots/'

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Manning coefficient mapping: Label -> (Value, Color)
# Note: In the raster, Tree=0.1 and Building=0.2. 
# Re-assigning 0.1 to Tree to ensure visibility/distinction.
manning_legend_dict = {
    'Water': (0.03, '#4366f5'),
    'Tree': (0.1, '#06bb15'),
    'Bush': (0.07, '#3acf18'),
    'Permanent herbaceous vegetation': (0.035, '#43a927'),
    'Seasonal herbaceous vegetation': (0.04, '#12c108'),
    'Bare soil': (0.02, '#25ca75'),
    'Building': (0.2, '#bbd819'),
    'Other constructed area': (0.02, '#d48a34')
}

# Create a mapping from Value -> Color for the plot
value_to_color = {v[0]: v[1] for k, v in manning_legend_dict.items()}
unique_values = sorted(value_to_color.keys())
colors = [value_to_color[v] for v in unique_values]

# Define bounds for discrete colormap
boundaries = []
if len(unique_values) > 0:
    boundaries = [unique_values[0] - 0.001]
    for i in range(len(unique_values) - 1):
        mid_point = (unique_values[i] + unique_values[i+1]) / 2
        boundaries.append(mid_point)
    boundaries.append(unique_values[-1] + 0.001)

cmap = ListedColormap(colors)
norm = BoundaryNorm(boundaries, len(colors))

print("Processing Manning raster...")

# 1. Read and Reproject the Raster to EPSG:4326 (Lat/Lon)
dst_crs = 'EPSG:4326'

with rasterio.open(manning_path) as src:
    if src.crs:
        src_crs = src.crs
    else:
        src_crs = 'EPSG:2169' 
    print(f"Source CRS: {src_crs}")
    
    raw_data = src.read(1)
    
    transform, width, height = calculate_default_transform(
        src_crs, dst_crs, src.width, src.height, *src.bounds)
    
    kwargs = src.meta.copy()
    kwargs.update({
        'crs': dst_crs,
        'transform': transform,
        'width': width,
        'height': height
    })

    destination = np.zeros((height, width), dtype=np.float32)

    reproject(
        source=raw_data,
        destination=destination,
        src_transform=src.transform,
        src_crs=src_crs,
        dst_transform=transform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest,
        src_nodata=src.nodata,
        dst_nodata=-9999)

    data_masked = np.ma.masked_equal(destination, -9999)
    bounds = rasterio.transform.array_bounds(height, width, transform)
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]

# 2. Plotting
print("Creating plot...")
fig, ax = plt.subplots(figsize=(12, 10))

im = ax.imshow(data_masked, cmap=cmap, norm=norm, extent=extent, interpolation='nearest', origin='upper')

ax.set_xlabel('Longitude (°)', fontsize=15)
ax.set_ylabel('Latitude (°)', fontsize=15)

ax.xaxis.set_major_locator(mticker.MultipleLocator(0.05))
ax.yaxis.set_major_locator(mticker.MultipleLocator(0.05))

from matplotlib.ticker import FormatStrFormatter
ax.xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))

ax.tick_params(axis='both', which='major', labelsize=18)

mean_lat = (extent[2] + extent[3]) / 2
aspect_ratio = 1.0 / np.cos(np.radians(mean_lat))
ax.set_aspect(aspect_ratio)

# 3. Create Legend
legend_elements = []
# Fixed ordered legend with full names as requested
requested_order = [
    'Water', 'Tree', 'Bush', 
    'Permanent herbaceous vegetation', 
    'Seasonal herbaceous vegetation', 
    'Bare soil', 'Building', 
    'Other constructed area'
]

for label in requested_order:
    if label in manning_legend_dict:
        val, color = manning_legend_dict[label]
        legend_elements.append(mpatches.Patch(facecolor=color, edgecolor='black', linewidth=0.5,
                                             label=f'{label} (n={val})'))

legend = ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0.02, 0.98),
                   fontsize=7, frameon=True, fancybox=False, title='Manning n', title_fontsize=8,
                   edgecolor='black', framealpha=0.9)
legend.get_frame().set_linewidth(0.5)

# 4. Add North Arrow (Scale Bar Removed)
x_arrow, y_arrow = 0.05, 0.70  # Lowered to clear the taller legend
ax.annotate('', xy=(x_arrow, y_arrow), xytext=(x_arrow, y_arrow - 0.04),
            arrowprops=dict(facecolor='black', width=1.5, headwidth=6),
            xycoords='axes fraction')
ax.text(x_arrow, y_arrow + 0.005, 'N', transform=ax.transAxes, 
        ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()

# Save
output_path = os.path.join(output_dir, 'Manning_n_ASCII_Map.png')
fig.savefig(output_path, dpi=600, bbox_inches='tight', facecolor='white')
print(f"✅ Manning map saved to: {output_path}")

plt.close(fig)
