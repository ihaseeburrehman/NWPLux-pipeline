# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

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

highest_value = -np.inf
highest_value_file = ""
path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/run_wrf/July_14_3hr_GPM_Model_output_from_WRF"
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
  
# Plotting figure with specific file
fig = plt.figure(figsize=(10, 10))
# Open the dataset with highest value of RAINNC variable
nc_dataset = gdal.Open(os.path.join(path, highest_value_file))
subdatasets = nc_dataset.GetSubDatasets()
RAINNC_variable = [s for s in subdatasets if "RAINNC" in s[0]][0]
RAINNC_dataset = gdal.Open(RAINNC_variable[0])
RAINNC_data = RAINNC_dataset.ReadAsArray()
                
# Define the projection for the map
data_crs = ccrs.PlateCarree()

# Create the map axes
ax = plt.axes(projection=ccrs.PlateCarree())

# add Luxembourg shapefile
shape_crs = CRS.from_epsg(4326)
shpfilename = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Luxembourg_Regions.shp'
gdf = gpd.read_file('/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Luxembourg_Regions.shp')
with fiona.open(shpfilename, 'r', crs=shape_crs) as src:
    shape_crs = src.crs
reader = shpreader.Reader(shpfilename)
countries = reader.records()
for country in countries:
   ax.add_geometries(country.geometry, ccrs.PlateCarree(),
                      facecolor='none', edgecolor='white' , alpha=0.5)
   
#Annotation for shape file 
gdf['coords'] = gdf['geometry'].apply(lambda x: x.representative_point().coords[:])
gdf['coords'] = [coords[0] for coords in gdf['coords']]
for idx, row in gdf.iterrows():
    plt.annotate(xy=row['coords'], horizontalalignment='center', text=row['Name'],fontsize=7, color='white', alpha=0.4)
   
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

# Display the raster data on the map
im = ax.imshow(RAINNC_data, origin='upper', extent=(5.160459954,7.040060602,49.189283005,50.403694888), transform=data_crs, cmap='cividis')

# Add a colorbar
plt.colorbar(im, ax=ax, shrink=0.5)

# Add a title
plt.annotate('RAINNC (mm) for Luxembourg Region', xy=(0.5, 1.08), xycoords='axes fraction', ha='center', fontsize=10)
plt.title((highest_value_file), fontsize=8)

# Show the plot
plt.show()
plt.close()

#Get the highest Value in Varaibale data
print("The highest RAINNC value is:", highest_value)
print("The file containing the highest RAINNC value is:", highest_value_file)
#plt.savefig('figure.png')

