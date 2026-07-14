#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Mar  2 13:46:27 2023
@author: haseeb.rehman
"""

import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import os
import contextily as ctx
import rasterio
from rasterio.warp import transform_bounds
import numpy as np
import warnings

# Suppress all warnings
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

# Define the projection for the map (Web Mercator)
data_crs = ccrs.epsg(3857)

#Create figure and axis with minimal margins
fig = plt.figure(figsize=(12, 12))  # Adjusted figure size for full-page fit
ax = plt.axes(projection=data_crs)
fig.subplots_adjust(left=0, right=1, top=2, bottom=1)
# -------------------------------------------------------------------------
# Set the extent using provided coordinates with 0.5 padding
lon_min, lat_min = -1.324371337890625, 44.60498809814453
lon_max, lat_max = 13.7489013671875, 54.220977783203125
ax.set_extent([lon_min - 0.5, lon_max + 0.5, lat_min - 0.5, lat_max + 0.5], crs=ccrs.PlateCarree())
'''
# Load and plot Greater Region shapefile with dotted boundary
greater_region_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region.shp"
try:
    greater_region_gdf = gpd.read_file(greater_region_path).to_crs(epsg=3857)
    greater_region_gdf.plot(
        ax=ax,
        facecolor='none',
        edgecolor='green',
        linewidth=1,
        linestyle='--',  # Dotted or dashed line
        zorder=4,
        label='Greater Region Boundary'
    )
    print("✔️ Greater Region shapefile plotted as dashed line.")
except Exception as e:
    print(f"⚠️ Could not load Greater Region shapefile: {e}")

# -------------------------------------------------------------------------
# Load and plot elevation data
# -------------------------------------------------------------------------
elevation_file = '/Users/haseeb.rehman/Documents/SRTM_DEM_for_study_area/merged_with_ocean.tif'

with rasterio.open(elevation_file) as src:
    elevation_data = src.read(1).astype("float32")
    elevation_crs = src.crs
    nodata = src.nodata

    # Clean and clamp elevation data
    elevation_data[elevation_data == nodata] = np.nan
    

    # Reproject bounds to display CRS
    left, bottom, right, top = transform_bounds(elevation_crs, data_crs, *src.bounds)

    if not np.isnan(elevation_data).all():
        im = ax.imshow(
            elevation_data,
            extent=[left, right, bottom, top],
            transform=data_crs,
            cmap='terrain',
            zorder=1
        )
    else:
        print("Warning: All elevation values are NaN. Check DEM source.")
'''
# -------------------------------------------------------------------------
# Add base layers and features
# -------------------------------------------------------------------------
ax.add_feature(cfeature.COASTLINE, linewidth=0.6, edgecolor="black")
ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.8, edgecolor="black")
ax.add_feature(cfeature.OCEAN, facecolor='deepskyblue')
#ax.add_feature(cfeature.RIVERS, edgecolor="blue", linewidth=0.3)

# Optional basemap

#try:
 #   ctx.add_basemap(ax, source=ctx.providers.Esri.WorldPhysical, crs=data_crs, zoom=6, attribution=False, zorder=0)
#except Exception as e:
#    print("Basemap loading failed:", e)


# Add gridlines with increased label size
gl = ax.gridlines(draw_labels=True, alpha=0.4, linestyle="--")
gl.xlocator = plt.FixedLocator([0, 2, 4, 6, 8, 10, 12, 14])
gl.ylocator = plt.FixedLocator([44, 46, 48, 50, 52, 54])
gl.top_labels = False
gl.right_labels = False
gl.xlabel_style = {'size': 21}  # Standardized to 21
gl.ylabel_style = {'size': 21}  # Standardized to 21
'''
cbar = plt.colorbar(im, ax=ax, orientation='vertical', pad=0.04, shrink=0.65)
cbar.set_label('Elevation (m)', fontsize=11)
'''
# -------------------------------------------------------------------------
# Function to plot observation points
# -------------------------------------------------------------------------
def plot_points(shapefile_path, marker, color, label):
    try:
        gdf = gpd.read_file(shapefile_path)
        gdf.to_crs(crs=data_crs, inplace=True)
        x, y = gdf.geometry.x, gdf.geometry.y
        ax.scatter(x, y, marker=marker, color=color, label=label, s=50, alpha=0.5)
        print(f"✔️ Number of {label}: {len(gdf)}")
    except Exception as e:
        print(f"⚠️ Could not load {label} from {shapefile_path}: {e}")

# -------------------------------------------------------------------------
# Plot observation point types
# -------------------------------------------------------------------------
# Plot each dataset with maximally distinct colors
plot_points('/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/SYNOP_data.shp', 
            'o', 'navy', 'SYNOP Stations')                    # Deep blue
plot_points('/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/TEMP_data.shp', 
            'D', 'darkorange', 'TEMP Stations')               # Orange
plot_points('/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/TAMDAR_data.shp', 
            '^', 'forestgreen', 'TAMDAR Stations')            # Green
plot_points('/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/GPSZD_data.shp', 
            's', 'mediumvioletred', 'GNSS ZTD Stations')      # Magenta-violet

ax.legend(loc='upper right', fontsize=26, facecolor='lightgrey', frameon=True, markerscale=1.5)

# -------------------------------------------------------------------------
# Save figure
# -------------------------------------------------------------------------
output_folder = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs'
os.makedirs(output_folder, exist_ok=True)
output_file = os.path.join(output_folder, "Stations_for_assimilation.png")
plt.savefig(output_file, dpi=500, bbox_inches='tight', pad_inches=0.2)
print(f"\n✅ Plot saved to: {output_file}")
plt.show()
plt.close()
