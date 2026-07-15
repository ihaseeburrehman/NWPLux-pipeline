# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import geopandas as gpd
from shapely.geometry import LineString
import rasterio

print("=" * 120)
print("CREATING BOUNDARY CONDITION SHAPEFILE")
print("=" * 120)

# DEM path to get extents
dem_path = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing/Alzette_5m_bathymetery.asc'

# Boundary specification
boundary_type = 'N'  # North
x_start = 75641.0
x_end = 75666.0

print(f"\nBoundary specification:")
print(f"  Type: {boundary_type} (North boundary)")
print(f"  X-coordinates: {x_start} to {x_end}")
print(f"  Condition: FREE")

# Read DEM to get Y coordinate
with rasterio.open(dem_path) as src:
    bounds = src.bounds
    crs = src.crs
    
    print(f"\nDEM CRS: {crs}")
    print(f"Domain extents:")
    print(f"  X: {bounds.left:.3f} to {bounds.right:.3f}")
    print(f"  Y: {bounds.bottom:.3f} to {bounds.top:.3f}")

# For North boundary, Y is at the top
y_coord = bounds.top

# Create line geometry
line = LineString([(x_start, y_coord), (x_end, y_coord)])

print(f"\nBoundary line:")
print(f"  Start point: ({x_start}, {y_coord})")
print(f"  End point: ({x_end}, {y_coord})")
print(f"  Length: {x_end - x_start:.1f} m")

# Create GeoDataFrame
gdf = gpd.GeoDataFrame({
    'type': [boundary_type],
    'condition': ['FREE'],
    'x_start': [x_start],
    'x_end': [x_end],
    'y_coord': [y_coord],
    'length_m': [x_end - x_start],
    'description': [f'{boundary_type} {x_start} {x_end} FREE']
}, geometry=[line], crs=crs)

# Output path
output_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/bathymetry_processing'
output_shp = f'{output_dir}/boundary_condition.shp'

# Save shapefile
gdf.to_file(output_shp)

print(f"\n✓ Shapefile saved to: {output_shp}")

# Also save as GeoJSON for easier viewing
output_geojson = f'{output_dir}/boundary_condition.geojson'
gdf.to_file(output_geojson, driver='GeoJSON')

print(f"✓ GeoJSON saved to: {output_geojson}")

# Display info
print(f"\nShapefile contents:")
print(gdf.to_string())

print("\n" + "=" * 120)
print("SHAPEFILE CREATED")
print("=" * 120)
print(f"\nYou can now open this shapefile in QGIS or ArcGIS:")
print(f"  {output_shp}")
print(f"\nThe shapefile contains:")
print(f"  - Geometry: LineString (2 points)")
print(f"  - CRS: {crs}")
print(f"  - Attributes:")
print(f"      type: {boundary_type}")
print(f"      condition: FREE")
print(f"      x_start: {x_start}")
print(f"      x_end: {x_end}")
print(f"      y_coord: {y_coord}")
print(f"      length_m: {x_end - x_start}")
print(f"      description: N {x_start} {x_end} FREE")
print("=" * 120)
