#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import rasterio
from rasterio.warp import reproject, Resampling
import numpy as np
import os

# Configuration
DEM_TEMPLATE_10M = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/Alzette_sub_basin_10m_bridge_burn.asc'
LUX_MANNING_10M = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/manning.n.ascii'
FRA_MANNING_5M = '/Users/haseeb.rehman/Documents/Misc/Data_Datasets/GIS_and_DEM/France_near_to_Lux_DEM/remaining_manning.asc'
OUTPUT_MANNING_10M = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/10m/Data/manning_complete_10m.n.ascii'

NODATA = -9999

def main():
    print("="*80)
    print("MERGING LUX AND FRANCE MANNING TO 10M COMPLETE MAP")
    print("="*80)

    # 1. Open DEM Template to get target grid
    print(f"\n[1/4] Reading DEM template: {os.path.basename(DEM_TEMPLATE_10M)}")
    with rasterio.open(DEM_TEMPLATE_10M) as src:
        target_transform = src.transform
        target_width = src.width
        target_height = src.height
        target_crs = src.crs if src.crs else 'EPSG:2169'
        dem_data = src.read(1)
        # Create a mask of valid DEM areas
        dem_mask = (dem_data != src.nodata)

    # 2. Process Luxembourg Manning (10m)
    print(f"\n[2/4] Reading Luxembourg 10m Manning...")
    with rasterio.open(LUX_MANNING_10M) as src:
        lux_data = np.full((target_height, target_width), np.nan, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=lux_data,
            src_transform=src.transform,
            src_crs=src.crs if src.crs else target_crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.nearest,
            src_nodata=src.nodata,
            dst_nodata=np.nan
        )

    # 3. Process France Manning (5m -> 10m)
    print(f"\n[3/4] Reading and Resampling France 5m Manning...")
    with rasterio.open(FRA_MANNING_5M) as src:
        fra_data = np.full((target_height, target_width), np.nan, dtype=np.float32)
        reproject(
            source=rasterio.band(src, 1),
            destination=fra_data,
            src_transform=src.transform,
            src_crs=src.crs if src.crs else target_crs,
            dst_transform=target_transform,
            dst_crs=target_crs,
            resampling=Resampling.nearest, # Nearest is best for landcover/manning
            src_nodata=src.nodata,
            dst_nodata=np.nan
        )

    # 4. Merge and Mask
    print(f"\n[4/4] Merging and applying DEM mask...")
    # Combine: Lux priority, then France
    final_manning = np.where(~np.isnan(lux_data), lux_data, fra_data)
    
    # Fill any remaining internal holes in the DEM domain with a default value
    DEFAULT_MANNING = 0.035
    final_manning = np.where(np.isnan(final_manning) & dem_mask, DEFAULT_MANNING, final_manning)
    
    # Apply NoData outside DEM domain
    final_manning = np.where(dem_mask, final_manning, NODATA)

    # Save to ASCII
    print(f"      Saving to: {OUTPUT_MANNING_10M}")
    with open(OUTPUT_MANNING_10M, 'w') as f:
        f.write(f"ncols {target_width}\n")
        f.write(f"nrows {target_height}\n")
        f.write(f"xllcorner {target_transform.c:.6f}\n")
        f.write(f"yllcorner {target_transform.f + target_height * target_transform.e:.6f}\n")
        f.write(f"cellsize {target_transform.a:.6f}\n")
        f.write(f"NODATA_value {int(NODATA)}\n")
        for row in final_manning:
            f.write(" ".join(f"{val:.4f}" if val != NODATA else str(int(NODATA)) for val in row) + "\n")

    print("\n✅ Merging Complete!")
    print(f"   Final range: {final_manning[dem_mask].min():.4f} to {final_manning[dem_mask].max():.4f}")
    print("="*80)

if __name__ == "__main__":
    main()
