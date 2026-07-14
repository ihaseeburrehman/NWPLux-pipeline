#!/usr/bin/env python3
"""
CORRECTED BRIDGE & STREAM PROCESSING
- Clip to actual DEM data (not just extent)
- Create 80m x 80m bridge polygons at intersection points
- 5m sampling beyond polygon edges
- 3 stream features with length_km attribute
"""

import numpy as np
import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import box, Point, Polygon, shape, MultiPolygon
from scipy.ndimage import gaussian_filter1d
import os
import math

# Paths
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Alzette_sub_basin_5m_fixed.asc'
streams_gpkg = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/river_and_water_courses/cours-deau.gpkg'
official_bridges_poly = '/Users/haseeb.rehman/Downloads/bridges/luxembourg_bridges_shapefiles/luxembourg_bridge_polygons.shp'
output_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing'

print("="*70)
print("CORRECTED BRIDGE & STREAM PROCESSING")
print("="*70)

# =================================================================
# STEP 1: LOAD DEM AND CREATE DATA MASK
# =================================================================
print("\n[1/7] Loading DEM and creating data mask...")
with rasterio.open(dem_path) as src:
    dem = src.read(1).astype(float)
    dem_profile = src.profile.copy()
    dem_transform = src.transform
    dem_bounds = src.bounds
    dem_crs = src.crs if src.crs is not None else 'EPSG:2169'
    nodata = src.nodata
    
    if nodata is not None:
        nodata_mask = (dem == nodata)
        dem[nodata_mask] = np.nan
    else:
        nodata_mask = np.isnan(dem)
    
    # Create valid data mask (1 where data exists, 0 where NoData)
    valid_mask = (~nodata_mask).astype(np.uint8)

print(f"   DEM: {dem.shape}, {dem_transform.a}m resolution")

# Create polygon from valid DEM pixels
print("   Creating DEM data boundary...")
geom_gen = shapes(valid_mask, mask=valid_mask, transform=dem_transform)
geoms = [shape(geom) for geom, val in geom_gen if val == 1]

if len(geoms) > 0:
    from shapely.ops import unary_union
    # Fix any invalid geometries
    geoms_fixed = [g.buffer(0) for g in geoms if g.is_valid]
    dem_data_polygon = unary_union(geoms_fixed)
    # Simplify and fix
    dem_data_polygon = dem_data_polygon.simplify(20, preserve_topology=True).buffer(0)
else:
    # Fallback to bounding box
    dem_data_polygon = box(dem_bounds.left, dem_bounds.bottom, dem_bounds.right, dem_bounds.top)

dem_clip_gdf = gpd.GeoDataFrame({'geometry': [dem_data_polygon]}, crs=dem_crs)
print(f"   ✓ DEM data area created")

# =================================================================
# STEP 2: CLIP STREAMS TO ACTUAL DEM DATA
# =================================================================
print("\n[2/7] Clipping streams to DEM data area...")

layers = ['Primäre Gewässer', 'Sekundäre Gewässer', 'Temporär fliessende Bäche']
stream_types = ['Primary', 'Secondary', 'Temporary']
combined_streams_data = []

for layer_name, stream_type in zip(layers, stream_types):
    print(f"   Loading '{stream_type}'...")
    streams = gpd.read_file(streams_gpkg, layer=layer_name)
    
    if streams.crs != dem_crs:
        streams = streams.to_crs(dem_crs)
    
    # Clip to actual DEM data
    clipped = gpd.clip(streams, dem_clip_gdf)
    
    if len(clipped) == 0:
        continue
    
    # Calculate total length for this type
    total_length_m = sum(
        g.length if g.geom_type == 'LineString' 
        else sum(seg.length for seg in g.geoms)
        for g in clipped.geometry
    )
    
    # Merge all geometries into one feature
    all_geoms = []
    for g in clipped.geometry:
        if g.geom_type == 'LineString':
            all_geoms.append(g)
        elif g.geom_type == 'MultiLineString':
            all_geoms.extend(list(g.geoms))
    
    from shapely.geometry import MultiLineString
    merged_geom = MultiLineString(all_geoms)
    
    combined_streams_data.append({
        'stream_type': stream_type,
        'length_km': total_length_m / 1000,
        'geometry': merged_geom
    })
    
    print(f"     Clipped: {len(clipped)} features, {total_length_m/1000:.2f} km")

# Create combined streams with 3 features
streams_final = gpd.GeoDataFrame(combined_streams_data, crs=dem_crs)
total_km = streams_final['length_km'].sum()

print(f"\n   TOTAL: 3 features, {total_km:.2f} km")

# Save streams
streams_out = os.path.join(output_dir, 'streams_alzette_basin.shp')
streams_final.to_file(streams_out)
print(f"   ✓ Saved: {streams_out}")

