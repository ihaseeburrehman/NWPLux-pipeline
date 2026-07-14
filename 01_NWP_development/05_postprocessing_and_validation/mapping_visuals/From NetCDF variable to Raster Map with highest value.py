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
from mpl_toolkits.basemap import Basemap
from matplotlib.ticker import MultipleLocator
import pyproj
from pyproj import CRS
import fiona
import geopandas as gpd
import matplotlib.ticker as mticker
import os
from datetime import datetime
import pandas as pd
from scipy.interpolate import interpn
from scipy.interpolate import griddata
from termcolor import colored

# Reading NetCDF files in a folder and get the highest value NetCDF File

highest_value = -np.inf
highest_value_file = ""
path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/run_wrf/WRF_output_3hr_Accumulation_ds083.3"
for filename in os.listdir(path):
    nc_file = os.path.join(path, filename)
    nc_dataset = gdal.Open(nc_file)
    # check if nc_dataset is None
    if nc_dataset is not None:
    
        # Get a list of all the variables in the file
        subdatasets = nc_dataset.GetSubDatasets()
        
        # Select the RAINNC variable from the list
        RAINNC_variable = [s for s in subdatasets if "RAINNC" in s[0]][0]
        
        # Open the RAINNC variable as a separate dataset
        RAINNC_dataset = gdal.Open(RAINNC_variable[0])
        
        # Get the data from the RAINNC variable as a NumPy array
        RAINNC_data = RAINNC_dataset.ReadAsArray()
        # Getting highest value among all netcdf file
        current_highest_value = np.amax(RAINNC_data)
        if current_highest_value > highest_value:
            highest_value = current_highest_value
            highest_value_file = filename
             

# Open the dataset with highest value of RAINNC variable
nc_dataset = gdal.Open(os.path.join(path, highest_value_file))
subdatasets = nc_dataset.GetSubDatasets()
RAINNC_variable = [s for s in subdatasets if "RAINNC" in s[0]][0]
RAINNC_dataset = gdal.Open(RAINNC_variable[0])
RAINNC_data = RAINNC_dataset.ReadAsArray()

# Open the dataset with highest value of RAINC variable
nc_dataset = gdal.Open(os.path.join(path, highest_value_file))
subdatasets = nc_dataset.GetSubDatasets()
RAINC_variable = [s for s in subdatasets if "RAINC" in s[0]][0]
RAINC_dataset = gdal.Open(RAINC_variable[0])
RAINC_data = RAINC_dataset.ReadAsArray()

# Add the RAINC and RAINNC data together to create a new variable
sum_data = RAINC_data + RAINNC_data

# Plotting figure with specific file
fig = plt.figure(figsize=(10, 10))

# Define the projection for the map
data_crs = ccrs.PlateCarree()

# Create the map axes
ax = plt.axes(projection=ccrs.PlateCarree())

# add Luxembourg shapefile
shape_crs = CRS.from_epsg(4326)
shpfilename = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Luxembourg_Regions.shp'
gdf = gpd.read_file(shpfilename)
with fiona.open(shpfilename, 'r', crs=shape_crs) as src:
    shape_crs = src.crs
reader = shpreader.Reader(shpfilename)
countries = reader.records()
for country in countries:
   ax.add_geometries(country.geometry, ccrs.PlateCarree(),
                      facecolor='none', edgecolor='white' , alpha=0.6)
   
#Annotation for shape file 
gdf['coords'] = gdf['geometry'].apply(lambda x: x.representative_point().coords[:])
gdf['coords'] = [coords[0] for coords in gdf['coords']]
for idx, row in gdf.iterrows():
    plt.annotate(xy=row['coords'], horizontalalignment='center', text=row['Name'],fontsize=7, color='white', alpha=0.6)
   
# add shapefile of those countries which are near Luxembourg
shape_crs = CRS.from_epsg(4326)
shpfilename_1 = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Countries_near_Lux.shp'
with fiona.open(shpfilename_1, 'r', crs=shape_crs) as src:
    shape_crs = src.crs
reader_1 = shpreader.Reader(shpfilename_1)
countries = reader_1.records()
for country in countries:
   ax.add_geometries(country.geometry, ccrs.PlateCarree(),
                      facecolor='none', edgecolor='black', alpha=0.5)
   
#add label for Germany, Belgium and France , Please adjust the lat/lon of labels on the map to better suit the area of interest
ax.text(6.352, 50, 'Germany', fontsize=7, transform=ccrs.Geodetic())
ax.text(5.504, 50.007, 'Belgium', fontsize=7, transform=ccrs.Geodetic())
ax.text(5.797, 49.41, 'France', fontsize=7, transform=ccrs.Geodetic())

