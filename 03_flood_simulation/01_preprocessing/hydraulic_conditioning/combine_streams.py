# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import geopandas as gpd
from shapely.ops import unary_union
import os

input_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/pre_processing/streams_alzette_basin.shp'
output_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/pre_processing/streams_alzette_basin_combine.shp'

if not os.path.exists(input_path):
    print(f"Error: Could not find input file at {input_path}")
else:
    print(f"Loading streams from {input_path}...")
    gdf = gpd.read_file(input_path)
    
    print(f"Combining {len(gdf)} segments into a single geometry...")
    # unary_union will merge all geometries into a single MultiLineString
    combined_geom = unary_union(gdf.geometry)
    
    # Create a new GeoDataFrame with the combined geometry
    new_gdf = gpd.GeoDataFrame(geometry=[combined_geom], crs=gdf.crs)
    
    # Save the combined shapefile
    print(f"Saving combined streams to {output_path}...")
    new_gdf.to_file(output_path)
    print("Done! All streams have been joined into a single MultiLineString.")
