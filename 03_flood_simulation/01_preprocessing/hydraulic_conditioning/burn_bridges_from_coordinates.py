#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Burn bridges into DEM using specific coordinates
- Creates rectangular polygons parallel to river centerline
- Long axis parallel to river, short axis perpendicular
- Uses upstream and downstream elevations for interpolation
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
# Width is perpendicular to river (varies)
# Length is parallel to river (varies)
# Type: 'Alzette_river' or 'streams_bridges'

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
print("BURNING BRIDGES INTO DEM")
print("="*70)

# ===================================================================
# STEP 1: Load river centerline, streams, and DEM
# ===================================================================
print("\n[1/5] Loading river centerline, streams network, and DEM...")

# Load Alzette river centerline
river_gdf = gpd.read_file(river_centerline_path)
river_line = river_gdf.geometry.iloc[0]
river_crs = river_gdf.crs

print(f"   Alzette river length: {river_line.length/1000:.2f} km")

# Load streams network
streams_gdf = gpd.read_file(streams_path)
if streams_gdf.crs != river_crs:
    streams_gdf = streams_gdf.to_crs(river_crs)

# Combine all stream geometries into a list
stream_lines = []
for geom in streams_gdf.geometry:
    if geom.geom_type == 'MultiLineString':
        stream_lines.extend(list(geom.geoms))
    elif geom.geom_type == 'LineString':
        stream_lines.append(geom)

total_stream_length = sum(line.length for line in stream_lines) / 1000
print(f"   Streams network: {len(stream_lines)} segments, {total_stream_length:.2f} km")


# Load DEM
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

print(f"   DEM shape: {dem.shape}, resolution: {dem_transform.a}m")

# ===================================================================
# STEP 2: Create bridge polygons parallel to river
# ===================================================================
print(f"\n[2/5] Creating {len(bridges)} bridge polygons...")

def create_bridge_polygon_along_river(river_line, center_point, width, length):
    """
    Create a polygon that follows the river centerline.
    Width is perpendicular to river (short axis, 15m).
    Length is parallel to river (long axis, follows river curve).
    
    The polygon is created by:
    1. Sampling points along the river for the specified length
    2. Creating perpendicular offsets at each point for the width
    3. Connecting these to form a corridor polygon
    """
    # Project center point onto river
    proj_dist = river_line.project(center_point)
    
    # Calculate upstream and downstream extents
    half_length = length / 2.0
    upstream_dist = max(0, proj_dist - half_length)
    downstream_dist = min(river_line.length, proj_dist + half_length)
    
    # Sample points along the river centerline
    sample_interval = 2.0  # Sample every 2 meters for smooth polygon
    num_samples = max(3, int((downstream_dist - upstream_dist) / sample_interval))
    
    left_points = []
    right_points = []
    half_width = width / 2.0
    
    for i in range(num_samples + 1):
        # Interpolate distance along river
        dist = upstream_dist + (downstream_dist - upstream_dist) * i / num_samples
        center_pt = river_line.interpolate(dist)
        
        # Calculate perpendicular direction at this point
        # Use small offset to get local direction
        delta = 2.0
        dist_before = max(0, dist - delta)
        dist_after = min(river_line.length, dist + delta)
        
        pt_before = river_line.interpolate(dist_before)
        pt_after = river_line.interpolate(dist_after)
        
        # River direction (tangent)
        dx = pt_after.x - pt_before.x
        dy = pt_after.y - pt_before.y
        
        # Normalize
        length_vec = math.sqrt(dx**2 + dy**2)
        if length_vec > 0:
            dx /= length_vec
            dy /= length_vec
        
        # Perpendicular direction (rotate 90° CCW for left, CW for right)
        perp_left_x = -dy
        perp_left_y = dx
        perp_right_x = dy
        perp_right_y = -dx
        
        # Create offset points
        left_pt = Point(center_pt.x + perp_left_x * half_width,
                       center_pt.y + perp_left_y * half_width)
        right_pt = Point(center_pt.x + perp_right_x * half_width,
                        center_pt.y + perp_right_y * half_width)
        
        left_points.append((left_pt.x, left_pt.y))
        right_points.append((right_pt.x, right_pt.y))
    
    # Create polygon: go along left side, then back along right side
    polygon_coords = left_points + list(reversed(right_points))
    polygon = Polygon(polygon_coords)
    
    return polygon


