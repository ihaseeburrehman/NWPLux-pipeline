import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import BoundaryNorm
from matplotlib import ticker

# Paths
base_dir = '/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/10m/'
dem_path = os.path.join(base_dir, 'walferdange_dem_10m.asc')
manning_path = os.path.join(base_dir, 'manning_coefficients_10m.asc')
output_dir = base_dir

# Hillshade function (QGIS-style)
def compute_hillshade(elevation, azimuth=315, altitude=45, z_factor=1):
    x, y = np.gradient(elevation * z_factor)
    slope = np.pi / 2 - np.arctan(np.sqrt(x**2 + y**2))
    aspect = np.arctan2(-x, y)
    az_rad = np.radians(azimuth)
    alt_rad = np.radians(altitude)
    shaded = np.sin(alt_rad) * np.sin(slope) + np.cos(alt_rad) * np.cos(slope) * np.cos(az_rad - aspect)
    return np.clip(shaded, 0, 1)

# Load DEM
with rasterio.open(dem_path) as dem_src:
    dem = dem_src.read(1).astype(float)
    dem[dem == dem_src.nodata] = np.nan
    extent = [dem_src.bounds.left, dem_src.bounds.right, dem_src.bounds.bottom, dem_src.bounds.top]

# Compute hillshade
hillshade = compute_hillshade(dem, azimuth=315, altitude=45, z_factor=1)

# Plot hillshade with elevation colorbar
fig, ax = plt.subplots(figsize=(12, 6))
im = ax.imshow(hillshade, extent=extent, cmap='Greys', origin='upper')
cbar = plt.colorbar(ax.imshow(dem, extent=extent, cmap='terrain', origin='upper'), ax=ax,
                    orientation='vertical', shrink=0.8, pad=0.02, format=ticker.FormatStrFormatter('%.0f'))
cbar.set_label("Elevation (m)")
ax.set_title("Digital Elevation Model (Hillshade)", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.grid(True, linestyle='--', color='gray', alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(output_dir, 'walferdange_dem_hillshade_elevation.png'), dpi=400, bbox_inches='tight')
plt.close(fig)

landcover_colors = [
    "#A9A9A9",  # grey (concrete/smooth)
    "#BDB76B",  # khaki
    "#DAA520",  # goldenrod
    "#F4A460",  # sandy brown
    "#DEB887",  # burlywood
    "#7CFC00",  # lawn green
    "#228B22",  # forest green
    "#006400"   # dark green (dense vegetation)
]

landcover_cmap = mcolors.LinearSegmentedColormap.from_list("Landcover", landcover_colors, N=256)


# Load Manning
with rasterio.open(manning_path) as man_src:
    manning = man_src.read(1).astype(float)
    manning[manning == man_src.nodata] = np.nan
    extent = [man_src.bounds.left, man_src.bounds.right, man_src.bounds.bottom, man_src.bounds.top]

# Plot Manning
man_masked = np.ma.masked_invalid(manning)
min_val, max_val = np.nanmin(manning), np.nanmax(manning)
levels = np.linspace(min_val, max_val, 10)
norm = BoundaryNorm(levels, landcover_cmap.N)

fig, ax = plt.subplots(figsize=(12, 6))
im = ax.imshow(man_masked, extent=extent, cmap=landcover_cmap, norm=norm, origin='upper')
cbar = plt.colorbar(im, ax=ax, orientation='vertical', shrink=0.8, pad=0.02, format=ticker.FormatStrFormatter('%.3f'))
cbar.set_label("Manning Coefficient (n)")
ax.set_title("Manning Roughness Map", fontsize=14)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.grid(True, linestyle='--', color='gray', alpha=0.3)
plt.tight_layout()
fig.savefig(os.path.join(output_dir, 'walferdange_manning_map.png'), dpi=400, bbox_inches='tight')
plt.close(fig)

print("✅ Done — DEM hillshade and Manning maps saved in the 10m folder.")