# Add gridlines
gl = ax.gridlines(draw_labels=True, alpha=0.3)
# Set gridline interval to 0.25
gl.xlocator = MultipleLocator(0.25)
gl.ylocator = MultipleLocator(0.25)
gl.xlabels_top = False
gl.ylabels_right = False

# Set the map extent
ax.set_extent([5.160459954,7.040060602,49.189283005,50.403694888])

# Getting sum of highest location
index_of_highest_value = np.unravel_index(RAINNC_data.argmax(), RAINNC_data.shape)
highest_RAINC_value = RAINC_data[index_of_highest_value]
highest_RAINNC_value = RAINNC_data[index_of_highest_value]
sum_at_highest_location = highest_RAINC_value + highest_RAINNC_value

# Below code is to identify the highest value with lat and lon inforamtion. 
# Open the XLAT variable as a separate dataset
XLAT_variable = [s for s in subdatasets if "XLAT" in s[0]][0]
XLAT_dataset = gdal.Open(XLAT_variable[0])
XLAT_data = XLAT_dataset.ReadAsArray()

# Open the XLONG variable as a separate dataset
XLONG_variable = [s for s in subdatasets if "XLONG" in s[0]][0]
XLONG_dataset = gdal.Open(XLONG_variable[0])
XLONG_data = XLONG_dataset.ReadAsArray()
#print(XLAT_data[22:31])
# Get the index of the highest value of RAINNC
index_of_highest_value = np.where(RAINNC_data == np.amax(RAINNC_data))

# Get the latitude and longitude of the highest value
lat, lon = XLAT_data[index_of_highest_value[0][0]][index_of_highest_value[1][0]], XLONG_data[index_of_highest_value[0][0]][index_of_highest_value[1][0]]
ax.plot(lon, lat , marker='^', markeredgecolor='black', markerfacecolor='brown', markersize=5, label='Highest Precip' )

# Get the value of data at observed location
# Define the coordinates you're interested in
latitude = 49.6326518200
longitude = 6.23292866800

# Interpolate the data
value = griddata((XLAT_data.flatten(), XLONG_data.flatten()), RAINNC_data.flatten(), (latitude, longitude))

# Add Observed data from Excel file
# Read the excel file and store it in a dataframe
df = pd.read_excel("/Users/haseeb.rehman/Desktop/Prec_July14_3hr.xlsx")

# Extract the lat, lon and precipitation columns from the dataframe
lats = df["lat"]
lons = df["lon"]
precip = df["precipitation"]

# Plot the marker on the figure
plt.scatter(lons, lats, marker='s', alpha=0.5, edgecolor='black', facecolor='blue', label='Obs Precip', s=10)

# Display the raster data on the map
im = ax.imshow(sum_data, origin='upper', extent=(5.160459954,7.040060602,49.189283005,50.403694888), transform=data_crs, cmap='cividis')

# Add a colorbar
plt.colorbar(im, ax=ax, shrink=0.5, label='Precipitation in mm')

# Add a title
plt.annotate('Precipitation for Grand Duchy of Luxembourg', xy=(0.5, 1.08), xycoords='axes fraction', ha='center', fontsize=10, color='black')
plt.title((highest_value_file), fontsize=8, color='grey')
plt.legend(bbox_to_anchor=(0.5, -0.1), loc='lower center', ncol=2)

# add date and time on figure
# Get the filename from the file path
file_path = highest_value_file
file_name = os.path.basename(file_path)

# Extract date and time from the filename
date = file_name[11:21]
time = file_name[22:27]

# Print date and time
#print(f"Date: {date} Time: {time}")
plt.title((f"Date: {date} Time: {time}"), fontsize=8, color='grey')

# Show the plot
plt.show()
plt.close()

# Print the value at the index
print(colored("WRF Predicted Precipitation at Airport, Luxembourg:", "cyan"), value)
print(colored("Sum at highest location:","cyan"), sum_at_highest_location)
print(colored("highest_RAINC_value:","cyan"),highest_RAINC_value)
print(colored("highest_RAINNC_value:","cyan"),highest_RAINNC_value)
print(colored("Lat, Lon of highest value:","cyan") ,lat, lon)
print(colored("The file containing the highest RAINNC value is:","cyan"), highest_value_file)
print(colored("Observed Precipitation at Airport, Luxembourg:","cyan"), precip)

