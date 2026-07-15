# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import netCDF4
import wrf
import numpy as np
import csv
import matplotlib.pyplot as plt
#The algorithm used to calculate PW is based on the method described by Wang and Zhang (2013)



# File paths to your WRF output files
first_guess_path = "/Users/haseeb.rehman/WRF/WRFV4.5/run/wrfout_d01_2021-07-14_06_00_00_copy"
analysis_file_path = "/Users/haseeb.rehman/WRF/WRFDA/WORK_DIR/wrfvar_output14-06hr"


# List of coordinates (latitude, longitude) and their corresponding names
coordinates = [
    ("BASC", 49.56793784, 5.93926708),
    ("KBG2", 49.62542749, 6.15948059),
    ("ECH2", 49.80305460, 6.44310355),
    ("ERPL", 49.54779150, 6.32318128),
    ("ROUL", 49.95142301, 5.91781449),
    ("TROS", 50.12673722, 6.00729884),
    ("WALF", 49.65814232, 6.13158256),
    ("KBG1", 49.62542800, 6.15948100)
]


# Function to extract PW data from a given file path
def extract_pw_data(file_path):
    with netCDF4.Dataset(file_path) as wrfnc:
        varname = 'pw'  # pressure-wet bulb
        pw_data = wrf.getvar(wrfnc, varname, timeidx=-1, method='cat', squeeze=True, cache=None, meta=True)
        lats, lons = wrf.latlon_coords(pw_data, as_np=True)
        data = []
        for name, lat, lon in coordinates:
            x, y = wrf.ll_to_xy(wrfnc, lat, lon)
            x = int(x.values)
            y = int(y.values)
            pw_at_lat_lon = pw_data[y, x]
            data.append(float(pw_at_lat_lon))
        return data

# Extract data for both files
pw_first_guess = extract_pw_data(first_guess_path)
pw_analysis_file = extract_pw_data(analysis_file_path)

# Extract station names
station_names = [name for name, _, _ in coordinates]

# Extract data for both files
data_first_guess = extract_pw_data(first_guess_path)
data_analysis_file = extract_pw_data(analysis_file_path)

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(station_names, pw_first_guess, label='PW First Guess', marker='o')
plt.plot(station_names, pw_analysis_file, label='PW Analysis File', marker='x')
plt.xlabel('Station Name')
plt.ylabel('PW Value (kg m-2)')
plt.title('Comparison of PW Values - First Guess vs Analysis at 2021-07-14-06 hr')
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()

# Save the plot as a PNG file
png_file_path = '/Users/haseeb.rehman/Desktop/pw_comparison_plot-06hr.png'
plt.savefig(png_file_path)

print(f"Plot saved as {png_file_path}")