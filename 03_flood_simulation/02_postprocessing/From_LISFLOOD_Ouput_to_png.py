import os
import glob
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from matplotlib.colors import BoundaryNorm
from pyproj import Transformer
import cv2
import requests
from io import BytesIO
from PIL import Image

# Adjust directory_path to match your .wd files location
directory_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Alzette_sub_basin_ERA5'

# Output directory for PNG files
output_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Animation_wd/'
os.makedirs(output_dir, exist_ok=True)

# DEM path
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/Alzette_5m_bathymetery.asc'

# ===================================================================
# USER OPTIONS
# ===================================================================
print("\n" + "="*60)
print("LISFLOOD VISUALIZATION OPTIONS")
print("="*60)

# Ask for WMS background
wms_input = input("Include WMS orthophoto background? (y/n) [default: y]: ").strip().lower()
use_wms = wms_input != 'n'  # Default to yes

# Ask for DEM background
dem_input = input("Include DEM hillshade background? (y/n) [default: n]: ").strip().lower()
use_dem = dem_input == 'y'  # Default to no

print(f"\nSettings:")
print(f"  WMS Background: {'YES' if use_wms else 'NO'}")
print(f"  DEM Background: {'YES' if use_dem else 'NO'}")
print("="*60 + "\n")

# Load DEM if needed
dem_data = None
dem_extent = None
if use_dem:
    print("Loading DEM...")
    try:
        with rasterio.open(dem_path) as dem_src:
            dem_data = dem_src.read(1).astype(float)
            dem_nodata = dem_src.nodata
            if dem_nodata is not None:
                dem_data[dem_data == dem_nodata] = np.nan
            dem_bounds = dem_src.bounds
            dem_extent = [dem_bounds.left, dem_bounds.right, dem_bounds.bottom, dem_bounds.top]
            
            # Normalize DEM for grayscale display (MinMax stretch)
            dem_min = np.nanmin(dem_data)
            dem_max = np.nanmax(dem_data)
            dem_data = (dem_data - dem_min) / (dem_max - dem_min)  # 0-1 range
            print(f"  DEM loaded: {dem_data.shape}, elevation range: {dem_min:.1f} - {dem_max:.1f} m")
    except Exception as e:
        print(f"  Warning: Could not load DEM: {e}")
        use_dem = False

# Find all .wd files in the directory
wd_files = glob.glob(os.path.join(directory_path, '*.wd'))
wd_files.sort()

if not wd_files:
    raise ValueError(f"No .wd files found in {directory_path}")

print(f"Found {len(wd_files)} .wd files to process")

# Custom colormap: white for 0, then medium to dark blues
colors = [(1, 1, 1)]  # White at 0

# Use PuBu colormap but start from ~0.4 to 1 to avoid light blues
orig_cmap = cm.get_cmap("turbo")
colors += [orig_cmap(i) for i in np.linspace(0.5, 1, 255)]  # Medium to dark blues

custom_cmap = mcolors.LinearSegmentedColormap.from_list("Custom_Blue_Shades", colors, N=256)


# Coordinate transformer: Luxembourg 1930 (LUREF) to WGS84
transformer = Transformer.from_crs("EPSG:2169", "EPSG:4326", always_xy=True)

