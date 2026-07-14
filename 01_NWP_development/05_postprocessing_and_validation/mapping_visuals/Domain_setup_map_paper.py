"""
WRF single-domain (d01, 12 km) setup map -- refreshed aesthetic for the
"WRF vs GraphCast" paper. Cool light-grey land, pale-blue ocean, translucent
domain fill, and a muted palette consistent with the paper's result figures.
Only the outer domain d01 is shown.

Output: <paper>/figures/domains_setup_map.png
"""
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.ticker as mticker
from matplotlib import patheffects
from matplotlib.patches import Rectangle

PLATE = ccrs.PlateCarree()
OUT = "/Users/haseeb.rehman/Documents/Research_papers/WRF_vs_GraphCast_v1/figures/domains_setup_map.png"

# ---- refreshed palette (distinct from the cream/steel-blue of the other paper)
LAND   = "#ECEFF1"   # cool light grey
OCEAN  = "#DCE8F0"   # pale desaturated blue
BORDER = "#9AA3AB"
COAST  = "#6B7884"
DBLUE  = "#2C5F8A"   # domain box
LABELC = "#5A6570"

d01 = dict(lon_min=-1.324371337890625, lat_min=44.60498809814453,
           lon_max=13.7489013671875,  lat_max=54.220977783203125)

fig = plt.figure(figsize=(8.0, 6.4))
ax  = plt.axes(projection=PLATE)
ax.set_extent([d01['lon_min'] - 1.2, d01['lon_max'] + 1.2,
               d01['lat_min'] - 0.8, d01['lat_max'] + 0.9], crs=PLATE)

ax.set_facecolor(OCEAN)
ax.add_feature(cfeature.OCEAN.with_scale("50m"), facecolor=OCEAN, edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("50m"),  facecolor=LAND,  edgecolor="none", zorder=1)
ax.add_feature(cfeature.LAKES.with_scale("50m"), facecolor=OCEAN, edgecolor="none", zorder=2)
ax.add_feature(cfeature.BORDERS.with_scale("50m"), linewidth=0.8, edgecolor=BORDER, zorder=3)
ax.add_feature(cfeature.COASTLINE.with_scale("50m"), linewidth=0.8, edgecolor=COAST, zorder=3)

# d01 box with translucent fill
w = d01['lon_max'] - d01['lon_min']
h = d01['lat_max'] - d01['lat_min']
ax.add_patch(Rectangle((d01['lon_min'], d01['lat_min']), w, h, transform=PLATE,
                       facecolor=DBLUE, alpha=0.06, edgecolor="none", zorder=4))
lons = [d01['lon_min'], d01['lon_max'], d01['lon_max'], d01['lon_min'], d01['lon_min']]
lats = [d01['lat_min'], d01['lat_min'], d01['lat_max'], d01['lat_max'], d01['lat_min']]
ax.plot(lons, lats, transform=PLATE, color=DBLUE, linewidth=2.0, zorder=5)
ax.text(d01['lon_min'] + 0.35, d01['lat_max'] - 0.35, "d01 (12 km)", transform=PLATE,
        fontsize=14, fontweight="bold", ha="left", va="top", color=DBLUE,
        path_effects=[patheffects.withStroke(linewidth=2.4, foreground="white")], zorder=6)

# country labels
_pe = [patheffects.withStroke(linewidth=2.2, foreground="white")]
countries = {"GERMANY": (10.2, 51.2), "FRANCE": (2.4, 47.0), "BELGIUM": (4.2, 50.6),
             "NETHERLANDS": (5.4, 52.4), "LUX.": (6.12, 49.7), "SWITZERLAND": (8.2, 46.9),
             "AUSTRIA": (13.2, 47.4), "U.K.": (-1.0, 52.6)}
for c, (lo, la) in countries.items():
    ax.text(lo, la, c, transform=PLATE, fontsize=8, fontweight="bold", color=LABELC,
            ha="center", va="center", zorder=7, path_effects=_pe)

gl = ax.gridlines(draw_labels=True, linestyle=(0, (1, 3)), linewidth=0.5,
                  color="#B0B0B0", alpha=0.8)
gl.top_labels = False
gl.right_labels = False
gl.xlocator = mticker.FixedLocator(range(0, 15, 2))
gl.ylocator = mticker.FixedLocator(range(44, 56, 2))
gl.xlabel_style = {"size": 9, "color": "#333333"}
gl.ylabel_style = {"size": 9, "color": "#333333"}

plt.savefig(OUT, dpi=400, bbox_inches="tight", pad_inches=0.05)
print(f"Saved -> {OUT}")
