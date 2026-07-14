#!/usr/bin/env python3
"""
Process LISFLOOD output:
1. Create PNGs from .wd files (0m transparent)
2. Create animation
3. Extract water depth at 7 stations
4. Create hydrographs
"""

import os
import glob
import rasterio
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import cv2
from datetime import datetime, timedelta

# Paths
wd_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Alzette_sub_basin_ERA5'
output_dir_png = os.path.join(wd_dir, 'animation')
output_dir_plots = os.path.join(wd_dir, 'plots')

# Create output directories
os.makedirs(output_dir_png, exist_ok=True)
os.makedirs(output_dir_plots, exist_ok=True)

# Simulation info
START_TIME = datetime(2021, 7, 14, 0, 0)  # July 14, 00:00
END_TIME = datetime(2021, 7, 15, 6, 0)    # July 15, 06:00
SAVEINT = 3600  # 1 hour in seconds

# Station locations (LUREF coordinates)
stations = [
    {'name': 'Walferdange', 'x': 77256, 'y': 81571},
    {'name': 'Steinsel', 'x': 77432, 'y': 82659},
    {'name': 'Pfaffenthal', 'x': 77409, 'y': 76226},
    {'name': 'Livange', 'x': 76151, 'y': 65753},
    {'name': 'Hesperange', 'x': 78623, 'y': 72404},
    {'name': 'Mersh', 'x': 76243, 'y': 90955},
    {'name': 'Ettelbruck', 'x': 74998, 'y': 101159}
]

print("="*70)
print("LISFLOOD OUTPUT PROCESSING")
print("="*70)

# ===================================================================
# STEP 1: Create PNGs from .wd files
# ===================================================================
print("\n[1/4] Creating PNGs from .wd files...")

# Find all .wd files
wd_files = glob.glob(os.path.join(wd_dir, '*.wd'))
wd_files.sort()

if not wd_files:
    raise ValueError(f"No .wd files found in {wd_dir}")

print(f"   Found {len(wd_files)} .wd files")

# Custom colormap with transparency for 0m (no water)
colors = [(1, 1, 1, 0)]  # White, fully transparent at 0
orig_cmap = cm.get_cmap("turbo")
for i in np.linspace(0.5, 1, 255):
    r, g, b, _ = orig_cmap(i)
    colors.append((r, g, b, 1))  # Fully opaque for water

custom_cmap = mcolors.LinearSegmentedColormap.from_list("WaterDepth", colors, N=256)
custom_cmap.set_bad(alpha=0)  # NoData fully transparent

png_files = []

for idx, wd_file in enumerate(wd_files, 1):
    with rasterio.open(wd_file) as src:
        wd_data = src.read(1).astype(float)
        transform = src.transform
        bounds = src.bounds
        nodata = src.nodata
        
        if nodata is not None:
            wd_data[wd_data == nodata] = np.nan
        
        # Set 0 to NaN for transparency
        wd_data[wd_data == 0] = np.nan
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # Plot water depth with transparency
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    im = ax.imshow(wd_data, origin='upper', extent=extent, 
                   cmap=custom_cmap, vmin=0.01, vmax=3.0, zorder=2)
    
    # Extract timestep from filename
    basename = os.path.basename(wd_file)
    timestep = int(basename.split('-')[-1].replace('.wd', ''))
    hours = timestep * SAVEINT / 3600
    current_time = START_TIME + timedelta(hours=hours)
    
    # Title
    ax.set_title(f"Water Depth - {current_time.strftime('%Y-%m-%d %H:%M UTC')}", 
                fontsize=14, fontweight='bold')
    
    # Colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label('Water Depth (m)', fontsize=12)
    
    # Save PNG
    png_path = os.path.join(output_dir_png, f"wd_{timestep:04d}.png")
    plt.savefig(png_path, dpi=150, bbox_inches='tight', facecolor='white', transparent=False)
    plt.close()
    
    png_files.append(png_path)
    
    if idx % 5 == 0 or idx == len(wd_files):
        print(f"   Processed {idx}/{len(wd_files)} files...")

