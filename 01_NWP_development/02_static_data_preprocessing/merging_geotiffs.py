import os
import numpy as np
from osgeo import gdal, gdalconst, osr

# Directory path containing the GeoTIFF files
directory = '/Users/haseeb.rehman/Documents/gis4wrf/datasets/geog/Lux_LiDAR2019/extracted/GeoTiffs/'

# Output merged GeoTIFF file
output_tiff = '/Users/haseeb.rehman/Documents/gis4wrf/datasets/geog/Lux_LiDAR2019/extracted/Merged.tif'

# List all GeoTIFF files in the directory
geotiff_files = [file for file in os.listdir(directory) if file.endswith('.tif')]

if len(geotiff_files) == 0:
    print("No GeoTIFF files found in the directory.")
    exit()

# Initialize variables for merged GeoTIFF dimensions and extents
min_x = float('inf')
max_x = float('-inf')
min_y = float('inf')
max_y = float('-inf')

# Loop through each GeoTIFF file to determine the merged extents
for file in geotiff_files:
    tiff_path = os.path.join(directory, file)
    dataset = gdal.Open(tiff_path)

    # Get the extents of the current GeoTIFF
    geo_transform = dataset.GetGeoTransform()
    curr_min_x = geo_transform[0]
    curr_max_x = curr_min_x + (geo_transform[1] * dataset.RasterXSize)
    curr_min_y = geo_transform[3] + (geo_transform[5] * dataset.RasterYSize)
    curr_max_y = geo_transform[3]

    # Update the merged extents
    min_x = min(min_x, curr_min_x)
    max_x = max(max_x, curr_max_x)
    min_y = min(min_y, curr_min_y)
    max_y = max(max_y, curr_max_y)

# Calculate the merged GeoTIFF dimensions and pixel size
width = int((max_x - min_x) / geo_transform[1])
height = int((max_y - min_y) / abs(geo_transform[5]))

# Create the output merged GeoTIFF file
driver = gdal.GetDriverByName('GTiff')
output_dataset = driver.Create(output_tiff, width, height, 1, gdal.GDT_Float32)
output_dataset.SetGeoTransform((min_x, geo_transform[1], 0, max_y, 0, geo_transform[5]))

# Define the projection
srs = osr.SpatialReference()
srs.ImportFromEPSG(4326) 
output_dataset.SetProjection(srs.ExportToWkt())

output_band = output_dataset.GetRasterBand(1)
output_band.SetNoDataValue(-9999)

# Loop through each GeoTIFF file and merge the bands into the output file
for file in geotiff_files:
    tiff_path = os.path.join(directory, file)
    dataset = gdal.Open(tiff_path, gdalconst.GA_ReadOnly)
    band = dataset.GetRasterBand(1)
    data = band.ReadAsArray()

    # Calculate the pixel indices for merging
    x_offset = int((dataset.GetGeoTransform()[0] - min_x) / geo_transform[1])
    y_offset = int((max_y - dataset.GetGeoTransform()[3]) / abs(geo_transform[5]))

    # Replace nodata values with neighboring values
    mask = (data == output_band.GetNoDataValue())
    filled_data = data.copy()

    # Perform nearest neighbor interpolation in the mask regions
    for i in range(filled_data.shape[0]):
        for j in range(filled_data.shape[1]):
            if mask[i, j]:
                neighbors = []
                for di in range(-20, 21):
                    for dj in range(-20, 21):
                        ni = i + di
                        nj = j + dj
                        if 0 <= ni < filled_data.shape[0] and 0 <= nj < filled_data.shape[1]:
                            if not mask[ni, nj]:
                                neighbors.append(filled_data[ni, nj])

                if neighbors:
                    filled_data[i, j] = np.mean(neighbors)

    # Write the data to the merged GeoTIFF
    output_band.WriteArray(filled_data, xoff=x_offset, yoff=y_offset)

    dataset = None

output_dataset.FlushCache()

# Fill remaining nodata regions with neighboring values
mask = (output_band.ReadAsArray() == output_band.GetNoDataValue())

# Perform nearest neighbor interpolation in the remaining nodata regions
for i in range(filled_data.shape[0]):
    for j in range(filled_data.shape[1]):
        if mask[i, j]:
            neighbors = []
            for di in range(-5, 6):
                for dj in range(-5, 6):
                    ni = i + di
                    nj = j + dj
                    if 0 <= ni < filled_data.shape[0] and 0 <= nj < filled_data.shape[1]:
                        if not mask[ni, nj]:
                            neighbors.append(filled_data[ni, nj])

            if neighbors:
                filled_data[i, j] = np.mean(neighbors)

# Write the final data to the merged GeoTIFF
output_band.WriteArray(filled_data)

# Check if there are still no data values in the filled data
# Check if there are still no data values in the filled data
if output_band.GetNoDataValue() in filled_data:
    print("Your generated TIFF file still has no data values.")
    
output_dataset = None

print(f"Merged GeoTIFF created: {output_tiff}")
