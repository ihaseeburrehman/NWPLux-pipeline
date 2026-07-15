# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
WRF three-domain setup map  —  designed for a double-column journal figure.

Domains (corners in geographic lon/lat, WRF Lambert-Conformal grid):
  d01 : -1.32 → 13.75 E,  44.60 → 54.22 N   (coarse, 12 km)
  d02 :  4.03 →  8.52 E,  48.20 → 51.09 N   (intermediate, 4 km)
  d03 :  5.40 →  6.81 E,  49.37 → 50.28 N   (inner / study area, ~1.3 km)

Projection : Lambert Conformal — matches WRF model grid exactly.
Style      : white/cream land, steel-blue ocean, matching assimilation map.

Output : ~/Desktop/For_Animation/4th_Year/Miscs/wrf_domains_map.png
"""

import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from matplotlib import patheffects
from shapely.geometry import box as sbox

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
import geopandas as gpd

warnings.filterwarnings("ignore")

# ── Output path ───────────────────────────────────────────────────────────────
OUT = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/wrf_domains_map.png"

# ── Projection  ───────────────────────────────────────────────────────────────
# Match WRF namelist: PHIC=49.63, XLONC=6.00, TRUE1=6.10, TRUE2=12.20
PROJ  = ccrs.LambertConformal(
    central_longitude=6.0,
    central_latitude=49.63,
    standard_parallels=(6.10, 12.20),
)
PLATE = ccrs.PlateCarree()

# ── Figure ────────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(7.2, 5.8))
ax  = plt.axes(projection=PROJ)

# Extent slightly wider than d01 for context
ax.set_extent([-4.0, 17.0, 43.0, 56.5], crs=PLATE)

# ── Background ────────────────────────────────────────────────────────────────
ax.set_facecolor("#b8d4e8")

ax.add_feature(cfeature.OCEAN.with_scale("50m"),
               facecolor="#b8d4e8", edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("50m"),
               facecolor="#f5f2eb", edgecolor="none", zorder=1)
ax.add_feature(cfeature.LAKES.with_scale("50m"),
               facecolor="#b8d4e8", edgecolor="none", zorder=2)
ax.add_feature(cfeature.RIVERS.with_scale("50m"),
               edgecolor="#9bbcd4", linewidth=0.35, zorder=2)
ax.add_feature(cfeature.BORDERS.with_scale("50m"),
               linestyle="-", linewidth=0.7, edgecolor="#888888", zorder=3)
ax.add_feature(cfeature.COASTLINE.with_scale("50m"),
               linewidth=0.8, edgecolor="#444444", zorder=3)

# ── Domain definitions ────────────────────────────────────────────────────────
#  (lon_min, lat_min, lon_max, lat_max, color, lw, linestyle, label_lon, label_lat)
DOMAINS = {
    "d01": dict(
        bounds=(-1.3244, 44.6050, 13.7489, 54.2210),
        color="#c0392b", lw=1.4, ls="--",
        label_lon=-1.00, label_lat=53.60,
    ),
    "d02": dict(
        bounds=(4.0264, 48.1988, 8.5182, 51.0938),
        color="#1a6faf", lw=1.9, ls="-",
        label_lon=4.15,  label_lat=48.35,
    ),
    "d03": dict(
        bounds=(5.3999, 49.3723, 6.8082, 50.2796),
        color="#1e8c45", lw=2.4, ls="-",
        label_lon=5.48,  label_lat=50.24,
    ),
}

_pe_domain = lambda color: [
    patheffects.Stroke(linewidth=3.0, foreground="white"),
    patheffects.Normal(),
]
_pe_label  = [patheffects.withStroke(linewidth=2.5, foreground="white")]

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
        path_effects=_pe_domain(cfg["color"]),
    )
    va = "bottom" if name == "d02" else "top"
    ax.text(
        cfg["label_lon"], cfg["label_lat"], name,
        transform=PLATE,
        fontsize=10, fontweight="bold",
        color=cfg["color"],
        ha="left", va=va,
        zorder=8,
        path_effects=_pe_label,
    )

# ── Country labels ────────────────────────────────────────────────────────────
_pe_ctry = [patheffects.withStroke(linewidth=2.2, foreground="white")]

country_labels = {
    "FRANCE":       (2.5,  46.5),
    "GERMANY":      (10.5, 51.5),
    "BELGIUM":      (4.3,  50.7),
    "NETHERLANDS":  (5.3,  52.6),
    "SWITZERLAND":  (8.3,  47.0),
    "AUSTRIA":      (13.8, 47.5),
    "DENMARK":      (10.0, 55.7),
    "ITALY":        (11.5, 44.5),
    "LUX.":         (6.1,  49.7),
    "U.K.":         (-1.5, 52.5),
    "POLAND":       (16.5, 52.0),
}
for name, (lon, lat) in country_labels.items():
    ax.text(lon, lat, name, transform=PLATE,
            fontsize=6.5, fontweight="bold", color="#333333",
            ha="center", va="center", zorder=9,
            path_effects=_pe_ctry)

# Legend removed — domain labels on the map are self-explanatory

# ── Gridlines ─────────────────────────────────────────────────────────────────
gl = ax.gridlines(
    draw_labels=True, alpha=0.25,
    linewidth=0.4, color="grey",
    x_inline=False, y_inline=False,
)
gl.top_labels   = False
gl.right_labels = False
gl.xlocator = mticker.FixedLocator(range(-4, 18, 2))
gl.ylocator = mticker.FixedLocator(range(44, 57, 2))
gl.xlabel_style = {"size": 8}
gl.ylabel_style = {"size": 8}

# ── Save ──────────────────────────────────────────────────────────────────────
plt.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.05)
print(f"Saved → {OUT}")
