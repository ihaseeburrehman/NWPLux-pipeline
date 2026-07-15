#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Create 10m Manning coefficient map for Luxembourg using the LC2018 GDB
"""

import os
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from shapely.geometry import box

# Paths
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/Alzette_sub_basin_10m_bridge_burn.asc'
gdb_path = '/Users/haseeb.rehman/Downloads/landcover2018-vector/LC_2018.gdb'
output_asc = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/manning.n.ascii'

# Manning map (Values from existing scripts)
manning_map = {
    'Bare soil': 0.02,
    'Building': 0.20,
    'Bush': 0.07,
    'Other constructed area': 0.016,
    'Permanent herbaceous vegetation': 0.035,
    'Seasonal herbaceous vegetation': 0.04,
    'Tree': 0.1,
    'Water': 0.03,
    'Vineyard': 0.045
}

DEFAULT_MANNING = 0.035

print("="*80)
print("CREATING 10M MANNING MAP FROM LUXEMBOURG GDB")
print("="*80)

# Step 1: Read DEM and valid mask
print(f"Reading DEM: {os.path.basename(dem_path)}")
with rasterio.open(dem_path) as dem:
    transform = dem.transform
    full_shape = (dem.height, dem.width)
    xllcorner = transform[2]
    yllcorner = transform[5] + full_shape[0] * transform[4]
    cellsize = transform[0]
    crs = dem.crs if dem.crs else 'EPSG:2169'
    nodata_val = dem.nodata
    
    # Read DEM data to create mask
    dem_data = dem.read(1)
    dem_mask = (dem_data != nodata_val)
    
    # Calculate bounds for spatial filtering
    xmin = transform.c
    ymax = transform.f
    xmax = xmin + dem.width * cellsize
    ymin = ymax + dem.height * transform.e

# Step 2: Read Land Cover from GDB using spatial filter
print(f"Reading Landcover from GDB with spatial filter...")
gdf = gpd.read_file(
    gdb_path, 
    layer='LC2018_Luxembourg_country',
    bbox=(xmin, ymin, xmax, ymax)
)

if gdf.empty:
    print("Error: No land cover data found within DEM extent.")
    exit(1)

print(f"Read {len(gdf)} features within the domain.")

# Step 3: Assign Manning values
print("Mapping Manning values...")
gdf['manning'] = gdf['LABEL_en'].map(manning_map).fillna(DEFAULT_MANNING)

# Step 4: Rasterize Manning values
print("Rasterizing to 10m grid...")
shapes_list = ((geom, value) for geom, value in zip(gdf.geometry, gdf.manning))
manning_raster = rasterize(
    shapes_list,
    out_shape=full_shape,
    transform=transform,
    fill=-9999, # Changed from DEFAULT_MANNING to -9999 to allow merging with France
    dtype='float32'
)

# Step 5: Apply DEM mask (Critical: match DEM shape exactly)
print("Applying DEM domain mask...")
manning_raster = np.where(dem_mask, manning_raster, -9999)

# Step 6: Write ASCII grid
print(f"Writing to: {output_asc}")
with open(output_asc, 'w') as f:
    f.write(f"ncols {full_shape[1]}\n")
    f.write(f"nrows {full_shape[0]}\n")
    f.write(f"xllcorner {xllcorner:.6f}\n")
    f.write(f"yllcorner {yllcorner:.6f}\n")
    f.write(f"cellsize {cellsize:.6f}\n")
    f.write("NODATA_value -9999\n")
    for row in manning_raster:
        f.write(" ".join(f"{val:.4f}" if val != -9999 else "-9999" for val in row) + "\n")

print("✅ Manning 10m ASCII grid created successfully (masked by DEM).")
print("="*80)
