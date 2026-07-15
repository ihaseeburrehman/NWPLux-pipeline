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
end_date = datetime(2021, 7, 15, 0, 0)    # July 15, 2021, 00:00

# Define file paths for the datasets
paths = {
    "Belgium_Radar": "/Users/haseeb.rehman/Documents/Misc/Belgium_Radar_data_2021/2021/07/14/accum1h/hdf/",
    "WRF_Before_DA": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000_cv5/Before_DA",
    "WRF_After_DA_cv3": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000/After_DA",
    "WRF_After_DA_cv5": "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000_cv5/After_DA"
}

# Output folder
output_folder = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/Miscs/Belgium_radar_vs_WRF"
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
def aggregate_belgium_radar(radar_dir, target_time):
    accum_data = np.zeros((700, 700), dtype=float)
    file_count = 0
    start_time = target_time - timedelta(hours=5)
    radar_files = [f for f in os.listdir(radar_dir) if f.endswith('accum1h.hdf')]
    period_files = []
    
    for f in radar_files:
        dt = datetime.strptime(f[:14], '%Y%m%d%H%M%S')
        if start_time <= dt <= target_time:
            period_files.append(f)
    period_files.sort()
    
    for pf in period_files:
        file_path = os.path.join(radar_dir, pf)
        try:
            with h5py.File(file_path, 'r') as hdf:
                data = hdf['dataset1']['data1']['data'][:].astype(float)
                data = np.where(data < 0, 0, data)
                accum_data += data
                file_count += 1
        except Exception as e:
            print(f"Error processing {pf}: {e}")
            continue
    
    return accum_data if file_count > 0 else None, file_count, period_files

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

# Process radar files for specified date range
proj = ccrs.PlateCarree()
radar_files = [f for f in os.listdir(paths["Belgium_Radar"]) if f.endswith('.accum1h.hdf') and f[12:14] == '00']
radar_files.sort()

for radar_file in radar_files:
    radar_path = os.path.join(paths["Belgium_Radar"], radar_file)
    timestamp = get_radar_timestamp(radar_file)
    if not timestamp or timestamp < start_date or timestamp > end_date:
        continue
    
    wrf_timestamp = timestamp.strftime("%Y-%m-%d_%H_%M_%S")
    wrf_filename = f"wrfout_d01_{wrf_timestamp}"
    
    matched_files = {"Belgium_Radar": radar_path}
    all_matched = True
    for dataset_name in paths:
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
    
    # Aggregate radar data for 6 hours
    accum_data, file_count, period_files = aggregate_belgium_radar(paths["Belgium_Radar"], timestamp)
    if accum_data is None:
        print(f"No valid aggregated data for {timestamp}")
        continue
    
    # Read data and compute max precipitation
    data_dict = {}
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
        if dataset_name != "Belgium_Radar":
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
    
    if len(data_dict) != 4 or radar_max is None:
        print(f"Incomplete data or no valid Radar max for {timestamp}")
        continue
    
    # Set levels based on aggregated Belgium Radar max
    levels = np.arange(0, radar_max + 5, 5)
    if len(levels) < 2:
        levels = np.array([0, radar_max if radar_max > 0 else 5])
    print(f"Levels for {timestamp}: {levels}")
    
    # Plotting
    fig, axes = plt.subplots(2, 2, figsize=(16, 12), subplot_kw={'projection': proj})
    axes = axes.flatten()
    norm = BoundaryNorm(levels, ncolors=custom_cmap.N, clip=True)
    fig.subplots_adjust(hspace=-0.25, right=0.85)
    
    labels = [
        "(a) Belgium RADAR",
        "(b) WRF Before DA",
        "(c) WRF After DA CV3",
        "(d) WRF After DA CV5"
    ]
    
    countries = [
        {"name": "Luxembourg", "lon": 6.13, "lat": 49.81},
        {"name": "Belgium", "lon": 5.5, "lat": 50.5},
        {"name": "Germany", "lon": 7.5, "lat": 49.8},
        {"name": "France", "lon": 5.9, "lat": 48.5}
    ]
    
    for idx, (dataset_name, data) in enumerate(data_dict.items()):
        ax = axes[idx]
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
        
        # Align with radar script: use origin='upper' and extent for Belgium Radar
        if dataset_name == "Belgium_Radar":
            contour = ax.contourf(lon_data, lat_data, precip_data, levels=levels,
                                 cmap=custom_cmap, norm=norm, transform=proj, zorder=1,
                                 extend='max', origin='upper', extent=extent)
        else:
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
        
        ax.text(0.5, -0.08, labels[idx], fontsize=10, color='black', ha='center',
                va='top', transform=ax.transAxes)
        
        #ax.annotate(filename, xy=(0.5, -0.15), xycoords='axes fraction', ha='center', fontsize=8)
    
    cbar_ax = fig.add_axes([0.87, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(contour, cax=cbar_ax, orientation='vertical')
    cbar.set_label("6-Hour Precipitation (mm)")
    
    output_file = os.path.join(output_folder, f"combined_precip_{wrf_timestamp.replace(':', '')}.png")
    plt.savefig(output_file, dpi=400, bbox_inches='tight')
    plt.close(fig)
    print(f"Plot saved to {output_file}")

print("All matched files processed.")