import rasterio
from rasterio.enums import Resampling
import os

# Input and output paths
input_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Differdange/DTM_Differdange.tif"
output_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Differdange/10m/walferdange_dem_10m.tif"

# Desired resolution
target_resolution = 10.0  # meters

# Open original DTM
with rasterio.open(input_path) as src:
    # Calculate new dimensions
    new_width = int(src.width * (src.res[0] / target_resolution))
    new_height = int(src.height * (src.res[1] / target_resolution))

    # Set up the transform for the new resolution
    transform = src.transform * src.transform.scale(
        (src.width / new_width),
        (src.height / new_height)
    )

    # Ensure the transform is set to the target resolution
    transform = transform * rasterio.Affine.translation(-target_resolution / 2, target_resolution / 2)

    kwargs = src.meta.copy()
    kwargs.update({
        'height': new_height,
        'width': new_width,
        'transform': transform,
        'crs': src.crs,  # Ensure the CRS is preserved
        'dtype': src.dtypes[0]  # Ensure the data type is preserved
    })

    # Write resampled raster
    with rasterio.open(output_path, 'w', **kwargs) as dst:
        for i in range(1, src.count + 1):
            dst.write(
                src.read(i, resampling=Resampling.average),
                i
            )

print(f"✅ Resampled DTM saved to: {output_path} with resolution: {target_resolution} m")
