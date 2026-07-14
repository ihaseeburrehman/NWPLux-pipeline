#!/usr/bin/env python3
"""
Burn bridges into DEM using specific coordinates - Clean Image Output
- Copy of burn_bridges_from_coordinates.py
- Generates a clean output comparison image with ONLY (a) and (b) pictures, without any text, labels, or lat-long.
"""

import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point, Polygon, box
from shapely.affinity import rotate
from shapely.ops import nearest_points
import math
import os

# ===================================================================
# INPUT DATA
# ===================================================================

# Bridge locations: (X, Y, width_m, length_m, type)
bridges = [
    # Alzette River Bridges
    (76112.0, 65743.972, 15, 100, 'Alzette_river'),
    (76855.997, 85843.554, 15, 100, 'Alzette_river'),
    (68965.316, 64357.473, 15, 350, 'Alzette_river'),
    (67440.799, 63764.665, 15, 150, 'Alzette_river'),
    (67808.556, 63804.021, 15, 200, 'Alzette_river'),
    
    # Stream Bridges
    (69521.7, 66845.4, 10, 200, 'streams_bridges'),
    (76117.5, 65720.3, 5, 70, 'streams_bridges'),
    (74552.5, 62713.3, 5, 350, 'streams_bridges'),
    (74097.0, 72442.0, 5, 350, 'streams_bridges'),
    (76197.2, 73519.3, 5, 150, 'streams_bridges'),
    (74146.2, 72460.9, 5, 300, 'streams_bridges'),
    (73923.0, 74245.15, 5, 30, 'streams_bridges'),
    (76203.1, 65408.4, 5, 70, 'streams_bridges'),
    (74572.342, 64879.053, 5, 30, 'streams_bridges'),
    (74405.0, 65111.6, 5, 30, 'streams_bridges'),
    (76046.0, 66607.7, 5, 100, 'streams_bridges'),
    (78519.8, 69048.7, 5, 220, 'streams_bridges'),
    (78621.6, 69103.02, 5, 180, 'streams_bridges'),
    (78775.0, 69131.0, 5, 50, 'streams_bridges'),
    (78904.8, 69170.6, 50, 50, 'streams_bridges'),
    (79100.6, 69223.6, 5, 50, 'streams_bridges'),
    (80792.5, 69518.3, 5, 30, 'streams_bridges'),
    (79388.8, 70928.8, 5, 100, 'streams_bridges'),
    (77691, 72181, 10, 700, 'streams_bridges'),
    (75839, 66869, 5, 150, 'streams_bridges'),
    (75298.64, 67923.74, 5, 100, 'streams_bridges'),
    (74048.7, 65055.5, 5, 30, 'streams_bridges'),
    (73290.5,64920.5, 5, 30,'streams_bridges'),
]

# File paths
river_centerline_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/pre_processing/alzette_river.shp'
streams_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/pre_processing/streams_alzette_basin.shp'
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/pre_processing/Alzette_5m_bathymetery.asc'
output_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/ready_data_for simulation/Alzette_sub_basin_bridge_burned.asc'
output_shapefile = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/pre_processing/bridge_polygons_burned.shp'

print("="*70)
print("BURNING BRIDGES INTO DEM - CLEAN VISUALIZATION")
print("="*70)

# ===================================================================
# STEP 1: Load river centerline, streams, and DEM
# ===================================================================
print("\n[1/5] Loading river centerline, streams network, and DEM...")
river_gdf = gpd.read_file(river_centerline_path)
river_line = river_gdf.geometry.iloc[0]
river_crs = river_gdf.crs

streams_gdf = gpd.read_file(streams_path)
if streams_gdf.crs != river_crs:
    streams_gdf = streams_gdf.to_crs(river_crs)

stream_lines = []
for geom in streams_gdf.geometry:
    if geom.geom_type == 'MultiLineString':
        stream_lines.extend(list(geom.geoms))
    elif geom.geom_type == 'LineString':
        stream_lines.append(geom)

with rasterio.open(dem_path) as src:
    dem = src.read(1).astype(float)
    dem_profile = src.profile.copy()
    dem_transform = src.transform
    dem_bounds = src.bounds
    nodata = src.nodata
    
    if nodata is not None:
        nodata_mask = (dem == nodata)
        dem[nodata_mask] = np.nan
    else:
        nodata_mask = np.isnan(dem)

# ===================================================================
# STEP 2: Create bridge polygons parallel to river
# ===================================================================
print(f"\n[2/5] Creating {len(bridges)} bridge polygons...")

