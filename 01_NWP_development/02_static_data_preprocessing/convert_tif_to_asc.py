# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import rasterio
import numpy as np
from rasterio.transform import from_origin

# Input and output paths
input_tif = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/5m/walferdange_dem_5m.tif"
output_asc = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/5m/walferdange_dem_5m.asc"

# Read the GeoTIFF
with rasterio.open(input_tif) as src:
    data = src.read(1)
    transform = src.transform
    nodata = -9999
    data[data == 0] = nodata  # Replace 0 with -9999

    # Extract header info
    ncols = src.width
    nrows = src.height
    xllcorner = transform.c
    yllcorner = transform.f - nrows * transform.e
    cellsize = transform.a

# Write to ASCII Grid
with open(output_asc, 'w') as f:
    f.write(f"ncols         {ncols}\n")
    f.write(f"nrows         {nrows}\n")
    f.write(f"xllcorner     {xllcorner:.6f}\n")
    f.write(f"yllcorner     {yllcorner:.6f}\n")
    f.write(f"cellsize      {cellsize:.6f}\n")
    f.write(f"NODATA_value  {nodata}\n")
    np.savetxt(f, data, fmt="%.2f")
import rasterio

with rasterio.open("/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/5m/walferdange_dem_5m.tif") as src:
    print(src.crs)
