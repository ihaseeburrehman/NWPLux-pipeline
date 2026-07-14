import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# Function to parse station data for a specific type
def parse_station_data(lines, station_type_key):
    station_data = []
    for line in lines:
        if station_type_key in line:
            parts = line.split()
            try:
                # Extract station type, timestamp, latitude, longitude, elevation, and station ID
                station_type = f"{parts[0]} {parts[1]}"  # Station type (e.g., FM-12 SYNOP)
                timestamp = parts[2]  # Timestamp
                latitude = float(parts[5])  # Latitude (5th column)
                longitude = float(parts[6])  # Longitude (6th column)
                elevation = float(parts[7])  # Elevation (7th column)
                name = parts[3]  # Station ID (8th column)
                
                # Ensure valid latitude and longitude
                if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                    station_data.append((station_type, timestamp, latitude, longitude, elevation, name))
                else:
                    print(f"Invalid coordinates: {latitude}, {longitude} in line: {line.strip()}")
            except (ValueError, IndexError) as e:
                # Log parsing errors for debugging
                print(f"Error parsing line: {line.strip()} | Error: {e}")
                continue
    return station_data

# File paths
input_file = "/Users/haseeb.rehman/Downloads/concatenate_June_July_2021_event/sample"
output_dir = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/"

# Read the file
with open(input_file, 'r') as file:
    lines = file.readlines()

# Skip header (first 21 lines)
lines = lines[21:]

# Parse data for each station type
station_types_data = {
    "SYNOP": parse_station_data(lines, "FM-12 SYNOP"),
    "TEMP": parse_station_data(lines, "FM-35 TEMP"),
    "TAMDAR": parse_station_data(lines, "FM-101 TAMDA"),
    "GPSZD": parse_station_data(lines, "FM-114 GPSZD"),
}

# Process and save shapefiles
for station_type, data in station_types_data.items():
    if data:
        # Convert to DataFrame
        columns = ['Type', 'Timestamp', 'Latitude', 'Longitude', 'Elevation', 'Name']
        df = pd.DataFrame(data, columns=columns)
        
        # Debug: Print a sample of parsed data
        print(f"Sample data for {station_type}:\n{df.head(5)}")
        
        # Convert to GeoDataFrame
        geometry = [Point(xy) for xy in zip(df['Longitude'], df['Latitude'])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
        
        # Save to shapefile
        shapefile_path = f"{output_dir}{station_type}_data.shp"
        gdf.to_file(shapefile_path)
        print(f"{station_type} shapefile created at: {shapefile_path}")
    else:
        print(f"No data found for {station_type}.")
