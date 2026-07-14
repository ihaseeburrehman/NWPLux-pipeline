#!/usr/bin/env python3
import rasterio
from rasterio.warp import reproject, Resampling
import numpy as np
import os

# Configuration
# This is the 5m DEM with bridges already burned
BURNED_DEM_5M = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/Alzette_sub_basin_bridge_burned.asc"
LUX_LIDAR_05M = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/GIS_and_DEM/Luxembourg_DEM/MNT_Lidar2024.tif"
FRA_DEM_5M = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/GIS_and_DEM/France_near_to_Lux_DEM/remaining_part_dem.asc"
OUTPUT_DEM_10M = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/Alzette_sub_basin_10m_bridge_preserved.asc"

STATIONS = {
    'Walferdange': {'x': 77256, 'y': 81571, 'gauge_altitude': 225.32},
    'Steinsel': {'x': 77432, 'y': 82659, 'gauge_altitude': 222.26},
    'Pfaffenthal': {'x': 77409, 'y': 76226, 'gauge_altitude': 235.25},
    'Livange': {'x': 76151, 'y': 65753, 'gauge_altitude': 265.8},
    'Hesperange': {'x': 78623, 'y': 72404, 'gauge_altitude': 255.74}
}

NODATA_VALUE = -9999

def main():
    print("="*120)
    print("RESAMPLING BURNED 5M DEM TO 10M - PRESERVING CHANNEL DEPTH")
    print("="*120)

    if not os.path.exists(BURNED_DEM_5M):
        print(f"Error: {BURNED_DEM_5M} not found.")
        return

    # 1. Load the 5m Burned DEM and sample station values
    print(f"\n[1/4] Reading 5m Burned DEM and sampling station values...")
    with rasterio.open(BURNED_DEM_5M) as src:
        data_5m = src.read(1)
        transform_5m = src.transform
        crs = src.crs if src.crs else "EPSG:2169"
        nodata = src.nodata
        
        # Capture 5m values at stations
        station_vals_5m = {}
        for name, info in STATIONS.items():
            r, c = src.index(info['x'], info['y'])
            if 0 <= r < src.height and 0 <= c < src.width:
                val = data_5m[r, c]
                station_vals_5m[name] = val if val != nodata else np.nan
            else:
                station_vals_5m[name] = np.nan

        # Calculate 10m grid dimensions
        new_width = int(src.width * (transform_5m.a / 10.0))
        new_height = int(src.height * (abs(transform_5m.e) / 10.0))
        new_transform = rasterio.Affine(10.0, 0.0, transform_5m.c,
                                        0.0, -10.0, transform_5m.f)
        
    print(f"      Grid Change: {data_5m.shape[1]}x{data_5m.shape[0]} (5m) -> {new_width}x{new_height} (10m)")

    # 2. Resample to 10m using MINIMUM resampling
    # Why MINIMUM? Because bridge burning lowers pixels. Average pulling up bank heights
    # is what causes the 2m difference. MIN will keep the burned (lowest) value in the 10m block.
    print(f"\n[2/4] Resampling to 10m using MINIMUM method (to keep burned bridges)...")
    data_10m = np.empty((new_height, new_width), dtype=np.float32)
    
    reproject(
        source=data_5m,
        destination=data_10m,
        src_transform=transform_5m,
        src_crs=crs,
        dst_transform=new_transform,
        dst_crs=crs,
        resampling=Resampling.min,  # Crucial for preserving burned features
        src_nodata=nodata,
        dst_nodata=nodata
    )

    # 3. Save the 10m DEM
    print(f"\n[3/4] Saving 10m DEM to {os.path.basename(OUTPUT_DEM_10M)}...")
    with open(OUTPUT_DEM_10M, 'w') as f:
        f.write(f"ncols        {new_width}\n")
        f.write(f"nrows        {new_height}\n")
        f.write(f"xllcorner    {new_transform.c}\n")
        f.write(f"yllcorner    {new_transform.f - new_height * 10.0}\n")
        f.write(f"cellsize     10.0\n")
        f.write(f"NODATA_value {nodata}\n")
        for row in data_10m:
            f.write(' '.join([f'{v:.3f}' if v != nodata else str(int(nodata)) for v in row]) + '\n')

    # 4. Final Comparison and Print
    print("\n[4/4] Final Validation and Comparison...")
    
    # Get 0.5m Lidar values for comparison
    station_vals_05m = {}
    if os.path.exists(LUX_LIDAR_05M):
        with rasterio.open(LUX_LIDAR_05M) as src_lidar:
            for name, info in STATIONS.items():
                try:
                    r, c = src_lidar.index(info['x'], info['y'])
                    val = src_lidar.read(1, window=((r, r+1), (c, c+1)))[0, 0]
                    station_vals_05m[name] = val
                except: station_vals_05m[name] = np.nan
    
    print("\n" + "-"*135)
    print(f"{'Station':<15} {'Station Alt':<12} {'Lidar 0.5m':<12} {'Burned 5m':<12} {'New 10m':<12} {'Diff (10m-Stat)':<15} {'Status'}")
    print("-"*135)

    for name, info in STATIONS.items():
        v_05m = station_vals_05m.get(name, np.nan)
        v_5m = station_vals_5m.get(name, np.nan)
        
        # Get 10m value from the new grid
        col_10 = int((info['x'] - new_transform.c) / 10.0)
        row_10 = int((new_transform.f - info['y']) / 10.0)
        v_10m = data_10m[row_10, col_10] if (0 <= row_10 < new_height and 0 <= col_10 < new_width) else np.nan
        if v_10m == nodata: v_10m = np.nan
        
        diff = v_10m - info['gauge_altitude']
        status = "✓ OK" if abs(diff) < 1.0 else "⚠️ >1m"
        
        print(f"{name:<15} {info['gauge_altitude']:<12.2f} {v_05m:<12.2f} {v_5m:<12.2f} {v_10m:<12.2f} {diff:<15.3f} {status}")

    print("\n" + "="*120)
    print("Note: Using MINIMUM resampling ensures that if a 5m pixel was burned (lowered), the 10m cell")
    print("      will maintain that lower elevation instead of averaging with the higher river banks.")
    print("="*120 + "\n")

if __name__ == "__main__":
    main()
