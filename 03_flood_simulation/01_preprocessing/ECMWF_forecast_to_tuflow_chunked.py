#!/usr/bin/env python3
"""
ECMWF Forecast (Fixed 6h) to TUFLOW NetCDF converter.
Converts ECMWF 'tp' (m) to 'rainfall_depth' (mm) on 5m projected grid.
Uses RegularGridInterpolator for efficiency.
"""

import xarray as xr
import numpy as np
import pandas as pd
from pyproj import Transformer
import glob
import os
import netCDF4 as nc
from scipy.interpolate import RegularGridInterpolator
from datetime import datetime

# Paths
ecmwf_dir = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Radar_and_Weather/ecmwf_operational_forecast/ecmwf_operational_fixed_6h_rainfall/test"
dem_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/Alzette_sub_basin_10m_bridge_burn.asc"
output_file = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/rain_10m_from_ecmwf.nc"

# Automatically extract DEM grid parameters with full precision
print(f"Reading DEM parameters from: {dem_path}")
import rasterio
with rasterio.open(dem_path) as dem:
    # Get bounds with full precision
    min_x = dem.bounds.left
    max_x = dem.bounds.right
    min_y = dem.bounds.bottom
    max_y = dem.bounds.top
    
    # Get resolution (assuming square pixels)
    resolution = dem.transform[0]  # Cell width
    
    # Get dimensions
    nx = dem.width
    ny = dem.height
    
    print(f"  Bounds: min_x={min_x}, max_x={max_x}")
    print(f"  Bounds: min_y={min_y}, max_y={max_y}")
    print(f"  Resolution: {resolution} meters")
    print(f"  Dimensions: nx={nx}, ny={ny}")

# Cell-center coordinates
x_target = min_x + (np.arange(nx) + 0.5) * resolution
y_target = max_y - (np.arange(ny) + 0.5) * resolution  # Decreasing: top to bottom

# Create meshgrid of target coordinates (needed for interpolation lookup)
print("Generating target coordinates...")
x_grid, y_grid = np.meshgrid(x_target, y_target)

# Coordinate transformer: EPSG:2169 (Target) -> EPSG:4326 (Source Lat/Lon)
print("Transforming target grid to Lat/Lon...")
transformer = Transformer.from_crs("EPSG:2169", "EPSG:4326", always_xy=True)
lon_target, lat_target = transformer.transform(x_grid, y_grid)

# Find ECMWF files
ecmwf_files = sorted(glob.glob(os.path.join(ecmwf_dir, "*.nc")))
if not ecmwf_files:
    raise ValueError(f"No NetCDF files found in {ecmwf_dir}")
print(f"Found {len(ecmwf_files)} ECMWF files")

# Extract timestamps and sort
all_times = []
valid_files = []
for f in ecmwf_files:
    try:
        # Parse filename for time: YYYY_MM_DD_HH_MM_SS.nc
        basename = os.path.basename(f)
        date_str = basename.replace(".nc", "")
        dt = datetime.strptime(date_str, "%Y_%m_%d_%H_%M_%S")
        all_times.append(dt)
        valid_files.append(f)
    except Exception as e:
        print(f"Skipping {f}: {e}")

if not valid_files:
    raise ValueError("No valid files found.")

# Convert to sorted pandas DatetimeIndex to ensure chronological order
time_index = pd.DatetimeIndex(all_times)
sorted_indices = np.argsort(time_index)
sorted_files = [valid_files[i] for i in sorted_indices]
sorted_times = time_index[sorted_indices]

# Calculate hourly time variable relative to start
start_time = sorted_times[0]
time_var = (sorted_times - start_time).total_seconds() / 3600.0
nt = len(time_var)

print(f"Total timesteps: {nt} (Start: {start_time})")

# Create NetCDF file
print(f"Creating output file: {output_file}")
ncfile = nc.Dataset(output_file, 'w', format='NETCDF4')

# Dimensions
ncfile.createDimension('time', None)
ncfile.createDimension('x', nx)
ncfile.createDimension('y', ny)

# Variables
t_nc = ncfile.createVariable('time', 'f8', ('time',))
t_nc.units = 'hour'
t_nc.axis = 'T'
t_nc[:] = time_var

