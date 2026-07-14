import os
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import contextily as ctx
import geopandas as gpd
from matplotlib.colors import BoundaryNorm
import matplotlib.colors as mcolors
import matplotlib
from netCDF4 import Dataset
from osgeo import gdal
from datetime import datetime, timedelta
import h5py
from pyproj import Transformer

# User input to select datasets to plot
plot_options = {
    "DWD_Radar": True,
    "WRF_Before_DA": True,
    "WRF_After_DA_cv3": False,
    "WRF_After_DA_cv5": True
}

# Input date range
start_date = datetime(2016, 7, 22, 18, 0)  # May 31, 2018, 18:00
end_date = datetime(2016, 7, 23, 0, 0)      # June 1, 2018, 06:00

# Define file paths for the datasets
paths = {
    "DWD_Radar": [
        "/Users/haseeb.rehman/Documents/Misc/DWD_Radar/2016/RW_2017.002_201607.nc" ],
    "WRF_Before_DA": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2016_GFS_000_cv5/Before_DA",
    "WRF_After_DA_cv3": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000/After_DA",
    "WRF_After_DA_cv5": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2016_GFS_000_cv5/After_DA"
}

# Output folder
output_folder = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/Miscs/DWD_Radar_vs_WRF"
os.makedirs(output_folder, exist_ok=True)

# Shapefile path (used for extent only)
shpfilename = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp"

# Load shapefile to get extent
gdf = gpd.read_file(shpfilename).to_crs(epsg=4326)
x_min, y_min, x_max, y_max = gdf.total_bounds

# Custom colormap (white at 0)
orig_cmap = matplotlib.colormaps["GnBu"]
colors = [(1, 1, 1)] + [orig_cmap(i) for i in range(1, 256)]
custom_cmap = mcolors.LinearSegmentedColormap.from_list("Custom_GnBu", colors, N=256)

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

# Function to select DWD radar file based on target time
def select_dwd_radar_files(file_paths, target_time):
    selected_files = []
    for file_path in file_paths:
        try:
            year_month = os.path.basename(file_path).split('_')[-1].replace('.nc', '')
            file_date = datetime.strptime(year_month, '%Y%m')
            if (file_date.year == target_time.year and file_date.month == target_time.month) or \
               (file_date.year == (target_time - timedelta(hours=5)).year and file_date.month == (target_time - timedelta(hours=5)).month):
                selected_files.append(file_path)
        except:
            continue
    return selected_files

