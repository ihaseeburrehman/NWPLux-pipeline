# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Validation-stations map  —  aligned with assimilation_stations_map.py and
wrf_domains_map.py for a consistent figure set in a two-column paper.

Flat cream land / steel-blue ocean (no DEM), same Lambert Conformal projection.
Shows key rivers with rotated labels, country labels, and all 34 MET validation
stations. Legend contains only "Validation stations".

Output : ~/Desktop/For_Animation/4th_Year/Miscs/validation_stations_map_v2.png
"""

import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import patheffects
from matplotlib.lines import Line2D

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge

import cartopy.crs as ccrs
import cartopy.feature as cfeature

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
RIVERS_SHP = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/merged_rivers/merged_rivers.shp"
OUT        = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/validation_stations_map_v2.png"

# ── Projection — identical to assimilation + domain maps ─────────────────────
PROJ  = ccrs.LambertConformal(
    central_longitude=6.0, central_latitude=49.63,
    standard_parallels=(6.10, 12.20),
)
PLATE = ccrs.PlateCarree()

# ── Figure — double-column width ──────────────────────────────────────────────
fig = plt.figure(figsize=(7.2, 6.0))
ax  = plt.axes(projection=PROJ)
ax.set_extent([2.4, 9.2, 47.2, 51.4], crs=PLATE)

# ── Background — exactly as assimilation / domain maps ───────────────────────
ax.set_facecolor("#b8d4e8")
ax.add_feature(cfeature.OCEAN.with_scale("10m"),
               facecolor="#b8d4e8", edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("10m"),
               facecolor="#f5f2eb", edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAKES.with_scale("10m"),
               facecolor="#b8d4e8", edgecolor="none", zorder=1)
ax.add_feature(cfeature.RIVERS.with_scale("50m"),
               edgecolor="#9bbcd4", linewidth=0.35, zorder=2)
ax.add_feature(cfeature.BORDERS.with_scale("10m"),
               linestyle="-", linewidth=0.8, edgecolor="#666666", zorder=3)
ax.add_feature(cfeature.COASTLINE.with_scale("10m"),
               linewidth=0.8, edgecolor="#444444", zorder=3)

# ── Country labels ────────────────────────────────────────────────────────────
_pe_txt = [patheffects.withStroke(linewidth=2.2, foreground="white")]

for name, (lon, lat) in {
    "FRANCE":       (3.80, 47.85),
    "GERMANY":      (8.50, 50.65),
    "BELGIUM":      (4.20, 50.85),
    "NETHERLANDS":  (5.10, 51.25),
    "SWITZERLAND":  (7.80, 47.35),
    "LUX.":         (6.12, 49.72),
}.items():
    ax.text(lon, lat, name, transform=PLATE,
            fontsize=6.5, fontweight="bold", color="#333333",
            ha="center", va="center", zorder=6, path_effects=_pe_txt)

# ── Rivers — load in EPSG:4326, plot via add_geometries so cartopy reprojects
#            correctly into the Lambert Conformal axes
rivers_4326 = gpd.read_file(RIVERS_SHP).to_crs(epsg=4326)

MAIN_R  = ["Rhine", "Moselle", "Meuse"]
STUDY_R = ["Sauer", "Our", "Alzette"]

def _add_rivers(mask, color, lw, alpha=1.0):
    for geom in rivers_4326.loc[mask, "geometry"]:
        ax.add_geometries([geom], crs=PLATE,
                          facecolor="none", edgecolor=color,
                          linewidth=lw, alpha=alpha, zorder=4)

_add_rivers(~rivers_4326["river_name"].isin(MAIN_R + STUDY_R),
            "#7aafd4", 0.4, alpha=0.65)
_add_rivers(rivers_4326["river_name"].isin(MAIN_R),  "#2c6aa0", 1.2)
_add_rivers(rivers_4326["river_name"].isin(STUDY_R), "#2c6aa0", 0.9)

# ── River labels — work in Lambert Conformal (PROJ) coordinates for correct
#    visibility check and rotation calculation
rivers_proj = gpd.read_file(RIVERS_SHP).to_crs(PROJ)   # native LC coords

RIVER_KW = dict(color="#1a4e7a", fontstyle="italic",
                ha="center", va="center", zorder=9,
                path_effects=[patheffects.withStroke(linewidth=1.8,
                                                     foreground="white")])

def _longest_visible_proj(name):
    """Return the longest river segment (in PROJ coords) inside the axes window."""
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    sub = rivers_proj[rivers_proj["river_name"] == name]
    best, bl = None, 0
    for geom in sub.geometry:
        if isinstance(geom, LineString): ln = geom
        elif isinstance(geom, MultiLineString):
            m = linemerge(geom)
            ln = m if isinstance(m, LineString) else max(m.geoms, key=lambda g: g.length)
        else: continue
        pts = [(x, y) for x, y in ln.coords
               if xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]]
        if len(pts) < 2: continue
        seg = LineString(pts)
        if seg.length > bl: best, bl = seg, seg.length
    return best

def _angle_proj(seg, frac):
    a = seg.interpolate(max(frac - .015, 0.0), normalized=True)
    b = seg.interpolate(min(frac + .015, 1.0), normalized=True)
    ang = np.degrees(np.arctan2(b.y - a.y, b.x - a.x))
    if ang >  90: ang -= 180
    if ang < -90: ang += 180
    return ang

def label_frac(name, size, frac):
    seg = _longest_visible_proj(name)
    if seg is None: return
    pt = seg.interpolate(frac, normalized=True)
    ax.text(pt.x, pt.y, name, rotation=_angle_proj(seg, frac),
            fontsize=size, rotation_mode="anchor", **RIVER_KW)

def label_lonlat(name, size, lon, lat):
    seg = _longest_visible_proj(name)
    if seg is None: return
    px, py = PROJ.transform_point(lon, lat, PLATE)
    frac = min(seg.project(Point(px, py)) / seg.length, 1.0)
    ax.text(px, py, name, rotation=_angle_proj(seg, frac),
            fontsize=size, rotation_mode="anchor", **RIVER_KW)

label_frac("Rhine",   9,   0.60)
label_frac("Moselle", 8.5, 0.32)
label_frac("Meuse",   8,   0.55)
label_lonlat("Sauer",   7.5, 6.45, 49.83)
label_lonlat("Our",     7.5, 6.18, 50.05)
label_lonlat("Alzette", 7.5, 5.95, 49.66)

# ── Validation MET stations (all 34) ─────────────────────────────────────────
met_stations = [
    (50.12385,6.06622),(49.8031, 6.44337),(49.85172,6.09754),(49.5122, 5.9011 ),
    (49.491,  6.349  ),(49.63265,6.23293),(49.7945, 5.8202 ),(49.99314,6.10147),
    (49.76739,5.96748),(49.63353,6.0193 ),(49.85891,5.84868),(50.09686,5.96961),
    (49.68087,6.43541),(50.0093, 5.8475 ),(49.79806,6.2773 ),(49.8741, 6.2095 ),
    (49.91445,6.19508),(49.762,  6.11179),(49.93595,5.98093),(50.9,    3.117  ),
    (47.917,  7.4    ),(49.973,  6.693  ),(51.408,  9.378  ),(48.776,  4.184  ),
    (50.583,  4.683  ),(51.289,  6.767  ),(50.637,  5.443  ),(48.325,  6.07   ),
    (50.026,  8.543  ),(51.199,  2.862  ),(51.35,   3.2    ),(51.115,  9.286  ),
    (47.85,   3.497  ),(47.59,   7.53   ),
]
ax.scatter([s[1] for s in met_stations], [s[0] for s in met_stations],
           transform=PLATE, marker="o", s=22,
           facecolor="#e63232", edgecolor="white", linewidth=0.5, zorder=9)

# ── Legend — validation stations only ────────────────────────────────────────
leg = ax.legend(
    handles=[
        Line2D([], [], marker="o", color="w", markerfacecolor="#e63232",
               markeredgecolor="white", markersize=7,
               label="Validation stations"),
    ],
    loc="lower right", fontsize=8,
    facecolor="white", edgecolor="0.5",
    framealpha=0.93, borderpad=0.65,
)
leg.set_zorder(20)

# ── Gridlines — same style as other maps ─────────────────────────────────────
gl = ax.gridlines(draw_labels=True, alpha=0.2, linewidth=0.4, color="grey",
                  x_inline=False, y_inline=False)
gl.top_labels   = False
gl.right_labels = False
gl.xlocator = mticker.FixedLocator(range(2, 10, 1))
gl.ylocator = mticker.FixedLocator(range(47, 52, 1))
gl.xlabel_style = {"size": 8}
gl.ylabel_style = {"size": 8}

# ── Save ─────────────────────────────────────────────────────────────────────
plt.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.05)
print(f"Saved → {OUT}")
