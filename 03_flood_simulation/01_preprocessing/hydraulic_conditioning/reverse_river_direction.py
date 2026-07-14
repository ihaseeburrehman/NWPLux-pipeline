#!/usr/bin/env python3
"""
Reverse Alzette river line direction (start from upstream)
"""

import geopandas as gpd
from shapely.geometry import LineString
import os

# Paths
river_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_setup/alzette_river.shp'
output_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_setup'

print("="*70)
print("REVERSING ALZETTE RIVER DIRECTION")
print("="*70)

# Load river
print("\n[1/3] Loading alzette_river.shp...")
river = gpd.read_file(river_path)
line = river.geometry.iloc[0]

print(f"   Original geometry: {line.geom_type}")
print(f"   Length: {line.length/1000:.2f} km")
print(f"   Vertices: {len(line.coords)}")

# Get coordinates
coords = list(line.coords)
print(f"\n   Current start point: ({coords[0][0]:.1f}, {coords[0][1]:.1f})")
print(f"   Current end point: ({coords[-1][0]:.1f}, {coords[-1][1]:.1f})")

# Reverse
print("\n[2/3] Reversing direction...")
reversed_coords = coords[::-1]
reversed_line = LineString(reversed_coords)

print(f"   New start point: ({reversed_coords[0][0]:.1f}, {reversed_coords[0][1]:.1f})")
print(f"   New end point: ({reversed_coords[-1][0]:.1f}, {reversed_coords[-1][1]:.1f})")

# Create new GeoDataFrame
reversed_river = gpd.GeoDataFrame(
    {'name': ['Alzette'], 'length_km': [reversed_line.length / 1000]},
    geometry=[reversed_line],
    crs=river.crs
)

# Save - overwrite original
print("\n[3/3] Saving reversed river...")

# Delete old files
for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
    file_path = river_path.replace('.shp', ext)
    if os.path.exists(file_path):
        os.remove(file_path)

reversed_river.to_file(river_path)
print(f"   ✓ Saved (overwritten): {river_path}")

# Verify
verify = gpd.read_file(river_path)
verify_line = verify.geometry.iloc[0]
verify_coords = list(verify_line.coords)

print("\n" + "="*70)
print("VERIFICATION")
print("="*70)
print(f"\nalzette_river.shp (REVERSED):")
print(f"  Geometry: {verify_line.geom_type}")
print(f"  Length: {verify_line.length/1000:.2f} km")
print(f"  Start (U/S): ({verify_coords[0][0]:.1f}, {verify_coords[0][1]:.1f})")
print(f"  End (D/S): ({verify_coords[-1][0]:.1f}, {verify_coords[-1][1]:.1f})")
print(f"  Direction: ✓ UPSTREAM → DOWNSTREAM")
print("="*70)
