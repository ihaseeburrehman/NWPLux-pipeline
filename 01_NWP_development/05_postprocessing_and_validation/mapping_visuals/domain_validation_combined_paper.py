# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Combined study-area figure for the "WRF vs GraphCast" paper:
  (a) WRF single domain (d01, 12 km) over Europe, in the WRF Lambert-Conformal
      projection, with the Greater Region highlighted.
  (b) Validation-station network (Lambert), with the major rivers labelled.

Output: <paper>/figures/study_domain_validation.png
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
import cartopy.io.shapereader as shpreader

warnings.filterwarnings("ignore")

BASE   = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg"
GR     = f"{BASE}/Greater_Region.shp"
RIVERS = f"{BASE}/merged_rivers/merged_rivers.shp"
OUT    = "/Users/haseeb.rehman/Documents/Research_papers/WRF_vs_GraphCast_v1/figures/study_domain_validation.png"

PLATE = ccrs.PlateCarree()
# WRF Lambert-Conformal (centred on the domain) -> curved graticule like WRF
PROJ  = ccrs.LambertConformal(central_longitude=6.0, central_latitude=49.63,
                              standard_parallels=(40, 58))

LAND="#ECEFF1"; OCEAN="#DCE8F0"; BORDER="#9AA3AB"; COAST="#6B7884"; LABELC="#5A6570"
DBLUE="#2C5F8A"; GRC="#C0603A"
RIVER_MAIN="#3B7AB3"; RIVER_MINOR="#A9C7DE"; RIVER_LABEL="#26557F"; STATION="#C44E52"
_pe = [patheffects.withStroke(linewidth=2.0, foreground="white")]

gr = gpd.read_file(GR).to_crs(epsg=4326)
# Luxembourg country (the Greater Region shapefile leaves it as a hole)
_ne = gpd.read_file(shpreader.natural_earth(resolution="10m", category="cultural",
                                            name="admin_0_countries"))
lux = _ne[_ne["NAME"].str.contains("Luxem", case=False, na=False)].to_crs(epsg=4326)

fig = plt.figure(figsize=(13, 6.3))
axA = fig.add_subplot(1, 2, 1, projection=PROJ)
axB = fig.add_subplot(1, 2, 2, projection=PROJ)

def base_map(ax, scale):
    ax.add_feature(cfeature.OCEAN.with_scale(scale), facecolor=OCEAN, edgecolor="none", zorder=0)
    ax.add_feature(cfeature.LAND.with_scale(scale),  facecolor=LAND,  edgecolor="none", zorder=1)
    ax.add_feature(cfeature.LAKES.with_scale(scale), facecolor=OCEAN, edgecolor="none", zorder=2)
    ax.add_feature(cfeature.BORDERS.with_scale(scale), linewidth=0.7, edgecolor=BORDER, zorder=3)
    ax.add_feature(cfeature.COASTLINE.with_scale(scale), linewidth=0.7, edgecolor=COAST, zorder=3)

def grid(ax, xs, ys):
    gl = ax.gridlines(draw_labels=True, x_inline=False, y_inline=False,
                      linewidth=0.4, color="grey", alpha=0.45, linestyle=(0, (1, 3)))
    gl.top_labels = False; gl.right_labels = False; gl.rotate_labels = False
    gl.xlocator = mticker.FixedLocator(xs); gl.ylocator = mticker.FixedLocator(ys)
    gl.xlabel_style = {"size": 8}; gl.ylabel_style = {"size": 8}

# =================== Panel (a): domain ===================
axA.set_extent([-3.0, 15.5, 43.2, 55.6], crs=PLATE)
base_map(axA, "50m")
axA.add_geometries(gr.geometry, crs=PLATE, facecolor=GRC, edgecolor="none", alpha=0.16, zorder=2.4)
axA.add_geometries(lux.geometry, crs=PLATE, facecolor=GRC, edgecolor="none", alpha=0.45, zorder=2.6)
axA.add_geometries(gr.geometry, crs=PLATE, facecolor="none", edgecolor=GRC, linewidth=1.2, zorder=4)
axA.add_geometries(lux.geometry, crs=PLATE, facecolor="none", edgecolor=GRC, linewidth=1.4, zorder=4.1)

