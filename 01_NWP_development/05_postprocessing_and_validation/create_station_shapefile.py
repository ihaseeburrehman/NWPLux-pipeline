#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Script to create a shapefile from Luxembourg ASTA station coordinates.
"""
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd

# Station coordinates (name, lat, lon)
stations = [
    ("Briedfeld", 50.12385, 6.06622), 
    ("Echternach", 49.8031, 6.44337), 
    ("Ettelbruck", 49.85172, 6.09754),
    ("Oberkorn", 49.5122, 5.9011), 
    ("Remerschen", 49.491, 6.349), 
    ("Findel", 49.63265182, 6.23292867),
    ("Roodt", 49.7945, 5.8202), 
    ("Hosingen", 49.99314, 6.10147), 
    ("Useldange", 49.76739, 5.96748),
    ("Mamer", 49.63353, 6.0193), 
    ("Arsdorf", 49.85891, 5.84868), 
    ("Asselborn", 50.09685689, 5.96960753),
    ("Grevenmacher", 49.68087, 6.43541), 
    ("Schimpach", 50.0093, 5.8475), 
    ("Waldbillig", 49.79806, 6.2773),
    ("Bettendorf", 49.8741, 6.2095), 
    ("Fouhren", 49.91445, 6.19508), 
    ("Beringen", 49.762, 6.11179),
    ("Dahl", 49.93595, 5.98093)
]

# Create DataFrame
df = pd.DataFrame(stations, columns=['Station', 'Lat', 'Lon'])

# Create geometry (Point from lon, lat)
geometry = [Point(lon, lat) for _, lat, lon in stations]

# Create GeoDataFrame
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# Output path
output_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Lux_ASTA_Stations.shp"

# Save to shapefile
gdf.to_file(output_path)

print(f"Shapefile saved to: {output_path}")
print(f"Total stations: {len(gdf)}")
print("\nStation list:")
for idx, row in gdf.iterrows():
    print(f"  {row['Station']}: ({row['Lat']:.4f}, {row['Lon']:.4f})")
