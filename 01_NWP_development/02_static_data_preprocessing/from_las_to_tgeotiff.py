# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import os
import pdal
import numpy as np
import json
from osgeo import gdal, osr

# Define the directory path
directory = '/Users/haseeb.rehman/Documents/gis4wrf/datasets/geog/Lux_LiDAR2019/extracted/Las_files/'

# Output GeoTIFF directory
output_directory = '/Users/haseeb.rehman/Documents/gis4wrf/datasets/geog/Lux_LiDAR2019/extracted/GeoTiffs/'

# Create the output directory if it doesn't exist
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# List all LAS files in the directory
las_files = [file for file in os.listdir(directory) if file.endswith('.las')]

# Iterate over each LAS file
for file in las_files:
    try:
        las_path = os.path.join(directory, file)
        output_tiff = os.path.join(output_directory, os.path.splitext(file)[0] + '.tif')

        # Create PDAL pipeline configuration
        pipeline_config = {
            "pipeline": [
                {
                    "type": "readers.las",
                    "filename": las_path
                },
                {
                    "type": "filters.chipper",
                    "capacity": 500
                },
                {
                    "type": "writers.gdal",
                    "resolution": 1.0,  # Placeholder value, will be replaced
                    "filename": output_tiff,
                    "output_type": "idw",
                    "radius": 0.5
                }
            ]
        }

        # Calculate pixel size
        pipeline = pdal.Pipeline(json.dumps(pipeline_config))
        pipeline.execute()
        metadata = pipeline.metadata

        pixel_size = metadata['metadata']['filters.chipper']['spacing']

        # Update pixel size in the pipeline configuration
        pipeline_config['pipeline'][2]['resolution'] = pixel_size

        # Create PDAL pipeline
        pipeline = pdal.Pipeline(json.dumps(pipeline_config))

        # Execute the pipeline
        pipeline.execute()

        # Retrieve the GeoTIFF array
        array = pipeline.arrays[0]

        # Extract coordinate information
        x = array["X"]
        y = array["Y"]
        z = array["Z"]

        # Determine raster dimensions
        min_x, max_x = np.min(x), np.max(x)
        min_y, max_y = np.min(y), np.max(y)
        width = int((max_x - min_x) / pixel_size) + 1
        height = int((max_y - min_y) / pixel_size) + 1

        # Create empty raster
        raster = np.zeros((height, width), dtype=np.float32)

        # Compute cell indices within the raster
        row_indices = ((max_y - y) / pixel_size).astype(int)
        col_indices = ((x - min_x) / pixel_size).astype(int)

        # Assign elevation values to raster cells
        raster[row_indices, col_indices] = z

        # Create GeoTIFF using gdal
        driver = gdal.GetDriverByName("GTiff")
        dataset = driver.Create(output_tiff, width, height, 1, gdal.GDT_Float32)
        dataset.SetGeoTransform((min_x, pixel_size, 0, max_y, 0, -pixel_size))
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        dataset.SetProjection(srs.ExportToWkt())
        band = dataset.GetRasterBand(1)
        band.WriteArray(raster)
        band.SetNoDataValue(0)
        band.FlushCache()

        print(f"GeoTIFF created: {output_tiff}")
    except Exception as e:
        print(f"Error processing file: {file}")
        print(f"Error message: {str(e)}")
