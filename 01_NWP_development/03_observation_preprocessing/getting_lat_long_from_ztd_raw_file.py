# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import os
import zipfile
import gzip

# Define input directory
base_dir = '/Users/haseeb.rehman/WRF/WRFDA/DAT_DIR/ztd_data_June_july_2021/for_validation'

# Function to convert DMS to decimal degrees
def dms_to_decimal(degrees, minutes, seconds):
    return degrees + minutes / 60 + seconds / 3600

# Function to dynamically search for the metadata line
def find_metadata_line(lines):
    for idx, line in enumerate(lines):
        parts = line.strip().split()
        numeric_fields = [v for v in parts if v.replace('.', '', 1).isdigit()]
        if len(numeric_fields) >= 7:
            return line.strip(), idx  # Return the valid line and its index
    return None, None

# Function to parse metadata from a valid metadata line
def parse_metadata_line(line):
    try:
        parts = line.split()
        if len(parts) < 7:
            raise ValueError("Insufficient fields in metadata line")

        lon_deg, lon_min, lon_sec = float(parts[-7]), float(parts[-6]), float(parts[-5])
        longitude = dms_to_decimal(lon_deg, lon_min, lon_sec)

        lat_deg, lat_min, lat_sec = float(parts[-4]), float(parts[-3]), float(parts[-2])
        latitude = dms_to_decimal(lat_deg, lat_min, lat_sec)

        return latitude, longitude
    except Exception as e:
        print(f"Error parsing metadata line: {e}")
        return -999, -999

# Function to extract metadata (lat, lon) from `.trop` files
def extract_lat_lon(file_content, site_coordinates):
    try:
        lines = file_content.decode('utf-8').splitlines()
        metadata_line, line_idx = find_metadata_line(lines)
        if not metadata_line:
            raise ValueError("Metadata line not found")

        site = lines[line_idx].split()[0] if len(lines[line_idx].split()) > 0 else "UNKNOWN"
        
        if site not in site_coordinates:
            latitude, longitude = parse_metadata_line(metadata_line)
            site_coordinates[site] = (latitude, longitude)
    except Exception as e:
        print(f"Error processing .trop file: {e}")

# Main processing function
def main():
    site_coordinates = {}
    
    # Iterate through all zip files in the base directory
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    for nested_file in zip_ref.namelist():
                        if nested_file.endswith('.gz'):
                            with zip_ref.open(nested_file) as gz_file:
                                with gzip.open(gz_file, 'rb') as trop_file:
                                    file_content = trop_file.read()
                                    extract_lat_lon(file_content, site_coordinates)
    
    # Print unique site coordinates
    for site, (latitude, longitude) in site_coordinates.items():
        print(f"Site: {site}, Latitude: {latitude:.3f}, Longitude: {longitude:.3f}")

if __name__ == "__main__":
    main()
