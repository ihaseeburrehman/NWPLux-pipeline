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
from osgeo import gdal
from datetime import datetime
# Define file paths for the four datasets
paths = {
    "GPM_IMERG": "/Users/haseeb.rehman/Documents/Misc/GPM_IMERG/2021_event/",
    "WRF_Before_DA": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000_cv5/Before_DA",
    "WRF_After_DA_cv3": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000/After_DA",
    "WRF_After_DA_conv": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/4th_year/2021_without_ZTD_cv3/After_DA",
    "WRF_After_DA_ztd": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/4th_year/2021_with_ZTD_only_cv3/After_DA"
}
# Output folder
output_folder = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/GPM_vs_WRF"
os.makedirs(output_folder, exist_ok=True)
# Shapefile path (used for extent only)
shpfilename = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp"
# Load shapefile to get extent
gdf = gpd.read_file(shpfilename).to_crs(epsg=4326)
x_min, y_min, x_max, y_max = gdf.total_bounds
# Custom colormap (white at 0)
orig_cmap = cm.get_cmap("GnBu")
colors = [(1, 1, 1)] + [orig_cmap(i) for i in range(1, 256)]
custom_cmap = mcolors.LinearSegmentedColormap.from_list("Custom_GnBu", colors, N=256)
# User input to select datasets to plot
plot_options = {
    "GPM_IMERG": True,
    "WRF_Before_DA": True,
    "WRF_After_DA_cv3": True,
    "WRF_After_DA_conv": True,
    "WRF_After_DA_ztd": True
}
# Filter active datasets
active_datasets = [name for name, active in plot_options.items() if active]
num_plots = len(active_datasets)
if num_plots < 1:
    raise ValueError("At least one dataset must be active for plotting.")
# Function to read WRF precipitation data
def read_wrf_precip(file_path):
    nc_dataset = gdal.Open(file_path)
    if nc_dataset is None:
        return None, None, None
    subdatasets = nc_dataset.GetSubDatasets()
    try:
        RAINNC_var = [s for s in subdatasets if "RAINNC" in s[0]][0]
        RAINC_var = [s for s in subdatasets if "RAINC" in s[0]][0]
        RAINSH_var = [s for s in subdatasets if "RAINSH" in s[0]][0]
        RAINNC_data = gdal.Open(RAINNC_var[0]).ReadAsArray()
        RAINC_data = gdal.Open(RAINC_var[0]).ReadAsArray()
        RAINSH_data = gdal.Open(RAINSH_var[0]).ReadAsArray()
        precip_data = RAINC_data + RAINNC_data + RAINSH_data
        XLAT_var = [s for s in subdatasets if "XLAT" in s[0]][0]
        XLONG_var = [s for s in subdatasets if "XLONG" in s[0]][0]
        lat_data = gdal.Open(XLAT_var[0]).ReadAsArray()
        lon_data = gdal.Open(XLONG_var[0]).ReadAsArray()
        precip_data = np.where(np.isnan(precip_data) | np.isinf(precip_data), 0, precip_data)
        return precip_data, lat_data, lon_data
    except:
        return None, None, None
# Function to read GPM IMERG precipitation data
def read_gpm_precip(file_path):
    try:
        nc_file = Dataset(file_path, "r")
        precip_data = np.squeeze(nc_file.variables["GPM_3IMERGHH_07_precipitation"][:])
        lat_data = nc_file.variables["lat"][:]
        lon_data = nc_file.variables["lon"][:]
        nc_file.close()
        precip_data = precip_data * 6 # Convert mm/hr to mm over 6 hours
        lon_grid, lat_grid = np.meshgrid(lon_data, lat_data)
        precip_data = np.where(np.isnan(precip_data) | np.isinf(precip_data), 0, precip_data)
        return precip_data, lat_grid, lon_grid
    except:
        return None, None, None
# Function to extract timestamp from GPM IMERG filename
def get_gpm_timestamp(filename):
    try:
        date_time = filename.split('_')[2:6]
        date_time_str = f"{date_time[0]}_{date_time[1]}_{date_time[2]}_{date_time[3]}"
        dt = datetime.strptime(date_time_str, "%Y_%m_%d_%H%M")
        return dt.strftime("%Y-%m-%d_%H:%M:%S")
    except:
        return None