def create_bridge_polygon_along_river(river_line, center_point, width, length):
    proj_dist = river_line.project(center_point)
    half_length = length / 2.0
    upstream_dist = max(0, proj_dist - half_length)
    downstream_dist = min(river_line.length, proj_dist + half_length)
    
    sample_interval = 2.0
    num_samples = max(3, int((downstream_dist - upstream_dist) / sample_interval))
    
    left_points = []
    right_points = []
    half_width = width / 2.0
    
    for i in range(num_samples + 1):
        dist = upstream_dist + (downstream_dist - upstream_dist) * i / num_samples
        center_pt = river_line.interpolate(dist)
        
        delta = 2.0
        dist_before = max(0, dist - delta)
        dist_after = min(river_line.length, dist + delta)
        
        pt_before = river_line.interpolate(dist_before)
        pt_after = river_line.interpolate(dist_after)
        
        dx = pt_after.x - pt_before.x
        dy = pt_after.y - pt_before.y
        
        length_vec = math.sqrt(dx**2 + dy**2)
        if length_vec > 0:
            dx /= length_vec
            dy /= length_vec
        
        perp_left_x = -dy
        perp_left_y = dx
        perp_right_x = dy
        perp_right_y = -dx
        
        left_pt = Point(center_pt.x + perp_left_x * half_width,
                       center_pt.y + perp_left_y * half_width)
        right_pt = Point(center_pt.x + perp_right_x * half_width,
                        center_pt.y + perp_right_y * half_width)
        
        left_points.append((left_pt.x, left_pt.y))
        right_points.append((right_pt.x, right_pt.y))
    
    polygon_coords = left_points + list(reversed(right_points))
    polygon = Polygon(polygon_coords)
    return polygon

bridge_polygons = []
bridge_data = []

for idx, bridge_entry in enumerate(bridges, 1):
    x, y, width, length, bridge_type = bridge_entry
    point = Point(x, y)
    
    if bridge_type == 'Alzette_river':
        nearest_pt = nearest_points(point, river_line)[1]
        distance_to_waterway = point.distance(nearest_pt)
        waterway_line = river_line
    else:
        min_dist = float('inf')
        nearest_stream = None
        nearest_pt_on_stream = None
        
        for stream in stream_lines:
            pt = nearest_points(point, stream)[1]
            dist = point.distance(pt)
            if dist < min_dist:
                min_dist = dist
                nearest_stream = stream
                nearest_pt_on_stream = pt
        
        nearest_pt = nearest_pt_on_stream
        distance_to_waterway = min_dist
        waterway_line = nearest_stream
    
    polygon = create_bridge_polygon_along_river(waterway_line, nearest_pt, width, length)
    bridge_polygons.append(polygon)
    bridge_data.append({
        'bridge_id': idx,
        'bridge_type': bridge_type,
        'orig_x': x,
        'orig_y': y,
        'snapped_x': nearest_pt.x,
        'snapped_y': nearest_pt.y,
        'width_m': width,
        'length_m': length,
        'dist_to_waterway_m': distance_to_waterway,
        'geometry': polygon
    })

bridges_gdf = gpd.GeoDataFrame(bridge_data, crs=river_crs)

# ===================================================================
# STEP 3: Sample upstream and downstream elevations
# ===================================================================
print(f"\n[3/5] Sampling upstream/downstream elevations...")

def get_elevation(point, dem, dem_bounds, dem_transform):
    col = (point.x - dem_bounds.left) / dem_transform.a
    row = (dem_bounds.top - point.y) / abs(dem_transform.e)
    
    if 0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]:
        z = dem[int(row), int(col)]
        if not np.isnan(z):
            return z
    return np.nan

sample_distance = 5.0

for idx, row in bridges_gdf.iterrows():
    polygon = row['geometry']
    center = Point(row['snapped_x'], row['snapped_y'])
    bridge_type = row['bridge_type']
    
    if bridge_type == 'Alzette_river':
        waterway_line = river_line
    else:
        min_dist = float('inf')
        for stream in stream_lines:
            pt = nearest_points(center, stream)[1]
            dist = center.distance(pt)
            if dist < min_dist:
                min_dist = dist
                waterway_line = stream
    
    proj_dist = waterway_line.project(center)
    half_length = row['length_m'] / 2.0
    sample_dist_total = half_length + sample_distance
    
    upstream_dist = max(0, proj_dist - sample_dist_total)
    pt_upstream = waterway_line.interpolate(upstream_dist)
    elev_upstream = get_elevation(pt_upstream, dem, dem_bounds, dem_transform)
    
    downstream_dist = min(waterway_line.length, proj_dist + sample_dist_total)
    pt_downstream = waterway_line.interpolate(downstream_dist)
    elev_downstream = get_elevation(pt_downstream, dem, dem_bounds, dem_transform)
    
    if not np.isnan(elev_upstream) and not np.isnan(elev_downstream):
        avg_elev = (elev_upstream + elev_downstream) / 2.0
        target_elev = min(avg_elev, elev_upstream - 0.1)
    elif not np.isnan(elev_upstream):
        target_elev = elev_upstream - 0.2
    elif not np.isnan(elev_downstream):
        target_elev = elev_downstream
    else:
        target_elev = np.nan
    
    if not np.isnan(target_elev) and not np.isnan(elev_upstream):
        if target_elev > elev_upstream:
            target_elev = elev_upstream - 0.2
    
    bridges_gdf.at[idx, 'elev_upstream'] = elev_upstream
    bridges_gdf.at[idx, 'elev_downstream'] = elev_downstream
    bridges_gdf.at[idx, 'target_elev'] = target_elev
    bridges_gdf.at[idx, 'elev_reduction'] = elev_upstream - target_elev if not np.isnan(target_elev) and not np.isnan(elev_upstream) else 0.0