# Function to aggregate DWD radar precipitation data over 6 hours
def aggregate_dwd_radar(file_paths, target_time):
    try:
        precip_6hr = None
        lon_grid = None
        lat_grid = None
        downsample_factor = 4
        
        for file_path in file_paths:
            nc = Dataset(file_path, "r")
            time_var = nc.variables["time"]
            precip_var = nc.variables["RR"]
            lon_var = nc.variables["lon"]
            lat_var = nc.variables["lat"]
            time_units = time_var.units
            time_base_str = time_units.split("since")[1].strip().split(".")[0]
            time_base = np.datetime64(datetime.strptime(time_base_str, "%Y-%m-%d %H:%M:%S"))
            times = [time_base + np.timedelta64(int(t), 'h') for t in time_var[:]]
            precip_data = precip_var[:]
            fill_value = precip_var._FillValue if hasattr(precip_var, '_FillValue') else 999.0
            precip_data = np.where((precip_data == fill_value) | (precip_data >= 999.0) | (precip_data <= 2.0), np.nan, precip_data)
            
            if precip_6hr is None:
                precip_6hr = np.zeros((precip_data.shape[1] // downsample_factor, precip_data.shape[2] // downsample_factor))
                lon_grid = lon_var[::downsample_factor, ::downsample_factor]
                lat_grid = lat_var[::downsample_factor, ::downsample_factor]
            
            start_time = target_time - timedelta(hours=5)
            indices = [i for i, t in enumerate(times) if start_time <= t <= target_time]
            
            for i in indices:
                hourly_data = precip_data[i, ::downsample_factor, ::downsample_factor]
                precip_6hr += np.nan_to_num(hourly_data, 0)
            
            nc.close()
        
        if precip_6hr is None:
            print(f"No data for period ending at {target_time}")
            return None, None, None
        
        return precip_6hr, lat_grid, lon_grid
    except Exception as e:
        print(f"Error processing DWD radar: {e}")
        return None, None, None

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

# Transformer for German radar alignment (assuming WGS84 from NetCDF)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:4326", always_xy=True)
UL_x, UL_y = x_min, y_max
xscale, yscale = (x_max - x_min) / 275, (y_max - y_min) / 225
xsize, ysize = 275, 225
extent = (x_min, x_max, y_min, y_max)

# Process radar files for specified date range
proj = ccrs.PlateCarree()
target_times = [start_date + timedelta(hours=6*i) for i in range(int((end_date - start_date).total_seconds() // (6*3600) + 1))]

for target_time in target_times:
    target_time_np = np.datetime64(target_time)
    wrf_timestamp = target_time.strftime("%Y-%m-%d_%H_%M_%S")
    wrf_filename = f"wrfout_d01_{wrf_timestamp}"
    
    matched_files = {}
    all_matched = True
    for dataset_name in paths:
        if dataset_name == "DWD_Radar":
            continue
        if not plot_options.get(dataset_name, False):  # Skip datasets not selected in plot_options
            continue
        wrf_file = os.path.join(paths[dataset_name], wrf_filename)
        if os.path.exists(wrf_file):
            matched_files[dataset_name] = wrf_file
        else:
            all_matched = False
            print(f"Missing {wrf_filename} in {dataset_name}")
            break
    
    if not all_matched:
        print(f"No complete match for {target_time}")
        continue
    
    # Select and aggregate DWD radar data for 6 hours
    dwd_files = select_dwd_radar_files(paths["DWD_Radar"], target_time)
    if not dwd_files:
        print(f"No valid DWD radar files for {target_time}")
        continue
    precip_6hr, lat_grid, lon_grid = aggregate_dwd_radar(dwd_files, target_time)
    if precip_6hr is None:
        print(f"No valid aggregated data for {target_time}")
        continue
    
    # Read data and compute max precipitation
    data_dict = {}
    radar_max = np.nanmax(precip_6hr)
    print(f"Aggregated DWD Radar max for {target_time}: {radar_max:.2f} mm")
    
    data_dict["DWD_Radar"] = {
        "precip": precip_6hr,
        "lat": lat_grid,
        "lon": lon_grid,
        "filename": os.path.basename(dwd_files[0]) if dwd_files else "DWD_Radar"
    }
    
    for dataset_name, file_path in matched_files.items():
        precip_data, lat_data, lon_data = read_wrf_precip(file_path)
        if precip_data is not None:
            max_value = np.nanmax(precip_data)
            if not np.isnan(max_value) and max_value > 0:
                if max_value > radar_max:
                    print(f"Higher value in {dataset_name}: {max_value} > Radar max {radar_max}")
                data_dict[dataset_name] = {
                    "precip": precip_data,
                    "lat": lat_data,
                    "lon": lon_data,
                    "filename": os.path.basename(file_path)
                }
    
    # Filter data_dict based on plot_options
    data_dict = {k: v for k, v in data_dict.items() if plot_options.get(k, False)}
    
    if not data_dict or radar_max is None:
        print(f"Incomplete data or no valid Radar max for {target_time}")
        continue
    
    # Set levels based on aggregated DWD Radar max
    levels = np.arange(0, radar_max + 5, 5)
    if len(levels) < 2:
        levels = np.array([0, radar_max if radar_max > 0 else 5])
    print(f"Levels for {target_time}: {levels}")
    
    # Plotting
    n_plots = len(data_dict)
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), subplot_kw={'projection': proj})
    axes = axes.flatten()
    norm = BoundaryNorm(levels, ncolors=custom_cmap.N, clip=True)
    fig.subplots_adjust(hspace=-0.25, right=0.85)
    
    label_dict = {
        "DWD_Radar": "(a) DWD RADAR",
        "WRF_Before_DA": "(b) WRF Before DA",
        "WRF_After_DA_cv3": "(c) WRF After DA CV3",
        "WRF_After_DA_cv5": "(d) WRF After DA CV5"
    }
    
    countries = [
        {"name": "Luxembourg", "lon": 6.13, "lat": 49.81},
        {"name": "Belgium", "lon": 5.5, "lat": 50.5},
        {"name": "Germany", "lon": 7.5, "lat": 49.8},
        {"name": "France", "lon": 5.9, "lat": 48.5}
    ]
    
    plot_idx = 0
    for dataset_name, data in data_dict.items():
        ax = axes[plot_idx]
        precip_data = data["precip"]
        lat_data = data["lat"]
        lon_data = data["lon"]
        filename = data["filename"]
        
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldPhysical,
                            crs=ccrs.epsg(3857), zoom=6, attribution=False, zorder=0)
        except:
            pass
        
        ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.6, edgecolor="black", zorder=2, alpha=0.8)
        
        contour = ax.contourf(lon_data, lat_data, precip_data, levels=levels,
                              cmap=custom_cmap, norm=norm, transform=proj, zorder=1,
                              extend='max')
        
        ax.set_extent([x_min, x_max, y_min, y_max], crs=proj)
        
        gl = ax.gridlines(draw_labels=True, alpha=0.3)
        gl.top_labels = False
        gl.right_labels = False
        
        for country in countries:
            ax.text(country["lon"], country["lat"], country["name"], fontsize=8,
                    color='black', ha='center', va='center', transform=proj, zorder=3,
                    bbox=None)
        
        ax.text(0.5, -0.08, label_dict[dataset_name], fontsize=10, color='black', ha='center',
                va='top', transform=ax.transAxes)
        
        plot_idx += 1
    
    # Hide unused subplots
    for i in range(plot_idx, len(axes)):
        axes[i].set_visible(False)
    
    cbar_ax = fig.add_axes([0.87, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(contour, cax=cbar_ax, orientation='vertical')
    cbar.set_label("6-Hour Precipitation (mm)")
    
    output_file = os.path.join(output_folder, f"combined_precip_{wrf_timestamp.replace(':', '')}.png")
    plt.savefig(output_file, dpi=400, bbox_inches='tight')
    plt.close(fig)
    print(f"Plot saved to {output_file}")

print("All matched files processed.")