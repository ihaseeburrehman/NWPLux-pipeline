# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd
import os
from matplotlib.patches import Circle

# Define projection
projection = ccrs.PlateCarree()

# Create figure and axis
fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': projection})

# Define map extent
lon_min, lat_min = -1.324371337890625, 44.60498809814453
lon_max, lat_max = 13.7489013671875, 54.220977783203125
ax.set_extent([lon_min - 0.5, lon_max + 0.5, lat_min - 0.5, lat_max + 0.5], crs=projection)

# Add ocean and land
ax.add_feature(cfeature.OCEAN, facecolor='deepskyblue')
ax.add_feature(cfeature.LAND, facecolor='white')

# Add borders and coastlines
ax.add_feature(cfeature.BORDERS, edgecolor='black', linewidth=0.6, linestyle='-')
ax.add_feature(cfeature.COASTLINE, edgecolor='black', linewidth=0.6)

# Load and plot Greater Region shapefile
greater_region_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region.shp"
plot_greater_region = True  # Switch to toggle Greater Region shapefile
if plot_greater_region:
    gdf = gpd.read_file(greater_region_path)
    gdf.to_crs(projection).plot(ax=ax, edgecolor='black', linestyle=':', linewidth=1, facecolor='none')

# Define domains with label coordinates (upper-left corner inside box)
domains = {
    'd01': {
        'lon_min': -1.324371337890625, 'lat_min': 44.60498809814453,
        'lon_max': 13.7489013671875, 'lat_max': 54.220977783203125,
        'color': 'red', 'label': 'd01', 'label_lon': -1.0, 'label_lat': 53.4
    },
    'd02': {
        'lon_min': 4.026397705078125, 'lat_min': 48.198829650878906,
        'lon_max': 8.518218994140625, 'lat_max': 51.09376525878906,
        'color': 'red', 'label': 'd02', 'label_lon': 4.1, 'label_lat': 51.0
    },
    'd03': {
        'lon_min': 5.399871826171875, 'lat_min': 49.37228775024414,
        'lon_max': 6.80816650390625, 'lat_max': 50.27959442138672,
        'color': 'red', 'label': 'd03', 'label_lon': 5.5, 'label_lat': 50.2
    }
}

# Switch to toggle domain plotting (True to plot, False to skip)
plot_domains = {
    'd01': True,
    'd02': False,
    'd03': False
}

# Plot domain boxes and labels
for domain_name, domain in domains.items():
    if plot_domains.get(domain_name, False):
        # Plot box
        domain_lons = [domain['lon_min'], domain['lon_max'], domain['lon_max'], domain['lon_min'], domain['lon_min']]
        domain_lats = [domain['lat_min'], domain['lat_min'], domain['lat_max'], domain['lat_max'], domain['lat_min']]
        ax.plot(domain_lons, domain_lats, transform=ccrs.PlateCarree(), 
                color=domain['color'], linewidth=2)
        # Add label
        ax.text(domain['label_lon'], domain['label_lat'], domain['label'], 
                transform=ccrs.PlateCarree(), fontsize=8, fontweight='bold', 
                ha='left', va='top', color='red')

# Add country labels
countries = {
    "Germany": (9.5, 51.0),
    "France": (4.5, 48.0),
    "Belgium": (4.8, 50.5),
    "Netherlands": (5.5, 52.0),
    "Lux": (6.1, 49.8),
    "Austria": (12.3, 47.2),
    "Italy": (10.0, 45.0),
    "UK": (-1.0, 52.5),
    "Switzerland": (8.0, 47.0)
}

for country, (lon, lat) in countries.items():
    ax.text(lon, lat, country, transform=ccrs.PlateCarree(), fontsize=8, 
            fontweight='bold', ha='center', va='center')

# Highlight affected countries with red dots and circles
affected_countries = {
    "Belgium": (5.8, 50.3),  # Brussels
    "Germany": (7.10, 50.73),  # Cologne, near Ahr Valley
    "Luxembourg": (6.13, 49.61),  # Luxembourg City
    "Netherlands": (5.96, 51.44)  # Maastricht, near Meuse
}

for country, (lon, lat) in affected_countries.items():
    # Plot red dot
    ax.plot(lon, lat, 'ro', markersize=6, transform=ccrs.PlateCarree())
    # Add red circle around the dot
    circle = Circle((lon, lat), 0.3, transform=ccrs.PlateCarree(), 
                    edgecolor='red', facecolor='none', linewidth=1.2)
    ax.add_patch(circle)

# Add gridlines
gl = ax.gridlines(draw_labels=True, linestyle="--", alpha=0.5)
gl.right_labels = False
gl.top_labels = False
gl.xlabel_style = {'size': 10, 'color': 'black'}
gl.ylabel_style = {'size': 10, 'color': 'black'}

# Define and ensure save path
save_path = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/map_flood_2021_with_wrf_domain.png"
os.makedirs(os.path.dirname(save_path), exist_ok=True)

# Save the figure
plt.savefig(save_path, dpi=300, bbox_inches="tight")

# Show the plot
plt.show()

print(f"Map saved at: {save_path}")