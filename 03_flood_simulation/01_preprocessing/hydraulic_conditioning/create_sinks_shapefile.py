# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point
import pandas as pd

# File path
dem_file = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/Alzette_5m_bathymetery.asc'

print("=" * 100)
print("CREATING SHAPEFILE FOR TOP 3 DEEPEST SINKS")
print("=" * 100)

# Read the CSV that was created earlier (much faster than recalculating)
csv_file = '/Users/haseeb.rehman/Python scripts/Bathymetrery_processing/sinks_detailed.csv'

print(f"\nReading sinks from: {csv_file}")
df = pd.read_csv(csv_file)

print(f"Total sinks in CSV: {len(df)}")

# Sort by sink_depth descending and get top 3
df_sorted = df.sort_values('sink_depth', ascending=False)
top_3 = df_sorted.head(3).reset_index(drop=True)

print("\nTop 3 Deepest Sinks:")
print("-" * 100)
print(f"{'Rank':<6} {'Row':<7} {'Col':<7} {'X':<12} {'Y':<12} {'Elevation':<12} {'Depth':<10}")
print("-" * 100)

# Create geometries and attributes
geometries = []
attributes = []

for idx, row in top_3.iterrows():
    rank = idx + 1
    print(f"{rank:<6} {row['row']:<7} {row['col']:<7} {row['x']:<12.2f} {row['y']:<12.2f} {row['elevation']:<12.4f} {row['sink_depth']:<10.4f}")
    
    # Create point geometry
    point = Point(row['x'], row['y'])
    geometries.append(point)
    
    # Add attributes
    attributes.append({
        'rank': rank,
        'row': int(row['row']),
        'col': int(row['col']),
        'elevation': round(row['elevation'], 4),
        'min_neighb': round(row['min_neighbor_elev'], 4),
        'sink_depth': round(row['sink_depth'], 4),
        'n_neighbor': int(row['n_neighbors']),
        'descrip': f"Sink #{rank}: {row['sink_depth']:.2f}m deep"
    })

# Get CRS from DEM
with rasterio.open(dem_file) as src:
    crs = src.crs

print(f"\nUsing CRS: {crs}")

# Create GeoDataFrame
gdf = gpd.GeoDataFrame(attributes, geometry=geometries, crs=crs)

# Save as shapefile
output_shapefile = '/Users/haseeb.rehman/Python scripts/Bathymetrery_processing/top_3_deepest_sinks.shp'
gdf.to_file(output_shapefile)

print("\n" + "=" * 100)
print("SHAPEFILE CREATED")
print("=" * 100)
print(f"\n✓ Saved to: {output_shapefile}")
print(f"\nThe shapefile contains:")
print(f"  - 3 point features (one for each sink)")
print(f"  - Attributes:")
print(f"      rank        - Ranking (1=deepest)")
print(f"      row         - DEM row index")
print(f"      col         - DEM column index")
print(f"      elevation   - Elevation at sink (m)")
print(f"      min_neighb  - Minimum neighbor elevation (m)")
print(f"      sink_depth  - Depth below neighbors (m)")
print(f"      n_neighbor  - Number of valid neighbors")
print(f"      descrip     - Text description")
print(f"  - CRS: {crs}")

# Also save as GeoJSON for easier viewing
output_geojson = '/Users/haseeb.rehman/Python scripts/Bathymetrery_processing/top_3_deepest_sinks.geojson'
gdf.to_file(output_geojson, driver='GeoJSON')
print(f"\n✓ Also saved as GeoJSON: {output_geojson}")

# Display GeoDataFrame info
print("\nGeoDataFrame contents:")
print(gdf.to_string())

# Create a buffer around each sink (50m radius) for easier visualization
gdf_buffered = gdf.copy()
gdf_buffered['geometry'] = gdf_buffered.geometry.buffer(50)  # 50m buffer

output_buffer_shp = '/Users/haseeb.rehman/Python scripts/Bathymetrery_processing/top_3_sinks_50m_buffer.shp'
gdf_buffered.to_file(output_buffer_shp)
print(f"\n✓ Also created 50m buffer shapefile: {output_buffer_shp}")

print("\n" + "=" * 100)
print("USAGE INSTRUCTIONS")
print("=" * 100)
print("""
You can now:
  1. Open these shapefiles in QGIS or ArcGIS
  2. Overlay them on your DEM to see the exact sink locations
  3. Check if these locations correspond to:
     - Bathymetry interpolation errors
     - River channel cross-sections
     - Other topographic features
  4. The 50m buffer file helps visualize the area around each sink
  
Next steps:
  - Inspect these locations in your original bathymetry data
  - Consider filling these sinks if they're artifacts
  - Check if water depth at 19 hours shows accumulation at these locations
""")

print("\n" + "=" * 100)
print("Complete!")