# ===================================================================
# STEP 4: Burn bridges into DEM
# ===================================================================
print(f"\n[4/5] Burning bridges into DEM...")
dem_burned = dem.copy()

for idx, row in bridges_gdf.iterrows():
    polygon = row['geometry']
    target_elev = row['target_elev']
    
    if np.isnan(target_elev):
        continue
    
    bounds = polygon.bounds
    c0 = max(0, int((bounds[0] - dem_bounds.left) / dem_transform.a))
    c1 = min(dem.shape[1], int((bounds[2] - dem_bounds.left) / dem_transform.a) + 1)
    r0 = max(0, int((dem_bounds.top - bounds[3]) / abs(dem_transform.e)))
    r1 = min(dem.shape[0], int((dem_bounds.top - bounds[1]) / abs(dem_transform.e)) + 1)
    
    for r in range(r0, r1):
        for c in range(c0, c1):
            x = dem_bounds.left + (c + 0.5) * dem_transform.a
            y = dem_bounds.top - (r + 0.5) * abs(dem_transform.e)
            cell_point = Point(x, y)
            
            cell_size = dem_transform.a
            dist_to_poly = polygon.distance(cell_point)
            
            if dist_to_poly < (cell_size * 0.6):
                current_elev = dem_burned[r, c]
                if not np.isnan(current_elev) and current_elev > target_elev:
                    dem_burned[r, c] = target_elev

# ===================================================================
# STEP 5: Save burned DEM
# ===================================================================
print(f"\n[5/5] Saving burned DEM...")
if nodata is not None:
    dem_burned[nodata_mask] = nodata

dem_profile.update({
    'driver': 'AAIGrid',
    'dtype': rasterio.float32,
    'nodata': nodata if nodata is not None else -9999
})

with rasterio.open(output_path, 'w', **dem_profile) as dst:
    dst.write(dem_burned.astype(np.float32), 1)

# ===================================================================
# VISUALIZATION - CLEAN IMAGE OUTPUT (A AND B ONLY, NO TEXT/AXES)
# ===================================================================
print("\n[6/6] Creating clean comparison figure (no labels, no text, a & b side-by-side)...")

import matplotlib.pyplot as plt

# Select one bridge for visualization (Bridge 6 - stream bridge 10x200m)
example_bridge_idx = 5  
bridge_row = bridges_gdf.iloc[example_bridge_idx]
bridge_polygon = bridge_row['geometry']
bridge_bounds = bridge_polygon.bounds

# Add buffer around bridge for context
buffer_m = 200
clip_bounds = (
    bridge_bounds[0] - buffer_m,
    bridge_bounds[1] - buffer_m,
    bridge_bounds[2] + buffer_m,
    bridge_bounds[3] + buffer_m
)

# Convert bounds to pixel coordinates
c_min = int((clip_bounds[0] - dem_bounds.left) / dem_transform.a)
c_max = int((clip_bounds[2] - dem_bounds.left) / dem_transform.a)
r_min = int((dem_bounds.top - clip_bounds[3]) / abs(dem_transform.e))
r_max = int((dem_bounds.top - clip_bounds[1]) / abs(dem_transform.e))

# Clip DEMs
dem_clip_before = dem[r_min:r_max, c_min:c_max]
dem_clip_after = dem_burned[r_min:r_max, c_min:c_max]

# Create high-quality clean figure containing side-by-side plots (a and b)
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

# Subplot 1: Before burning (left side)
ax1.imshow(dem_clip_before, cmap='terrain', vmin=np.nanmin(dem_clip_before), 
           vmax=np.nanmax(dem_clip_before), origin='upper')
ax1.axis('off')  # Turn off all axis lines, ticks, labels, and text

# Subplot 2: After burning (right side)
ax2.imshow(dem_clip_after, cmap='terrain', vmin=np.nanmin(dem_clip_before),
           vmax=np.nanmax(dem_clip_before), origin='upper')
ax2.axis('off')  # Turn off all axis lines, ticks, labels, and text

# Save clean comparison plot in the plots directory
plots_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/plots'
os.makedirs(plots_dir, exist_ok=True)
output_fig_png = os.path.join(plots_dir, 'bridge_burning_comparison_clean.png')

# Save without margins, boundaries, or padding
plt.savefig(output_fig_png, dpi=600, bbox_inches='tight', pad_inches=0, facecolor='white')
plt.close()

print(f"   ✓ Clean comparison figure successfully saved to:")
print(f"      {output_fig_png}")
