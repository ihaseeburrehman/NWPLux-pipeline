# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Single-panel study-area figure for the "WRF vs GraphCast" paper:
the WRF model domain (Lambert-conformal) over Europe, with the Greater Region
and Luxembourg highlighted and the precipitation validation stations overlaid.
No in-figure domain label or "Greater Region" text (explained in the caption).

Output: <paper>/figures/study_area_map.png
"""
import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import patheffects
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

warnings.filterwarnings("ignore")

BASE = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg"
GR   = f"{BASE}/Greater_Region.shp"
OUT  = "/Users/haseeb.rehman/Documents/Research_papers/WRF_vs_GraphCast_v1/figures/study_area_map.png"

PLATE = ccrs.PlateCarree()
PROJ  = ccrs.LambertConformal(central_longitude=6.0, central_latitude=49.63,
                              standard_parallels=(40, 58))

LAND="#ECEFF1"; OCEAN="#DCE8F0"; BORDER="#9AA3AB"; COAST="#6B7884"; LABELC="#5A6570"
DBLUE="#2C5F8A"; GRC="#C0603A"; STATION="#C44E52"
_pe = [patheffects.withStroke(linewidth=2.0, foreground="white")]

gr  = gpd.read_file(GR).to_crs(epsg=4326)
_ne = gpd.read_file(shpreader.natural_earth(resolution="10m", category="cultural",
                                            name="admin_0_countries"))
lux = _ne[_ne["NAME"].str.contains("Luxem", case=False, na=False)].to_crs(epsg=4326)

fig = plt.figure(figsize=(8.2, 6.6))
ax  = plt.axes(projection=PROJ)
ax.set_extent([-3.0, 15.5, 43.2, 55.6], crs=PLATE)

ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor=OCEAN, edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("50m"),  facecolor=LAND,  edgecolor="none", zorder=1)
ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor=OCEAN, edgecolor="none", zorder=2)
ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.7, edgecolor=BORDER, zorder=3)
ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.7, edgecolor=COAST, zorder=3)

# Greater Region + Luxembourg highlight (no text label in-figure)
ax.add_geometries(gr.geometry,  crs=PLATE, facecolor=GRC, edgecolor="none", alpha=0.16, zorder=2.4)
ax.add_geometries(lux.geometry, crs=PLATE, facecolor=GRC, edgecolor="none", alpha=0.45, zorder=2.6)
ax.add_geometries(gr.geometry,  crs=PLATE, facecolor="none", edgecolor=GRC, linewidth=1.1, zorder=4)
ax.add_geometries(lux.geometry, crs=PLATE, facecolor="none", edgecolor=GRC, linewidth=1.3, zorder=4.1)

# WRF domain box (no label)
d = dict(lo0=-1.324371337890625, la0=44.60498809814453,
         lo1=13.7489013671875,  la1=54.220977783203125)
ax.plot([d['lo0'], d['lo1'], d['lo1'], d['lo0'], d['lo0']],
        [d['la0'], d['la0'], d['la1'], d['la1'], d['la0']],
        transform=PLATE, color=DBLUE, linewidth=2.0, zorder=5)

# Validation stations
met = [(50.12385,6.06622),(49.8031,6.44337),(49.85172,6.09754),(49.5122,5.9011),
       (49.491,6.349),(49.63265,6.23293),(49.7945,5.8202),(49.99314,6.10147),
       (49.76739,5.96748),(49.63353,6.0193),(49.85891,5.84868),(50.09686,5.96961),
       (49.68087,6.43541),(50.0093,5.8475),(49.79806,6.2773),(49.8741,6.2095),
       (49.91445,6.19508),(49.762,6.11179),(49.93595,5.98093),(50.9,3.117),
       (47.917,7.4),(49.973,6.693),(51.408,9.378),(48.776,4.184),(50.583,4.683),
       (51.289,6.767),(50.637,5.443),(48.325,6.07),(50.026,8.543),(51.199,2.862),
       (51.35,3.2),(51.115,9.286),(47.85,3.497),(47.59,7.53)]
ax.scatter([s[1] for s in met], [s[0] for s in met], transform=PLATE, marker="o",
           s=26, facecolor=STATION, edgecolor="white", linewidth=0.5, zorder=9)

# country labels
for c, (lo, la) in {"GERMANY": (10.6, 51.4), "FRANCE": (1.9, 46.3), "BELGIUM": (4.0, 50.8),
                    "NETHERLANDS": (5.6, 52.5), "SWITZERLAND": (8.5, 46.6),
                    "AUSTRIA": (13.7, 47.6), "U.K.": (-1.8, 52.9)}.items():
    ax.text(lo, la, c, transform=PLATE, fontsize=7.5, fontweight="bold", color=LABELC,
            ha="center", va="center", zorder=7, path_effects=_pe)
ax.text(6.12, 49.81, "LUX.", transform=PLATE, fontsize=7, fontweight="bold",
        color="#7A3B22", ha="center", va="center", zorder=8, path_effects=_pe)

# legend
leg = ax.legend(handles=[
        Line2D([], [], color=DBLUE, lw=2.0, label="WRF model domain"),
        Patch(facecolor=GRC, alpha=0.30, edgecolor=GRC, label="Greater Region"),
        Line2D([], [], marker="o", color="none", markerfacecolor=STATION,
               markeredgecolor="white", markersize=7, label="Validation stations"),
    ], loc="lower left", fontsize=8, facecolor="white", edgecolor="0.7",
    framealpha=0.95, borderpad=0.6, fancybox=True)
leg.set_zorder(20)

gl = ax.gridlines(draw_labels=True, x_inline=False, y_inline=False,
                  linewidth=0.4, color="grey", alpha=0.45, linestyle=(0, (1, 3)))
gl.top_labels = False; gl.right_labels = False; gl.rotate_labels = False
gl.xlocator = mticker.FixedLocator(np.arange(-4, 17, 4))
gl.ylocator = mticker.FixedLocator(np.arange(44, 57, 2))
gl.xlabel_style = {"size": 8}; gl.ylabel_style = {"size": 8}

plt.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.05)
print(f"Saved -> {OUT}")
