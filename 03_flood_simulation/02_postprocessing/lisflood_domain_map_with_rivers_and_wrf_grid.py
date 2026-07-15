# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os
import xarray as xr
import numpy as np
import geopandas as gpd
from matplotlib.lines import Line2D
import matplotlib.ticker as mticker
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from matplotlib.ticker import FormatStrFormatter

# Define projection (EPSG:4326)
projection = ccrs.PlateCarree()

# Load observation station shapefile
station_path = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Stations_and_Observations/Discharge_data_walferdange_2021/location_of_walferdange_area_stations/Walferdange_station.shp"
stations_gdf = gpd.read_file(station_path).to_crs(epsg=4326)

# Extract sub-basin boundary from DEM instead of using shapefile
print("\n📍 Extracting sub-basin boundary from DEM...")
dem_path_for_boundary = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/ready_for_simulation/Alzette_sub_basin_10m_bridge_burn.asc"

from rasterio.features import shapes as rasterio_shapes
from shapely.geometry import shape
from shapely.ops import unary_union

with rasterio.open(dem_path_for_boundary) as src:
    dem_data = src.read(1)
    transform = src.transform
    src_crs = src.crs if src.crs else 'EPSG:2169'
    
    # Create mask of valid pixels
    valid_mask = (dem_data != -9999).astype('uint8')
    
    # Extract polygons from valid pixels
    polygons = []
    for geom, value in rasterio_shapes(valid_mask, transform=transform):
        if value == 1:
            polygons.append(shape(geom))
    
    # Merge into single polygon
    basin_polygon = unary_union(polygons) if len(polygons) > 1 else polygons[0]
    
    # Create GeoDataFrame
    sub_basin_gdf = gpd.GeoDataFrame({'id': [1]}, geometry=[basin_polygon], crs=src_crs)
    sub_basin_gdf = sub_basin_gdf.to_crs(epsg=4326)
    
    print(f"   ✓ Extracted boundary from {len(polygons)} polygon(s)")
    print(f"   ✓ Basin area: {basin_polygon.area / 1e6:.2f} km²")


# Load full Alzette basin (for inset map)
full_basin_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/Alzette_basin_cleaned.shp"
full_basin_gdf = gpd.read_file(full_basin_path)
# Set CRS if not defined
if full_basin_gdf.crs is None:
    full_basin_gdf = full_basin_gdf.set_crs(epsg=2169)
full_basin_gdf = full_basin_gdf.to_crs(epsg=4326)

# Load Alzette river shapefile
river_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/pre_processing/alzette_river.shp"
river_gdf = gpd.read_file(river_path).to_crs(epsg=4326)

# Load streams shapefile
streams_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/5m/sub_basin_complete/pre_processing/streams_alzette_basin.shp"
streams_gdf = gpd.read_file(streams_path).to_crs(epsg=4326)

# Load countries for inset map
countries_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Countries_near_Lux.shp"
countries_gdf = gpd.read_file(countries_path).to_crs(epsg=4326)

# Load Luxembourg boundary for inset
lux_boundary_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Luxembourg_Regions.shp"
lux_boundary_gdf = gpd.read_file(lux_boundary_path).to_crs(epsg=4326)

# Get extent from sub-basin shapefile
sub_basin_bounds = sub_basin_gdf.total_bounds  # [minx, miny, maxx, maxy]

# Define LISFLOOD domain extent from sub-basin bounds with small buffer
domain_lon_min = sub_basin_bounds[0]
domain_lat_min = sub_basin_bounds[1] 
domain_lon_max = sub_basin_bounds[2]
domain_lat_max = sub_basin_bounds[3]

# Apply buffer for map extent
lon_min = domain_lon_min - 0.01
lon_max = domain_lon_max + 0.01
lat_min = domain_lat_min - 0.01
lat_max = domain_lat_max + 0.01

# Create figure and axis with white background
fig, ax = plt.subplots(figsize=(12, 10), subplot_kw={'projection': projection})
ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=projection)
ax.set_facecolor('white')  # White background

# Fix aspect ratio to match Manning map (correcting for latitude distortion)
# Aspect ratio = 1 / cos(latitude)
mean_lat = (lat_min + lat_max) / 2
aspect_ratio = 1.0 / np.cos(np.radians(mean_lat))
ax.set_aspect(aspect_ratio, adjustable='box') # 'box' ensures extent is preserved


# --- PLOT DEM BACKGROUND ---
dem_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/ready_for_simulation/Alzette_sub_basin_10m_bridge_burn.asc"

