import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import xarray as xr
import numpy as np
import geopandas as gpd
from matplotlib.lines import Line2D
import requests
from io import BytesIO
from PIL import Image

# Define projection (EPSG:4326)
projection = ccrs.PlateCarree()

# Load observation station shapefile
station_path = "/Users/haseeb.rehman/Documents/Misc/Discharge_data_walferdange_2021/location_of_walferdange_area_stations/Walferdange_station.shp"
stations_gdf = gpd.read_file(station_path).to_crs(epsg=4326)

# Get station bounds
station_bounds = stations_gdf.total_bounds  # [minx, miny, maxx, maxy]

# Define LISFLOOD domain extent
domain_lon_min, domain_lat_min = 6.078567232106224, 49.64497057062498
domain_lon_max, domain_lat_max = 6.171199700005181, 49.67548366312442

# Combine extents
lon_min = min(domain_lon_min, station_bounds[0]) - 0.01
lon_max = max(domain_lon_max, station_bounds[2]) + 0.01
lat_min = min(domain_lat_min, station_bounds[1]) - 0.01
lat_max = max(domain_lat_max, station_bounds[3]) + 0.01

# Create figure and axis
fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': projection})
ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=projection)

# WMS request (EPSG:4326)
wms_url = "https://wmts1.geoportail.lu/opendata/service"
bbox = f"{lat_min},{lon_min},{lat_max},{lon_max}"  # WMS 1.3.0 expects lat/lon order for EPSG:4326
params = {
    "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
    "LAYERS": "basemap", "STYLES": "", "CRS": "EPSG:4326",
    "BBOX": bbox, "WIDTH": "2048", "HEIGHT": "2048", "FORMAT": "image/jpeg"
}
response = requests.get(wms_url, params=params)
bg_img = Image.open(BytesIO(response.content))
bg_rgb = np.array(bg_img)

# Plot WMS background
ax.imshow(bg_rgb, extent=[lon_min, lon_max, lat_min, lat_max], transform=projection, origin='upper')

# Add borders and coastlines
ax.add_feature(cfeature.BORDERS, edgecolor='black', linewidth=1, linestyle='--')
ax.add_feature(cfeature.COASTLINE, edgecolor='black', linewidth=1)

# Plot LISFLOOD domain box
domain_lons = [domain_lon_min, domain_lon_max, domain_lon_max, domain_lon_min, domain_lon_min]
domain_lats = [domain_lat_min, domain_lat_min, domain_lat_max, domain_lat_max, domain_lat_min]
ax.plot(domain_lons, domain_lats, transform=projection, color='red', linewidth=2)

# Read NetCDF file
nc_file = "/Users/haseeb.rehman/Documents/Misc/WRF_Local_machine/4th_year/2021_ERA5_local_machine_3_domains/After_DA/wrfout_d03_2021-07-14_18_00_00"
ds = xr.open_dataset(nc_file)

# Extract latitude and longitude
lat = ds['XLAT'].isel(Time=0).values
lon = ds['XLONG'].isel(Time=0).values
ny, nx = lat.shape

# Plot WRF grid tiles within LISFLOOD domain
tile_count = 0
for i in range(ny - 1):
    for j in range(nx - 1):
        tile_lons = [lon[i,j], lon[i,j+1], lon[i+1,j+1], lon[i+1,j], lon[i,j]]
        tile_lats = [lat[i,j], lat[i,j+1], lat[i+1,j+1], lat[i+1,j], lat[i,j]]
        tile_lon_min, tile_lon_max = min(tile_lons), max(tile_lons)
        tile_lat_min, tile_lat_max = min(tile_lats), max(tile_lats)
        if (tile_lon_min <= domain_lon_max and tile_lon_max >= domain_lon_min and 
            tile_lat_min <= domain_lat_max and tile_lat_max >= domain_lat_min):
            ax.plot(tile_lons, tile_lats, transform=projection, color='blue', linewidth=0.5, alpha=0.7)
            tile_count += 1

# Plot observation stations in blue
stations_gdf.plot(ax=ax, transform=projection, color='blue', markersize=40, label='Observation Station', zorder=5)
for idx, row in stations_gdf.iterrows():
    ax.text(row.geometry.x, row.geometry.y, row.get('name', f"Station {idx+1}"), fontsize=7,
            transform=projection, ha='left', va='bottom', color='blue')

# Add gridlines with alternating labels (keep all gridlines visible in light green)
import matplotlib.ticker as mticker

# First, draw gridlines WITHOUT labels at fine intervals (all gridlines visible)
gl_no_labels = ax.gridlines(draw_labels=False, linestyle="--", alpha=0.5, color='grey', linewidth=0.8)
gl_no_labels.xlocator = mticker.MultipleLocator(0.02)  # Gridline every 0.01 degrees
gl_no_labels.ylocator = mticker.MultipleLocator(0.02)  # Gridline every 0.01 degrees

# Then, draw gridlines WITH labels at double the interval (every other gridline gets labeled)
gl = ax.gridlines(draw_labels=True, linestyle="--", alpha=0.5, color='grey', linewidth=0.8)
gl.xlocator = mticker.MultipleLocator(0.02)  # Label every 0.02 degrees (every other gridline)
gl.ylocator = mticker.MultipleLocator(0.02)  # Label every 0.02 degrees (every other gridline)
gl.right_labels = False
gl.top_labels = False
gl.xlabel_style = {'size': 10, 'color': 'black'}
gl.ylabel_style = {'size': 10, 'color': 'black'}

# Add legend
legend_elements = [
    Line2D([0], [0], color='red', linewidth=2, label='LISFLOOD_Domain'),
    Line2D([0], [0], color='blue', linewidth=0.5, label='WRF_grid'),
    Line2D([0], [0], marker='o', color='blue', label='Observation Station', markersize=6, linestyle='None')
]
ax.legend(handles=legend_elements, loc='upper right', fontsize=8)

# Save the figure
save_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/10m/domain_Lisflood_with_stations.png"
os.makedirs(os.path.dirname(save_path), exist_ok=True)
plt.savefig(save_path, dpi=300, bbox_inches="tight")
plt.show()

print(f"✅ Map saved at: {save_path}")
print(f"📦 Number of WRF tiles within LISFLOOD domain: {tile_count}")