x_nc = ncfile.createVariable('x', 'f8', ('x',))
x_nc.units = 'm'
x_nc.axis = 'X'
x_nc.spatial_ref = 'EPSG:2169'
x_nc[:] = x_target

y_nc = ncfile.createVariable('y', 'f8', ('y',))
y_nc.units = 'm'
y_nc.axis = 'Y'
y_nc.spatial_ref = 'EPSG:2169'
y_nc[:] = y_target

rain_nc = ncfile.createVariable('rainfall_depth', 'f4', ('time', 'y', 'x'), zlib=True, complevel=4)
rain_nc.units = 'mm'  # Converted from m
rain_nc.long_name = 'rainfall_depth'

# Global Attributes
ncfile.crs = 'EPSG:2169'
ncfile.spatial_ref = '+proj=tmerc +lat_0=49.8333333333333 +lon_0=6.16666666666667 +k=0.9996 +x_0=80000 +y_0=100000 +ellps=GRS80 +units=m +no_defs'

# Load first file to get grid coordinates for Interpolator optimization
# We assume all ECMWF files share the same Lat/Lon grid
with xr.open_dataset(sorted_files[0]) as ds0:
    # ECMWF latitude is typically decreasing (90 -> -90)
    # RegularGridInterpolator requires increasing coordinates
    src_lat = ds0['latitude'].values
    src_lon = ds0['longitude'].values
    
    # Store explicit grid for later check
    lat_increasing = src_lat[1] > src_lat[0]
    lon_increasing = src_lon[1] > src_lon[0]
    
    # Prepare coordinates for interpolator (must be strictly increasing)
    if not lat_increasing:
        interp_lat = src_lat[::-1]
    else:
        interp_lat = src_lat
        
    if not lon_increasing:
        interp_lon = src_lon[::-1]
    else:
        interp_lon = src_lon

# Flatten target coordinates for batch interpolation
# target_points shape: (N, 2) where N = nx*ny, columns are (Lat, Lon)
target_points = np.column_stack((lat_target.ravel(), lon_target.ravel()))

# Process files
for idx, f in enumerate(sorted_files):
    print(f"Processing [{idx}/{nt-1}]: {os.path.basename(f)}")
    
    try:
        with xr.open_dataset(f) as ds:
            # Load 'tp' (Total Precipitation)
            tp_var = ds['tp']
            input_units = tp_var.attrs.get('units', 'm')  # Default to m if unknown, careful
            
            # Determine scaling factor
            if input_units == 'm':
                scale_factor = 1000.0
            elif input_units in ['mm', 'kg m**-2', 'kg/m^2']:
                scale_factor = 1.0
            else:
                print(f"  Warning: Unknown units '{input_units}'. Assuming 'm' (x1000).")
                scale_factor = 1000.0
                
            rain_val = tp_var.values[0, :, :] # (lat, lon)
            
            # Handle flipping if lat/lon were flipped for interpolator
            if not lat_increasing:
                rain_val = rain_val[::-1, :]
            if not lon_increasing:
                rain_val = rain_val[:, ::-1]
            
            # Create Interpolator
            # (lat, lon) -> data
            interpolator = RegularGridInterpolator((interp_lat, interp_lon), rain_val, 
                                                   method='linear', bounds_error=False, fill_value=0.0)
            
            # Interpolate
            # Result shape (N,) -> Reshape to (ny, nx)
            rain_mm_flat = interpolator(target_points) * scale_factor
            rain_mm = rain_mm_flat.reshape(ny, nx)
            
            # Clean negatives
            rain_mm = np.maximum(rain_mm, 0.0)
            
            # Write
            rain_nc[idx, :, :] = rain_mm.astype(np.float32)
            
            print(f"  Sum: {np.sum(rain_mm):.2f} mm | Max: {np.max(rain_mm):.2f} mm")

    except Exception as e:
        print(f"  ERROR processing {f}: {e}")
        rain_nc[idx, :, :] = np.zeros((ny, nx), dtype=np.float32)

ncfile.close()
print(f"\n✅ Success! Saved to: {output_file}")
