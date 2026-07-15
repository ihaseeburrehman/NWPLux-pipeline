#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Convert river_merged from MultiLineString to single LineString
with 5m vertex spacing
"""

import geopandas as gpd
from shapely.geometry import LineString
import numpy as np
import os

# Path
river_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_setup/river_merged.shp'
backup_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_setup/river_merged_backup.shp'

print("="*70)
print("CONVERTING RIVER TO SINGLE LINESTRING WITH 5M SPACING")
print("="*70)

# Load river
print("\n[1/4] Loading river...")
river = gpd.read_file(river_path)
geom = river.geometry.iloc[0]

print(f"   Original geometry type: {geom.geom_type}")

# Get all segments
if geom.geom_type == 'MultiLineString':
    segments = list(geom.geoms)
    print(f"   Number of segments: {len(segments)}")
    for i, seg in enumerate(segments, 1):
        print(f"     Segment {i}: {len(seg.coords)} vertices, {seg.length/1000:.3f} km")
else:
    segments = [geom]
    print(f"   Single LineString: {len(geom.coords)} vertices")

# Concatenate all coordinates
print("\n[2/4] Concatenating all segments...")
all_coords = []
for seg in segments:
    all_coords.extend(list(seg.coords))

original_line = LineString(all_coords)
print(f"   Combined: {len(all_coords)} vertices, {original_line.length/1000:.2f} km")

# Densify at 5m intervals
print("\n[3/4] Densifying to 5m intervals...")
densify_interval = 5.0  # meters
total_length = original_line.length
num_points = int(total_length / densify_interval) + 1

densified_coords = []
for i in range(num_points):
    distance = min(i * densify_interval, total_length)
    point = original_line.interpolate(distance)
    densified_coords.append((point.x, point.y))

# Create new LineString
new_line = LineString(densified_coords)

print(f"   New vertices: {len(densified_coords)}")
print(f"   Length: {new_line.length/1000:.2f} km")
print(f"   Geometry type: {new_line.geom_type}")

# Backup original
print("\n[4/4] Saving...")
print(f"   Backing up original to: {os.path.basename(backup_path)}")
river.to_file(backup_path)

# Create new GeoDataFrame
new_river = gpd.GeoDataFrame(
    {'geometry': [new_line]},
    crs=river.crs
)

# Delete old files
for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
    file_path = river_path.replace('.shp', ext)
    if os.path.exists(file_path):
        os.remove(file_path)

# Save new file with same name
new_river.to_file(river_path)

print(f"   ✓ Saved: {river_path}")

# Verify
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)
verify = gpd.read_file(river_path)
verify_geom = verify.geometry.iloc[0]

print(f"\nNew river_merged.shp:")
print(f"  Geometry type: {verify_geom.geom_type}")
print(f"  Is single LineString: {verify_geom.geom_type == 'LineString'}")
print(f"  Vertices: {len(verify_geom.coords)}")
print(f"  Length: {verify_geom.length/1000:.2f} km")
print(f"  Vertex spacing: ~{verify_geom.length / len(verify_geom.coords):.1f}m")

print("\n" + "="*70)
print("COMPLETE!")
print("="*70)
print(f"\n✓ river_merged.shp is now a SINGLE LineString")
print(f"✓ Densified with {len(verify_geom.coords)} vertices at ~5m spacing")
print(f"✓ Original backed up as river_merged_backup.shp")
print("="*70)
