import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib import gridspec


# Define the map projection (Web Mercator for basemap compatibility)
data_crs = ccrs.epsg(3857)

# Create the figure with a grid layout
fig = plt.figure(figsize=(15, 8))
gs = gridspec.GridSpec(2, 2, width_ratios=[3, 1], height_ratios=[3, 1])

# Create the map axes with the correct projection
ax = plt.subplot(gs[0, 0], projection=data_crs)

# Load Greater Region shapefile
shpfilename = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp'
gdf = gpd.read_file(shpfilename)

# Print column names to check for annotation field
print("Shapefile Columns:", gdf.columns)

# Ensure the shapefile is projected correctly to Web Mercator
if gdf.crs is None:
    print("Warning: Shapefile has no CRS. Assigning default UTM CRS.")
    gdf.set_crs(epsg=4326, inplace=True)  # Assign WGS 84 if CRS is missing

gdf = gdf.to_crs(epsg=3857)  # Convert to Web Mercator for compatibility

# Plot the shapefile
gdf.plot(ax=ax, facecolor='none', edgecolor='black', alpha=0, zorder=2)

# Check for a valid annotation field
annotation_column = None
for col in ['NAME', 'name', 'region', 'ID']:  # Common column names
    if col in gdf.columns:
        annotation_column = col
        break

if annotation_column:
    print(f"Using '{annotation_column}' for annotation.")

    # Compute centroid of each shape for annotation
    gdf['centroid'] = gdf.geometry.centroid
    gdf['coords'] = gdf['centroid'].apply(lambda x: (x.x, x.y))

    # Annotate the map
    for idx, row in gdf.iterrows():
        ax.annotate(text=row[annotation_column], xy=row['coords'], ha='center', 
                    fontsize=7, color='black', fontweight='regular', alpha=0)
else:
    print("No valid annotation column found!")

# Load second shapefile to determine the correct map extent
shpfilename_2 = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_Domain.shp'
gdf_extent = gpd.read_file(shpfilename_2).to_crs(epsg=3857)

# Get the extent of the shapefile
x_min, y_min, x_max, y_max = gdf_extent.total_bounds
ax.set_extent([x_min, x_max, y_min, y_max], crs=ccrs.epsg(3857))

# Add basemap
try:
    ctx.add_basemap(ax, source = ctx.providers.OpenTopoMap, crs=ccrs.epsg(3857), zoom=6, attribution=False)
except Exception as e:
    print("Failed to load basemap. Error:", e)

# Add coastlines, borders, and gridlines
ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linestyle=':')

# Configure gridlines
gl = ax.gridlines(draw_labels=True, alpha=0.3, linestyle='--')
gl.xlabels_top = False
gl.ylabels_right = False
gl.xlabel_style = {'size': 10, 'color': 'gray'}
gl.ylabel_style = {'size': 10, 'color': 'gray'}

# Show the plot
plt.show()
