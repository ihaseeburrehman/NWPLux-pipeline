"""
All three WRF domains + validation stations — personal overview figure.

Domains (WRF Lambert-Conformal):
  d01 : -1.32 → 13.75 E, 44.60 → 54.22 N  (12 km)
  d02 :  4.03 →  8.52 E, 48.20 → 51.09 N  (4 km)
  d03 :  5.40 →  6.81 E, 49.37 → 50.28 N  (~1.3 km)

Output : ~/Desktop/For_Animation/4th_Year/Miscs/wrf_domains_stations.png
"""

import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib import patheffects
from shapely.geometry import box as sbox

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import geopandas as gpd

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE   = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg"
GR_SHP = f"{BASE}/Greater_Region.shp"
OUT    = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/wrf_domains_stations.png"

# ── Projections ───────────────────────────────────────────────────────────────
PLATE = ccrs.PlateCarree()
PROJ  = ccrs.LambertConformal(
    central_longitude=6.0,
    central_latitude=49.63,
    standard_parallels=(40, 58),
)

# ── Colour palette ────────────────────────────────────────────────────────────
LAND        = "#F4EFE6"   # warm cream — clearly land
OCEAN       = "#A8C8E0"   # muted steel-blue ocean, not too dark
LAKE        = "#A8C8E0"
BORDER_C    = "#BBBBBB"   # light grey country borders
COAST_C     = "#777777"   # slightly darker coast
LABELC      = "#3A3A3A"   # country label colour
GRC         = "#B05820"   # Greater Region outline (terracotta)
STATION_C   = "#D62728"   # validation station markers (strong red)

# Domain colours — clearly distinct
D01_C = "#C0392B"   # brick-red
D02_C = "#1A5FA8"   # royal blue
D03_C = "#1E8C45"   # forest green

# ── Load shapefiles ───────────────────────────────────────────────────────────
gr = gpd.read_file(GR_SHP).to_crs(epsg=4326)
_ne = gpd.read_file(
    shpreader.natural_earth(resolution="10m", category="cultural",
                            name="admin_0_countries")
)
lux = _ne[_ne["NAME"].str.contains("Luxem", case=False, na=False)].to_crs(epsg=4326)

# ── Figure ────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(9.5, 7.8))
ax  = fig.add_subplot(1, 1, 1, projection=PROJ)

# Extent: slightly wider than d01 for context
ax.set_extent([-5.0, 18.0, 42.8, 56.8], crs=PLATE)

# ── Base map ──────────────────────────────────────────────────────────────────
ax.set_facecolor(OCEAN)
ax.add_feature(cfeature.OCEAN.with_scale("50m"),
               facecolor=OCEAN, edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("50m"),
               facecolor=LAND, edgecolor="none", zorder=1)
ax.add_feature(cfeature.LAKES.with_scale("50m"),
               facecolor=LAKE, edgecolor="none", zorder=2)
ax.add_feature(cfeature.RIVERS.with_scale("50m"),
               edgecolor="#85AECB", linewidth=0.3, zorder=2)
ax.add_feature(cfeature.BORDERS.with_scale("50m"),
               linestyle="-", linewidth=0.6, edgecolor=BORDER_C, zorder=3)
ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
               linewidth=0.9, edgecolor=COAST_C, zorder=3)

# ── Greater Region ────────────────────────────────────────────────────────────
ax.add_geometries(gr.geometry, crs=PLATE,
                  facecolor=GRC, edgecolor="none", alpha=0.13, zorder=2.5)
ax.add_geometries(gr.geometry, crs=PLATE,
                  facecolor="none", edgecolor=GRC, linewidth=1.3, alpha=0.85, zorder=4)
ax.add_geometries(lux.geometry, crs=PLATE,
                  facecolor=GRC, edgecolor=GRC, alpha=0.22, linewidth=1.0, zorder=2.6)

# ── WRF domain boxes ──────────────────────────────────────────────────────────
_pe_w = lambda lw: [patheffects.Stroke(linewidth=lw + 2.5, foreground="white"),
                    patheffects.Normal()]

DOMAINS = {
    "d01\n(12 km)": dict(
        bounds=(-1.3244, 44.6050, 13.7489, 54.2210),
        color=D01_C, lw=1.6, ls=(0, (6, 3)),
        label_lon=-0.9, label_lat=53.65, va="top",
    ),
    "d02\n(4 km)": dict(
        bounds=(4.0264, 48.1988, 8.5182, 51.0938),
        color=D02_C, lw=2.0, ls="-",
        label_lon=4.15, label_lat=48.28, va="bottom",
    ),
    "d03\n(1.3 km)": dict(
        bounds=(5.3999, 49.3723, 6.8082, 50.2796),
        color=D03_C, lw=2.5, ls="-",
        label_lon=5.46, label_lat=50.31, va="bottom",
    ),
}

