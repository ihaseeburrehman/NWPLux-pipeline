# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import os
import zipfile
import gzip
import pandas as pd
from datetime import datetime, timedelta

# Define input directory and output file
base_dir = '/Users/haseeb.rehman/WRF/WRFDA/DAT_DIR/ztd_data_July_August_2016/for_validation'
output_excel_path = os.path.join(base_dir, "ztd_data.xlsx")

# Function to check if a file corresponds to months
def is_june_or_july(file_name):
    try:
        parts = file_name.split('.')
        year = int(parts[1])  # Extract year
        day_of_year = int(parts[2])  # Extract day of year
        date = datetime(year=2000 + year, month=1, day=1) + timedelta(days=day_of_year - 1)
        return date.month in [7, 8]
    except Exception:
        return False

# Function to extract ZTD data from `.trop` files
def process_trop_file(file_content):
    hourly_data = []

    try:
        lines = file_content.decode('utf-8').splitlines()
        ztd_start_idx = None
        for idx, line in enumerate(lines):
            if line.startswith('*SITE ___EPOCH____ TROTOT'):
                ztd_start_idx = idx + 1
                break
        if ztd_start_idx is None:
            return hourly_data

        for line in lines[ztd_start_idx:]:
            if line.strip() == "" or line.startswith('%=ENDTRO'):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            epoch = parts[1]
            trot = float(parts[2]) / 10.0  # Convert TROTOT from mm to cm
            try:
                year, day_of_year, seconds = map(int, epoch.split(':'))
                date_time = datetime(year=2000 + year, month=1, day=1) + timedelta(days=day_of_year - 1, seconds=seconds)

                # Ensure format is YYYY-MM-DD HH
                formatted_datetime = date_time.strftime("%Y-%m-%d %H")

                hourly_data.append({
                    "UTC_Datetime": formatted_datetime,
                    "ZTD (m)": trot / 100,  # Convert to meters
                })
            except Exception:
                continue
    except Exception:
        pass

    return hourly_data

# Main processing function
def main():
    all_data = {}  # Dictionary to store DataFrames for each station

    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for nested_file in zip_ref.namelist():
                        if nested_file.endswith('.gz') and is_june_or_july(nested_file):
                            station_name = nested_file.split('.')[0]  # Extract station name (before first '.')

                            with zip_ref.open(nested_file) as gz_file:
                                with gzip.open(gz_file, 'rb') as trop_file:
                                    file_content = trop_file.read()
                                    hourly_data = process_trop_file(file_content)

                                    if hourly_data:
                                        df = pd.DataFrame(hourly_data)

                                        # Ensure consistent datetime format
                                        df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], format="%Y-%m-%d %H")

                                        # Append data if station already exists, otherwise create new DataFrame
                                        if station_name in all_data:
                                            all_data[station_name] = pd.concat([all_data[station_name], df], ignore_index=True)
                                        else:
                                            all_data[station_name] = df

    # Save to Excel with multiple sheets and set correct datetime format
    with pd.ExcelWriter(output_excel_path, engine='xlsxwriter') as writer:
        for station, df in all_data.items():
            # Sort by datetime to ensure correct order
            df = df.sort_values(by="UTC_Datetime")

            # Convert `UTC_Datetime` to string to avoid Excel formatting issues
            df["UTC_Datetime"] = df["UTC_Datetime"].dt.strftime("%Y-%m-%d %H")

            # Save each station's data in its own sheet
            df.to_excel(writer, sheet_name=station[:31], index=False)

            # Apply proper format to avoid Excel default date-time formatting
            workbook  = writer.book
            worksheet = writer.sheets[station[:31]]
            datetime_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh'})  # Ensure correct format

            worksheet.set_column('A:A', 20, datetime_format)  # Apply format to first column (UTC_Datetime)

    print(f"Excel file saved at {output_excel_path}")

if __name__ == "__main__":
    main()