print(f"   ✓ Created {len(png_files)} PNG files")

# ===================================================================
# STEP 2: Create MP4 Animation
# ===================================================================
print("\n[2/4] Creating animation...")

if png_files:
    images = []
    for png_path in sorted(png_files):
        img = cv2.imread(png_path)
        if img is not None:
            images.append(img)
    
    if images:
        height, width, _ = images[0].shape
        vid_path = os.path.join(output_dir_png, 'WaterDepth_Animation.mp4')
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(vid_path, fourcc, 5, (width, height))
        
        for img in images:
            video.write(img)
        
        video.release()
        print(f"   ✓ Animation saved: {vid_path}")
        print(f"   Frames: {len(images)}, Duration: {len(images)/5:.1f} seconds")
else:
    print("   ⚠ No PNG files to create animation")

# ===================================================================
# STEP 3: Extract water depth at stations
# ===================================================================
print("\n[3/4] Extracting water depth at stations...")

# Read first file to get transform
with rasterio.open(wd_files[0]) as src:
    transform = src.transform
    bounds = src.bounds

station_data = {st['name']: {'times': [], 'depths': []} for st in stations}

for wd_file in wd_files:
    basename = os.path.basename(wd_file)
    timestep = int(basename.split('-')[-1].replace('.wd', ''))
    hours = timestep * SAVEINT / 3600
    current_time = START_TIME + timedelta(hours=hours)
    
    with rasterio.open(wd_file) as src:
        wd_data = src.read(1).astype(float)
        if src.nodata is not None:
            wd_data[wd_data == src.nodata] = np.nan
    
    for station in stations:
        # Convert coordinates to pixel indices
        col = int((station['x'] - bounds.left) / transform.a)
        row = int((bounds.top - station['y']) / abs(transform.e))
        
        if 0 <= row < wd_data.shape[0] and 0 <= col < wd_data.shape[1]:
            depth = wd_data[row, col]
            if np.isnan(depth):
                depth = 0.0
        else:
            depth = 0.0
        
        station_data[station['name']]['times'].append(current_time)
        station_data[station['name']]['depths'].append(depth)

# Save to Excel
excel_data = []
for station in stations:
    for t, d in zip(station_data[station['name']]['times'], 
                   station_data[station['name']]['depths']):
        excel_data.append({
            'Station': station['name'],
            'Time': t,
            'WaterDepth_m': round(d, 3)
        })

df_stations = pd.DataFrame(excel_data)
excel_path = os.path.join(output_dir_plots, 'station_water_depths.xlsx')
df_stations.to_excel(excel_path, index=False)
print(f"   ✓ Station data saved: {excel_path}")

# ===================================================================
# STEP 4: Create hydrographs
# ===================================================================
print("\n[4/4] Creating hydrographs...")

for station in stations:
    times = station_data[station['name']]['times']
    depths = station_data[station['name']]['depths']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    ax.plot(times, depths, color='#4366f5', linewidth=2, label='LISFLOOD')
    ax.fill_between(times, depths, alpha=0.3, color='#4366f5')
    
    ax.set_xlabel('Time (UTC)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Water Depth (m)', fontsize=12, fontweight='bold')
    ax.set_title(f"{station['name']} - Water Depth Hydrograph", 
                fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11)
    
    # Format x-axis
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b\n%H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')
    
    plt.tight_layout()
    plot_path = os.path.join(output_dir_plots, f'hydrograph_{station["name"]}.png')
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

print(f"   ✓ Created {len(stations)} hydrographs")

print("\n" + "="*70)
print("PROCESSING COMPLETE!")
print("="*70)
print(f"\nOutputs:")
print(f"  PNGs: {output_dir_png}/")
print(f"  Animation: {output_dir_png}/WaterDepth_Animation.mp4")
print(f"  Hydrographs: {output_dir_plots}/")
print(f"  Station data: {excel_path}")
print("="*70)