# Find nearest waterway for each bridge and create polygons
bridge_polygons = []
bridge_data = []

for idx, bridge_entry in enumerate(bridges, 1):
    x, y, width, length, bridge_type = bridge_entry
    point = Point(x, y)
    
    # Find nearest waterway based on bridge type
    if bridge_type == 'Alzette_river':
        # Snap to main Alzette river
        nearest_pt = nearest_points(point, river_line)[1]
        distance_to_waterway = point.distance(nearest_pt)
        waterway_line = river_line
        waterway_name = 'Alzette River'
    else:
        # Snap to nearest stream
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
        waterway_name = 'Stream'
    
    # Create polygon that follows the waterway curve
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
    
    area = polygon.area
    print(f"   Bridge {idx} ({bridge_type}): ({x:.1f}, {y:.1f}) → {waterway_name} ({nearest_pt.x:.1f}, {nearest_pt.y:.1f})")
    print(f"      {width}m × {length}m corridor, area: {area:.0f}m², distance: {distance_to_waterway:.1f}m")

# Create GeoDataFrame
bridges_gdf = gpd.GeoDataFrame(bridge_data, crs=river_crs)

# Save shapefile
bridges_gdf.to_file(output_shapefile)
print(f"\n   ✓ Saved bridge polygons: {output_shapefile}")

# ===================================================================
# STEP 3: Sample upstream and downstream elevations
# ===================================================================
print(f"\n[3/5] Sampling upstream/downstream elevations...")

def get_elevation(point, dem, dem_bounds, dem_transform):
    """Get elevation from DEM at given point"""
    col = (point.x - dem_bounds.left) / dem_transform.a
    row = (dem_bounds.top - point.y) / abs(dem_transform.e)
    
    if 0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]:
        z = dem[int(row), int(col)]
        if not np.isnan(z):
            return z
    return np.nan

# For each bridge, sample elevations
sample_distance = 5.0  # Sample 5m beyond polygon edge

for idx, row in bridges_gdf.iterrows():
    polygon = row['geometry']
    center = Point(row['snapped_x'], row['snapped_y'])
    bridge_type = row['bridge_type']
    
    # Get the appropriate waterway for this bridge
    if bridge_type == 'Alzette_river':
        waterway_line = river_line
    else:
        # Find the nearest stream again
        min_dist = float('inf')
        for stream in stream_lines:
            pt = nearest_points(center, stream)[1]
            dist = center.distance(pt)
            if dist < min_dist:
                min_dist = dist
                waterway_line = stream
    
    # Find projection on waterway
    proj_dist = waterway_line.project(center)
    
    # Calculate how far to sample (polygon half-length + 5m)
    half_length = row['length_m'] / 2.0
    sample_dist_total = half_length + sample_distance
    
    # Sample upstream
    upstream_dist = max(0, proj_dist - sample_dist_total)
    pt_upstream = waterway_line.interpolate(upstream_dist)
    elev_upstream = get_elevation(pt_upstream, dem, dem_bounds, dem_transform)
    
    # Sample downstream
    downstream_dist = min(waterway_line.length, proj_dist + sample_dist_total)
    pt_downstream = waterway_line.interpolate(downstream_dist)
    elev_downstream = get_elevation(pt_downstream, dem, dem_bounds, dem_transform)
    
    # Calculate target elevation
    # IMPORTANT: Target must be <= upstream to ensure water can flow through
    if not np.isnan(elev_upstream) and not np.isnan(elev_downstream):
        # Use average but ensure it's not higher than upstream
        avg_elev = (elev_upstream + elev_downstream) / 2.0
        target_elev = min(avg_elev, elev_upstream - 0.1)  # At least 0.1m below upstream
    elif not np.isnan(elev_upstream):
        # Only upstream available: use it with small reduction
        target_elev = elev_upstream - 0.2
    elif not np.isnan(elev_downstream):
        # Only downstream available: use it (risky, but best we can do)
        target_elev = elev_downstream
    else:
        target_elev = np.nan
    
    # Validation check
    if not np.isnan(target_elev) and not np.isnan(elev_upstream):
        if target_elev > elev_upstream:
            print(f"   WARNING: Bridge {row['bridge_id']} target ({target_elev:.2f}m) > upstream ({elev_upstream:.2f}m)!")
            target_elev = elev_upstream - 0.2  # Force it lower
    
    # Store in dataframe
    bridges_gdf.at[idx, 'elev_upstream'] = elev_upstream
    bridges_gdf.at[idx, 'elev_downstream'] = elev_downstream
    bridges_gdf.at[idx, 'target_elev'] = target_elev
    bridges_gdf.at[idx, 'elev_reduction'] = elev_upstream - target_elev if not np.isnan(target_elev) and not np.isnan(elev_upstream) else 0.0
    
    status = "✓" if (np.isnan(elev_upstream) or target_elev <= elev_upstream) else "⚠"
    print(f"   {status} Bridge {row['bridge_id']}: U/S={elev_upstream:.2f}m, D/S={elev_downstream:.2f}m, Target={target_elev:.2f}m (reduction: {elev_upstream - target_elev:.2f}m)")

