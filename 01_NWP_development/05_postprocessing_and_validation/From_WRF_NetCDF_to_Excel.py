#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 13:39:43 2023

@author: haseeb.rehman
"""

import os
import pandas as pd
import xarray as xr
from osgeo import gdal
import glob
from osgeo import osr
import numpy as np

path = "/Users/haseeb.rehman/WRF/WRFV4.5/run/July_event_2021_based_on_GFS_14_00_withZTD/test"

# Create an empty list to store the extracted data from each file
dfs = []

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
       #Select the RAINC variable from the list
       RAINC_variable = [s for s in subdatasets if "RAINC" in s[0]][0]

       # Open the RAINC variable as a separate dataset
       RAINC_dataset = gdal.Open(RAINC_variable[0])

       # Get the RAINC data
       RAINC_data = RAINC_dataset.ReadAsArray()

       #Select the RAINC variable from the list
       RAINSH_variable = [s for s in subdatasets if "RAINC" in s[0]][0]

       # Open the RAINC variable as a separate dataset
       RAINSH_dataset = gdal.Open(RAINC_variable[0])

       # Get the RAINC data
       RAINSH_data = RAINC_dataset.ReadAsArray()

       # Add the RAINC and RAINNC data together to create a new variable
       sum_data = RAINC_data + RAINNC_data + RAINSH_data
        
            
       # Get the XLAT and XLON arrays
       XLAT_variable = [s for s in subdatasets if "XLAT" in s[0]][0]
       XLAT_dataset = gdal.Open(XLAT_variable[0])
       XLAT_data = XLAT_dataset.ReadAsArray()
       
       XLONG_variable = [s for s in subdatasets if "XLONG" in s[0]][0]
       XLONG_dataset = gdal.Open(XLONG_variable[0])
       XLONG_data = XLONG_dataset.ReadAsArray()

       # add date and time on figure
       # Get the filename from the file path
       file_path = filename
       file_name = os.path.basename(file_path)
        
        # Extract date and time from the filename
       date = file_name[11:21]
       time = file_name[22:27]
       # Flatten the XLAT and XLONG arrays
       flat_lat = XLAT_data.flatten()
       flat_lon = XLONG_data.flatten()
       flat_sum = sum_data.flatten()
       flat_rainc = RAINC_data.flatten()
       flat_rainnc = RAINNC_data.flatten()
       flat_rainsh = RAINSH_data.flatten()
       
       # Create a pandas dataframe with the flattened data
       df = pd.DataFrame({'Date': [date] * len(flat_lat),
                    'Time (hr)': [time] * len(flat_lat),
                    'Latitude': flat_lat,
                    'Longitude': flat_lon,
                    'RAINC (mm)': flat_rainc,
                    'RAINNC (mm)': flat_rainnc,
                    'RAINSH (mm)': flat_rainsh,
                    'Sum': flat_sum})

       # Append the dataframe to the list of dataframes
       dfs.append(df)

#Concatenate all the dataframes in the list into a single dataframe

final_df = pd.concat(dfs)
        
# Write the dataframe to an excel file
final_df.to_csv('Sum of RAINC RAINNC & RAINSH from WRF 08 July to 15 July 2021.csv', index=False)