print("\n📊 Loading DEM for background...")
# Read and reproject DEM to EPSG:4326 for plotting
dst_crs = 'EPSG:4326'
try:
    with rasterio.open(dem_path) as src:
        # Read DEM data
        dem_data = src.read(1)
        
        # Assume EPSG:2169 if not defined
        src_crs = src.crs if src.crs else 'EPSG:2169'
        print(f"   DEM Source CRS: {src_crs}")
        print(f"   DEM Shape: {src.shape}")
        print(f"   DEM Bounds (source): {src.bounds}")
        
        # Check valid data in source
        valid_source = np.sum(dem_data != -9999)
        print(f"   Valid pixels in source: {valid_source:,}")
        
        transform, width, height = calculate_default_transform(
            src_crs, dst_crs, src.width, src.height, *src.bounds)
        
        print(f"   Reprojected shape: {height} x {width}")
        
        # Destination array - initialize with nodata
        destination = np.full((height, width), -9999, dtype=np.float32)
        
        reproject(
            source=dem_data,
            destination=destination,
            src_transform=src.transform,
            src_crs=src_crs,
            dst_transform=transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=-9999,
            dst_nodata=-9999)  # Keep -9999 as nodata

        # Mask nodata values
        dem_masked = np.ma.masked_equal(destination, -9999)
        
        # Calculate extent in EPSG:4326
        bounds = rasterio.transform.array_bounds(height, width, transform)
        dem_extent = [bounds[0], bounds[2], bounds[1], bounds[3]] # [west, east, south, north]
        
        print(f"   DEM Extent (EPSG:4326): West={dem_extent[0]:.4f}, East={dem_extent[1]:.4f}, South={dem_extent[2]:.4f}, North={dem_extent[3]:.4f}")
        
        # Check if we have valid data
        valid_pixels = np.sum(~dem_masked.mask)
        print(f"   Valid DEM pixels: {valid_pixels:,} / {dem_masked.size:,}")
        
        if valid_pixels > 0:
            # Get elevation range for proper colormap scaling
            valid_data = dem_masked[~dem_masked.mask]
            vmin, vmax = valid_data.min(), valid_data.max()
            print(f"   Elevation range: {vmin:.1f} to {vmax:.1f} m")
            
            # Plot DEM with full opacity for clear colors
            im = ax.imshow(dem_masked, extent=dem_extent, transform=ccrs.PlateCarree(), 
                           cmap='Spectral_r', zorder=1, alpha=1.0, interpolation='bilinear',
                           vmin=vmin, vmax=vmax)
            print(f"   ✅ DEM plotted successfully")
        else:
            print(f"   ⚠️  No valid DEM data after reprojection!")
            
except Exception as e:
    print(f"   ❌ Could not plot DEM background. Error: {e}")
    import traceback
    traceback.print_exc()


# Sub-basin boundary removed from main map (shown only in inset)
# sub_basin_gdf.plot(ax=ax, transform=projection, facecolor='none', edgecolor='grey', 
#                    linewidth=0.8, alpha=0.8, zorder=1)


# Plot streams (thinner - 0.5) - now #4a7eff
streams_gdf.plot(ax=ax, transform=projection, color='#4a7eff', linewidth=0.5, 
                 alpha=0.8, zorder=2)

# Plot Alzette river on top (thicker - 0.8) - now #0157ff
river_gdf.plot(ax=ax, transform=projection, color='#0157ff', linewidth=0.8, 
               alpha=0.9, zorder=2.2)

# Configuration Flags
plot_lisflood_domain = False
plot_wrf_grid = False
plot_ecmwf_grid = False  # User requested counting only

# Plot LISFLOOD domain box (LISFLOOD-FP Grid)
if plot_lisflood_domain:
    domain_lons = [domain_lon_min, domain_lon_max, domain_lon_max, domain_lon_min, domain_lon_min]
    domain_lats = [domain_lat_min, domain_lat_min, domain_lat_max, domain_lat_max, domain_lat_min]
    ax.plot(domain_lons, domain_lats, transform=projection, color='red', linewidth=1.5, zorder=3)

# --- WRF GRID COUNTING ---
# Read NetCDF file
nc_file = "/Users/haseeb.rehman/Documents/Misc/From_HPC_and_WRF/WRF_Local_machine/4th_year/2021_ERA5_local_machine_3_domains/After_DA/test/wrfout_d03_2021-07-14_18_00_00"
ds = xr.open_dataset(nc_file)

# Extract latitude and longitude
lat = ds['XLAT'].isel(Time=0).values
lon = ds['XLONG'].isel(Time=0).values
ny, nx = lat.shape

