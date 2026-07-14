#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 07:22:00 2025

@author: haseeb.rehman
"""
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import os
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Define projection (PlateCarree for geographic coordinates)
projection = ccrs.PlateCarree()

# Create figure and axis
fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={'projection': projection})

# Define map extent for Europe
lon_min_eu, lon_max_eu = -10, 30
lat_min_eu, lat_max_eu = 35, 70
ax.set_extent([lon_min_eu, lon_max_eu, lat_min_eu, lat_max_eu], crs=projection)

# Add ocean in blue and land in white
ax.add_feature(cfeature.OCEAN, facecolor='deepskyblue')
ax.add_feature(cfeature.LAND, facecolor='white')

# Add country borders and coastlines
ax.add_feature(cfeature.BORDERS, edgecolor='black', linewidth=1, linestyle='--')
ax.add_feature(cfeature.COASTLINE, edgecolor='black', linewidth=1)

# Define domain coordinates
#d01
lon_min, lat_min = -1.324371337890625, 44.60498809814453
lon_max, lat_max = 13.7489013671875, 54.220977783203125

# Plot the domain box
domain_lons = [lon_min, lon_max, lon_max, lon_min, lon_min]
domain_lats = [lat_min, lat_min, lat_max, lat_max, lat_min]
ax.plot(domain_lons, domain_lats, transform=ccrs.PlateCarree(), color='red', linewidth=2, label="Domain Extent")

# Read and reproject shapefiles
data_crs = {'init': 'epsg:3857'}
shpfilename_2 = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_Domain_EPSG4386.shp'
gdf2 = gpd.read_file(shpfilename_2).to_crs(data_crs)

shpfilename_3 = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Domain_epsg4326.shp'
gdf3 = gpd.read_file(shpfilename_3).to_crs(data_crs)

# Plot shapefiles
gdf2.plot(ax=ax, edgecolor='red', linewidth=2, facecolor='none', label='Greater Region Domain')
gdf3.plot(ax=ax, edgecolor='green', linewidth=2, facecolor='none', label='Grand Duchy of Luxembourg Domain')

# Add gridlines
gl = ax.gridlines(draw_labels=True, linestyle="--", alpha=0.5)
gl.right_labels = False
gl.top_labels = False
gl.xlabel_style = {'size': 10, 'color': 'black'}
gl.ylabel_style = {'size': 10, 'color': 'black'}

# Add north arrow
ax.arrow(0.95, 0.05, 0, 0.15, transform=ax.transAxes, color='black',
         length_includes_head=True, head_width=0.03, head_length=0.05)
ax.text(0.95, 0.02, 'N', transform=ax.transAxes, fontsize=12, ha='center', color='black')

# Add legend
ax.legend(loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.2), frameon=True, framealpha=1)

# Define the save path
output_folder = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/Miscs/'
output_file = os.path.join(output_folder, 'Europe_map.png')

# Save the figure
plt.savefig(output_file, dpi=400, bbox_inches="tight")

# Show the plot
plt.show()

print(f"Map saved at: {output_file}")