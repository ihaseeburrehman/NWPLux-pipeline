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
import matplotlib.colors as mcolors
import matplotlib  # Updated import
from netCDF4 import Dataset
from osgeo import gdal
from datetime import datetime, timedelta
import h5py
from pyproj import Transformer

# Input date range
start_date = datetime(2021, 7, 14, 6, 0)  # July 14, 2021, 06:00
end_date = datetime(2021, 7, 15, 0, 0)  # July 15, 2021, 00:00

# Define file paths for the datasets
paths = {
    "Belgium_Radar": "/Users/haseeb.rehman/Documents/Misc/Belgium_Radar_data_2021/2021/07/14/accum1h/hdf/",
    "WRF_Before_DA": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000_cv5/Before_DA",
    "WRF_After_DA_cv3": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000/After_DA",
    "WRF_After_DA_conv": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/4th_year/2021_without_ZTD_cv3/After_DA",
    "WRF_After_DA_ztd": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/4th_year/2021_with_ZTD_only_cv3/After_DA"
}

# Additional radar dir for 15th
radar_dirs_list = [paths["Belgium_Radar"], paths["Belgium_Radar"].replace("/14/", "/15/")]

# Output folder
output_folder = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/Belgium_radar_vs_WRF"
os.makedirs(output_folder, exist_ok=True)

# Shapefile path (used for extent only)
shpfilename = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp"

# Load shapefile to get extent
gdf = gpd.read_file(shpfilename).to_crs(epsg=4326)
x_min, y_min, x_max, y_max = gdf.total_bounds

# Custom colormap (white at 0) - Updated as per your fix
orig_cmap = matplotlib.colormaps["GnBu"]
colors = [(1, 1, 1)] + [orig_cmap(i) for i in range(1, 256)]
custom_cmap = mcolors.LinearSegmentedColormap.from_list("Custom_GnBu", colors, N=256)