# Function to extract timestamp from WRF filename
def get_wrf_timestamp(filename):
    try:
        parts = filename.split('_')
        if len(parts) < 4:
            return None
        date_time = f"{parts[2]}_{parts[3]}"
        dt = datetime.strptime(date_time, "%Y-%m-%d_%H_%M_%S")
        return dt.strftime("%Y-%m-%d_%H:%M:%S")
    except:
        return None
# Collect matched data for all timestamps
proj = ccrs.PlateCarree()
matched_data = {}
timestamp_to_max = {}
for filename in sorted(os.listdir(paths["GPM_IMERG"])):
    if not filename.startswith("GPM_IMERG"):
        continue
    gpm_file = os.path.join(paths["GPM_IMERG"], filename)
    if not os.path.isfile(gpm_file):
        continue
    
    # Get GPM timestamp
    timestamp = get_gpm_timestamp(filename)
    if not timestamp:
        print(f"Skipping {filename}: Invalid timestamp")
        continue
    
    # Convert GPM timestamp to WRF filename format
    try:
        dt = datetime.strptime(timestamp, "%Y-%m-%d_%H:%M:%S")
        wrf_timestamp = dt.strftime("%Y-%m-%d_%H_%M_%S")
    except:
        print(f"Failed to convert timestamp {timestamp}")
        continue
    
    # Check for matching files
    matched_files = {}
    if "GPM_IMERG" in active_datasets:
        matched_files["GPM_IMERG"] = gpm_file
    all_matched = True
    for dataset_name in active_datasets:
        if dataset_name == "GPM_IMERG":
            continue
        wrf_file = os.path.join(paths[dataset_name], f"wrfout_d01_{wrf_timestamp}")
        if os.path.exists(wrf_file):
            matched_files[dataset_name] = wrf_file
        else:
            all_matched = False
            print(f"Missing wrfout_d01_{wrf_timestamp} in {dataset_name}")
            break
    
    if not all_matched or len(matched_files) != num_plots:
        print(f"No complete match for {timestamp}")
        continue
    
    # Read data
    data_dict = {}
    gpm_max = 0
    for dataset_name, file_path in matched_files.items():
        if dataset_name == "GPM_IMERG":
            precip_data, lat_data, lon_data = read_gpm_precip(file_path)
        else:
            precip_data, lat_data, lon_data = read_wrf_precip(file_path)
        if precip_data is None:
            break
        max_value = np.nanmax(precip_data)
        print(f"{dataset_name} max value: {max_value}")
        data_dict[dataset_name] = {
            "precip": precip_data,
            "lat": lat_data,
            "lon": lon_data,
            "filename": os.path.basename(file_path)
        }
        if dataset_name == "GPM_IMERG":
            gpm_max = max_value
    
    if len(data_dict) != num_plots:
        print(f"Incomplete data for {timestamp}")
        continue
    
    if gpm_max == 0:
        print(f"No valid GPM max for {timestamp}")
        continue
    
    matched_data[wrf_timestamp] = data_dict
    timestamp_to_max[wrf_timestamp] = gpm_max
# Process if there are matched timestamps
valid_timestamps = sorted(matched_data.keys())
num_timestamps = len(valid_timestamps)
if num_timestamps == 0:
    print("No matched files processed.")