# ===================================================================
# STEP 4: Burn bridges into DEM
# ===================================================================
print(f"\n[4/5] Burning bridges into DEM...")

dem_burned = dem.copy()
total_pixels_modified = 0

for idx, row in bridges_gdf.iterrows():
    polygon = row['geometry']
    target_elev = row['target_elev']
    
    if np.isnan(target_elev):
        print(f"   WARNING: Bridge {row['bridge_id']} has no valid target elevation, skipping")
        continue
    
    # Get polygon bounds in grid coordinates
    bounds = polygon.bounds  # (minx, miny, maxx, maxy)
    
    c0 = max(0, int((bounds[0] - dem_bounds.left) / dem_transform.a))
    c1 = min(dem.shape[1], int((bounds[2] - dem_bounds.left) / dem_transform.a) + 1)
    r0 = max(0, int((dem_bounds.top - bounds[3]) / abs(dem_transform.e)))
    r1 = min(dem.shape[0], int((dem_bounds.top - bounds[1]) / abs(dem_transform.e)) + 1)
    
    pixels_modified = 0
    
    # Iterate over cells in bounding box
    for r in range(r0, r1):
        for c in range(c0, c1):
            # Get cell center coordinates
            x = dem_bounds.left + (c + 0.5) * dem_transform.a
            y = dem_bounds.top - (r + 0.5) * abs(dem_transform.e)
            cell_point = Point(x, y)
            
            # Check if cell center is inside polygon OR close enough to ensure connectivity
            # Strict .contains() can leave diagonal gaps for narrow polygons on raster grids
            # We use a distance threshold of 0.6 * cell_size (approx 3m for 5m grid)
            # This effectively buffers the selection slightly to ensure 8-way connectivity
            cell_size = dem_transform.a
            dist_to_poly = polygon.distance(cell_point)
            
            if dist_to_poly < (cell_size * 0.6):
                current_elev = dem_burned[r, c]
                
                # Only lower if current elevation is higher
                if not np.isnan(current_elev) and current_elev > target_elev:
                    dem_burned[r, c] = target_elev
                    pixels_modified += 1
    
    total_pixels_modified += pixels_modified
    print(f"   Bridge {row['bridge_id']}: {pixels_modified} pixels modified")

print(f"\n   ✓ Total pixels modified: {total_pixels_modified:,}")

# Calculate statistics
diff = dem - dem_burned
valid_diff = diff[~np.isnan(diff)]
pixels_lowered = np.sum(valid_diff > 0.01)
max_lowering = np.nanmax(diff)
volume_removed = np.nansum(diff) * (dem_transform.a ** 2)  # m³

print(f"   Pixels lowered: {pixels_lowered:,}")
print(f"   Max lowering: {max_lowering:.2f}m")
print(f"   Volume removed: {volume_removed:.1f} m³")

# ===================================================================
# STEP 5: Save burned DEM
# ===================================================================
print(f"\n[5/5] Saving burned DEM...")

# Restore NoData
if nodata is not None:
    dem_burned[nodata_mask] = nodata

# Update profile
dem_profile.update({
    'driver': 'AAIGrid',
    'dtype': rasterio.float32,
    'nodata': nodata if nodata is not None else -9999
})