# Count WRF grid tiles within LISFLOOD domain
wrf_tile_count = 0
for i in range(ny - 1):
    for j in range(nx - 1):
        tile_lons = [lon[i,j], lon[i,j+1], lon[i+1,j+1], lon[i+1,j], lon[i,j]]
        tile_lats = [lat[i,j], lat[i,j+1], lat[i+1,j+1], lat[i+1,j], lat[i,j]]
        tile_lon_min, tile_lon_max = min(tile_lons), max(tile_lons)
        tile_lat_min, tile_lat_max = min(tile_lats), max(tile_lats)
        
        # Check if tile intersects with domain (simplified containment check)
        if (tile_lon_min <= domain_lon_max and tile_lon_max >= domain_lon_min and 
            tile_lat_min <= domain_lat_max and tile_lat_max >= domain_lat_min):
            
            if plot_wrf_grid:
                ax.plot(tile_lons, tile_lats, transform=projection, color='green', linewidth=0.3, alpha=0.4, zorder=4)
            wrf_tile_count += 1
ds.close()

# --- ECMWF GRID COUNTING ---
ecmwf_file = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Radar_and_Weather/ecmwf_operational_forecast/ecmwf_operational_fixed_6h_rainfall/2021_07_10_06_00_00.nc"
ds_ecmwf = xr.open_dataset(ecmwf_file)
ecmwf_lat = ds_ecmwf['latitude'].values
ecmwf_lon = ds_ecmwf['longitude'].values

# Create meshgrid for ECMWF
ecmwf_lon_grid, ecmwf_lat_grid = np.meshgrid(ecmwf_lon, ecmwf_lat)
eny, enx = ecmwf_lat_grid.shape

ecmwf_tile_count = 0
# Iterate through ECMWF grid cells (rectilinear)
for i in range(eny - 1):
    for j in range(enx - 1):
        # Define cell bounds
        # Note: ECMWF lat often decreases, so careful with min/max
        lats = [ecmwf_lat_grid[i,j], ecmwf_lat_grid[i+1,j]]
        lons = [ecmwf_lon_grid[i,j], ecmwf_lon_grid[i,j+1]]
        
        cell_min_lat = min(lats)
        cell_max_lat = max(lats)
        cell_min_lon = min(lons)
        cell_max_lon = max(lons)

        # Check intersection with LISFLOOD domain
        if (cell_min_lon <= domain_lon_max and cell_max_lon >= domain_lon_min and 
            cell_min_lat <= domain_lat_max and cell_max_lat >= domain_lat_min):
            
            if plot_ecmwf_grid:
                 # Plot logic if ever needed
                 pass
            ecmwf_tile_count += 1
ds_ecmwf.close()


# Filter out Mersh and Ettelbruck stations
stations_filtered = stations_gdf[~stations_gdf['name'].isin(['Mersh', 'Ettelbruck'])]

# Plot observation stations with triangle markers (yellow, size 50)
stations_filtered.plot(ax=ax, transform=projection, color='yellow', marker='^', markersize=50, 
                  label='Observation Station', zorder=5, edgecolor='black', linewidth=0.5)
for idx, row in stations_filtered.iterrows():
    ax.text(row.geometry.x, row.geometry.y, row.get('name', f"Station {idx+1}"), fontsize=7,
            transform=projection, ha='left', va='bottom', color='blue')

# Generate ticks at 0.05 intervals within the map extent
x_ticks = np.arange(np.ceil(lon_min/0.05)*0.05, np.floor(lon_max/0.05)*0.05 + 0.01, 0.05)
y_ticks = np.arange(np.ceil(lat_min/0.05)*0.05, np.floor(lat_max/0.05)*0.05 + 0.01, 0.05)

ax.set_xticks(x_ticks, crs=projection)
ax.set_yticks(y_ticks, crs=projection)

# Use plain number format (no degree symbol, no E/N)
ax.xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))

# Set axis labels (matching DEM_3D_render style)
ax.set_xlabel('Longitude (°)', fontsize=15, labelpad=5)
ax.set_ylabel('Latitude (°)', fontsize=15, labelpad=5)

ax.tick_params(axis='both', labelsize=15, direction='out', length=5, width=1)

# Add legend with specified order and wavy line for rivers
from matplotlib.legend_handler import HandlerLine2D
import matplotlib.patches as mpatches

# Custom handler to draw wavy line in legend
class HandlerWavyLine(HandlerLine2D):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        # Create wavy line
        x = np.linspace(0, width, 50)
        y = height/2 + height/4 * np.sin(2 * np.pi * 2 * x / width)
        line = plt.Line2D(x, y, color=orig_handle.get_color(), 
                         linewidth=orig_handle.get_linewidth(), transform=trans)
        return [line]

