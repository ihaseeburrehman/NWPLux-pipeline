# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import pandas as pd
from datetime import datetime, timedelta
import numpy as np

OBS_FILE = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Stations_and_Observations/Discharge_data_walferdange_2021/Alzette_gauges_data_2021.xlsx"
SHEET_NAME = "Pfaffenthal Q15 VO 07 2021"

def extract_data():
    # Read data from Excel
    df = pd.read_excel(OBS_FILE, sheet_name=SHEET_NAME, skiprows=16)
    
    # Parse time (columns 0=Date, 1=Time)
    df['DateTime_Local'] = pd.to_datetime(
        df.iloc[:, 0].astype(str) + ' ' + df.iloc[:, 1].astype(str),
        format='%d.%m.%y %H:%M:%S', errors='coerce'
    )
    
    # The user says "starting from July 13 00 2021"
    # Let's assume this is the timestamp in the Excel file's local time columns
    start_time = datetime(2021, 7, 13, 0, 0, 0)
    end_time = start_time + timedelta(hours=72)
    
    # Get value (column 2)
    value_str = df.iloc[:, 2].astype(str).str.replace(',', '.').replace('---', '')
    df['Discharge_m3s'] = pd.to_numeric(value_str, errors='coerce')
    
    # Filter for the relevant period
    mask = (df['DateTime_Local'] >= start_time) & (df['DateTime_Local'] <= end_time)
    df_filtered = df.loc[mask].copy()
    
    # Calculate elapsed seconds from start_time
    df_filtered['seconds'] = (df_filtered['DateTime_Local'] - start_time).dt.total_seconds()
    
    # Filter for 6-hour intervals (21600 seconds)
    interval = 6 * 3600
    df_6hr = df_filtered[np.abs(df_filtered['seconds'] % interval) < 1.0].copy()
    
    # Scale by 15m (m3/s -> m2/s)
    df_6hr['Discharge_m2s'] = df_6hr['Discharge_m3s'] / 15.0
    
    # Print in the requested format
    for _, row in df_6hr.iterrows():
        print(f"{row['Discharge_m2s']:.6f}    {int(row['seconds'])}")

if __name__ == "__main__":
    extract_data()
