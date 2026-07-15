# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import h5py
import numpy as np
import matplotlib.pyplot as plt
import os
from pyproj import Transformer
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import contextily as ctx
from datetime import datetime, timedelta
from matplotlib.colors import BoundaryNorm
import matplotlib.colors as mcolors
import matplotlib
# File paths
input_dir = "/Users/haseeb.rehman/Documents/Misc/Belgium_Radar_data_2021/2021/07/14/accum1h/hdf/"
output_folder = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000/RADFLOOD21_single/"
os.makedirs(output_folder, exist_ok=True)

# Transformer for Belgian Lambert 2008 (EPSG:3812) to WGS84 (EPSG:4326)
transformer = Transformer.from_crs("EPSG:3812", "EPSG:4326", always_xy=True)

# Radar metadata
UL_x = 300000.0     # upper-left x in meters
UL_y = 1000000.0    # upper-left y in meters
xscale = 1000.0     # pixel width
yscale = 1000.0     # pixel height
xsize = 700         # number of columns
ysize = 700         # number of rows

# Convert extent corners to lat/lon
UL_lon, UL_lat = transformer.transform(UL_x, UL_y)
LR_x = UL_x + xscale * xsize
LR_y = UL_y - yscale * ysize
LR_lon, LR_lat = transformer.transform(LR_x, LR_y)

# Adjust extent to center pixels in lat/lon
extent = (
    UL_lon - (xscale / 2) * (LR_lon - UL_lon) / (LR_x - UL_x),
    LR_lon + (xscale / 2) * (LR_lon - UL_lon) / (LR_x - UL_x),
    LR_lat - (yscale / 2) * (UL_lat - LR_lat) / (UL_y - LR_y),
    UL_lat + (yscale / 2) * (UL_lat - LR_lat) / (UL_y - LR_y)
)

# Get only hourly 1-hour files (minutes = 00)
files = [f for f in os.listdir(input_dir) if f.endswith('accum1h.hdf') and f[12:14] == '00']
files.sort()

# Aggregate data for 6-hour periods ending at 00, 12, 18
target_hours = [0, 6, 12, 18]
for target_hour in target_hours:
    # Initialize accumulated data
    accum_data = np.zeros((ysize, xsize), dtype=float)
    file_count = 0
    end_time = None
    target_file = None

    # Find target file for the hour
    for f in files:
        try:
            date_time_str = f[:14]
            dt = datetime.strptime(date_time_str, '%Y%m%d%H%M%S')
            if dt.hour == target_hour and dt.minute == 0:
                end_time = dt
                target_file = f
                # Sum files from t-5h to t (e.g., for 18:00, sum 13:00 to 18:00)
                start_time = dt - timedelta(hours=5)
                period_files = []
                for f2 in files:
                    dt2 = datetime.strptime(f2[:14], '%Y%m%d%H%M%S')
                    if start_time <= dt2 <= dt:
                        period_files.append(f2)
                period_files.sort()

                # Aggregate data
                for pf in period_files:
                    with h5py.File(os.path.join(input_dir, pf), 'r') as hdf:
                        data = hdf['dataset1']['data1']['data'][:].astype(float)
                        # Replace invalid values with 0
                        data = np.where(data < 0, 0, data)
                        accum_data += data
                        file_count += 1
                break
        except Exception as e:
            print(f"Error processing {f}: {e}")
            continue

    if file_count == 0 or target_file is None:
        print(f"No data for period ending at {target_hour:02d}:00")
        continue

    # Debug: Print max accumulated value and files used
    max_precip = np.nanmax(accum_data)
    print(f"Period ending {end_time.strftime('%Y-%m-%d %H:%M')}: Max precip = {max_precip:.2f} mm, Files used = {file_count}, Files: {period_files}")

       # Plot with Cartopy
    data_crs = ccrs.PlateCarree()
    fig, ax = plt.subplots(figsize=(12, 6), subplot_kw={'projection': data_crs})

    # Custom colormap (aligned with provided script)
    orig_cmap = matplotlib.colormaps["GnBu"]
    colors = [(1, 1, 1)] + [orig_cmap(i) for i in range(1, 256)]
    custom_cmap = mcolors.LinearSegmentedColormap.from_list("Custom_GnBu", colors, N=256)
    
    # Add filled contours at 5 mm intervals
    contour_levels = np.arange(0, max_precip + 5, 5)
    contour = ax.contourf(accum_data, levels=contour_levels, cmap=custom_cmap, origin='upper', 
                          extent=extent, transform=data_crs)
    
    # Add basemap and features
    try:
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor="black")
        ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.8, edgecolor="black")
        ax.add_feature(cfeature.LAKES, facecolor="lightblue", alpha=0.5)
        ctx.add_basemap(
            ax,
            source=ctx.providers.Esri.WorldPhysical,
            crs='EPSG:3857',
            zoom=6,
            attribution=False,
            zorder=0
        )
    except Exception as e:
        print(f"Failed to load basemap: {e}")
    
    # Set map extent
    ax.set_extent([2.7, 8.5, 47.7, 51], crs=data_crs)
    
    # Add colorbar with dynamic range
    cbar = plt.colorbar(contour, ax=ax, orientation='vertical', shrink=0.8, pad=0.02)
    major_ticks = np.arange(0, max_precip + 1, 20)
    minor_ticks = np.arange(0, max_precip + 1, 10)
    cbar.set_ticks(major_ticks)
    cbar.set_ticklabels([str(int(t)) if t != 100 else "" for t in major_ticks])
    cbar.ax.tick_params(which='both', length=4, width=1)
    cbar.ax.yaxis.set_ticks(minor_ticks, minor=True)
    cbar.ax.yaxis.set_tick_params(which='minor', length=2, width=0.8)
    
    # Set title and annotations
    plt.annotate('Belgium Radar Precipitation', xy=(0.5, 1.05), xycoords='axes fraction', ha='center', fontsize=10, color='black')
    formatted_date = end_time.strftime('Date: %Y-%m-%d Time: %H:%M')
    plt.title(formatted_date, fontsize=8, color='grey')
    
    # Gridlines
    gl = ax.gridlines(draw_labels=True, alpha=0.3)
    gl.top_labels = False
    gl.right_labels = False
    gl.xlabel_style = {'size': 8, 'color': 'grey'}
    gl.ylabel_style = {'size': 8, 'color': 'grey'}
    
    # Add country labels
    ax.text(5.8, 49.8, "Luxembourg", transform=data_crs, fontsize=6, color="black")
    ax.text(4.5, 50.5, "Belgium", transform=data_crs, fontsize=6, color="black")
    ax.text(7.5, 50.5, "Germany", transform=data_crs, fontsize=6, color="black")
    ax.text(5.8, 48.5, "France", transform=data_crs, fontsize=6, color="black")
    
    # Save output with filename based on target file
    output_filename = f"radar_accum_6h_{target_file[:14]}.png"
    output_path = os.path.join(output_folder, output_filename)
    plt.savefig(output_path, dpi=400, bbox_inches='tight')
    plt.show()
    plt.close()