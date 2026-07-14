import geopandas as gpd
import os

# Define paths
river_path = "/Users/haseeb.rehman/Downloads/Alzette_Major_Rivers.shp"
mask_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/bathymetry_processing/Alzette_sub_basin_complete.shp"
output_dir = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/bathymetry_processing/"
output_path = os.path.join(output_dir, "streams_alzette_basin.shp")

print("="*60)
print("CLIPPING RIVERS TO SUB-BASIN EXTENT")
print("="*60)

# Load data
print(f"Loading rivers: {os.path.basename(river_path)}")
rivers = gpd.read_file(river_path)

print(f"Loading mask: {os.path.basename(mask_path)}")
mask = gpd.read_file(mask_path)

# Check CRS and match if necessary
if rivers.crs is None:
    print(f"⚠️ Rivers data has no CRS defined. Since coordinates match mask range, assigning {mask.crs}...")
    rivers.set_crs(mask.crs, inplace=True)

if rivers.crs != mask.crs:
    print(f"CRS mismatch detected. Reprojecting rivers to match mask CRS ({mask.crs})...")
    rivers = rivers.to_crs(mask.crs)

# Perform clip
print("Performing clip operation...")
clipped_rivers = gpd.clip(rivers, mask)

# Save result
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print(f"Saving clipped rivers to: {output_path}")
clipped_rivers.to_file(output_path)

# Print summary
print("\nSuccess!")
print(f"Original segments: {len(rivers)}")
print(f"Clipped segments: {len(clipped_rivers)}")
print("="*60)