d = dict(lo0=-1.324371337890625, la0=44.60498809814453,
         lo1=13.7489013671875,  la1=54.220977783203125)
axA.plot([d['lo0'], d['lo1'], d['lo1'], d['lo0'], d['lo0']],
         [d['la0'], d['la0'], d['la1'], d['la1'], d['la0']],
         transform=PLATE, color=DBLUE, linewidth=2.0, zorder=5)

for c, (lo, la) in {"GERMANY": (10.6, 51.4), "FRANCE": (2.2, 46.5), "BELGIUM": (4.2, 50.7),
                    "NETHERLANDS": (5.6, 52.5), "SWITZERLAND": (8.4, 46.7),
                    "AUSTRIA": (13.7, 47.6), "U.K.": (-1.8, 52.9)}.items():
    axA.text(lo, la, c, transform=PLATE, fontsize=7.5, fontweight="bold", color=LABELC,
             ha="center", va="center", zorder=7, path_effects=_pe)
axA.text(3.6, 48.55, "Greater Region", transform=PLATE, fontsize=9, fontstyle="italic",
         fontweight="bold", color=GRC, ha="center", va="center", zorder=8, path_effects=_pe)
axA.text(6.12, 49.81, "LUX.", transform=PLATE, fontsize=7, fontweight="bold",
         color="#7A3B22", ha="center", va="center", zorder=8, path_effects=_pe)
grid(axA, np.arange(-4, 17, 4), np.arange(44, 57, 2))
axA.set_title("(a) Model domain", fontsize=10, fontweight="bold")

# =================== Panel (b): validation ===================
axB.set_extent([2.2, 9.5, 46.9, 51.7], crs=PLATE)
base_map(axB, "10m")
axB.add_geometries(gr.geometry, crs=PLATE, facecolor="none", edgecolor=GRC,
                   linewidth=1.0, alpha=0.75, zorder=3.5)
axB.add_geometries(lux.geometry, crs=PLATE, facecolor=GRC, edgecolor=GRC,
                   alpha=0.16, linewidth=1.1, zorder=3.6)

rivers = gpd.read_file(RIVERS).to_crs(epsg=4326)
MAIN = ["Rhine", "Moselle", "Meuse"]; STUDY = ["Sauer", "Our", "Alzette"]
def add_rivers(mask, color, lw, alpha=1.0):
    for g in rivers.loc[mask, "geometry"]:
        axB.add_geometries([g], crs=PLATE, facecolor="none", edgecolor=color,
                           linewidth=lw, alpha=alpha, zorder=4)
add_rivers(~rivers["river_name"].isin(MAIN + STUDY), RIVER_MINOR, 0.4, 0.7)
add_rivers(rivers["river_name"].isin(MAIN),  RIVER_MAIN, 1.2)
add_rivers(rivers["river_name"].isin(STUDY), RIVER_MAIN, 0.9)

rivers_proj = gpd.read_file(RIVERS).to_crs(PROJ)
RKW = dict(color=RIVER_LABEL, fontstyle="italic", ha="center", va="center", zorder=9,
           path_effects=[patheffects.withStroke(linewidth=1.8, foreground="white")])
def _seg(name):
    xlim, ylim = axB.get_xlim(), axB.get_ylim()
    best, bl = None, 0
    for geom in rivers_proj[rivers_proj["river_name"] == name].geometry:
        if isinstance(geom, LineString): ln = geom
        elif isinstance(geom, MultiLineString):
            m = linemerge(geom); ln = m if isinstance(m, LineString) else max(m.geoms, key=lambda g: g.length)
        else: continue
        pts = [(x, y) for x, y in ln.coords if xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]]
        if len(pts) < 2: continue
        seg = LineString(pts)
        if seg.length > bl: best, bl = seg, seg.length
    return best
