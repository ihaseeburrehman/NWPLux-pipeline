# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd
from netCDF4 import Dataset
from datetime import datetime
import warnings
import sys
import time
import pandas as pd
from matplotlib.colors import BoundaryNorm
import matplotlib.colors as mcolors

# Suppress Matplotlib deprecation warning
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# File paths
file_path = "/Users/haseeb.rehman/Documents/Misc/DWD_Radar_2021/RW_2017.002_202107.nc"
output_folder = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000/DWD_Radar_202107/"
shpfilename = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp"

# Ensure output folder exists
os.makedirs(output_folder, exist_ok=True)

# Custom colormap (aligned with WRF script)
orig_cmap = matplotlib.colormaps["GnBu"]
colors = [(1, 1, 1)] + [orig_cmap(i) for i in range(1, 256)]
custom_cmap = mcolors.LinearSegmentedColormap.from_list("Custom_GnBu", colors, N=256)

# Open the NetCDF file
try:
    nc = Dataset(file_path, "r")
except Exception as e:
    print(f"Error opening file: {e}")
    sys.exit(1)

# Extract variables
try:
    time_var = nc.variables["time"]
    precip_var = nc.variables["RR"]
    lon_var = nc.variables["lon"]
    lat_var = nc.variables["lat"]
    time_units = time_var.units
    time_base_str = time_units.split("since")[1].strip().split(".")[0]
    time_base = np.datetime64(datetime.strptime(time_base_str, "%Y-%m-%d %H:%M:%S"))
    times = [time_base + np.timedelta64(int(t), 'h') for t in time_var[:]]
    precip_data = precip_var[:]
    lon_data = lon_var[:]
    lat_data = lat_var[:]
except KeyError as e:
    print(f"Missing variable: {e}")
    nc.close()
    sys.exit(1)
except ValueError as e:
    print(f"Error parsing time units: {e}, using fallback time base")
    time_base = np.datetime64("2001-01-01T00:50:00")
    times = [time_base + np.timedelta64(int(t), 'h') for t in time_var[:]]

# Handle _FillValue and boundary values for masking
fill_value = precip_var._FillValue if hasattr(precip_var, '_FillValue') else 999.0
print(f"NetCDF _FillValue: {fill_value}")
precip_data = np.where((precip_data == fill_value) | (precip_data >= 999.0) | (precip_data <= 2.0), np.nan, precip_data)
print(f"Max precip after masking: {np.nanmax(precip_data):.2f} mm")

# Downsample grid for performance
downsample_factor = 4  # 275x225 grid
lon_grid = lon_data[::downsample_factor, ::downsample_factor]
lat_grid = lat_data[::downsample_factor, ::downsample_factor]
print(f"lon_grid shape: {lon_grid.shape}, lat_grid shape: {lat_grid.shape}")

# Load shapefile and get extent
try:
    gdf = gpd.read_file(shpfilename).to_crs(epsg=4326)
    x_min, y_min, x_max, y_max = gdf.total_bounds
    print(f"Shapefile extent: [{x_min}, {y_min}, {x_max}, {y_max}]")
except Exception as e:
    print(f"Error reading shapefile: {e}, using default extent")
    x_min, y_min, x_max, y_max = 2.0, 47.0, 10.0, 54.0

# Define target times for 6-hour accumulations ending at 00, 06, 12, 18 on July 14
target_times = [
    np.datetime64('2021-07-14T00:00:00'),
    np.datetime64('2021-07-14T06:00:00'),
    np.datetime64('2021-07-14T12:00:00'),
    np.datetime64('2021-07-14T18:00:00')
]

