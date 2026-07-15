#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-

import os
from netCDF4 import Dataset
from wrf import getvar, rh, to_np, ll_to_xy
import numpy as np
import pandas as pd  # Standard pandas module for table formatting

# Base directory and WRF file paths
base_dir = "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2021_new_GFS_000/"
before_da_file = os.path.join(base_dir, "Before_DA", "wrfout_d01_2021-07-14_18_00_00")
after_da_file = os.path.join(base_dir, "After_DA", "wrfout_d01_2021-07-14_18_00_00")

# General station list (Name, Latitude, Longitude)
general_stations = [
    ("Briedfeld", 50.12385000, 6.06622000),
    ("Echternach", 49.80310000, 6.44337000),
    ("Ettelbruck", 49.85172000, 6.09754000),
    ("Oberkorn", 49.51220000, 5.90110000),
    ("Remerschen", 49.49100000, 6.34900000),
    ("Findel", 49.63265182, 6.23292867),
    ("Roodt", 49.79450000, 5.82020000),
    ("Hosingen", 49.99314000, 6.10147000),
    ("Useldange", 49.76739000, 5.96748000),
    ("Mamer", 49.63353000, 6.01930000),
    ("Arsdorf", 49.85891000, 5.84868000),
    ("Asselborn", 50.09685689, 5.96960753),
    ("Grevenmacher", 49.68087000, 6.43541000),
    ("Schimpach", 50.00930000, 5.84750000),
    ("Waldbillig", 49.79806000, 6.27730000),
    ("Bettendorf", 49.87410000, 6.20950000),
    ("Fouhren", 49.91445000, 6.19508000),
    ("Beringen", 49.76200000, 6.11179000),
    ("Dahl", 49.93595000, 5.98093000),
]

# Function to extract variables and return as DataFrame
def extract_vars_from_wrf(wrf_file, label, stations):
    try:
        # Open WRF file
        ncfile = Dataset(wrf_file)
        
        # Extract variables
        temp = getvar(ncfile, "tk", timeidx=0, meta=True)  # Model Level 0 Temperature (K)
        qv = getvar(ncfile, "QVAPOR", timeidx=0, meta=True)  # Water vapor mixing ratio
        pres = getvar(ncfile, "pressure", timeidx=0, meta=True) * 100  # Convert hPa to Pa
        rh_data = rh(qv, pres, temp, meta=True)  # Relative Humidity (%)
        temp2 = getvar(ncfile, "T2", timeidx=0, meta=True)  # 2m Temperature (K)
        rainc = getvar(ncfile, "RAINC", timeidx=0, meta=True)
        rainnc = getvar(ncfile, "RAINNC", timeidx=0, meta=True)

        try:
            rainsh = getvar(ncfile, "RAINSH", timeidx=0, meta=True)
        except Exception:
            rainsh = 0  # Default to zero if RAINSH is not available

        precip = rainc + rainnc + rainsh  # Total precipitation

        # Extract simulation time
        times = to_np(getvar(ncfile, "Times", timeidx=0))
        if isinstance(times, np.ndarray) and times.dtype.type is np.bytes_:
            time_str = ''.join(t.decode('utf-8', errors='ignore').strip() for t in times)
        else:
            time_str = str(times)

        # Store station data
        data_list = []
        for station in stations:
            name, lat, lon = station
            x, y = ll_to_xy(ncfile, lat, lon)

            # Extract values at the grid point
            station_rh = to_np(rh_data[0, y, x])
            station_temp = to_np(temp[0, y, x])
            station_t2 = to_np(temp2[y, x])
            station_precip = to_np(precip[y, x])

            data_list.append([name, lat, lon, station_rh, station_temp, station_t2, station_precip])

        # Close the NetCDF file
        ncfile.close()

        # Convert to DataFrame
        df = pd.DataFrame(data_list, columns=["Station", "Latitude", "Longitude", "RH (%)", "Temp (K)", "T2 (K)", "Precipitation"])
        return time_str, df

    except Exception as e:
        print(f"Error processing {wrf_file}: {e}")
        return None, None

# Extract and display data for Before DA
time_before, df_before = extract_vars_from_wrf(before_da_file, "Before DA", general_stations)
if df_before is not None:
    print(f"\nBefore DA Data (File: {before_da_file}, Time: {time_before})")
    print(df_before.to_string(index=False))  # Prints formatted table

# Extract and display data for After DA
time_after, df_after = extract_vars_from_wrf(after_da_file, "After DA", general_stations)
if df_after is not None:
    print(f"\nAfter DA Data (File: {after_da_file}, Time: {time_after})")
    print(df_after.to_string(index=False))  # Prints formatted table
