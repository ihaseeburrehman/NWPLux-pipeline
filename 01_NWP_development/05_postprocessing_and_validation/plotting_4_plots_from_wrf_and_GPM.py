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
    "WRF_After_DA_cv5": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000_cv5/After_DA"
}

# Output folder
output_folder = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/Miscs/GPM_vs_WRF"
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
    "WRF_After_DA_cv5": True
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
        precip_data = precip_data * 6  # Convert mm/hr to mm over 6 hours
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

# Process GPM IMERG files and find matching WRF files
proj = ccrs.PlateCarree()
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
    matched_files = {"GPM_IMERG": gpm_file}
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
    
    if not all_matched:
        print(f"No complete match for {timestamp}")
        continue
    
    # Read data and compute max precipitation
    data_dict = {}
    gpm_max = None
    for dataset_name, file_path in matched_files.items():
        if dataset_name == "GPM_IMERG":
            precip_data, lat_data, lon_data = read_gpm_precip(file_path)
        else:
            precip_data, lat_data, lon_data = read_wrf_precip(file_path)
        if precip_data is not None:
            max_value = np.nanmax(precip_data)
            print(f"{dataset_name} max value: {max_value}")
            if not np.isnan(max_value) and max_value > 0:
                if dataset_name == "GPM_IMERG":
                    gpm_max = max_value
                else:
                    if max_value > gpm_max:
                        print(f"Higher value in {dataset_name}: {max_value} > GPM max {gpm_max}")
                data_dict[dataset_name] = {
                    "precip": precip_data,
                    "lat": lat_data,
                    "lon": lon_data,
                    "filename": os.path.basename(file_path)
                }
    
    if len(data_dict) != num_plots or gpm_max is None:
        print(f"Incomplete data or no valid GPM max for {timestamp}")
        continue
    
    # Set levels based on GPM IMERG max
    levels = np.arange(0, gpm_max + 1, 1)
    if len(levels) < 5:
        levels = np.array([0, gpm_max if gpm_max > 0 else 1])
    print(f"Levels for {timestamp}: {levels}")
    
    # Plotting setup based on number of plots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), subplot_kw={'projection': proj})
    axes = axes.flatten()
    
    # Hide unused axes
    for i in range(num_plots, 4):
        axes[i].axis('off')
    
    norm = BoundaryNorm(levels, ncolors=custom_cmap.N, clip=True)
    fig.subplots_adjust(hspace=-0.25, right=0.85)
    
    labels = {
        "GPM_IMERG": "(a) GPM IMERG",
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
    
    for idx, dataset_name in enumerate(data_dict.keys()):
        ax = axes[idx]
        precip_data = data_dict[dataset_name]["precip"]
        lat_data = data_dict[dataset_name]["lat"]
        lon_data = data_dict[dataset_name]["lon"]
        filename = data_dict[dataset_name]["filename"]
        
        # Add basemap
        try:
            ctx.add_basemap(ax, source=ctx.providers.Esri.WorldPhysical,
                            crs=ccrs.epsg(3857), zoom=6, attribution=False, zorder=0)
        except:
            pass
        
        # Add country boundaries
        ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.6, edgecolor="black", zorder=2, alpha=0.8)
        
        # Plot precipitation
        contour = ax.contourf(lon_data, lat_data, precip_data, levels=levels,
                              cmap=custom_cmap, norm=norm, transform=proj, zorder=1,
                              extend='max')
        
        # Set extent
        ax.set_extent([x_min, x_max, y_min, y_max], crs=proj)
        
        # Add gridlines
        gl = ax.gridlines(draw_labels=True, alpha=0.3)
        gl.top_labels = False
        gl.right_labels = False
        
        # Add country names
        for country in countries:
            ax.text(country["lon"], country["lat"], country["name"], fontsize=8,
                    color='black', ha='center', va='center', transform=proj, zorder=3,
                    bbox=None)
        
        # Add figure label
        ax.text(0.5, -0.08, labels[dataset_name], fontsize=10, color='black', ha='center',
                va='top', transform=ax.transAxes)
    
    # Add single colorbar
    cbar_ax = fig.add_axes([0.87, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(contour, cax=cbar_ax, orientation='vertical')
    cbar.set_label("6-Hour Precipitation (mm)")
    
    # Save plot
    output_file = os.path.join(output_folder, f"combined_precip_{wrf_timestamp.replace(':', '')}.png")
    plt.savefig(output_file, dpi=400, bbox_inches='tight')
    plt.close(fig)
    print(f"Plot saved to {output_file}")

print("All matched files processed.")