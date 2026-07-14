"""
Assimilation observation-network map  —  redesigned for a double-column
journal figure (~7 in wide).

Shows all four observation types ingested by WRF-DA for the July 2021 event:
  • SYNOP  — surface synoptic stations
  • TEMP   — radiosonde ascents
  • TAMDAR — aircraft reports
  • GNSS ZTD — ground-based GPS zenith total delay

WRF inner domain rectangle is drawn for geographic reference.

Source data : shapefiles created from 2021-07-14 assimilation ASCII files
Output      : assimilation_stations_map.png
              saved to ~/Desktop/For_Animation/4th_Year/Miscs/
"""

import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import patheffects
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────────────────────
BASE   = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg"
SYNOP  = f"{BASE}/SYNOP_data.shp"
TEMP   = f"{BASE}/TEMP_data.shp"
TAMDAR = f"{BASE}/TAMDAR_data.shp"
GPSZD  = f"{BASE}/GPSZD_data.shp"
DOMAIN = f"{BASE}/Domain_epsg4326.shp"
OUT    = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/assimilation_stations_map.png"

# ── Projection ───────────────────────────────────────────────────────────────
PLATE = ccrs.PlateCarree()
PROJ  = ccrs.LambertConformal(central_longitude=6.0, central_latitude=49.63,
                               standard_parallels=(46, 53))

# Double-column figure: ~7 in wide, aspect ratio ~0.80
fig = plt.figure(figsize=(7.2, 6.0))
ax  = plt.axes(projection=PROJ)

# Map extent — wide enough to show all station types (SYNOP spread wider)
ax.set_extent([-2.5, 16.0, 43.5, 56.5], crs=PLATE)

# ── Background ───────────────────────────────────────────────────────────────
ax.set_facecolor("#b8d4e8")           # ocean fallback

ax.add_feature(cfeature.OCEAN.with_scale("50m"),
               facecolor="#b8d4e8", edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("50m"),
               facecolor="#f5f2eb", edgecolor="none", zorder=1)
ax.add_feature(cfeature.LAKES.with_scale("50m"),
               facecolor="#b8d4e8", edgecolor="none", zorder=2)
ax.add_feature(cfeature.RIVERS.with_scale("50m"),
               edgecolor="#9bbcd4", linewidth=0.4, zorder=2)

# Country borders — subtle but clear
_pe_border = [patheffects.Stroke(linewidth=1.8, foreground="white"),
              patheffects.Normal()]
ax.add_feature(cfeature.BORDERS.with_scale("50m"),
               linestyle="-", linewidth=0.9, edgecolor="#555555", zorder=3)
ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
               linewidth=0.9, edgecolor="#333333", zorder=3)

# WRF domain rectangle removed (not needed in this figure)

# ── Observation stations ─────────────────────────────────────────────────────
_pe_txt = [patheffects.withStroke(linewidth=2.0, foreground="white")]

def _load(path):
    return gpd.read_file(path).to_crs(4326)

obs_cfg = [
    # (shapefile, marker, face-colour, edge-colour, size, alpha, label, zorder)
    (SYNOP,  "o", "#1f78b4", "#0a4f7a", 14, 0.75, "SYNOP",     5),
    (GPSZD,  "s", "#e31a1c", "#8b0000", 22, 0.85, "GNSS ZTD",  6),
    (TEMP,   "^", "#33a02c", "#1a5c14", 40, 0.90, "TEMP",       7),
    (TAMDAR, "D", "#ff7f00", "#a85200", 28, 0.85, "TAMDAR",     8),
]

for path, mk, fc, ec, sz, al, lbl, zo in obs_cfg:
    gdf = _load(path)
    ax.scatter(
        gdf.geometry.x, gdf.geometry.y,
        transform=PLATE,
        marker=mk, s=sz,
        facecolor=fc, edgecolor=ec,
        linewidth=0.4, alpha=al,
        zorder=zo,
    )

# ── Country name labels ───────────────────────────────────────────────────────
country_labels = {
    "FRANCE":       (2.5,  46.5),
    "GERMANY":      (10.5, 51.5),
    "BELGIUM":      (4.3,  50.7),
    "NETHERLANDS":  (5.3,  52.5),
    "SWITZERLAND":  (8.2,  47.0),
    "AUSTRIA":      (14.0, 47.5),
    "DENMARK":      (10.0, 55.5),
    "CZECH REP.":   (15.5, 50.0),
    "LUX.":         (6.1,  49.7),
}
for name, (lon, lat) in country_labels.items():
    ax.text(lon, lat, name, transform=PLATE,
            fontsize=6.5, fontweight="bold", color="#333333",
            ha="center", va="center", zorder=9,
            path_effects=_pe_txt)

# ── Legend ────────────────────────────────────────────────────────────────────
legend_handles = [
    Line2D([], [], marker=mk, color="none", markerfacecolor=fc,
           markeredgecolor=ec, markeredgewidth=0.4,
           markersize=np.sqrt(sz) * 0.85, label=lbl)
    for (_, mk, fc, ec, sz, _, lbl, _) in obs_cfg
]

leg = ax.legend(
    handles=legend_handles,
    loc="lower right",
    fontsize=8,
    facecolor="white",
    edgecolor="0.5",
    framealpha=0.93,
    borderpad=0.6,
    handlelength=1.4,
)
leg.set_zorder(20)

# ── Gridlines ─────────────────────────────────────────────────────────────────
gl = ax.gridlines(
    draw_labels=True, alpha=0.25,
    linewidth=0.4, color="grey",
    x_inline=False, y_inline=False,
)
gl.top_labels   = False
gl.right_labels = False
gl.xlocator = mticker.FixedLocator(range(-2, 17, 2))
gl.ylocator = mticker.FixedLocator(range(44, 57, 2))
gl.xlabel_style = {"size": 8}
gl.ylabel_style = {"size": 8}

# ── Save ──────────────────────────────────────────────────────────────────────
plt.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.05)
print(f"Saved → {OUT}")