# Create legend elements with matching line widths
wavy_river_line = Line2D([0], [0], color='#0157ff', linewidth=0.8, label='River and Streams')

legend_elements = [
    # Line2D([0], [0], color='red', linewidth=1.5, label='LISFLOOD-FP Domain'),  # REMOVED
    # Line2D([0], [0], color='green', linewidth=0.3, label='WRF Grid'),  # REMOVED
    # Line2D([0], [0], color='grey', linewidth=0.8, label='Catchment Area'),  # REMOVED
    wavy_river_line,
    Line2D([0], [0], marker='^', color='yellow', markeredgecolor='black', markeredgewidth=0.5, 
           label='Observation Stations', markersize=6, linestyle='None'),
]

# Create legend inside LISFLOOD domain box (upper left)
# Position in data coordinates inside the red box
ax.legend(handles=legend_elements, loc='upper left', fontsize=6,  # Reduced from ~8-9 to 6
          handler_map={wavy_river_line: HandlerWavyLine()},
          bbox_to_anchor=(0.02, 0.98), framealpha=0.9)

# Add North Arrow below legend
x_arrow, y_arrow = 0.05, 0.85  # Adjusted position below legend
ax.annotate('', xy=(x_arrow, y_arrow), xytext=(x_arrow, y_arrow - 0.04),
            arrowprops=dict(facecolor='black', width=1.5, headwidth=6),
            xycoords='axes fraction')
ax.text(x_arrow, y_arrow + 0.005, 'N', transform=ax.transAxes, 
        ha='center', va='bottom', fontsize=8, fontweight='bold')

# Scale bar removed per user request

# Add inset map with specific extent inside the red LISFLOOD domain box
# Position inset box exactly where user requested: [6.15, 49.45] width=0.06 height=0.05
# This places the box itself at these coordinates
inset_x = 6.12
inset_y = 49.36
inset_w = 6.23 - 6.12
inset_h = 49.48 - 49.36

# Create inset positioned at specific data coordinates
ax_inset = ax.inset_axes([inset_x, inset_y, inset_w, inset_h],
                         transform=ax.transData)

# Plot neighboring countries borders only (no fill)
countries_gdf.plot(ax=ax_inset, facecolor='none', edgecolor='black', 
                   linewidth=0.6, alpha=0.8, zorder=1)

# Plot Luxembourg boundary (dissolved - all regions as one)
lux_boundary_dissolved = lux_boundary_gdf.dissolve()
lux_boundary_dissolved.plot(ax=ax_inset, facecolor='white', edgecolor='black', 
                            linewidth=0.8, alpha=0.6, zorder=1.5)

# Plot full Alzette basin (larger catchment) - no edge to avoid dots
full_basin_gdf.plot(ax=ax_inset, facecolor='lightblue', edgecolor='none', 
                    alpha=0.5, zorder=2)

# Highlight Alzette sub-basin (smaller, study area) in red
sub_basin_gdf.plot(ax=ax_inset, facecolor='red', edgecolor='darkred', 
                   linewidth=1.2, alpha=0.7, zorder=3)

# Set extent to show region with buffer (zoom out to see context)
all_bounds = [
    min(full_basin_gdf.total_bounds[0], sub_basin_gdf.total_bounds[0]),
    min(full_basin_gdf.total_bounds[1], sub_basin_gdf.total_bounds[1]),
    max(full_basin_gdf.total_bounds[2], sub_basin_gdf.total_bounds[2]),
    max(full_basin_gdf.total_bounds[3], sub_basin_gdf.total_bounds[3])
]

# Zoom out more in inset to show broader context
buffer = 0.5  # Larger buffer to zoom out
ax_inset.set_xlim(all_bounds[0] - buffer, all_bounds[2] + buffer)
ax_inset.set_ylim(all_bounds[1] - buffer, all_bounds[3] + buffer)

# Style the inset map
ax_inset.set_aspect('equal')
ax_inset.set_xticks([])
ax_inset.set_yticks([])
ax_inset.set_facecolor('white')
for spine in ax_inset.spines.values():
    spine.set_edgecolor('black')
    spine.set_linewidth(0.8)  # Reduced thickness

# Save the figure in plots folder
save_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/ready_for_simulation/plots/domain_Lisflood_rivers.png"
os.makedirs(os.path.dirname(save_path), exist_ok=True)
plt.savefig(save_path, dpi=300, bbox_inches="tight")


print(f"✅ Map saved at: {save_path}")
print(f"📦 WRF tiles within LISFLOOD domain: {wrf_tile_count}")
print(f"📦 ECMWF tiles within LISFLOOD domain: {ecmwf_tile_count}")