else:
    # Calculate aspect ratio and figsize for A4-like proportions
    aspect = (x_max - x_min) / (y_max - y_min)
    height_per = 3.0
    width_per = aspect * height_per
    figsize = (width_per * num_timestamps, height_per * num_plots)
    
    # Plotting setup
    fig, axes = plt.subplots(num_plots, num_timestamps, figsize=figsize, subplot_kw={'projection': proj})
    if num_plots == 1 and num_timestamps == 1:
        axes = [[axes]]
    elif num_plots == 1:
        axes = [axes]
    elif num_timestamps == 1:
        axes = [[ax] for ax in axes]
    
    fig.subplots_adjust(hspace=0.05, wspace=0.0, bottom=0.12, top=0.95, left=0.08, right=0.98)
    
    labels = {
        "GPM_IMERG": "(a) GPM IMERG",
        "WRF_Before_DA": "(b) WRF Before DA",
        "WRF_After_DA_conv": "(c) WRF After DA CONV",
        "WRF_After_DA_ztd": "(d) WRF After DA ZTD",
        "WRF_After_DA_cv3": "(e) WRF After DA CONV + ZTD"
    }
    
    countries = [
        {"name": "Lux", "lon": 6.13, "lat": 49.81},
        {"name": "Belgium", "lon": 5.5, "lat": 50.5},
        {"name": "Germany", "lon": 7.5, "lat": 49.8},
        {"name": "France", "lon": 5.9, "lat": 48.5}
    ]
    
    row_order = [name for name in ["GPM_IMERG", "WRF_Before_DA", "WRF_After_DA_conv", "WRF_After_DA_ztd", "WRF_After_DA_cv3"] if name in active_datasets]
    
    for col_idx, timestamp in enumerate(valid_timestamps):
        data_dict = matched_data[timestamp]
        gpm_max = timestamp_to_max[timestamp]
        levels = np.arange(0, gpm_max + 5, 5)
        if len(levels) < 2:
            levels = np.array([0, gpm_max if gpm_max > 0 else 5])
        print(f"Levels for {timestamp}: {levels}")
        norm = BoundaryNorm(levels, ncolors=custom_cmap.N, clip=True)
        
        for row_idx, dataset_name in enumerate(row_order):
            ax = axes[row_idx][col_idx]
            precip_data = data_dict[dataset_name]["precip"]
            lat_data = data_dict[dataset_name]["lat"]
            lon_data = data_dict[dataset_name]["lon"]
            
            # Add basemap
            try:
                ctx.add_basemap(ax, source=ctx.providers.Esri.WorldPhysical,
                                crs=ccrs.epsg(3857), zoom=6, attribution=False, zorder=0)
            except:
                pass
            
            # Add country boundaries
            ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.6, edgecolor="black", zorder=2, alpha=0.8)
            
            # Plot precipitation
            contourf = ax.contourf(lon_data, lat_data, precip_data, levels=levels,
                                  cmap=custom_cmap, norm=norm, transform=proj, zorder=1,
                                  extend='max')
            ax.contour(lon_data, lat_data, precip_data, levels=levels,
                       colors='k', linewidths=0.1, transform=proj, alpha=0.1, zorder=1)
            
            # Set extent
            ax.set_extent([x_min, x_max, y_min, y_max], crs=proj)
            
            # Add gridlines
            gl = ax.gridlines(draw_labels=True, alpha=0.3)
            gl.top_labels = False
            gl.right_labels = False
            if col_idx > 0:
                gl.left_labels = False
            if row_idx < num_plots - 1:
                gl.bottom_labels = False
            
            # Add country names
            for country in countries:
                ax.text(country["lon"], country["lat"], country["name"], fontsize=8,
                        color='black', ha='center', va='center', transform=proj, zorder=3)
            
        # Add row labels on left
        for row_idx, dataset_name in enumerate(row_order):
            pos = axes[row_idx][0].get_position()
            fig.text(0.03, pos.y0 + (pos.height / 2), labels[dataset_name],
                     va='center', ha='center', rotation=90, fontsize=10)
        
        # Add timestamp title on top of each column
        axes[0][col_idx].set_title(timestamp, fontsize=12)
        
        # Add separate horizontal colorbar at bottom for this column
        bottom_ax = axes[-1][col_idx]
        pos = bottom_ax.get_position()
        cbar_ax = fig.add_axes([pos.x0, 0.05, pos.width, 0.02])
        cbar = fig.colorbar(contourf, cax=cbar_ax, orientation='horizontal')
        cbar.set_label("6-Hour Precipitation (mm)")
    
    # Save plot
    output_file = os.path.join(output_folder, f"GPM_vs_WRF.png")
    plt.savefig(output_file, dpi=400, bbox_inches='tight')
    plt.close(fig)
    print(f"Plot saved to {output_file}")
print("All matched files processed.")