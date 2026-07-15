#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Created on Thu Sep 18 16:51:31 2025
@author: haseeb.rehman
"""

import os
import geopandas as gpd
import numpy as np
from shapely.geometry import shape as shapely_shape
from shapely.ops import unary_union
import rasterio
from rasterio.features import shapes, rasterize

# Set environment variables before importing rasterio-dependent libraries
os.environ['PROJ_LIB'] = '/opt/homebrew/share/proj'
os.environ['GDAL_DATA'] = '/opt/homebrew/share/gdal'

# Paths
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/Alzette_sub_basin_10m_bridge_burn.asc'
landcover_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/Alzette_landcover_valid_dem_only.gpkg'
output_asc = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/manning.n.ascii'

# Step 1: Read DEM metadata and mask
with rasterio.open(dem_path) as dem:
    meta = dem.meta.copy()
    transform = dem.transform
    full_shape = (dem.height, dem.width)
    xllcorner = transform[2]
    yllcorner = transform[5] + full_shape[0] * transform[4]  # Correct yllcorner for ASC
    cellsize = transform[0]
    crs = dem.crs
    mask = dem.read_masks(1) > 0
    shapes_gen = shapes(mask.astype(np.uint8), transform=transform)
    polygons = [shapely_shape(geom) for geom, value in shapes_gen if value == 1]
    dem_mask = unary_union(polygons)

# Step 2: Read and clip land cover
gdf = gpd.read_file(landcover_path)
gdf.crs = crs
mask_gdf = gpd.GeoDataFrame(geometry=[dem_mask], crs=crs)
gdf = gpd.clip(gdf, mask_gdf)

# Step 3: Assign Manning values
manning_map = {
    'Bare soil': 0.02,
    'Building': 0.20, # Reduced from 0.3 to 0.2 as requested
    'Bush': 0.07,
    'Other constructed area': 0.025,
    'Permanent herbaceous vegetation': 0.035,
    'Seasonal herbaceous vegetation': 0.04,
    'Tree': 0.1,
    'Water': 0.03
}
gdf['manning'] = gdf['LABEL_en'].map(manning_map).fillna(0.03)

# Step 4: Rasterize Manning values using DEM shape
shapes_list = ((geom, value) for geom, value in zip(gdf.geometry, gdf.manning))
manning_raster = rasterize(
    shapes_list,
    out_shape=full_shape,
    transform=transform,
    fill=-9999,
    dtype='float32'
)

# Step 5: Validate shape and pad if needed
if manning_raster.shape != full_shape:
    print(f"⚠️ Shape mismatch: expected {full_shape}, got {manning_raster.shape}")
    last_row = manning_raster[-1]
    pad_rows = full_shape[0] - manning_raster.shape[0]
    manning_raster = np.vstack([manning_raster] + [last_row] * pad_rows)

# Step 6: Write ASCII grid
with open(output_asc, 'w') as f:
    f.write(f"ncols {full_shape[1]}\n")
    f.write(f"nrows {full_shape[0]}\n")
    f.write(f"xllcorner {xllcorner:.6f}\n")
    f.write(f"yllcorner {yllcorner:.6f}\n")
    f.write(f"cellsize {cellsize:.6f}\n")
    f.write("NODATA_value -9999\n")
    for row in manning_raster:
        f.write(" ".join(f"{val:.4f}" if val != -9999 else "-9999" for val in row) + "\n")

print("✅ Manning ASCII grid saved to:", output_asc)
