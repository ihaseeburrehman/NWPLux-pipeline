#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Created on Tue Mar  7 12:15:09 2023

@author: haseeb.rehman
"""
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import geopandas as gpd
import os
import cartopy.crs as ccrs
from cartopy.feature import OCEAN, LAND, COASTLINE
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter

# Define the projection for the map
data_crs = {'init': 'epsg:3857'}

# Create the map figure
fig = plt.figure(figsize=(10, 6))

# Create a Basemap object for the globe
m = Basemap(projection='cyl', lat_0=52.0, lon_0=5.0, llcrnrlon=0.0, llcrnrlat=45.0, urcrnrlon=12.5, urcrnrlat=55.0, resolution='h')

# Draw coastlines and countries
m.drawcoastlines(linewidth=0.5)
m.drawcountries(linewidth=0.5)

# Draw parallels and meridians
m.drawparallels(np.arange(30., 76., 2.5), labels=[1,0,0,0], fontsize=10)
m.drawmeridians(np.arange(-20., 46., 2.5), labels=[0,0,0,1], fontsize=10)

# Draw the area of interest
m.drawmapboundary(fill_color='skyblue')
m.fillcontinents(color='sandybrown',lake_color='skyblue')

# Read the shapefile using GeoPandas
shpfilename_2 = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_Domain_EPSG4386.shp'
gdf = gpd.read_file(shpfilename_2)

# Reproject the shapefile to match the map projection
gdf = gdf.to_crs(data_crs)

#shpfilename_3 = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Domain_epsg4326.shp'
#gdf = gpd.read_file(shpfilename_3)

# Reproject the shapefile to match the map projection
gdf = gdf.to_crs(data_crs)

# Plot the shapefile and add legend
m.readshapefile(shpfilename_2[:-4], 'my_shapefile_2', drawbounds=True, linewidth=2, color='red')
#m.readshapefile(shpfilename_3[:-4], 'my_shapefile_3', drawbounds=True, linewidth=2, color='green')
ax = plt.gca()
# Create the legend
legend_labels = ['Greater Region Domain'] #'Grand Duchy of Luxembourg Domain']
legend_handles = [plt.Line2D([], [], linewidth=2, color='red'),
                  plt.Line2D([], [], linewidth=2, color='green')]
ax.legend(legend_handles, legend_labels, loc='lower center', ncol=2, bbox_to_anchor=(0.5, -0.2), frameon=True, framealpha=1)

# add north arrow
ax.arrow(0.95, 0.05, 0, 0.15, transform=ax.transAxes, color='White',
         length_includes_head=True, head_width=0.03, head_length=0.05)

# add 'N' label
ax.text(0.95, 0.02, 'N', transform=ax.transAxes, fontsize=12, ha='center', color='white')



# specify the path to the folder where you want to save the PNG file
output_folder = '/Users/haseeb.rehman/Desktop/For_Animation/Miscs'

# save the plot as PNG with the same name as the NetCDF file
output_file = os.path.join(output_folder, 'Europe map Zoomed-GR.png')
plt.savefig(output_file, dpi=400, bbox_inches='tight', pad_inches=0.1)

# Show the plot
plt.show()

