# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import os
import numpy as np
import rasterio
from rasterio.merge import merge
from rasterio.transform import from_origin
from itertools import product
import requests
import warnings
import logging

# Suppress PROJ-related warnings
warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*PROJ.*")
logging.getLogger('rasterio').setLevel(logging.ERROR)

# Define spatial extent
lon_min, lon_max = -2, 14
lat_min, lat_max = 44, 55

# Define where your tiles are stored
tile_dir = "/Users/haseeb.rehman/Documents/SRTM_DEM_for_study_area/minio_srtm"
output_path = os.path.join(tile_dir, "merged_with_ocean.tif")
base_url = "https://opentopography.s3.sdsc.edu/raster/SRTM_GL1/SRTM_GL1_srtm"

# Ensure tile directory exists
os.makedirs(tile_dir, exist_ok=True)

# Step 1: Extract CRS and profile from a valid reference tile
ref_tile = os.path.join(tile_dir, "N50E005.tif")
if not os.path.exists(ref_tile):
    ref_url = f"{base_url}/N50E005.hgt"
    print(f"Downloading reference tile: {ref_url}")
    response = requests.get(ref_url)
    with open(ref_tile, 'wb') as f:
        f.write(response.content)

with rasterio.open(ref_tile) as ref:
    ref_crs = ref.crs
    ref_dtype = ref.dtypes[0]
    tile_size = ref.height
    ref_transform = ref.transform
    ref_profile = ref.profile.copy()

# Step 2: Build list of all required tiles in extent
tile_names = []
for lat in range(lat_min, lat_max + 1):
    for lon in range(lon_min, lon_max + 1):
        lat_prefix = "N" if lat >= 0 else "S"
        lon_prefix = "E" if lon >= 0 else "W"
        tile_name = f"{lat_prefix}{abs(lat):02d}{lon_prefix}{abs(lon):03d}"
        tile_names.append(tile_name)
print(f"Expected tiles ({len(tile_names)}): {tile_names}")

# Step 3: Download or create dummy tiles
for tile_name in tile_names:
    filename = f"{tile_name}.tif"
    full_path = os.path.join(tile_dir, filename)

    if not os.path.exists(full_path):
        # Try downloading from OpenTopography
        hgt_url = f"{base_url}/{tile_name}.hgt"
        print(f"Attempting to download: {hgt_url}")
        response = requests.get(hgt_url)
        
        if response.status_code == 200:
            hgt_path = os.path.join(tile_dir, f"{tile_name}.hgt")
            with open(hgt_path, 'wb') as f:
                f.write(response.content)
            # Convert HGT to TIF
            try:
                with rasterio.open(hgt_path) as src:
                    data = src.read()
                    profile = ref_profile.copy()
                    profile.update({
                        'height': src.height,
                        'width': src.width,
                        'transform': src.transform,
                        'crs': ref_crs
                    })
                    with rasterio.open(full_path, 'w', **profile) as dst:
                        dst.write(data)
                os.remove(hgt_path)
                print(f"Downloaded and converted: {filename}")
            except Exception as e:
                print(f"Failed to process {tile_name}.hgt: {e}")
                os.remove(hgt_path) if os.path.exists(hgt_path) else None
                # Create dummy tile if HGT fails
                print(f"🌊 Creating synthetic ocean tile: {filename}")
                lat = int(tile_name[1:3])
                lon = int(tile_name[4:7])
                if tile_name.startswith("S"):
                    lat = -lat
                if tile_name[3] == "W":
                    lon = -lon

                transform = from_origin(lon, lat + 1, 1 / 3600, 1 / 3600)
                profile = ref_profile.copy()
                profile.update({
                    'height': tile_size,
                    'width': tile_size,
                    'count': 1,
                    'dtype': ref_dtype,
                    'crs': ref_crs,
                    'transform': transform,
                    'nodata': -32768,
                    'compress': 'lzw'
                })

                with rasterio.open(full_path, 'w', **profile) as dst:
                    data = np.zeros((1, tile_size, tile_size), dtype=ref_dtype)
                    dst.write(data)
        else:
            # Create dummy ocean tile with elevation 0
            print(f"🌊 Creating synthetic ocean tile: {filename}")
            lat = int(tile_name[1:3])
            lon = int(tile_name[4:7])
            if tile_name.startswith("S"):
                lat = -lat
            if tile_name[3] == "W":
                lon = -lon

            transform = from_origin(lon, lat + 1, 1 / 3600, 1 / 3600)
            profile = ref_profile.copy()
            profile.update({
                'height': tile_size,
                'width': tile_size,
                'count': 1,
                'dtype': ref_dtype,
                'crs': ref_crs,
                'transform': transform,
                'nodata': -32768,
                'compress': 'lzw'
            })

            with rasterio.open(full_path, 'w', **profile) as dst:
                data = np.zeros((1, tile_size, tile_size), dtype=ref_dtype)
                dst.write(data)

# Step 4: Validate all tiles exist
print("📥 Validating tiles...")
missing_tiles = []
src_files = []
for tile_name in tile_names:
    file_path = os.path.join(tile_dir, f"{tile_name}.tif")
    if not os.path.exists(file_path):
        print(f"❌ Tile {tile_name} missing after creation!")
        missing_tiles.append(tile_name)
        continue
    try:
        src = rasterio.open(file_path)
        if src.crs == ref_crs:
            src_files.append(src)
        else:
            print(f"CRS mismatch in {tile_name}, skipping.")
            src.close()
    except Exception as e:
        print(f"Failed to open {tile_name}: {e}")
        missing_tiles.append(tile_name)

if missing_tiles:
    print(f"❌ Missing tiles: {missing_tiles}")
    raise ValueError("Cannot proceed with missing tiles.")
else:
    print("✅ All tiles present.")

# Step 5: Merge the rasters
print("🧩 Merging raster tiles...")
mosaic, out_transform = merge(src_files)

# Step 6: Update metadata and save
out_meta = ref_profile.copy()
out_meta.update({
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": out_transform,
    "compress": "lzw"
})

with rasterio.open(output_path, "w", **out_meta) as dest:
    dest.write(mosaic)

print(f"\n✅ Final merged DEM written to:\n{output_path}")