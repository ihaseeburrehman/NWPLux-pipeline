# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import matplotlib.pyplot as plt
import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import rasterio
from rasterio.warp import transform_bounds
from matplotlib.colors import LightSource
from shapely.ops import unary_union
from shapely.geometry import LineString
from matplotlib.text import TextPath
from matplotlib.patches import PathPatch
from matplotlib.font_manager import FontProperties
import numpy as np
import warnings
from matplotlib import patheffects

warnings.filterwarnings("ignore")

# Projection
data_crs = ccrs.epsg(3857)

# Create plot
fig = plt.figure(figsize=(10, 10))
ax = plt.axes(projection=data_crs)

# Load domain shapefile
domain_path = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_Domain.shp'
domain_gdf = gpd.read_file(domain_path).to_crs(epsg=4326)
domain_gdf = domain_gdf[domain_gdf.geometry.notnull() & ~domain_gdf.is_empty & domain_gdf.is_valid]
minx, miny, maxx, maxy = domain_gdf.total_bounds
ax.set_extent([minx, maxx, miny, maxy], crs=ccrs.PlateCarree())

# Load DEM and apply hillshade
elevation_file = '/Users/haseeb.rehman/Documents/SRTM_DEM_for_study_area/DEM_SRTM_30m.tif'
with rasterio.open(elevation_file) as src:
    elevation_data = src.read(1)
    elevation_crs = src.crs
    left, bottom, right, top = src.bounds
    left_t, bottom_t, right_t, top_t = transform_bounds(elevation_crs, data_crs, left, bottom, right, top)

    # Create hillshade with intensity control
    ls = LightSource(azdeg=315, altdeg=45)
    hillshade = ls.hillshade(elevation_data,
                              vert_exag=1.5,
                              dx=1, dy=1,
                              fraction=1.0)

    # ✅ Plot hillshade and capture image object
    hillshade_img = ax.imshow(hillshade,
                              extent=[left_t, right_t, bottom_t, top_t],
                              transform=data_crs,
                              cmap='Greys',
                              zorder=1,
                              alpha=0.7)

    # ✅ Add colorbar for hillshade intensity
    cbar = fig.colorbar(hillshade_img, ax=ax, orientation='vertical', shrink=0.6, pad=0.02)
    cbar.set_label("Hillshade Intensity", fontsize=9)


# Plot national borders
ax.add_feature(cfeature.BORDERS, linewidth=0.7, edgecolor='black', zorder=2)
ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
# Plot Greater Region boundary (no labels)
greater_region_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_without_lux.shp"
try:
    greater_region_gdf = gpd.read_file(greater_region_path).to_crs(epsg=3857)
    greater_region_gdf.plot(ax=ax, facecolor='none',
                            edgecolor='black',
                            linewidth=1.5,
                            linestyle=':',
                            zorder=3)
except Exception as e:
    print(f"⚠️ Could not load Greater Region shapefile: {e}")

# Define major rivers
major_rivers = {"Moselle", "Rhine", "Meuse"}

# Load and plot rivers directly
try:
    rivers_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/merged_rivers/merged_rivers.shp"
    rivers_gdf = gpd.read_file(rivers_path).to_crs(epsg=3857)
    rivers_gdf = rivers_gdf[rivers_gdf.geometry.notnull() & ~rivers_gdf.is_empty & rivers_gdf.is_valid]

    # Define major rivers (adjust names to match your attribute values)
    major_rivers = ["Moselle", "Sauer", "Our"]

    # Split major and minor rivers
    major = rivers_gdf[rivers_gdf["river_name"].isin(major_rivers)]
    others = rivers_gdf[~rivers_gdf["river_name"].isin(major_rivers)]

    # Use the same blue for all rivers; thickness differs
    river_blue = "#0831c5"   # single blue color for both
    major_width = 2.5        # thickened for paper shrinkage
    minor_width = 1.5        # thickened for paper shrinkage

    # Plot rivers (same color, different linewidth)
    major.plot(ax=ax, color=river_blue, linewidth=major_width, zorder=6)
    others.plot(ax=ax, color=river_blue, linewidth=minor_width, zorder=5)

    # (Optional) Labels using same blue family but darker for legibility
    label_color_major = "#0045ac"
    label_color_minor = "#0045ac"
    for _, row in rivers_gdf.iterrows():
        geom = row.geometry
        name = row.get("river_name")
        if not name or geom is None:
            continue
        if geom.type in ("LineString", "MultiLineString"):
            try:
                line = geom if geom.type == "LineString" else list(geom.geoms)[0]
                midpoint = line.interpolate(0.5, normalized=True)
                dx = line.interpolate(0.51, normalized=True).x - line.interpolate(0.49, normalized=True).x
                dy = line.interpolate(0.51, normalized=True).y - line.interpolate(0.49, normalized=True).y
                angle = np.degrees(np.arctan2(dy, dx))

                ax.text(
                    midpoint.x, midpoint.y, name,
                    fontsize=12 if name in major_rivers else 9,
                    color=label_color_major if name in major_rivers else label_color_minor,
                    fontweight='bold' if name in major_rivers else 'bold',
                    rotation=angle,
                    rotation_mode='anchor',
                    ha='center',
                    va='top', # Places text 'under' the river
                    transform=data_crs,
                    zorder=10,
                    path_effects=[patheffects.withStroke(linewidth=3, foreground='white')]
                )
            except Exception as e:
                print(f"⚠️ Label failed for {name}: {e}")