# Save
with rasterio.open(output_path, 'w', **dem_profile) as dst:
    dst.write(dem_burned.astype(np.float32), 1)

print(f"   ✓ Saved: {output_path}")

print("\n" + "="*70)
print("COMPLETE!")
print("="*70)
print(f"\nOutput files:")
print(f"  1. {output_shapefile}")
print(f"  2. {output_path}")
print(f"\nBridge Summary:")
alzette_count = len([b for b in bridges if b[4] == 'Alzette_river'])
stream_count = len([b for b in bridges if b[4] == 'streams_bridges'])
print(f"  - Alzette River bridges: {alzette_count}")
print(f"  - Stream bridges: {stream_count}")
print(f"  - Total bridges processed: {len(bridges)}")
print(f"  - Total pixels modified: {total_pixels_modified:,}")
print(f"  - Max lowering: {max_lowering:.2f}m")
print(f"  - Volume removed: {volume_removed:.1f} m³")
print("="*70)

# ===================================================================
# VISUALIZATION FOR RESEARCH PAPER
# ===================================================================
print("\n[6/6] Creating publication figure...")

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from pyproj import Transformer
from mpl_toolkits.axes_grid1 import make_axes_locatable

# Select one bridge for visualization (Bridge 6 - stream bridge 10x250m)
example_bridge_idx = 5  # Bridge 6: (69521.7, 66845.4, 10, 200, 'streams_bridges')
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

# Transform extent to degrees (EPSG:2169 -> EPSG:4326)
transformer = Transformer.from_crs("EPSG:2169", "EPSG:4326", always_xy=True)
lon_min, lat_min = transformer.transform(clip_bounds[0], clip_bounds[1])
lon_max, lat_max = transformer.transform(clip_bounds[2], clip_bounds[3])
extent_deg = [lon_min, lon_max, lat_min, lat_max]

# Create cross-section line (perpendicular to river through bridge center)
center_x = bridge_row['snapped_x']
center_y = bridge_row['snapped_y']

# Sample cross-section (perpendicular to river)
cross_section_length = 240  # meters
num_samples = 60
cross_section_dist = np.linspace(-cross_section_length/2, cross_section_length/2, num_samples)

# Get river direction at bridge
if bridge_row['bridge_type'] == 'Alzette_river':
    waterway = river_line
else:
    # Find nearest stream
    min_dist = float('inf')
    for stream in stream_lines:
        pt = nearest_points(Point(center_x, center_y), stream)[1]
        dist = Point(center_x, center_y).distance(pt)
        if dist < min_dist:
            min_dist = dist
            waterway = stream

# Sample LONGITUDINAL profile along stream (240m total, centered on bridge)
longitudinal_length = 240  # meters total (updated to match user's change)
num_long_samples = 120  # 2m spacing
proj_dist = waterway.project(Point(center_x, center_y))

# Calculate start and end distances along stream
start_dist = max(0, proj_dist - longitudinal_length/2)
end_dist = min(waterway.length, proj_dist + longitudinal_length/2)

# Sample elevations along stream centerline
elevs_before_long = []
elevs_after_long = []
distances_long = []
actual_distances = []

for i in range(num_long_samples):
    dist_along = start_dist + (end_dist - start_dist) * i / (num_long_samples - 1)
    point = waterway.interpolate(dist_along)
    
    col = int((point.x - dem_bounds.left) / dem_transform.a)
    row = int((dem_bounds.top - point.y) / abs(dem_transform.e))
    
    if 0 <= row < dem.shape[0] and 0 <= col < dem.shape[1]:
        elev_before = dem[row, col] if not np.isnan(dem[row, col]) else None
        elev_after = dem_burned[row, col] if not np.isnan(dem_burned[row, col]) else None
        
        if elev_before is not None and elev_after is not None:
            elevs_before_long.append(elev_before)
            elevs_after_long.append(elev_after)
            # Distance relative to bridge center
            distances_long.append(dist_along - proj_dist)
            actual_distances.append(dist_along)

# Identify bridge extent on longitudinal profile
bridge_start = -bridge_row['length_m']/2
bridge_end = bridge_row['length_m']/2

# Create publication-quality figure
fig = plt.figure(figsize=(22, 12))  # Wider figure to accommodate spacing
gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.45, height_ratios=[1.1, 1])

