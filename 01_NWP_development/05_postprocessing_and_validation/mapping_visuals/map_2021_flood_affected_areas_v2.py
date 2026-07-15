# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
July 2021 flood-affected-areas map with WRF d01 domain overlay.
Restyled to match wrf_domains_map.py: cream/tan land, steel-blue ocean,
Lambert-Conformal projection matching the WRF grid.

Output: thesis/figures/map_flood_2021_with_wrf_domain.png
"""

import warnings
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import patheffects
from matplotlib.patches import Circle
from shapely.geometry import box as sbox

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd

warnings.filterwarnings("ignore")

OUT = "/Users/haseeb.rehman/Documents/Phd_thesis/thesis/figures/map_flood_2021_with_wrf_domain.png"

PROJ  = ccrs.LambertConformal(
    central_longitude=6.0,
    central_latitude=49.63,
    standard_parallels=(6.10, 12.20),
)
PLATE = ccrs.PlateCarree()

fig = plt.figure(figsize=(7.2, 5.2))
ax  = plt.axes(projection=PROJ)
ax.set_extent([-4.0, 17.0, 43.0, 56.5], crs=PLATE)

# ── Background (matches wrf_domains_map.py) ─────────────────────────────────
ax.set_facecolor("#b8d4e8")
ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor="#b8d4e8", edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("50m"), facecolor="#f5f2eb", edgecolor="none", zorder=1)
ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor="#b8d4e8", edgecolor="none", zorder=2)
ax.add_feature(cfeature.RIVERS.with_scale("50m"), edgecolor="#9bbcd4", linewidth=0.35, zorder=2)
ax.add_feature(cfeature.BORDERS.with_scale("50m"), linestyle="-", linewidth=0.7, edgecolor="#888888", zorder=3)
ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.8, edgecolor="#444444", zorder=3)

# ── Greater Region outline ───────────────────────────────────────────────────
greater_region_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region.shp"
gdf = gpd.read_file(greater_region_path)
gdf.to_crs(PROJ.proj4_init).plot(ax=ax, edgecolor="#444444", linestyle=":", linewidth=1.1, facecolor="none", zorder=4)

# ── d01 domain box (same style/colour as wrf_domains_map.py) ────────────────
d01_bounds = (-1.3244, 44.6050, 13.7489, 54.2210)
poly = sbox(*d01_bounds)
ax.add_geometries(
    [poly], crs=PLATE, facecolor="none", edgecolor="#c0392b",
    linewidth=1.4, linestyle="--", zorder=6,
    path_effects=[patheffects.Stroke(linewidth=3.0, foreground="white"), patheffects.Normal()],
)
ax.text(-1.00, 53.60, "d01", transform=PLATE, fontsize=10, fontweight="bold",
        color="#c0392b", ha="left", va="top", zorder=8,
        path_effects=[patheffects.withStroke(linewidth=2.5, foreground="white")])

# ── Country labels ────────────────────────────────────────────────────────────
_pe_ctry = [patheffects.withStroke(linewidth=2.2, foreground="white")]
country_labels = {
    "FRANCE": (2.5, 46.5), "GERMANY": (10.5, 51.5), "BELGIUM": (4.3, 50.7),
    "NETHERLANDS": (5.3, 52.6), "SWITZERLAND": (8.3, 47.0), "AUSTRIA": (13.8, 47.5),
    "DENMARK": (10.0, 55.7), "ITALY": (11.5, 44.5), "LUX.": (6.1, 49.7),
    "U.K.": (-1.5, 52.5), "POLAND": (16.5, 52.0),
}
for name, (lon, lat) in country_labels.items():
    ax.text(lon, lat, name, transform=PLATE, fontsize=6.5, fontweight="bold",
            color="#333333", ha="center", va="center", zorder=9, path_effects=_pe_ctry)

# ── Flood-affected areas (red dot + circle, as in original script) ──────────
affected_countries = {
    "Netherlands": (5.96, 51.44),  # Maastricht, near Meuse
    "Belgium":     (5.8, 50.3),    # Brussels area
    "Germany":     (7.10, 50.73),  # Cologne, near Ahr Valley
    "Luxembourg":  (6.13, 49.61),  # Luxembourg City
}
for country, (lon, lat) in affected_countries.items():
    ax.plot(lon, lat, "o", markersize=6, color="#c0392b", transform=PLATE, zorder=7)
    circ = Circle((lon, lat), 0.28, transform=PLATE, edgecolor="#c0392b",
                  facecolor="none", linewidth=1.3, zorder=7)
    ax.add_patch(circ)

# ── Gridlines ─────────────────────────────────────────────────────────────────
gl = ax.gridlines(draw_labels=True, alpha=0.25, linewidth=0.4, color="grey",
                   x_inline=False, y_inline=False)
gl.top_labels = False
gl.right_labels = False
gl.xlocator = mticker.FixedLocator(range(-4, 18, 2))
gl.ylocator = mticker.FixedLocator(range(44, 57, 2))
gl.xlabel_style = {"size": 8}
gl.ylabel_style = {"size": 8}

plt.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.05)
print(f"Saved -> {OUT}")
