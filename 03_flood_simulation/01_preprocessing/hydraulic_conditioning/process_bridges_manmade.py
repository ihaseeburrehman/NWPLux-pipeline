#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Process bridges and man-made objects for bathymetry analysis
"""

import os
import numpy as np
import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape, Point
from shapely.ops import unary_union
import matplotlib.pyplot as plt

# Paths
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Alzette_sub_basin_5m_2024.asc'
dem_corrected = dem_path  # Same file
manmade_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/man_made_objects_on_rivers.shp/Querbauwerke 2021.shp'
bridges_path = '/Users/haseeb.rehman/Downloads/bridges/luxembourg_bridges_shapefiles/luxembourg_bridge_polygons.shp'
alzette_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/alzette_river.shp'
streams_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/streams_alzette_basin.shp'
output_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing'

# Delete old bathymetery DEM
import os
old_dem = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/Alzette_5m_bathymetery.asc'
if os.path.exists(old_dem):
    os.remove(old_dem)
    print(f"✓ Deleted old bathymetery DEM")

print("="*70)
print("PROCESSING BRIDGES AND MAN-MADE OBJECTS")
print("="*70)

# ===================================================================
# STEP 1: Get valid DEM extent (no NoData)
# ===================================================================
print("\n[1/5] Loading DEM and creating valid data boundary...")
with rasterio.open(dem_path) as src:
    dem = src.read(1).astype(float)
    transform = src.transform
    bounds = src.bounds
    nodata = src.nodata
    crs = src.crs if src.crs is not None else 'EPSG:2169'
    
    if nodata is not None:
        valid_mask = (dem != nodata).astype(np.uint8)
    else:
        valid_mask = (~np.isnan(dem)).astype(np.uint8)

# Create polygon from valid DEM pixels
geom_gen = shapes(valid_mask, mask=valid_mask, transform=transform)
geoms = [shape(geom) for geom, val in geom_gen if val == 1]

if len(geoms) > 0:
    geoms_fixed = [g.buffer(0) for g in geoms if g.is_valid]
    dem_data_polygon = unary_union(geoms_fixed)
    dem_data_polygon = dem_data_polygon.simplify(20, preserve_topology=True).buffer(0)
else:
    from shapely.geometry import box
    dem_data_polygon = box(bounds.left, bounds.bottom, bounds.right, bounds.top)

dem_clip_gdf = gpd.GeoDataFrame({'geometry': [dem_data_polygon]}, crs=crs)
print(f"   ✓ Valid DEM area created")

# ===================================================================
# STEP 2: Clip man-made objects
# ===================================================================
print("\n[2/5] Clipping man-made objects...")
manmade = gpd.read_file(manmade_path)
if manmade.crs != crs:
    manmade = manmade.to_crs(crs)

manmade_clipped = gpd.clip(manmade, dem_clip_gdf)
print(f"   Original: {len(manmade)} features")
print(f"   Clipped: {len(manmade_clipped)} features")

# Save
manmade_out = os.path.join(output_dir, 'man_made_objects.shp')
manmade_clipped.to_file(manmade_out)
print(f"   ✓ Saved: {manmade_out}")

# ===================================================================
# STEP 3: Clip bridges and filter to streams
# ===================================================================
print("\n[3/5] Processing bridges...")
bridges = gpd.read_file(bridges_path)
if bridges.crs != crs:
    bridges = bridges.to_crs(crs)

# Fix geometries
bridges['geometry'] = bridges.geometry.buffer(0)

# Clip to valid DEM
bridges_clipped = gpd.clip(bridges, dem_clip_gdf)
print(f"   Original: {len(bridges)} features")
print(f"   Clipped to DEM: {len(bridges_clipped)} features")

# Load streams and river
alzette = gpd.read_file(alzette_path)
streams = gpd.read_file(streams_path)

# Combine all waterways
all_waterways = []
all_waterways.append(alzette.geometry.iloc[0])
for geom in streams.geometry:
    all_waterways.append(geom)

# Create buffer around waterways
waterway_buffer = unary_union([g.buffer(15) for g in all_waterways])
buffer_gdf = gpd.GeoDataFrame({'geometry': [waterway_buffer]}, crs=crs)

# Filter bridges that intersect waterways
bridges_on_water = gpd.sjoin(bridges_clipped, buffer_gdf, how='inner', predicate='intersects')
bridges_on_water = bridges_on_water.drop(columns=['index_right'], errors='ignore')

print(f"   Bridges on streams/river: {len(bridges_on_water)} features")

# Save
bridges_out = os.path.join(output_dir, 'bridges_on_waterways.shp')
bridges_on_water.to_file(bridges_out)
print(f"   ✓ Saved: {bridges_out}")

# ===================================================================
# STEP 4: Extract man-made objects on Alzette river
# ===================================================================
print("\n[4/5] Extracting man-made objects on Alzette river...")
alzette_buffer = alzette.geometry.buffer(20).iloc[0]
alzette_buffer_gdf = gpd.GeoDataFrame({'geometry': [alzette_buffer]}, crs=crs)

manmade_on_alzette = gpd.sjoin(manmade_clipped, alzette_buffer_gdf, how='inner', predicate='intersects')
manmade_on_alzette = manmade_on_alzette.drop(columns=['index_right'], errors='ignore')

print(f"   Man-made objects on Alzette: {len(manmade_on_alzette)} features")

# Get distance along river for each object
alzette_line = alzette.geometry.iloc[0]
distances = []
for geom in manmade_on_alzette.geometry:
    if geom.geom_type == 'Point':
        dist = alzette_line.project(geom)
    else:
        dist = alzette_line.project(geom.centroid)
    distances.append(dist / 1000)  # Convert to km

manmade_on_alzette['dist_km'] = distances

print(f"   Distance range: {min(distances):.2f} - {max(distances):.2f} km")

# ===================================================================
# STEP 5: Create profile plot with man-made objects
# ===================================================================
print("\n[5/5] Creating profile plot...")

# Sample profile
def sample_profile(dem_path, river_line):
    with rasterio.open(dem_path) as src:
        dem_data = src.read(1).astype(float)
        transform = src.transform
        bounds = src.bounds
        if src.nodata is not None:
            dem_data[dem_data == src.nodata] = np.nan
    
    elevs = []
    dists = []
    
    for dist_m in range(0, int(river_line.length) + 1, 5):
        pt = river_line.interpolate(dist_m)
        col = int((pt.x - bounds.left) / transform.a)
        row = int((bounds.top - pt.y) / abs(transform.e))
        
        if 0 <= row < dem_data.shape[0] and 0 <= col < dem_data.shape[1]:
            z = dem_data[row, col]
            if not np.isnan(z):
                elevs.append(z)
                dists.append(dist_m / 1000)
    
    return np.array(dists), np.array(elevs)

dist_orig, elev_orig = sample_profile(dem_path, alzette_line)
dist_corr, elev_corr = sample_profile(dem_corrected, alzette_line)

# Plot
fig, ax = plt.subplots(figsize=(16, 6))

ax.plot(dist_orig, elev_orig, color='gray', linewidth=1.8, 
        label='Before correction', alpha=0.7, linestyle='--')
ax.plot(dist_corr, elev_corr, color='#1E88E5', linewidth=2.2,
        label='After correction', alpha=0.95)
ax.fill_between(dist_corr, elev_corr, np.min(elev_corr), 
                alpha=0.15, color='#1E88E5')

# Mark man-made objects
if len(manmade_on_alzette) > 0:
    for idx, obj in manmade_on_alzette.iterrows():
        dist_km = obj['dist_km']
        # Find closest elevation
        closest_idx = np.argmin(np.abs(dist_corr - dist_km))
        if closest_idx < len(elev_corr):
            elev = elev_corr[closest_idx]
            ax.plot(dist_km, elev, 'ro', markersize=6, zorder=10)
    
    ax.plot([], [], 'ro', markersize=6, label=f'Man-made objects ({len(manmade_on_alzette)})')

ax.set_xlabel('Distance from upstream (km)', fontsize=12)
ax.set_ylabel('Elevation (m)', fontsize=12)
ax.set_title('Alzette River Profile with Man-Made Objects', fontsize=14, fontweight='bold')
ax.set_xlim(0, max(dist_corr))
ax.set_ylim(210, 315)
ax.grid(True, alpha=0.4, linestyle=':', linewidth=0.8, color='gray')
ax.set_axisbelow(True)
ax.legend(loc='upper right', fontsize=11)

plt.tight_layout()
plot_path = os.path.join(output_dir, 'profile_with_manmade_objects.png')
plt.savefig(plot_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"   ✓ Saved: {plot_path}")

# ===================================================================
# CLEANUP
# ===================================================================
print("\n[6/6] Cleaning up unnecessary files...")

# Files to keep
keep_files = {
    'bridges_on_waterways.shp', 'bridges_on_waterways.shx', 'bridges_on_waterways.dbf', 
    'bridges_on_waterways.prj', 'bridges_on_waterways.cpg',
    'man_made_objects.shp', 'man_made_objects.shx', 'man_made_objects.dbf', 
    'man_made_objects.prj', 'man_made_objects.cpg',
    'streams_alzette_basin.shp', 'streams_alzette_basin.shx', 'streams_alzette_basin.dbf', 
    'streams_alzette_basin.prj', 'streams_alzette_basin.cpg',
    'alzette_river.shp', 'alzette_river.shx', 'alzette_river.dbf', 
    'alzette_river.prj', 'alzette_river.cpg', 'alzette_river.qmd',
    'profile_with_manmade_objects.png'
}

# Delete other files
deleted = 0
for item in os.listdir(output_dir):
    if item.startswith('.'):
        continue
    item_path = os.path.join(output_dir, item)
    if os.path.isfile(item_path) and item not in keep_files:
        try:
            os.remove(item_path)
            deleted += 1
        except Exception as e:
            print(f"  Could not delete {item}: {e}")

print(f"   Deleted {deleted} unnecessary files")

print("\n" + "="*70)
print("COMPLETE!")
print("="*70)
print(f"\nFinal files in bathymetry_processing:")
print(f"  - bridges_on_waterways.shp ({len(bridges_on_water)} bridges)")
print(f"  - man_made_objects.shp ({len(manmade_clipped)} objects)")
print(f"  - Man-made on Alzette: {len(manmade_on_alzette)} objects")
print(f"  - streams_alzette_basin.shp")
print(f"  - alzette_river.shp")
print(f"  - Alzette_5m_FINAL.asc")
print(f"  - profile_with_manmade_objects.png")
print("="*70)