# =================================================================
# STEP 3: DETECT BRIDGES FROM DEM (6m threshold)
# =================================================================
print("\n[3/7] Detecting bridges from DEM (6m threshold)...")

# Sample along all streams
sample_interval = 5.0
elevations = []
median_elevations = []
coords = []

for _, stream_row in streams_final.iterrows():
    geom = stream_row.geometry
    
    if geom.geom_type == 'MultiLineString':
        segments = list(geom.geoms)
    else:
        segments = [geom]
    
    for segment in segments:
        seg_length = segment.length
        num_points = int(seg_length / sample_interval)
        
        for i in range(num_points):
            dist = i * sample_interval
            point = segment.interpolate(dist)
            
            col = (point.x - dem_bounds.left) / dem_transform.a
            row = (dem_bounds.top - point.y) / abs(dem_transform.e)
            
            if 0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]:
                z = dem[int(row), int(col)]
                if not np.isnan(z):
                    elevations.append(z)
                    median_elevations.append(z)
                    coords.append((point.x, point.y))

elevations = np.array(elevations)
median_elevations = np.array(median_elevations)

# Detect bridges
smoothed = gaussian_filter1d(median_elevations, sigma=30)
deviations = median_elevations - smoothed

detected_bridge_points = []
i = 0
while i < len(deviations):
    if deviations[i] > 6.0:
        start = i
        while i < len(deviations) and deviations[i] > 6.0:
            i += 1
        center = (start + i) // 2
        detected_bridge_points.append(Point(coords[center]))
    else:
        i += 1

print(f"   Detected {len(detected_bridge_points)} bridge locations from DEM")

# =================================================================
# STEP 4: EXTRACT OFFICIAL BRIDGES INTERSECTING STREAMS
# =================================================================
print("\n[4/7] Extracting official bridge polygons...")

official = gpd.read_file(official_bridges_poly)
if official.crs != dem_crs:
    official = official.to_crs(dem_crs)

# Fix invalid geometries
official['geometry'] = official.geometry.buffer(0)

# Clip official bridges to DEM data
official_clipped = gpd.clip(official, dem_clip_gdf)
print(f"   Official bridges in DEM area: {len(official_clipped)}")

# Create buffer around streams
all_stream_geoms = list(streams_final.geometry)
stream_buffer = unary_union([g.buffer(15) for g in all_stream_geoms])
buffer_gdf = gpd.GeoDataFrame({'geometry': [stream_buffer]}, crs=dem_crs)

# Find intersecting
bridges_on_streams = gpd.sjoin(official_clipped, buffer_gdf, how='inner', predicate='intersects')
bridges_on_streams = bridges_on_streams.drop(columns=['index_right'], errors='ignore')

print(f"   Bridges intersecting streams: {len(bridges_on_streams)}")

# Get centroids of official bridges
official_bridge_points = [geom.centroid for geom in bridges_on_streams.geometry]

# =================================================================
# STEP 5: CREATE BRIDGE POLYGONS (30m×30m for main river, 10m×10m for others)
# =================================================================
print("\n[5/7] Creating bridge polygons (30m main river, 10m others)...")

all_bridge_points = detected_bridge_points + official_bridge_points

# Remove duplicates (within 30m)
unique_points = []
for pt in all_bridge_points:
    is_dup = False
    for kept in unique_points:
        if pt.distance(kept) < 30:
            is_dup = True
            break
    if not is_dup:
        unique_points.append(pt)

print(f"   Unique bridge locations: {len(unique_points)}")

# Load main Alzette river
alzette_river = gpd.read_file(os.path.join(output_dir, 'alzette_river.shp'))
main_river_line = alzette_river.geometry.iloc[0]
main_river_buffer = main_river_line.buffer(20)  # 20m buffer to identify main river bridges

# Create polygons with appropriate sizes
bridge_polygons = []
main_river_count = 0
other_count = 0

for pt in unique_points:
    # Check if bridge is on main Alzette river
    if main_river_buffer.contains(pt):
        # Main river: 30m x 30m
        half = 15.0
        area = 900
        bridge_type = 'main_river'
        main_river_count += 1
    else:
        # Other streams: 10m x 10m  
        half = 5.0
        area = 100
        bridge_type = 'other'
        other_count += 1
    
    poly = box(pt.x - half, pt.y - half, pt.x + half, pt.y + half)
    bridge_polygons.append({
        'geometry': poly,
        'area_m2': area,
        'type': bridge_type
    })

print(f"   Main river bridges (30m×30m): {main_river_count}")
print(f"   Other stream bridges (10m×10m): {other_count}")

bridges_gdf = gpd.GeoDataFrame(bridge_polygons, crs=dem_crs)
bridges_out = os.path.join(output_dir, 'bridge_polygons_alzette_basin.shp')
bridges_gdf.to_file(bridges_out)
print(f"   ✓ Saved: {bridges_out}")

