# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Created on Mon Mar  6 10:42:20 2023

@author: haseeb.rehman
"""

import glob
from osgeo import gdal
from osgeo import osr
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import rasterio
from cartopy.feature import NaturalEarthFeature
import matplotlib.pyplot as plt
#from mpl_toolkits.basemap import Basemap
from matplotlib.ticker import MultipleLocator
import pyproj
from pyproj import crs
from pyproj import Proj
import fiona
import geopandas as gpd
import matplotlib.ticker as mticker
import os
from datetime import datetime
import pandas as pd
from scipy.interpolate import interpn
from scipy.interpolate import griddata
from termcolor import colored
from pyproj import Proj
from pyproj import Transformer
import matplotlib.gridspec as gridspec
import wrf
from netCDF4 import Dataset


# Define new latitude, longitude, and station name coordinates
station_coordinates =  [
    ("Breidfeld", 50.12385000, 6.06622000),
    ("Echternach", 49.80310000, 6.44337000),
    ("Ettelbruck", 49.85172000, 6.09754000),
    ("Obercorn", 49.51220000, 5.90110000),
    ("Remerchen", 49.49100000, 6.34900000),
    ("Findel", 49.63265182, 6.23292867),
    ("Roodt", 49.79450000, 5.82020000),
    # Add more stations here as ("Station Name", Latitude, Longitude)
]

path= '/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/1_day_simulation_using_GFS/analysis_dir/After_DA/'
    # Open the netCDF dataset
for filename in os.listdir(path):
    if not filename.endswith('.DS_Store'):  # Skip .DS_Store files
        nc_file = os.path.join(path, filename)
        try:
            nc_dataset = Dataset(nc_file)
            # Rest of your code to process valid NetCDF files
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    # Extract the 'T2' variable using WRF-Python
    T2_variable = wrf.getvar(nc_dataset, "T2")
    
    # Get the data from the 'T2' variable as a NumPy array
    T2_data = T2_variable.values
 
    # Extract the 'T2' variable using WRF-Python
    T2_variable = wrf.getvar(nc_dataset, "T2")
       
    # Define the source (Lambert Conformal) and destination (UTM) projections
    lambert = pyproj.Proj(proj='lcc',lat_0 = 49.8, lon_0=6.0, lat_1=6.1, lat_2=12.2, a=6370000, b=6370000)
    utm = pyproj.Proj(proj='utm', zone=32, northern=True, datum='WGS84')
    
    # Create a transformer object
    transformer = Transformer.from_proj(lambert, utm)
    
    # Access the 'XLAT' variable directly from the WRF dataset
    XLAT_variable = nc_dataset.variables['XLAT']
    
    # Access the 'XLONG' variable directly from the WRF dataset
    XLONG_variable = nc_dataset.variables['XLONG']
    
    # Get the data from the 'XLAT' and 'XLONG' variables as NumPy arrays
    XLAT_data = XLAT_variable[:]
    XLONG_data = XLONG_variable[:]
    
    # Perform the transformation
    x, y = transformer.transform(XLAT_data, XLONG_data)
     
    xmin, ymin, xmax, ymax = np.nanmin(x), np.nanmin(y), np.nanmax(x), np.nanmax(y)
    
    # Define the projection for the map
    data_crs = ccrs.epsg(3857)
    
    # Plotting figure with specific file
    fig = plt.figure(figsize=(15, 8))
    gs = gridspec.GridSpec(2, 2, width_ratios=[3, 1], height_ratios=[3, 1])
    
    # Create the map axes
    ax = plt.subplot(gs[0, 0], projection=data_crs)
    
    # add Greater Region shapefile
    
    shpfilename = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp'
    gdf = gpd.read_file(shpfilename)
    gdf.to_crs(crs=data_crs, inplace=True)
    gdf.plot(ax=ax, facecolor='none', edgecolor='White', alpha=0.6, zorder=2)
    
    # Annotation for shapefile 
    gdf['coords'] = gdf['geometry'].apply(lambda x: x.representative_point().coords[:])
    gdf['coords'] = [coords[0] for coords in gdf['coords']]
    for idx, row in gdf.iterrows():
        plt.annotate(xy=row['coords'], horizontalalignment='center', text=row['NAME'], fontsize=7, color='white', alpha=0.6)
    
    # shapefile for setting the extent of map only, it does not have any other purpose, because map extent was not setting automatically    
    shpfilename_2 = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_Domain.shp'
    gdf = gpd.read_file(shpfilename_2)
    gdf=gdf.to_crs(crs=data_crs)
    
    # Get the extent of the shapefile
    x_min, y_min, x_max, y_max = gdf.total_bounds
    
    # Set the map extent
    ax.set_extent([x_min, x_max, y_min, y_max], crs=data_crs)
    
    # Add gridlines
    gl = ax.gridlines(draw_labels=True, alpha=0.3)
    # Set gridline suitable interval
    gl.xlabels_top = False
    gl.ylabels_right = False
    
    # Get the value of data at observed location and store them in interpolated_values
    interpolated_values = []
    for station_name, latitude, longitude in station_coordinates:
        value = griddata((XLAT_data.flatten(), XLONG_data.flatten()), T2_data.flatten(), (latitude, longitude))
        interpolated_values.append(value)
    
    # Convert station coordinates to UTM
    station_coordinates_utm = [(name, *transformer.transform(lat, lon), value) for name, lat, lon, value in zip([name for name, _, _ in station_coordinates], [lat for _, lat, _ in station_coordinates], [lon for _, _, lon in station_coordinates], interpolated_values)]
    station_names, station_utm_x, station_utm_y, station_values = zip(*station_coordinates_utm)
    
    import matplotlib.colors as mcolors
    from matplotlib.lines import Line2D
     #Create a colormap with as many colors as there are stations
    num_stations = len(station_names)
    colors = plt.cm.get_cmap('tab20', num_stations)
    
    # Create a scatter plot for each station with a single point and unique colors
    for i, (station_name, lat, lon, value) in enumerate(zip(station_names, [lat for _, lat, lon in station_coordinates], [lon for _, lat, lon in station_coordinates], interpolated_values)):
        color = colors(i)  # Get a unique color for each station
        ax.scatter(lon, lat, marker='^', s=5, c=color, label=station_name, transform=ccrs.PlateCarree())
    
    # Create a legend with custom labels
    legend_labels = [f"Station {i + 1}" for i in range(num_stations)]
    legend = ax.legend(title='Stations', loc='lower center', bbox_to_anchor=(0.5, -0.3), ncol=num_stations)
    
    # Create a custom legend for the table
    legend_handles = []
    for i, station_name in enumerate(station_names):
        color = colors(i)  # Get a unique color for each station
    legend_handle = Line2D([0], [0], marker='^', color=color, markersize=10, label=station_name)
    legend_handles.append(legend_handle)
    
    # Create a DataFrame with custom legend symbols, station names, and interpolated values
    data_table = {
    'Station Name': [f"{station_name}" for station_name in station_names],
        'T2 - k': [int(value) for value in interpolated_values]  # Convert values to integers
    }
    df_table = pd.DataFrame(data_table)
      
    # Add a colorbar
    im = ax.imshow((T2_data), extent=(x_min, x_max, y_min, y_max), transform=data_crs, cmap='cividis')
    plt.colorbar(im, ax=ax, shrink=0.5, label='T2 %')
    
    # Add a title
    plt.annotate('T2 for The Greater Region', xy=(0.5, 1.05), xycoords='axes fraction', ha='center', fontsize=10, color='black')
    
    # Add date and time on figure
    # Extract date and time from the filename
    file_path = filename
    file_name = os.path.basename(file_path)
    date = file_name[13:23]
    time = file_name[24:29]
    
    # Add date and time on figure
    plt.title((f"Date: {date} Time: {time}"), fontsize=8, color='grey')

    # Create a subplot for the table
    table_ax = plt.subplot(gs[0, 1], frame_on=False)  # Set frame_on=False to remove the border
    # Remove the coordinates (xticks and yticks) from the table subplot
    table_ax.set_xticks([])
    table_ax.set_yticks([])
    
    # Display the table below the color bar
    table = table_ax.table(cellText=df_table.values, colLabels=df_table.columns, cellLoc='left', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1)
    
    # specify the path to the folder where you want to save the PNG file
    output_folder = '/Users/haseeb.rehman/Desktop/For_Animation/2nd_Year_CET/1_day_simulation_using_GFS/After_DA/T2/'
    
    # save the plot as PNG with the same name as the NetCDF file
    output_file = os.path.join(output_folder, f"{filename}.png")
    plt.savefig(output_file, dpi=400) 
        
# Show the plot
plt.show()
plt.close()

