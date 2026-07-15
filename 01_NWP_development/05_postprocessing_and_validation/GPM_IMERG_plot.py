# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import os
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import contextily as ctx
import geopandas as gpd
from matplotlib.colors import BoundaryNorm
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from netCDF4 import Dataset

# File paths
input_folder = "/Users/haseeb.rehman/Documents/Misc/GPM_IMERG/2018_event/"
output_folder = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2018_GFS_000_cv5/GPM_IMERG/"
shpfilename = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp"

# Ensure output folder exists
os.makedirs(output_folder, exist_ok=True)

# Load shapefile and get extent
gdf = gpd.read_file(shpfilename).to_crs(epsg=4326)
x_min, y_min, x_max, y_max = gdf.total_bounds

# Custom colormap
orig_cmap = cm.get_cmap("GnBu")
colors = [(1, 1, 1)] + [orig_cmap(i) for i in range(1, 256)]
custom_cmap = mcolors.LinearSegmentedColormap.from_list("Custom_GnBu", colors, N=256)

# Loop through all files in the input folder
for file in os.listdir(input_folder):
    file_path = os.path.join(input_folder, file)

    # Skip if it's a directory
    if not os.path.isfile(file_path):
        continue

    # Try to open the file as NetCDF
    try:
        nc_file = Dataset(file_path, "r")
    except:
        print(f"Skipping {file} — not a valid NetCDF file.")
        continue

    # Try extracting required variables
    try:
        precip_data = nc_file.variables["GPM_3IMERGHH_07_precipitation"][:]
        lat_data = nc_file.variables["lat"][:]
        lon_data = nc_file.variables["lon"][:]
    except KeyError as e:
        print(f"Skipping {file} — missing variable: {e}")
        nc_file.close()
        continue
    nc_file.close()

    # Squeeze in case of singleton time dimension
    precip_data = np.squeeze(precip_data)

    # Convert lat/lon to grid
    lon_grid, lat_grid = np.meshgrid(lon_data, lat_data)
    precip_accumulated = precip_data * 6  # convert mm/hr to mm over 6 hours

    # Define levels
    max_value = np.nanmax(precip_accumulated)
    levels = np.arange(0, max_value + 5, 5) if max_value > 0 else np.array([0, 5])
    if len(levels) < 2:
        levels = np.array([0, max_value if max_value > 0 else 5])

    # Plot
    proj = ccrs.PlateCarree()
    fig, ax = plt.subplots(figsize=(12, 6), subplot_kw={'projection': proj})
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.8)
    ax.add_feature(cfeature.LAKES, facecolor="lightblue", alpha=0.5)

    try:
        ctx.add_basemap(ax, source=ctx.providers.Esri.WorldPhysical,
                        crs=ccrs.epsg(3857), zoom=6, attribution=False, zorder=0)
    except Exception:
        pass

    norm = BoundaryNorm(levels, custom_cmap.N)
    contour = ax.contourf(lon_grid, lat_grid, precip_accumulated, levels=levels,
                          cmap=custom_cmap, norm=norm, transform=proj)

    cbar = plt.colorbar(contour, ax=ax, orientation='vertical', shrink=0.8, pad=0.02)
    cbar.set_label("Accumulated Precipitation (mm)")

    ax.set_extent([x_min, x_max, y_min, y_max], crs=proj)
    plt.title("GPM IMERG Accumulated Precipitation (6-hourly)", fontsize=10)

    gl = ax.gridlines(draw_labels=True, alpha=0.3)
    gl.xlabels_top = False
    gl.ylabels_right = False

    # Save plot
    output_file = os.path.join(output_folder, f"{file}.png")
    print(f"Saving: {output_file}")
    plt.savefig(output_file, dpi=400, bbox_inches='tight')
    plt.close(fig)

print("✅ All valid NetCDF files processed and plots saved.")