except Exception as e:
    print(f"⚠️ River loading or plotting failed: {e}")
# Station plotting function
def plot_stations(stations, marker, color, label, ax, add_legend=False):
    names = [s[0] for s in stations]
    lats = [s[1] for s in stations]
    lons = [s[2] for s in stations]
    ax.scatter(lons, lats, transform=ccrs.PlateCarree(), marker=marker,
               color=color, label=label if add_legend else "",
                s=84, zorder=5, alpha=1.0, edgecolors='black', linewidths=1.2)

# GNSS and MET stations
# ztd_stations = [("D596", 51.200, 8.524), ("KLEV", 51.768, 6.142), ("FFMJ", 50.091, 8.665),
#                 ("D624", 50.868, 7.056), ("NIKL", 51.141, 4.151), ("D402", 48.073, 8.528),
#                 ("LAIG", 47.842, 4.373), ("TRI2", 49.725, 6.618), ("CT58", 49.150, 3.044),
#                 ("BAT1", 50.637, 5.834), ("VIT2", 50.317, 6.085), ("MABO", 50.075, 5.739),
#                 ("DBMH", 48.604, 6.364), ("SMSP", 49.115, 4.581), ("REDU", 50.002, 5.145),
#                 ("D931", 49.314, 6.746)]
met_stations = [("Briedfeld", 50.12385, 6.06622), ("Echternach", 49.8031, 6.44337),
                ("Ettelbruck", 49.85172, 6.09754), ("Oberkorn", 49.5122, 5.9011),
                ("Remerschen", 49.491, 6.349), ("Findel", 49.63265182, 6.23292867),
                ("Roodt", 49.7945, 5.8202), ("Hosingen", 49.99314, 6.10147),
                ("Useldange", 49.76739, 5.96748), ("Mamer", 49.63353, 6.0193),
                ("Arsdorf", 49.85891, 5.84868), ("Asselborn", 50.09685689, 5.96960753),
                ("Grevenmacher", 49.68087, 6.43541), ("Schimpach", 50.0093, 5.8475),
                ("Waldbillig", 49.79806, 6.2773), ("Bettendorf", 49.8741, 6.2095),
                ("Fouhren", 49.91445, 6.19508), ("Beringen", 49.762, 6.11179),
                ("Dahl", 49.93595, 5.98093),    ("BEITEM", 50.9, 3.117),
    ("MEYENHEIM", 47.917, 7.4),
    ("SPANGDAHLEM AB", 49.973, 6.693),
    ("KASSEL CALDEN", 51.408, 9.378),
    ("VATRY", 48.776, 4.184),
    ("ERNAGE", 50.583, 4.683),
    ("DUSSELDORF", 51.289, 6.767),
    ("LIEGE", 50.637, 5.443),
    ("MIRECOURT", 48.325, 6.07),
    ("FRANKFURT MAIN", 50.026, 8.543),
    ("OOSTENDE", 51.199, 2.862),
    ("ZEEBRUGGE", 51.35, 3.2),
    ("FRITZLAR", 51.115, 9.286),
    ("BRANCHES", 47.85, 3.497),
    ("BALE MULHOUSE", 47.59, 7.53),
]

# Plot stations - MET Stations now in RED DOTS
# plot_stations(ztd_stations, marker='s', color='brown', label='GNSS Stations', ax=ax, add_legend=True)
plot_stations(met_stations, marker='o', color='red', label='MET Stations', ax=ax, add_legend=True)

# Country labels
countries = {
    "Germany": (7.5, 50.0),
    "France": (6.5, 48.0),
    "Belgium": (4.8, 50.5),
    "Netherlands": (5.4, 51.5),
    "Lux": (6.1, 49.8),
}
for country, (lon, lat) in countries.items():
    ax.text(lon, lat, country, transform=ccrs.PlateCarree(), fontsize=16,
            fontweight='bold', ha='center', va='center',
            path_effects=[patheffects.withStroke(linewidth=2.5, foreground='white')])
# Gridlines
gl = ax.gridlines(draw_labels=True, alpha=0.4)
gl.xlabels_top = False
gl.ylabels_right = False
gl.xlabel_style = {'size': 16, 'color': 'black'}  
gl.ylabel_style = {'size': 16, 'color': 'black'}  

# Legend
ax.legend(loc='upper right', fontsize=18, facecolor='white', framealpha=0.9, edgecolor='black', frameon=True)
# Save and show
output_path = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/validation_stations_with_topo.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight', pad_inches=0.1)
plt.show()
print(f"🗺️ Final map saved to: {output_path}")