# User input to select datasets to plot
plot_options = {
    "Belgium_Radar": True,
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

# Function to aggregate Belgium radar precipitation data over 6 hours
def aggregate_belgium_radar(radar_dirs_list, target_time):
    accum_data = np.zeros((700, 700), dtype=float)
    file_count = 0
    start_time = target_time - timedelta(hours=5)
    period_files = []
    
    for radar_dir in radar_dirs_list:
        if not os.path.exists(radar_dir):
            continue
        files = [f for f in os.listdir(radar_dir) if f.endswith('accum1h.hdf')]
        for f in files:
            dt = datetime.strptime(f[:14], '%Y%m%d%H%M%S')
            if start_time <= dt <= target_time:
                period_files.append(os.path.join(radar_dir, f))
    
    period_files.sort(key=os.path.basename)
    
    for pf in period_files:
        try:
            with h5py.File(pf, 'r') as hdf:
                data = hdf['dataset1']['data1']['data'][:].astype(float)
                data = np.where(data < 0, 0, data)
                accum_data += data
                file_count += 1
        except Exception as e:
            print(f"Error processing {pf}: {e}")
            continue
    
    return accum_data if file_count > 0 else None, file_count, [os.path.basename(p) for p in period_files]

# Function to extract timestamp from radar filename (e.g., 20210714160000.radclim.accum1h.hdf)
def get_radar_timestamp(filename):
    try:
        date_time_str = filename[:14]
        dt = datetime.strptime(date_time_str, '%Y%m%d%H%M%S')
        return dt
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
        return dt
    except:
        return None

# Transformer for Belgian Lambert 2008 (EPSG:3812) to WGS84 (EPSG:4326)
transformer = Transformer.from_crs("EPSG:3812", "EPSG:4326", always_xy=True)
UL_x, UL_y = 300000.0, 1000000.0
xscale, yscale = 1000.0, 1000.0
xsize, ysize = 700, 700
UL_lon, UL_lat = transformer.transform(UL_x, UL_y)
LR_x, LR_y = UL_x + xscale * xsize, UL_y - yscale * ysize
LR_lon, LR_lat = transformer.transform(LR_x, LR_y)
extent = (
    UL_lon - (xscale / 2) * (LR_lon - UL_lon) / (LR_x - UL_x),
    LR_lon + (xscale / 2) * (LR_lon - UL_lon) / (LR_x - UL_x),
    LR_lat - (yscale / 2) * (UL_lat - LR_lat) / (UL_y - LR_y),
    UL_lat + (yscale / 2) * (UL_lat - LR_lat) / (UL_y - LR_y)
)

# Collect matched data for all timestamps
proj = ccrs.PlateCarree()
matched_data = {}
timestamp_to_max = {}
radar_full_files = []
for radar_dir in radar_dirs_list:
    if not os.path.exists(radar_dir):
        continue
    files = [f for f in os.listdir(radar_dir) if f.endswith('.accum1h.hdf') and f[12:14] == '00']
    for f in files:
        radar_full_files.append((radar_dir, f))
radar_full_files.sort(key=lambda x: get_radar_timestamp(x[1]))
for radar_dir, radar_file in radar_full_files:
    radar_path = os.path.join(radar_dir, radar_file)
    timestamp = get_radar_timestamp(radar_file)
    if not timestamp or timestamp < start_date or timestamp > end_date:
        continue
    
    wrf_timestamp = timestamp.strftime("%Y-%m-%d_%H_%M_%S")
    wrf_filename = f"wrfout_d01_{wrf_timestamp}"
    
    matched_files = {}
    all_matched = True
    for dataset_name in active_datasets:
        if dataset_name == "Belgium_Radar":
            continue
        wrf_file = os.path.join(paths[dataset_name], wrf_filename)
        if os.path.exists(wrf_file):
            matched_files[dataset_name] = wrf_file
        else:
            all_matched = False
            print(f"Missing {wrf_filename} in {dataset_name}")
            break
    
    if not all_matched:
        print(f"No complete match for {timestamp}")
        continue
    
    data_dict = {}
    radar_max = 0
    if "Belgium_Radar" in active_datasets:
        # Aggregate radar data for 6 hours
        accum_data, file_count, period_files = aggregate_belgium_radar(radar_dirs_list, timestamp)
        if accum_data is None:
            print(f"No valid aggregated data for {timestamp}")
            continue
        
        radar_max = np.nanmax(accum_data)
        print(f"Aggregated Radar max for {timestamp}: {radar_max:.2f} mm, Files used: {file_count}, Files: {period_files}")
        
        # Match radar script's grid orientation
        lon_data = np.linspace(extent[0], extent[1], xsize)  # Left to right
        lat_data = np.linspace(extent[3], extent[2], ysize)  # Top to bottom (reversed to match upper origin)
        lon_grid, lat_grid = np.meshgrid(lon_data, lat_data)
        data_dict["Belgium_Radar"] = {
            "precip": accum_data,
            "lat": lat_grid,
            "lon": lon_grid,
            "filename": radar_file
        }
    
    for dataset_name, file_path in matched_files.items():
        precip_data, lat_data, lon_data = read_wrf_precip(file_path)
        if precip_data is not None:
            max_value = np.nanmax(precip_data)
            print(f"{dataset_name} max value: {max_value}")
            if max_value > radar_max:
                radar_max = max_value
            data_dict[dataset_name] = {
                "precip": precip_data,
                "lat": lat_data,
                "lon": lon_data,
                "filename": os.path.basename(file_path)
            }
    
    if len(data_dict) != num_plots:
        print(f"Incomplete data for {timestamp}")
        continue
    
    if radar_max == 0:
        print(f"No valid max for {timestamp}")
        continue
    
    matched_data[wrf_timestamp] = data_dict
    timestamp_to_max[wrf_timestamp] = radar_max

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
        "Belgium_Radar": "(a) Belgium RADAR",
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
    
    row_order = [name for name in ["Belgium_Radar", "WRF_Before_DA", "WRF_After_DA_conv", "WRF_After_DA_ztd", "WRF_After_DA_cv3"] if name in active_datasets]
    
    for col_idx, timestamp in enumerate(valid_timestamps):
        data_dict = matched_data[timestamp]
        radar_max = timestamp_to_max[timestamp]
        levels = np.arange(0, radar_max + 5, 5)
        if len(levels) < 2:
            levels = np.array([0, radar_max if radar_max > 0 else 5])
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
            if dataset_name == "Belgium_Radar":
                contourf = ax.contourf(lon_data, lat_data, precip_data, levels=levels,
                                      cmap=custom_cmap, norm=norm, transform=proj, zorder=1,
                                      extend='max', origin='upper', extent=extent)
            else:
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
    output_file = os.path.join(output_folder, f"Belgium_RADAR_vs_WRF.png")
    plt.savefig(output_file, dpi=400, bbox_inches='tight')
    plt.close(fig)
    print(f"Plot saved to {output_file}")
print("All matched files processed.")