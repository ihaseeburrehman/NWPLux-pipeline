#!/usr/bin/env python3
"""
Manning's n / land-cover roughness map for the WRF-vs-AI -> LISFLOOD-FP paper.
Distinct from the prior paper's all-green categorical map: a smooth->rough
sequential palette (blue water, tan bare/built, green vegetation gradient, red
buildings) keyed to the Manning n value, with the Alzette river overlaid.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from matplotlib.colors import ListedColormap, BoundaryNorm

BASE = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin"
MANNING = f"{BASE}/sub_basins/10m/ready_for_simulation/manning.n.ascii"
RIVER = f"{BASE}/sub_basins/5m/sub_basin_complete/pre_processing/alzette_river.shp"
OUT = "/Users/haseeb.rehman/Documents/Phd_thesis/Research_papers/WRF_vs_AI_LISFLOOD_v1/figures/figure2.png"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# value -> (label, colour), ordered smooth -> rough
CLASSES = [
    (0.02,  "Bare soil / constructed", "#e3d3a6"),
    (0.03,  "Water",                   "#3b7dd8"),
    (0.035, "Permanent herbaceous",    "#c7e9b4"),
    (0.04,  "Seasonal herbaceous",     "#7fcdbb"),
    (0.07,  "Bush",                    "#41ab5d"),
    (0.10,  "Tree",                    "#00602a"),
    (0.20,  "Building",                "#b30000"),
]
vals = [c[0] for c in CLASSES]
cmap = ListedColormap([c[2] for c in CLASSES])
bounds = [vals[0] - 0.005] + [(vals[i] + vals[i + 1]) / 2 for i in range(len(vals) - 1)] + [vals[-1] + 0.05]
norm = BoundaryNorm(bounds, len(vals))

with rasterio.open(MANNING) as src:
    scrs = src.crs if src.crs else "EPSG:2169"
    tr, w, h = calculate_default_transform(scrs, "EPSG:4326", src.width, src.height, *src.bounds)
    dst = np.full((h, w), -9999, dtype=np.float32)
    reproject(src.read(1), dst, src_transform=src.transform, src_crs=scrs,
              dst_transform=tr, dst_crs="EPSG:4326",
              resampling=Resampling.nearest, src_nodata=src.nodata, dst_nodata=-9999)
data = np.ma.masked_equal(dst, -9999)
b = rasterio.transform.array_bounds(h, w, tr)
ext = [b[0], b[2], b[1], b[3]]

fig, ax = plt.subplots(figsize=(11, 10))
ax.imshow(data, extent=ext, origin="upper", cmap=cmap, norm=norm, interpolation="nearest", zorder=1)
try:
    gpd.read_file(RIVER).to_crs(4326).plot(ax=ax, color="#08306b", linewidth=1.1, alpha=0.9, zorder=2)
except Exception as e:
    print("river:", e)

ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3])
ax.set_aspect(1.0 / np.cos(np.radians((ext[2] + ext[3]) / 2)))
ax.set_xlabel("Longitude (°E)", fontsize=13); ax.set_ylabel("Latitude (°N)", fontsize=13)
ax.tick_params(labelsize=11)

handles = [mpatches.Patch(facecolor=c[2], edgecolor="black", linewidth=0.4,
                          label=f"{c[1]}  (n={c[0]})") for c in CLASSES]
handles.append(plt.Line2D([0], [0], color="#08306b", lw=1.1, label="Alzette river"))
ax.legend(handles=handles, loc="upper left", fontsize=8, framealpha=0.92, title="Manning's $n$",
          title_fontsize=9)

ax.annotate("", xy=(0.06, 0.93), xytext=(0.06, 0.86), xycoords="axes fraction",
            arrowprops=dict(facecolor="black", width=2, headwidth=8))
ax.text(0.06, 0.935, "N", transform=ax.transAxes, ha="center", fontsize=11, fontweight="bold")

plt.tight_layout()
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
print("SAVED", OUT)
