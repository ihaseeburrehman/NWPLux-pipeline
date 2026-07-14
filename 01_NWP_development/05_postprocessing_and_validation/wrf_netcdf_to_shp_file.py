#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 24 08:47:25 2025

@author: haseeb.rehman
"""

import xarray as xr
import geopandas as gpd
from shapely.geometry import Polygon
import os

# Load WRF NetCDF file
nc_file = "/Users/haseeb.rehman/Documents/Misc/WRF_Local_machine/4th_year/1.33km_resolution/After_DA/wrfout_d03_2021-07-15_00_00_00"
ds = xr.open_dataset(nc_file)

# Extract lat/lon and rain
lat = ds['XLAT'].isel(Time=0).values
lon = ds['XLONG'].isel(Time=0).values
rain = ds['RAINNC'].isel(Time=0).values
ny, nx = lat.shape

# Define LISFLOOD domain bounds (replace with actual values)
domain_lat_min = 49.4
domain_lat_max = 50.2
domain_lon_min = 5.8
domain_lon_max = 6.5

# Prepare polygons and rain values
polygons = []
rain_values = []

for i in range(ny - 1):
    for j in range(nx - 1):
        tile_lats = [lat[i,j], lat[i,j+1], lat[i+1,j+1], lat[i+1,j], lat[i,j]]
        tile_lons = [lon[i,j], lon[i,j+1], lon[i+1,j+1], lon[i+1,j], lon[i,j]]
        tile_lon_min, tile_lon_max = min(tile_lons), max(tile_lons)
        tile_lat_min, tile_lat_max = min(tile_lats), max(tile_lats)

        if (tile_lon_min <= domain_lon_max and tile_lon_max >= domain_lon_min and 
            tile_lat_min <= domain_lat_max and tile_lat_max >= domain_lat_min):
            polygon = Polygon(zip(tile_lons, tile_lats))
            polygons.append(polygon)
            rain_values.append(float(rain[i, j]))

# Create GeoDataFrame
gdf = gpd.GeoDataFrame({'RAINNC': rain_values}, geometry=polygons, crs="EPSG:4326")

# Reproject to EPSG:2169 (Luxembourg 2000 / Gauss)
gdf = gdf.to_crs(epsg=2169)

# Extract timestamp from WRF filename
wrf_basename = os.path.basename(nc_file)  # gets wrfout_d03_2021-07-15_00_00_00
timestamp = wrf_basename.split('_d03_')[1].replace('-', '_').replace(':', '_')  # gets 2021_07_15_00_00_00

# Save to shapefile

output_dir = "/Users/haseeb.rehman/Desktop/For_Animation/4th_year/Miscs/wrf_tiles_with_rain"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, f"wrf_rain_tiles_{timestamp}_epsg2169.shp")
gdf.to_file(output_path)


print(f"Shapefile saved to: {output_path}")