def _ang(seg, frac):
    a = seg.interpolate(max(frac - .015, 0.0), normalized=True)
    b = seg.interpolate(min(frac + .015, 1.0), normalized=True)
    ang = np.degrees(np.arctan2(b.y - a.y, b.x - a.x))
    return ang - 180 if ang > 90 else (ang + 180 if ang < -90 else ang)
def lab_frac(name, size, frac):
    s = _seg(name)
    if s is None: return
    p = s.interpolate(frac, normalized=True)
    axB.text(p.x, p.y, name, rotation=_ang(s, frac), fontsize=size, rotation_mode="anchor", **RKW)
def lab_ll(name, size, lon, lat):
    s = _seg(name)
    if s is None: return
    px, py = PROJ.transform_point(lon, lat, PLATE)
    frac = min(s.project(Point(px, py)) / s.length, 1.0)
    axB.text(px, py, name, rotation=_ang(s, frac), fontsize=size, rotation_mode="anchor", **RKW)
lab_frac("Rhine", 9, 0.60); lab_frac("Moselle", 8.5, 0.32); lab_frac("Meuse", 8, 0.55)
lab_ll("Sauer", 7.5, 6.45, 49.83); lab_ll("Our", 7.5, 6.18, 50.05); lab_ll("Alzette", 7.5, 5.95, 49.66)

met = [(50.12385,6.06622),(49.8031,6.44337),(49.85172,6.09754),(49.5122,5.9011),
       (49.491,6.349),(49.63265,6.23293),(49.7945,5.8202),(49.99314,6.10147),
       (49.76739,5.96748),(49.63353,6.0193),(49.85891,5.84868),(50.09686,5.96961),
       (49.68087,6.43541),(50.0093,5.8475),(49.79806,6.2773),(49.8741,6.2095),
       (49.91445,6.19508),(49.762,6.11179),(49.93595,5.98093),(50.9,3.117),
       (47.917,7.4),(49.973,6.693),(51.408,9.378),(48.776,4.184),(50.583,4.683),
       (51.289,6.767),(50.637,5.443),(48.325,6.07),(50.026,8.543),(51.199,2.862),
       (51.35,3.2),(51.115,9.286),(47.85,3.497),(47.59,7.53)]
axB.scatter([s[1] for s in met], [s[0] for s in met], transform=PLATE, marker="o", s=24,
            facecolor=STATION, edgecolor="white", linewidth=0.5, zorder=9)
for c, (lo, la) in {"FRANCE": (3.7, 47.6), "GERMANY": (8.6, 50.7), "BELGIUM": (4.1, 50.95),
                    "NETHERLANDS": (5.0, 51.35), "SWITZERLAND": (7.8, 47.25), "LUX.": (6.12, 49.74)}.items():
    axB.text(lo, la, c, transform=PLATE, fontsize=6.8, fontweight="bold", color=LABELC,
             ha="center", va="center", zorder=8, path_effects=_pe)
leg = axB.legend(handles=[Line2D([], [], marker="o", color="w", markerfacecolor=STATION,
                 markeredgecolor="white", markersize=7, label="Validation stations")],
                 loc="lower right", fontsize=8, facecolor="white", edgecolor="0.7",
                 framealpha=0.95, borderpad=0.6, fancybox=True)
leg.set_zorder(20)
grid(axB, np.arange(2, 10, 1), np.arange(47, 52, 1))
axB.set_title("(b) Validation stations", fontsize=10, fontweight="bold")

plt.subplots_adjust(wspace=0.08)
plt.savefig(OUT, dpi=350, bbox_inches="tight", pad_inches=0.05)
print(f"Saved -> {OUT}")