for name, cfg in DOMAINS.items():
    lon0, lat0, lon1, lat1 = cfg["bounds"]
    poly = sbox(lon0, lat0, lon1, lat1)
    ax.add_geometries(
        [poly], crs=PLATE,
        facecolor="none",
        edgecolor=cfg["color"],
        linewidth=cfg["lw"],
        linestyle=cfg["ls"],
        zorder=6,
        path_effects=_pe_w(cfg["lw"]),
    )

# ── Validation stations ───────────────────────────────────────────────────────
met = [
    (50.12385, 6.06622), (49.8031,  6.44337), (49.85172, 6.09754),
    (49.5122,  5.9011),  (49.491,   6.349),   (49.63265, 6.23293),
    (49.7945,  5.8202),  (49.99314, 6.10147), (49.76739, 5.96748),
    (49.63353, 6.0193),  (49.85891, 5.84868), (50.09686, 5.96961),
    (49.68087, 6.43541), (50.0093,  5.8475),  (49.79806, 6.2773),
    (49.8741,  6.2095),  (49.91445, 6.19508), (49.762,   6.11179),
    (49.93595, 5.98093), (50.9,     3.117),   (47.917,   7.4),
    (49.973,   6.693),   (51.408,   9.378),   (48.776,   4.184),
    (50.583,   4.683),   (51.289,   6.767),   (50.637,   5.443),
    (48.325,   6.07),    (50.026,   8.543),   (51.199,   2.862),
    (51.35,    3.2),     (51.115,   9.286),   (47.85,    3.497),
    (47.59,    7.53),
]
lats = [s[0] for s in met]
lons = [s[1] for s in met]
ax.scatter(lons, lats, transform=PLATE,
           marker="o", s=28,
           facecolor=STATION_C, edgecolor="white",
           linewidth=0.7, zorder=10)

# ── Country labels ────────────────────────────────────────────────────────────
_pe_c = [patheffects.withStroke(linewidth=2.0, foreground="white")]
country_labels = {
    "FRANCE":       (2.3,  46.4),
    "GERMANY":      (10.8, 51.5),
    "BELGIUM":      (4.3,  50.6),
    "NETHERLANDS":  (5.3,  52.5),
    "SWITZERLAND":  (8.3,  47.0),
    "AUSTRIA":      (14.0, 47.5),
    "DENMARK":      (10.0, 55.8),
    "ITALY":        (11.5, 44.4),
    "LUX.":         (6.1,  49.8),
    "U.K.":         (-1.5, 52.5),
    "SPAIN":        (0.0,  43.5),
    "CZECH REP.":   (15.7, 50.1),
}
for name, (lon, lat) in country_labels.items():
    ax.text(lon, lat, name, transform=PLATE,
            fontsize=6.5, fontweight="bold", color=LABELC,
            ha="center", va="center", zorder=9,
            path_effects=_pe_c)

# ── Greater Region label ──────────────────────────────────────────────────────
ax.text(4.2, 49.3, "Greater\nRegion", transform=PLATE,
        fontsize=7.5, fontstyle="italic", fontweight="bold",
        color=GRC, ha="center", va="center", zorder=10,
        path_effects=_pe_c)

# ── Legend (upper-right) ──────────────────────────────────────────────────────
legend_handles = [
    Line2D([0], [0], marker="o", color="none",
           markerfacecolor=STATION_C, markeredgecolor="white",
           markeredgewidth=0.7, markersize=8,
           label="Validation stations"),
    mpatches.Patch(facecolor=GRC, edgecolor=GRC, alpha=0.55,
                   label="Greater Region"),
]
leg = ax.legend(
    handles=legend_handles,
    loc="upper right",
    fontsize=9,
    facecolor="white",
    edgecolor="#AAAAAA",
    framealpha=0.95,
    borderpad=0.8,
    labelspacing=0.6,
    handlelength=2.0,
    fancybox=True,
)
leg.set_zorder(20)

# ── Gridlines ─────────────────────────────────────────────────────────────────
gl = ax.gridlines(draw_labels=True, x_inline=False, y_inline=False,
                  linewidth=0.4, color="#888888", alpha=0.4,
                  linestyle=(0, (2, 4)))
gl.top_labels   = False
gl.right_labels = False
gl.rotate_labels = False
gl.xlocator = mticker.FixedLocator(range(-4, 19, 2))
gl.ylocator = mticker.FixedLocator(range(43, 57, 2))
gl.xlabel_style = {"size": 10, "color": "#444444"}
gl.ylabel_style = {"size": 10, "color": "#444444"}

# ── Title ─────────────────────────────────────────────────────────────────────
ax.set_title("WRF Model Domains & Validation Stations",
             fontsize=12, fontweight="bold", pad=8)

# ── Save ──────────────────────────────────────────────────────────────────────
plt.savefig(OUT, dpi=350, bbox_inches="tight", pad_inches=0.08)
print(f"Saved → {OUT}")
