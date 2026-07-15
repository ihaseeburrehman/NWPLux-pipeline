#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Extract Alzette river from merged_rivers shapefile
Clip to DEM extent, convert to single LineString
"""

import geopandas as gpd
from shapely.geometry import LineString, box, Point
from shapely.ops import linemerge
import rasterio
import os

# Paths
merged_rivers_path = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/merged_rivers/merged_rivers.shp'
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Alzette_sub_basin_5m_fixed.asc'
output_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_setup'

print("="*70)
print("EXTRACTING ALZETTE FROM MERGED_RIVERS")
print("="*70)

# Load merged rivers
print("\n[1/5] Loading merged_rivers.shp...")
rivers = gpd.read_file(merged_rivers_path)

print(f"   Total features: {len(rivers)}")
print(f"   CRS: {rivers.crs}")
print(f"   Columns: {list(rivers.columns)}")

# Show all features
print(f"\n   Available rivers:")
for col in ['river_name', 'name', 'Name', 'NAME', 'nom', 'NOM']:
    if col in rivers.columns:
        print(f"\n   Column '{col}':")
        for idx, row in rivers.iterrows():
            name = row[col]
            geom = row.geometry
            length = geom.length / 1000 if geom.geom_type == 'LineString' else sum(s.length for s in geom.geoms) / 1000
            print(f"     {idx}: '{name}' - {length:.2f} km ({geom.geom_type})")
        break
    else:
        if col == rivers.columns[-1]:  # Last attempt
            print(f"   ⚠ No name column found. Showing all columns: {list(rivers.columns)}")

# Find Alzette
print("\n[2/5] Searching for Alzette...")
alzette_found = False

for col in ['river_name', 'name', 'Name', 'NAME', 'nom', 'NOM']:
    if col in rivers.columns:
        mask = rivers[col].str.contains('Alzette', case=False, na=False)
        if mask.any():
            alzette = rivers[mask].iloc[0]
            print(f"   ✓ Found Alzette in column '{col}'")
            print(f"   Name: {alzette[col]}")
            print(f"   Original geometry: {alzette.geometry.geom_type}")
            
            if alzette.geometry.geom_type == 'LineString':
                total_length = alzette.geometry.length / 1000
                print(f"   Length: {total_length:.2f} km")
                print(f"   Vertices: {len(alzette.geometry.coords)}")
            else:
                segments = list(alzette.geometry.geoms)
                total_length = sum(s.length for s in segments) / 1000
                print(f"   Segments: {len(segments)}")
                print(f"   Total length: {total_length:.2f} km")
                for i, seg in enumerate(segments, 1):
                    print(f"     Segment {i}: {seg.length/1000:.2f} km, {len(seg.coords)} vertices")
            
            alzette_found = True
            alzette_geom = alzette.geometry
            alzette_crs = rivers.crs
            break

if not alzette_found:
    print("   ERROR: Alzette not found!")
    exit(1)

# Reproject to LUREF if needed
print("\n[3/5] Ensuring LUREF (EPSG:2169)...")
target_crs = 'EPSG:2169'

if alzette_crs != target_crs:
    print(f"   Reprojecting from {alzette_crs} to {target_crs}...")
    alzette_gdf = gpd.GeoDataFrame({'geometry': [alzette_geom]}, crs=alzette_crs)
    alzette_gdf = alzette_gdf.to_crs(target_crs)
    alzette_geom = alzette_gdf.geometry.iloc[0]
else:
    print(f"   Already in {target_crs}")

# Load DEM extent
print("\n[4/5] Clipping to DEM extent...")
with rasterio.open(dem_path) as src:
    dem_bounds = src.bounds
    dem_crs = src.crs if src.crs is not None else 'EPSG:2169'

dem_box = box(dem_bounds.left, dem_bounds.bottom, dem_bounds.right, dem_bounds.top)
dem_gdf = gpd.GeoDataFrame({'geometry': [dem_box]}, crs=target_crs)

# Clip Alzette to DEM
alzette_gdf = gpd.GeoDataFrame({'geometry': [alzette_geom]}, crs=target_crs)
clipped = gpd.clip(alzette_gdf, dem_gdf)

if len(clipped) == 0:
    print("   ERROR: No overlap with DEM!")
    exit(1)

clipped_geom = clipped.geometry.iloc[0]
print(f"   Clipped geometry: {clipped_geom.geom_type}")

# Convert to single LineString by connecting segments at nearest vertices
if clipped_geom.geom_type == 'MultiLineString':
    segments = list(clipped_geom.geoms)
    print(f"   Connecting {len(segments)} segments at nearest vertices...")
    
    # Start with longest segment
    sorted_segments = sorted(segments, key=lambda x: x.length, reverse=True)
    connected_coords = list(sorted_segments[0].coords)
    remaining = sorted_segments[1:]
    
    while remaining:
        # Get current endpoints
        start_pt = Point(connected_coords[0])
        end_pt = Point(connected_coords[-1])
        
        # Find nearest remaining segment
        min_dist = float('inf')
        best_seg = None
        best_reverse = False
        best_at_start = False
        
        for seg in remaining:
            seg_coords = list(seg.coords)
            seg_start = Point(seg_coords[0])
            seg_end = Point(seg_coords[-1])
            
            # Check all 4 connection possibilities
            # Connect to end of current line
            dist_end_to_start = end_pt.distance(seg_start)
            dist_end_to_end = end_pt.distance(seg_end)
            
            # Connect to start of current line
            dist_start_to_start = start_pt.distance(seg_start)
            dist_start_to_end = start_pt.distance(seg_end)
            
            # Find best connection
            if dist_end_to_start < min_dist:
                min_dist = dist_end_to_start
                best_seg = seg
                best_reverse = False
                best_at_start = False
            
            if dist_end_to_end < min_dist:
                min_dist = dist_end_to_end
                best_seg = seg
                best_reverse = True
                best_at_start = False
            
            if dist_start_to_start < min_dist:
                min_dist = dist_start_to_start
                best_seg = seg
                best_reverse = True
                best_at_start = True
            
            if dist_start_to_end < min_dist:
                min_dist = dist_start_to_end
                best_seg = seg
                best_reverse = False
                best_at_start = True
        
        if best_seg is None:
            break
        
        # Add segment with proper orientation
        seg_coords = list(best_seg.coords)
        if best_reverse:
            seg_coords = seg_coords[::-1]
        
        if best_at_start:
            # Prepend to start
            connected_coords = seg_coords + connected_coords
        else:
            # Append to end
            connected_coords = connected_coords + seg_coords
        
        remaining.remove(best_seg)
        print(f"     Connected segment (gap: {min_dist:.1f}m), {len(remaining)} remaining")
    
    final_geom = LineString(connected_coords)
    total_length = sum(s.length for s in segments) / 1000
    print(f"   ✓ Connected into single LineString")
    print(f"   Actual segments length: {total_length:.2f} km")
else:
    final_geom = clipped_geom
    print(f"   Already single LineString")

print(f"   Clipped length: {final_geom.length/1000:.2f} km")
print(f"   Vertices: {len(final_geom.coords)}")

# Densify at 5m
print("\n[5/5] Densifying at 5m intervals...")
total_length = final_geom.length
num_points = int(total_length / 5.0) + 1

densified_coords = []
for i in range(num_points):
    distance = min(i * 5.0, total_length)
    point = final_geom.interpolate(distance)
    densified_coords.append((point.x, point.y))

final_line = LineString(densified_coords)

# Create shapefile
new_river = gpd.GeoDataFrame(
    {'name': ['Alzette'], 'length_km': [final_line.length / 1000]},
    geometry=[final_line],
    crs=target_crs
)

# Save
output_path = os.path.join(output_dir, 'alzette_river.shp')

# Delete old file if exists
for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
    file_path = output_path.replace('.shp', ext)
    if os.path.exists(file_path):
        os.remove(file_path)

new_river.to_file(output_path)

print(f"\n   ✓ Saved: {output_path}")

# Verify
print("\n" + "="*70)
print("VERIFICATION")
print("="*70)
verify = gpd.read_file(output_path)
verify_geom = verify.geometry.iloc[0]

print(f"\nalzette_river.shp:")
print(f"  Name: {verify['name'].iloc[0]}")
print(f"  Geometry type: {verify_geom.geom_type}")
print(f"  CRS: {verify.crs}")
print(f"  Length: {verify['length_km'].iloc[0]:.2f} km")
print(f"  Vertices: {len(verify_geom.coords)}")
print(f"  Vertex spacing: ~{verify_geom.length / len(verify_geom.coords):.1f}m")

print("\n" + "="*70)
print("COMPLETE!")
print("="*70)
print(f"\n✓ alzette_river.shp - Single LineString in LUREF (EPSG:2169)")
print(f"✓ Length: {verify['length_km'].iloc[0]:.2f} km")
print(f"✓ Densified at 5m intervals")
print(f"✓ Clipped to DEM extent")
print("="*70)
