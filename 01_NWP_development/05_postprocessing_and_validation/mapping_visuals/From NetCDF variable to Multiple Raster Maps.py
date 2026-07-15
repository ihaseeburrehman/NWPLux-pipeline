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

path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/run_wrf/July_14_3hr_GPM_Model_output_from_WRF"
for filename in os.listdir(path):
    nc_file = os.path.join(path, filename)
    nc_dataset = gdal.Open(nc_file)
    # check if nc_dataset is None
    if nc_dataset is not None:

        # Open the WRF NETCDF file using GDAL
        #nc_dataset = gdal.Open("/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/run_wrf/July_14_3hr_GPM_Model_output_from_WRF/wrfout_d01_2021-07-14_05_00_00")
        #nc_dataset = gdal.Open(nc_file)

        # Get a list of all the variables in the file
        subdatasets = nc_dataset.GetSubDatasets()

        # Select the RAINNC variable from the list
        RAINNC_variable = [s for s in subdatasets if "RAINNC" in s[0]][0]

        # Open the RAINNC variable as a separate dataset
        RAINNC_dataset = gdal.Open(RAINNC_variable[0])

        # Get the data from the RAINNC variable as a NumPy array
        RAINNC_data = RAINNC_dataset.ReadAsArray()

        #If code is plotting the zero value also and not giving the correct information on  map then you should remove zero value from your dataset
        # Create a new array that contains only the non-zero values from the variable data
        #non_zero_data = RAINNC_data[RAINNC_data != 0]

        # Reshape the non_zero_data array into a 2D array with the same number of rows as the original data array
        #non_zero_data_2d = non_zero_data.reshape(RAINNC_data.shape[0], -1)


        # Get the variable that you want to convert
        RAINNC = nc_dataset.GetRasterBand(1)

        # Create a GeoTIFF driver
        driver = gdal.GetDriverByName("GTiff")

        # Create an empty GeoTIFF file
        tiff_dataset = driver.Create("output_file.tiff", 45, 45, 1, gdal.GDT_Byte)

        # create a SpatialReference object
        srs = osr.SpatialReference()
        # set it to EPSG 4326
        srs.ImportFromEPSG(4326)
        # get the WKT format of the spatial reference
        wkt = srs.ExportToWkt()

        # Set the projection of the GeoTIFF file
        tiff_dataset.SetProjection(wkt)

        # Get the raster band for the GeoTIFF file
        tiff_band = tiff_dataset.GetRasterBand(1)

        # Set the "NoData" value for the raster band
        tiff_band.SetNoDataValue(0)

        # Set the geo-transform of the GeoTIFF file (replace the values with the appropriate values for your dataset)
        tiff_dataset.SetGeoTransform([0.0, 1.0, 0.0, 0.0, 0.0, 1.0])

        # Write the non-zero data to the GeoTIFF file
        tiff_dataset.GetRasterBand(1).WriteArray(RAINNC_data)

        fig = plt.figure(figsize=(10, 10))

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

        # Close the datasets
        tiff_dataset.FlushCache()
        #tiff_dataset = None
        nc_dataset = None

        # Add a title
        plt.annotate('RAINNC (mm) for Luxembourg Region', xy=(0.5, 1.08), xycoords='axes fraction', ha='center', fontsize=10)
        plt.title((filename), fontsize=8)

# Show the plot
plt.show()
#plt.savefig('figure.png')