# =================================================================
# STEP 6: CREATE CORRECTED DEM
# =================================================================
print("\n[6/7] Creating corrected DEM...")
print("   Sampling 5m beyond polygon edges (45m from center)")

def get_elevation(point):
    col = (point.x - dem_bounds.left) / dem_transform.a
    row = (dem_bounds.top - point.y) / abs(dem_transform.e)
    if 0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]:
        return dem[int(row), int(col)]
    return np.nan

dem_corrected = dem.copy()
sample_beyond_edge = 5.0  # 5m beyond edge

processed = 0

for idx, bridge in bridges_gdf.iterrows():
    poly = bridge.geometry
    centroid = poly.centroid
    
    # Calculate polygon half-width from geometry bounds
    bounds = poly.bounds
    polygon_half = (bounds[2] - bounds[0]) / 2.0  # Half of polygon width
    total_sample_dist = polygon_half + sample_beyond_edge
    
    # Find closest stream
    min_dist = float('inf')
    closest_stream = None
    proj_dist = 0
    
    for _, stream_row in streams_final.iterrows():
        geom = stream_row.geometry
        
        if geom.geom_type == 'MultiLineString':
            for seg in geom.geoms:
                d = seg.distance(centroid)
                if d < min_dist:
                    min_dist = d
                    closest_stream = seg
                    proj_dist = seg.project(centroid)
        else:
            d = geom.distance(centroid)
            if d < min_dist:
                min_dist = d
                closest_stream = geom
                proj_dist = geom.project(centroid)
    
    if closest_stream is None or min_dist > 50:
        continue
    
    # Sample along centerline
    stream_len = closest_stream.length
    elev_us = np.nan
    elev_ds = np.nan
    
    if proj_dist >= total_sample_dist:
        pt_us = closest_stream.interpolate(proj_dist - total_sample_dist)
        elev_us = get_elevation(pt_us)
    
    if proj_dist <= stream_len - total_sample_dist:
        pt_ds = closest_stream.interpolate(proj_dist + total_sample_dist)
        elev_ds = get_elevation(pt_ds)
    
    # Interpolate
    if not np.isnan(elev_us) and not np.isnan(elev_ds):
        target = (elev_us + elev_ds) / 2.0
    elif not np.isnan(elev_us):
        target = elev_us
    elif not np.isnan(elev_ds):
        target = elev_ds
    else:
        continue
    
    # Lower polygon area
    bounds = poly.bounds
    c0 = max(0, int((bounds[0] - dem_bounds.left) / dem_transform.a))
    c1 = min(dem.shape[1], int((bounds[2] - dem_bounds.left) / dem_transform.a) + 1)
    r0 = max(0, int((dem_bounds.top - bounds[3]) / abs(dem_transform.e)))
    r1 = min(dem.shape[0], int((dem_bounds.top - bounds[1]) / abs(dem_transform.e)) + 1)
    
    for r in range(r0, r1):
        for c in range(c0, c1):
            val = dem_corrected[r, c]
            if not np.isnan(val) and val > target:
                dem_corrected[r, c] = target
    
    processed += 1
    if (idx + 1) % 50 == 0:
        print(f"   Processed {idx + 1}/{len(bridges_gdf)}...")

print(f"   ✓ Processed {processed} bridges")

# Restore NoData
if nodata is not None:
    dem_corrected[nodata_mask] = nodata

# Stats
diff = dem - dem_corrected
pixels = np.sum(diff[~np.isnan(diff)] > 0.01)
max_low = np.nanmax(diff)
volume = np.nansum(diff) * 25

print(f"   Pixels modified: {pixels:,}")
print(f"   Max lowering: {max_low:.1f}m")

# =================================================================
# STEP 7: SAVE DEM
# =================================================================
print("\n[7/7] Saving corrected DEM...")

dem_out = os.path.join(output_dir, 'Alzette_5m_bridges_removed.asc')

dem_profile.update({
    'driver': 'AAIGrid',
    'dtype': rasterio.float32,
    'nodata': nodata if nodata is not None else -9999
})

with rasterio.open(dem_out, 'w', **dem_profile) as dst:
    dst.write(dem_corrected.astype(np.float32), 1)

print(f"   ✓ Saved: {dem_out}")

print("\n" + "="*70)
print("COMPLETE!")
print("="*70)
print(f"\n1. streams_alzette_basin.shp - 3 features, {total_km:.2f} km")
print(f"2. bridge_polygons_alzette_basin.shp - {len(bridges_gdf)} × 80m×80m")
print(f"3. Alzette_5m_bridges_removed.asc - {pixels:,} pixels modified")
print("="*70)
