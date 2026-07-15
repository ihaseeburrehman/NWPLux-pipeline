# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import os

# Define projection
projection = ccrs.PlateCarree()

# Create figure and axis
fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': projection})

# Define map extent
lon_min, lat_min = 5.399871826171875, 49.37228775024414
lon_max, lat_max = 6.80816650390625, 50.27959442138672
ax.set_extent([lon_min - 0.5, lon_max + 0.5, lat_min - 0.5, lat_max + 0.5], crs=projection)

# Add ocean and land
ax.add_feature(cfeature.OCEAN, facecolor='deepskyblue')
ax.add_feature(cfeature.LAND, facecolor='white')

# Add borders and coastlines
ax.add_feature(cfeature.BORDERS, edgecolor='black', linewidth=1, linestyle='--')
ax.add_feature(cfeature.COASTLINE, edgecolor='black', linewidth=1)

# Convert extent to lon/lat (using Luxembourg coordinate system, EPSG:2169)
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:2169", "EPSG:4326", always_xy=True)
# Bottom-left
x1, y1 = 73532.0, 78934.5
lon1, lat1 = transformer.transform(x1, y1)

# Top-right
x2, y2 = 80222.0, 82324.5
lon2, lat2 = transformer.transform(x2, y2)


# Print converted coordinates
print(f"Converted coordinates: Bottom-left ({lon1}, {lat1}), Top-right ({lon2}, {lat2})")

# Plot single box
domain_lons = [lon1, lon2, lon2, lon1, lon1]
domain_lats = [lat1, lat1, lat2, lat2, lat1]
ax.plot(domain_lons, domain_lats, transform=ccrs.PlateCarree(), color='red', linewidth=2)


# Add country labels within extent
countries = {
    "Germany": (6.75, 49.8),
    "France": (5.4, 49.4),
    "Belgium": (5.5, 50.0),
    "Lux": (6.1, 49.75),
}
for country, (lon, lat) in countries.items():
    if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
        ax.text(lon, lat, country, transform=ccrs.PlateCarree(), fontsize=8, fontweight='bold', ha='center', va='center')

# Add gridlines
gl = ax.gridlines(draw_labels=True, linestyle="--", alpha=0.5)
gl.right_labels = False
gl.top_labels = False
gl.xlabel_style = {'size': 10, 'color': 'black'}
gl.ylabel_style = {'size': 10, 'color': 'black'}

# Define and ensure save path
save_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/10m"
os.makedirs(os.path.dirname(save_path), exist_ok=True)

# Save the figure
plt.savefig(save_path, dpi=300, bbox_inches="tight")

# Show the plot
plt.show()
print(f"Map saved at: {save_path}")