# Set style for publication
plt.rcParams['font.size'] = 20
plt.rcParams['font.family'] = 'serif'

# Subplot 1: Before burning (top-left)
ax1 = fig.add_subplot(gs[0, 0])
im1 = ax1.imshow(dem_clip_before, cmap='terrain', vmin=np.nanmin(dem_clip_before), 
                 vmax=np.nanmax(dem_clip_before), origin='upper', extent=extent_deg)
ax1.set_title('(a) DEM Before Bridge Burning', fontweight='bold', fontsize=26)
ax1.set_xlabel('Longitude (°)', fontsize=22)
ax1.set_ylabel('Latitude (°)', fontsize=22)

# Fix scientific notation and offset (+4.951e1)
ax1.ticklabel_format(useOffset=False, style='plain')

# Proportional colorbar that matches axes height
divider1 = make_axes_locatable(ax1)
cax1 = divider1.append_axes("right", size="5%", pad=0.1)
plt.colorbar(im1, cax=cax1, label='Elevation (m)')

# Subplot 2: After burning (top-right)
ax2 = fig.add_subplot(gs[0, 1])
im2 = ax2.imshow(dem_clip_after, cmap='terrain', vmin=np.nanmin(dem_clip_before),
                 vmax=np.nanmax(dem_clip_before), origin='upper', extent=extent_deg)
ax2.set_title('(b) DEM After Bridge Burning', fontweight='bold', fontsize=26)
ax2.set_xlabel('Longitude (°)', fontsize=22)
ax2.set_ylabel('Latitude (°)', fontsize=22)

# Fix scientific notation and offset
ax2.ticklabel_format(useOffset=False, style='plain')

# Proportional colorbar that matches axes height
divider2 = make_axes_locatable(ax2)
cax2 = divider2.append_axes("right", size="5%", pad=0.1)
plt.colorbar(im2, cax=cax2, label='Elevation (m)')

# Subplot 3: Longitudinal profile before (bottom-left)
ax3 = fig.add_subplot(gs[1, 0])
ax3.plot(distances_long, elevs_before_long, 'k-', linewidth=2.5, label='Original DEM')
ax3.axvspan(bridge_start, bridge_end, alpha=0.2, color='red', label='Bridge Extent')
ax3.axvline(0, color='gray', linestyle='--', linewidth=1.5, alpha=0.5, label='Bridge Center')
ax3.set_title('(c) Longitudinal Profile Before', fontweight='bold', fontsize=26)
ax3.set_xlabel('Distance Along Stream (m)', fontsize=22)
ax3.set_ylabel('Elevation (m)', fontsize=22)
ax3.grid(True, alpha=0.3, linestyle=':')
ax3.legend(fontsize=16, loc='upper right')
ax3.set_xlim([min(distances_long), max(distances_long)])

# Subplot 4: Longitudinal profile After (bottom-right)
ax4 = fig.add_subplot(gs[1, 1])
ax4.plot(distances_long, elevs_before_long, 'k--', linewidth=2, alpha=0.4, label='Before')
ax4.plot(distances_long, elevs_after_long, 'b-', linewidth=3, label='After Burning')
ax4.axvspan(bridge_start, bridge_end, alpha=0.2, color='red', label='Bridge Extent')
ax4.axvline(0, color='gray', linestyle='--', linewidth=1.5, alpha=0.5)
ax4.set_title('(d) Longitudinal Profile After', fontweight='bold', fontsize=26)
ax4.set_xlabel('Distance Along Stream (m)', fontsize=22)
ax4.set_ylabel('Elevation (m)', fontsize=22)
ax4.grid(True, alpha=0.3, linestyle=':')
ax4.legend(fontsize=16, loc='upper right')
ax4.set_xlim([min(distances_long), max(distances_long)])

# Save figure (PNG only)
plots_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/plots'
os.makedirs(plots_dir, exist_ok=True)
output_fig_png = os.path.join(plots_dir, 'bridge_burning_comparison.png')
plt.savefig(output_fig_png, dpi=600, bbox_inches='tight')
plt.close()

print(f"   ✓ Publication figure saved:")
print(f"      PNG: {output_fig_png}")



