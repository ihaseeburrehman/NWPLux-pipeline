import os
import pandas as pd
from datetime import datetime, timedelta


# Define the input folder path
input_folder = '/Users/haseeb.rehman/Downloads/GNSS_Lux_July_2021_event/archive-ZTD-LUXMBOURG/'

# Define the output folder path
output_folder = '/Users/haseeb.rehman/Downloads/Lux_ZTD_ASCII/'

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Define the station coordinates
station_coordinates = {
    "BASC": {"Latitude_SPS": 49.56793784, "Longitude_SPS": 5.93926708, "Height": 330.7800},
    "KBG2": {"Latitude_SPS": 49.62542749, "Longitude_SPS": 6.15948059, "Height": 359.8490},
    "ECH2": {"Latitude_SPS": 49.80305460, "Longitude_SPS": 6.44310355, "Height": 255.3950},
    "ERPL": {"Latitude_SPS": 49.54779150, "Longitude_SPS": 6.32318128, "Height": 172.4010},
    "ROUL": {"Latitude_SPS": 49.95142301, "Longitude_SPS": 5.91781449, "Height": 497.3920},
    "TROS": {"Latitude_SPS": 50.12673722, "Longitude_SPS": 6.00729884, "Height": 492.8320},
    "WALF": {"Latitude_SPS": 49.65814232, "Longitude_SPS": 6.13158256, "Height": 247.4110},
    "KBG1": {"Latitude_SPS": 49.62542800, "Longitude_SPS": 6.15948100, "Height": 359.8690},
}

# Function to convert the date and time format
def convert_date_time(epoch_str):
    # Split the epoch_str into its components
    year_str, day_str, time_str = epoch_str.split(':')

    # Convert the components to integers
    year = int(year_str) + 2000  # Assuming it represents years in the 21st century
    day_of_year = int(day_str)
    time_seconds = int(time_str)

    # Calculate the date and time
    dt = datetime(year, 1, 1) + timedelta(days=day_of_year - 1, seconds=time_seconds)
    
    # Format the date and time as required
    formatted_date_time = dt.strftime("%Y-%m-%d_%H:%M:%S")
    
    return formatted_date_time

# ...

# Create a dictionary to store data frames for each date and time
data_frames = {}

# Iterate through the subfolders
for subfolder in os.listdir(input_folder):
    subfolder_path = os.path.join(input_folder, subfolder)
    
    # Iterate through the files in the 'ATM' subfolder
    for filename in os.listdir(os.path.join(subfolder_path, 'ATM')):
        if filename.endswith('.TRO.gz'):
            file_path = os.path.join(subfolder_path, 'ATM', filename)
            
            # Read the data, skipping the first 34 lines, and use the correct column names
            df = pd.read_csv(file_path, delim_whitespace=True, skiprows=34, usecols=['*SITE', '____EPOCH___', 'TROTOT'])
            
            # Remove lines containing "-TROP/SOLUTION" and "%=ENDTRO" at the end of the file
            while not df.empty and (df['*SITE'].iloc[-1] == '-TROP/SOLUTION' or df['*SITE'].iloc[-1] == '%=ENDTRO'):
                df = df.iloc[:-1]

            # Check if there are any rows left after removing the lines
            if not df.empty:
                # Extract relevant columns and convert units
                df['Date_Time'] = df['____EPOCH___'].apply(convert_date_time)
                df['ZTD'] = df['TROTOT'] / 10  # Convert from millimeters to centimeters
                df['Latitude_SPS'] = df['*SITE'].map(lambda x: station_coordinates.get(x, {}).get('Latitude_SPS', ''))
                df['Longitude_SPS'] = df['*SITE'].map(lambda x: station_coordinates.get(x, {}).get('Longitude_SPS', ''))
                df['Height'] = df['*SITE'].map(lambda x: station_coordinates.get(x, {}).get('Height', ''))
                
                # Iterate through rows and add them to the appropriate data frame based on date and time
                for index, row in df.iterrows():
                    date_time = row['Date_Time']
                    if date_time not in data_frames:
                        data_frames[date_time] = pd.DataFrame(columns=df.columns)
                    data_frames[date_time] = pd.concat([data_frames[date_time], row.to_frame().T])

# Create the output files for each date and time
for date_time, data_frame in data_frames.items():
    # Create the output file name
    output_filename = f"ob_{date_time}.ascii"
    output_filepath = os.path.join(output_folder, output_filename)

    # Create constant values
    constant_values = "-888888.000 -88 200.00"

    # Create the output file content with two lines for each timestamp
    with open(output_filepath, 'w') as f:
        for index, row in data_frame.iterrows():
            f.write(f"FM-114 GPSZD {row['Date_Time']}{row['*SITE']}                                     0      {row['Latitude_SPS']:.3f}                  {row['Longitude_SPS']:.3f}                {row['Height']:.3f}\n")
            f.write(f"{constant_values}       {row['ZTD']:.3f}   0  0.800\n")

    print(f"Processed: {output_filename}")

print("Conversion completed.")


