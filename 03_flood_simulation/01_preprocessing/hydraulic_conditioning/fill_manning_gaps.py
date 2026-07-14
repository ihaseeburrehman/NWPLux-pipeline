#!/usr/bin/env python3
"""
Fill missing Manning values ONLY where DEM has valid data.
Preserves NoData (-9999) where DEM is also NoData.
"""

import numpy as np

# Paths
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/Alzette_sub_basin_complete.asc'
existing_manning = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/manning.n.ascii'
output_manning = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/manning_filled.n.ascii'

# Default Manning value for internal gaps
DEFAULT_MANNING = 0.035
NODATA = -9999

print("=" * 80)
print("FILLING INTERNAL MANNING GAPS (preserving NoData boundary)")
print("=" * 80)

# 1. Read DEM to get valid domain mask
print(f"\n1. Reading DEM for valid domain mask...")
print(f"   {dem_path}")

# Read DEM using simple ASCII format
with open(dem_path, 'r') as f:
    dem_ncols = int(f.readline().split()[1])
    dem_nrows = int(f.readline().split()[1])
    dem_xllcorner = float(f.readline().split()[1])
    dem_yllcorner = float(f.readline().split()[1])
    dem_cellsize = float(f.readline().split()[1])
    dem_nodata_line = f.readline().split()
    dem_nodata = float(dem_nodata_line[1])
    
    # Read data
    dem_data = []
    for line in f:
        dem_data.extend([float(x) for x in line.split()])

dem_array = np.array(dem_data).reshape(dem_nrows, dem_ncols)
print(f"   DEM shape: {dem_array.shape}")
print(f"   DEM NoData: {dem_nodata}")

# Create valid DEM mask (True where DEM has real data)
dem_valid_mask = (dem_array != dem_nodata) & ~np.isnan(dem_array)

print(f"   Valid DEM cells: {dem_valid_mask.sum():,}")

# 2. Read existing Manning file
print(f"\n2. Reading existing Manning file...")
print(f"   {existing_manning}")

with open(existing_manning, 'r') as f:
    ncols = int(f.readline().split()[1])
    nrows = int(f.readline().split()[1])
    xllcorner = float(f.readline().split()[1])
    yllcorner = float(f.readline().split()[1])
    cellsize = float(f.readline().split()[1])
    nodata_line = f.readline().split()
    manning_nodata = float(nodata_line[1])
    
    # Read data
    manning_data = []
    for line in f:
        manning_data.extend([float(x) for x in line.split()])

manning_array = np.array(manning_data).reshape(nrows, ncols)
print(f"   Manning shape: {manning_array.shape}")

# 3. Identify internal gaps vs boundary NoData
print(f"\n3. Analyzing gaps...")

# Manning is missing where it equals NoData or NaN
manning_missing = (manning_array == manning_nodata) | np.isnan(manning_array)

# Internal gaps = DEM valid but Manning missing
internal_gaps = dem_valid_mask & manning_missing

# Boundary NoData = DEM is also NoData (keep as -9999)
boundary_nodata = ~dem_valid_mask

print(f"   Internal gaps (DEM valid, Manning missing): {internal_gaps.sum():,}")
print(f"   Boundary NoData (DEM NoData): {boundary_nodata.sum():,}")

# 4. Fill only internal gaps
print(f"\n4. Filling internal gaps with {DEFAULT_MANNING}...")
manning_filled = manning_array.copy()
manning_filled[internal_gaps] = DEFAULT_MANNING

# Ensure boundary stays as NoData
manning_filled[boundary_nodata] = NODATA

print(f"   Filled {internal_gaps.sum():,} internal gap cells")
print(f"   Preserved {boundary_nodata.sum():,} boundary NoData cells")

# 5. Write output
print(f"\n5. Writing output...")
print(f"   {output_manning}")

with open(output_manning, 'w') as f:
    f.write(f"ncols {ncols}\n")
    f.write(f"nrows {nrows}\n")
    f.write(f"xllcorner {xllcorner}\n")
    f.write(f"yllcorner {yllcorner}\n")
    f.write(f"cellsize {cellsize}\n")
    f.write(f"NODATA_value {NODATA}\n")
    
    for row in manning_filled:
        line = []
        for val in row:
            if val == NODATA:
                line.append("-9999")
            else:
                line.append(f"{val:.3f}")
        f.write(' '.join(line) + '\n')

print(f"   ✓ Saved!")

# Final stats
print(f"\n6. Final Statistics:")
valid_cells = manning_filled != NODATA
print(f"   Valid Manning cells: {valid_cells.sum():,}")
print(f"   Manning range: {manning_filled[valid_cells].min():.3f} to {manning_filled[valid_cells].max():.3f}")

print("\n" + "=" * 80)
print("✓ DONE - Internal gaps filled, boundary NoData preserved")
print("=" * 80)
