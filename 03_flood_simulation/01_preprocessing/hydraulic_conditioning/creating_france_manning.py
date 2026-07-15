#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Create Manning Manning coefficient map for the French part of the basin
template derived from creating_manning_file_from_landcover.py
"""

import os
import geopandas as gpd
import numpy as np
from shapely.geometry import shape as shapely_shape
from shapely.ops import unary_union
import rasterio
from rasterio.features import shapes, rasterize

# Paths for France
dem_path = '/Users/haseeb.rehman/Documents/Misc/Data_Datasets/GIS_and_DEM/France_near_to_Lux_DEM/remaining_part_dem.asc'
landcover_path = '/Users/haseeb.rehman/Documents/Misc/Data_Datasets/GIS_and_DEM/France_near_to_Lux_DEM/Landcover/remaining_basin_landcover.gpkg'
output_asc = '/Users/haseeb.rehman/Documents/Misc/Data_Datasets/GIS_and_DEM/France_near_to_Lux_DEM/remaining_manning.asc'

print("="*80)
print("CREATING MANNING MAP FOR FRANCE PART")
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
    
    # Read mask (valid data areas) for clipping features
    mask_data_for_clip = dem.read_masks(1) > 0
    shapes_gen = shapes(mask_data_for_clip.astype(np.uint8), transform=transform)
    polygons = [shapely_shape(geom) for geom, value in shapes_gen if value == 1]
    dem_clip_poly = unary_union(polygons)

# Step 2: Read and clip land cover
print(f"Reading Landcover: {os.path.basename(landcover_path)}")
gdf = gpd.read_file(landcover_path)
if gdf.crs is None:
    gdf.crs = crs

# Ensure we only process landcover within the DEM domain
mask_gdf = gpd.GeoDataFrame(geometry=[dem_clip_poly], crs=crs)
gdf = gpd.clip(gdf, mask_gdf)

# Step 3: Assign Manning values based on code_cs (OCS codes)
manning_map = {
    'CS1.1.1.1': 0.20,   # Continuous urban (Buildings)
    'CS1.1.1.2': 0.016,   # Discontinuous urban
    'CS1.1.2.1': 0.10,   # Industrial units
    'CS1.2.2':   0.025,  # Transport units (Constructed)
    'CS2.1.1.1': 0.04,   # Arable land
    'CS2.1.1.2': 0.045,  # Arable land (permanent crops)
    'CS2.1.1.3': 0.035,  # Pastures (Permanent herbaceous)
    'CS2.1.2':   0.05,   # Complex agriculture
    'CS2.2.1':   0.10,   # Broad-leaved forest (Trees)
}

DEFAULT_MANNING = 0.035

print("Assigning Manning values...")
gdf['manning'] = gdf['code_cs'].map(manning_map).fillna(DEFAULT_MANNING)

# Step 4: Rasterize Manning values
print("Rasterizing...")
shapes_list = ((geom, value) for geom, value in zip(gdf.geometry, gdf.manning))
manning_raster = rasterize(
    shapes_list,
    out_shape=full_shape,
    transform=transform,
    fill=-9999, # Changed from DEFAULT_MANNING to -9999
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

print("✅ Manning ASCII grid created successfully (masked by DEM).")
print("="*80)
