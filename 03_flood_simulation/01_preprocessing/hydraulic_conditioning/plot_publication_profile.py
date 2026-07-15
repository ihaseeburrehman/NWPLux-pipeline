#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Create publication plot comparing before/after bridge removal
Blue river, dotted gridlines, Elevation (m)
"""

import numpy as np
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt

# Paths
dem_corrected = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/Alzette_5m_CORRECTED_FINAL.asc'
dem_original = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Alzette_sub_basin_5m_fixed.asc'
river_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/alzette_river.shp'
output_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing'

print("="*70)
print("CREATING PUBLICATION PROFILE PLOT")
print("="*70)

# Load river
print("\n[1/2] Loading river...")
river = gpd.read_file(river_path)
river_line = river.geometry.iloc[0]
print(f"   River length: {river_line.length/1000:.2f} km")

# Sample profile function
def sample_profile(dem_path, river_line):
    print(f"   Sampling {dem_path.split('/')[-1]}...")
    with rasterio.open(dem_path) as src:
        dem_data = src.read(1).astype(float)
        transform = src.transform
        bounds = src.bounds
        if src.nodata is not None:
            dem_data[dem_data == src.nodata] = np.nan
    
    elevs = []
    dists = []
    
    for dist_m in range(0, int(river_line.length) + 1, 5):
        pt = river_line.interpolate(dist_m)
        col = int((pt.x - bounds.left) / transform.a)
        row = int((bounds.top - pt.y) / abs(transform.e))
        
        if 0 <= row < dem_data.shape[0] and 0 <= col < dem_data.shape[1]:
            z = dem_data[row, col]
            if not np.isnan(z):
                elevs.append(z)
                dists.append(dist_m / 1000)
    
    return np.array(dists), np.array(elevs)

# Sample both DEMs
dist_orig, elev_orig = sample_profile(dem_original, river_line)
dist_corr, elev_corr = sample_profile(dem_corrected, river_line)

print(f"   Original: {len(elev_orig)} points")
print(f"   Corrected: {len(elev_corr)} points")

# Create publication plot
print("\n[2/2] Creating publication plot...")

fig, ax = plt.subplots(figsize=(12, 5))

# Plot with blue color for river
ax.plot(dist_orig, elev_orig, color='gray', linewidth=1.8, 
        label='Before bridge removal', alpha=0.7, linestyle='--')
ax.plot(dist_corr, elev_corr, color='#1E88E5', linewidth=2.2,  # Blue
        label='After bridge removal', alpha=0.95)
ax.fill_between(dist_corr, elev_corr, np.min(elev_corr), 
                alpha=0.15, color='#1E88E5')  # Blue fill

# Axes labels
ax.set_xlabel('Distance from upstream (km)', fontsize=12)
ax.set_ylabel('Elevation (m)', fontsize=12)
ax.set_xlim(0, max(dist_corr))
ax.set_ylim(210, 315)

# Dotted gridlines
ax.grid(True, alpha=0.4, linestyle=':', linewidth=0.8, color='gray')
ax.set_axisbelow(True)

# Legend
ax.legend(loc='upper right', fontsize=11, frameon=True, 
         fancybox=False, shadow=False, framealpha=0.95)

# Tick parameters
ax.tick_params(axis='both', which='major', labelsize=10)

plt.tight_layout()

# Save PNG
output_plot = f'{output_dir}/profile_publication.png'
plt.savefig(output_plot, dpi=300, bbox_inches='tight', facecolor='white')
print(f"   ✓ Saved: {output_plot}")

print("\n" + "="*70)
print("COMPLETE!")
print("="*70)
print(f"\nProfile plot: profile_publication.png")
print(f"  - Blue river profile")
print(f"  - Dotted gridlines")
print(f"  - Elevation (m) label")
print("="*70)