# Function to read and plot a single .wd file, then save as PNG
def plot_and_save_wd_file(file_path, output_path):
    with rasterio.open(file_path) as src:
        water_depth = src.read(1).astype(float)
        nodata = src.nodata
        if nodata is not None:
            water_depth[water_depth == nodata] = np.nan
        
        # Get bounds from the raster (in LUREF meters)
        bounds = src.bounds  # (left, bottom, right, top)
        
        # Create extent in LUREF for proper alignment: [x_min, x_max, y_min, y_max]
        extent_luref = [bounds.left, bounds.right, bounds.bottom, bounds.top]
        
        # WMS request for background in LUREF (EPSG:2169)
        bg_rgb = None
        has_background = False
        if use_wms:
            bbox_wms = f"{bounds.left},{bounds.bottom},{bounds.right},{bounds.top}"
            wms_url = "https://wmts1.geoportail.lu/opendata/service"
            params = {
                "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
                "LAYERS": "ortho_2021", "STYLES": "", "CRS": "EPSG:2169",
                "BBOX": bbox_wms, "WIDTH": "2048", "HEIGHT": "2048", "FORMAT": "image/jpeg"
            }
            
            try:
                response = requests.get(wms_url, params=params, timeout=10)
                response.raise_for_status()  # Raise error for bad status codes
                bg_img = Image.open(BytesIO(response.content))
                bg_rgb = np.array(bg_img)
                has_background = True
            except Exception as e:
                print(f"  Warning: Could not fetch WMS background: {e}")
        
        # Define levels
        max_value = np.nanmax(water_depth)
        
        # Mask out very low water depths (< 0.01m) - make them COMPLETELY transparent
        # Use np.ma.masked_where to ensure matplotlib doesn't plot these values at all
        water_depth_masked = np.ma.masked_where((water_depth < 0.05) | np.isnan(water_depth), water_depth)
        
        # If no significant water, create image with background only
        if np.ma.is_masked(water_depth_masked) and water_depth_masked.mask.all():
            print(f"  No significant water depth (all < 0.01m), background only")
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot DEM if enabled
            if use_dem and dem_data is not None:
                ax.imshow(dem_data, extent=dem_extent, origin='upper', cmap='gray', zorder=0)
            
            # Plot WMS if enabled
            if has_background:
                ax.imshow(bg_rgb, extent=extent_luref, zorder=1)
            
            ax.set_xlabel('Longitude')
            ax.set_ylabel('Latitude')
            ax.set_aspect('equal')
            ax.grid(True, linestyle='--', color='white', alpha=0.5, zorder=2)
            plt.title("LISFLOOD Water Depth (No significant flooding)", fontsize=10)
            fig.savefig(output_path, dpi=400, bbox_inches='tight')
            plt.close(fig)
            return
        
        # Create levels - use adaptive intervals to avoid too many bins
        if max_value < 1.0:
            interval = 0.1
        elif max_value < 5.0:
            interval = 0.2
        elif max_value < 10.0:
            interval = 0.5
        else:
            interval = 1.0
        
        levels = np.arange(0.01, max_value + interval, interval)
        
        # Ensure we don't exceed 256 colors
        if len(levels) > 256:
            interval = (max_value - 0.01) / 200
            levels = np.arange(0.01, max_value + interval, interval)
        
        if len(levels) < 2:
            levels = np.array([0.01, max_value if max_value > 0.01 else 0.1])
        
        # Create plot
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Layer order (bottom to top):
        # 1. DEM (zorder=0)
        # 2. WMS (zorder=1)
        # 3. Water depth (zorder=2)
        
        # Plot DEM background if enabled
        if use_dem and dem_data is not None:
            ax.imshow(dem_data, extent=dem_extent, origin='upper', cmap='gray', zorder=0)
        
        # Plot WMS background if enabled
        if has_background:
            ax.imshow(bg_rgb, extent=extent_luref, zorder=1)
        
        # Plot water depth - only values >= 0.01m (masked values are NOT plotted)
        norm = BoundaryNorm(levels, custom_cmap.N)
        im = ax.contourf(water_depth_masked, levels=levels, cmap=custom_cmap, norm=norm, 
                        extent=extent_luref, origin='upper', alpha=0.7, zorder=2)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax, orientation='vertical', shrink=0.8, pad=0.02)
        cbar.set_label("Water Depth (m)")
        
        # Convert axis labels to lat/lon for readability
        x_ticks = ax.get_xticks()
        y_ticks = ax.get_yticks()
        
        # Convert to lat/lon
        x_labels = []
        for x in x_ticks:
            if bounds.left <= x <= bounds.right:
                lon, _ = transformer.transform(x, bounds.bottom)
                x_labels.append(f'{lon:.3f}°')
            else:
                x_labels.append('')
        
        y_labels = []
        for y in y_ticks:
            if bounds.bottom <= y <= bounds.top:
                _, lat = transformer.transform(bounds.left, y)
                y_labels.append(f'{lat:.3f}°')
            else:
                y_labels.append('')
        
        ax.set_xticklabels(x_labels)
        ax.set_yticklabels(y_labels)
        
        # Set labels and title
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_aspect('equal')
        ax.grid(True, linestyle='--', color='white', alpha=0.5, zorder=3)
        plt.title("LISFLOOD Water Depth", fontsize=10)
        
        # Save the figure
        fig.savefig(output_path, dpi=400, bbox_inches='tight')
        plt.close(fig)

# ===================================================================
# STEP 1: Process each .wd file and create PNGs
# ===================================================================
print("\n" + "="*60)
print("STEP 1: Creating PNG images from .wd files")
print("="*60)

png_files = []
for idx, wd_file in enumerate(wd_files, 1):
    base_name = os.path.basename(wd_file)
    png_name = base_name.replace('.wd', '.png')
    output_path = os.path.join(output_dir, png_name)
    
    print(f"[{idx}/{len(wd_files)}] Processing {base_name}...")
    plot_and_save_wd_file(wd_file, output_path)
    png_files.append(output_path)

print(f"\n✓ All {len(wd_files)} PNG files created!")

# ===================================================================
# STEP 2: Create MP4 animation from PNG files
# ===================================================================
print("\n" + "="*60)
print("STEP 2: Creating MP4 animation")
print("="*60)

# Get sorted list of PNG files
png_files_sorted = sorted(png_files)

if not png_files_sorted:
    print("⚠ Warning: No PNG files found. Animation not created.")
else:
    # Load and resize images
    images = []
    target_size = None  # Will be set to first image's dimensions
    
    for idx, png_path in enumerate(png_files_sorted, 1):
        img = cv2.imread(png_path)
        if img is None:
            print(f"  ⚠ Failed to load {os.path.basename(png_path)}")
            continue
        
        if target_size is None:
            target_size = (img.shape[1], img.shape[0])  # (width, height)
            print(f"Target size: {target_size[0]}x{target_size[1]} pixels")
        
        # Resize image to target size
        img_resized = cv2.resize(img, target_size, interpolation=cv2.INTER_LANCZOS4)
        images.append(img_resized)
        
        if idx % 10 == 0 or idx == len(png_files_sorted):
            print(f"  Loaded {idx}/{len(png_files_sorted)} images...")
    
    if not images:
        print("⚠ Warning: No valid images loaded. Animation not created.")
    else:
        # Get dimensions from first image
        height, width, _ = images[0].shape
        
        # Save video in output directory
        vid_path = os.path.join(output_dir, 'Animation.mp4')
        video = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc(*'mp4v'), 5, (width, height))
        
        # Write images to video
        for img in images:
            video.write(img)
        
        video.release()
        print(f"\n✓ Animation created: {vid_path}")
        print(f"  Processed {len(images)} frames at 5 fps")
        print(f"  Duration: {len(images)/5:.1f} seconds")

# ===================================================================
# SUMMARY
# ===================================================================
print("\n" + "="*60)
print("PROCESSING COMPLETE!")
print("="*60)
print(f"PNG files:  {output_dir}")
print(f"Animation:  {os.path.join(output_dir, 'Animation.mp4')}")
print("="*60)