# Aggregate and plot 6-hour totals
for target_time in target_times:
    start_time = target_time - np.timedelta64(5, 'h')  # t-5h to t, e.g., 13:00 to 18:00 for 18:00
    indices = [i for i, t in enumerate(times) if start_time <= t <= target_time]
    if not indices:
        print(f"No data for period ending at {target_time}")
        continue
    
    # Debug: Print max precipitation for each hour and their sum
    print(f"\nDebug for period ending at {pd.Timestamp(target_time).strftime('%Y-%m-%d %H:%M')}:")
    hourly_maxes = []
    precip_6hr = np.zeros_like(precip_data[0, ::downsample_factor, ::downsample_factor])
    for i in indices:
        hourly_data = precip_data[i, ::downsample_factor, ::downsample_factor]
        max_precip = np.nanmax(hourly_data)
        hourly_time = pd.Timestamp(times[i]).strftime('%Y-%m-%d %H:%M')
        print(f"Hour {hourly_time}: Max precip = {max_precip:.2f} mm")
        hourly_maxes.append(max_precip)
        precip_6hr += np.nan_to_num(hourly_data, 0)  # Sum, replacing NaN with 0
    sum_maxes = np.nansum(hourly_maxes)
    print(f"Sum of hourly maxes: {sum_maxes:.2f} mm")
    
    max_value = np.nanmax(precip_6hr)
    print(f"6-hour accumulated max: {max_value:.2f} mm")
    if np.isnan(max_value) or max_value == 0:
        print(f"Warning: No valid data for period ending at {target_time}")
        continue
    
    # Levels aligned with WRF script (5 mm intervals)
    levels = np.arange(0, max_value + 5, 5)
    if len(levels) > 256:  # Ensure <= 256 levels
        step = np.ceil(max_value / 256).astype(int)
        levels = np.arange(0, max_value + step, step)
    if len(levels) < 2:
        levels = np.array([0, max_value if max_value > 0 else 5])

    # Plot
    proj = ccrs.PlateCarree()
    fig, ax = plt.subplots(figsize=(12, 6), subplot_kw={'projection': proj})
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.8)
    ax.add_feature(cfeature.LAKES, facecolor="lightblue", alpha=0.5)

    norm = BoundaryNorm(levels, ncolors=256, clip=True)
    contour = ax.contourf(lon_grid, lat_grid, precip_6hr, levels=levels,
                          cmap=custom_cmap, norm=norm, transform=proj)

    # Colorbar formatting
    cbar = plt.colorbar(contour, ax=ax, orientation='vertical', shrink=0.8, pad=0.02)
    major_ticks = np.arange(0, max_value + 1, 20)
    minor_ticks = np.arange(0, max_value + 1, 10)
    cbar.set_ticks(major_ticks)
    cbar.set_ticklabels([str(int(t)) if t != 100 else "" for t in major_ticks])
    cbar.ax.yaxis.set_ticks(minor_ticks, minor=True)
    cbar.ax.yaxis.set_tick_params(which='minor', length=2, width=0.8)
    cbar.set_label("6-Hour Precipitation (mm)")

    ax.set_extent([x_min, x_max, y_min, y_max], crs=proj)

    # Country labels
    ax.text(5.8, 49.8, "Luxembourg", transform=proj, fontsize=6, color="black")
    ax.text(4.5, 50.5, "Belgium", transform=proj, fontsize=6, color="black")
    ax.text(7.5, 50.5, "Germany", transform=proj, fontsize=6, color="black")
    ax.text(5.8, 48.5, "France", transform=proj, fontsize=6, color="black")

    # Title and annotation
    ax.text(0.5, 1.05, 'DWD Radar Precipitation', transform=ax.transAxes, ha='center', fontsize=10, color='black')
    formatted_date = pd.Timestamp(target_time).strftime('Date: %Y-%m-%d Time: %H:%M')
    plt.title(formatted_date, fontsize=8, color='grey')

    # Gridlines
    gl = ax.gridlines(draw_labels=True, alpha=0.3)
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 8, 'color': 'grey'}
    gl.ylabel_style = {'size': 8, 'color': 'grey'}

    # Save plot
    output_file = os.path.join(output_folder, f"DWD_Radar_6hr_ending_{pd.Timestamp(target_time).strftime('%Y%m%d_%H%M')}.png")
    plt.savefig(output_file, dpi=400, bbox_inches='tight')
    print(f"Saving: {output_file}")
    plt.close(fig)
    time.sleep(1)

nc.close()
print("✅ Plotting completed.")