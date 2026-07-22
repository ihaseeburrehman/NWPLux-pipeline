#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Animated 2x2-panel comparison of 6-hour precipitation pattern, with Luxembourg's
12 cantons (Luxembourg_Regions.shp; cantons are the country's administrative
divisions since the 2015 abolition of districts) overlaid on every panel, so
CGDIS can see which part of the country each system placed the rainfall in.

Each frame, 2x2 grid:
    RADAR                | NWPLux
    AI Model - GraphCast  | AI Model - AIFS

Two output modes (see MODE below):
    "full"   -- same Greater-Region extent as the original animation, canton
                boundaries drawn but NOT labelled (cantons are too small at
                this zoom for legible labels).
    "zoomed" -- zoomed to Luxembourg's own extent, canton boundaries AND
                labels, with each label's font size shrunk automatically so
                it fits inside its own canton polygon.

Cadence: 6 hours
Window: 2021-07-10 06 UTC -> 2021-07-17 18 UTC
Requires ffmpeg in PATH.
"""

import os
import sys
import shutil
from datetime import datetime, timedelta

if sys.platform == "darwin":
    homebrew_bin = "/opt/homebrew/bin"
    if homebrew_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = homebrew_bin + os.pathsep + os.environ.get("PATH", "")

import numpy as np
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import BoundaryNorm
from matplotlib.animation import FuncAnimation, FFMpegWriter

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from shapely.geometry import box

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from radar_wrf_ai_precip_comparison import (
    aggregate_radar_6h, wrf_6h, gc_6h, aifs_6h, radar_grid_to_latlon, make_colormap,
    LON_MIN, LON_MAX, LAT_MIN, LAT_MAX,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODE = sys.argv[1] if len(sys.argv) > 1 else "full"   # "full" or "zoomed"
assert MODE in ("full", "zoomed")

TS_START = datetime(2021, 7, 10, 6)
TS_END   = datetime(2021, 7, 17, 18)
DT_HOURS = 6
FPS      = 2

CANTON_SHP = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Luxembourg_Regions.shp"

OUTPUT_DIR  = "/Users/haseeb.rehman/Python scripts/output"
if MODE == "full":
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "radar_wrf_ai_2021_animation_cantons.mp4")
else:
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, "radar_wrf_ai_2021_animation_cantons_zoomed.mp4")

ROW_LABELS  = ["RADAR", "NWPLux", "AI Model - GraphCast", "AI Model - AIFS"]
ROW_KEYS    = ["RAD", "WRF", "GC", "AIFS"]

COUNTRY_LABELS = [
    ("BELGIUM",    4.9, 50.6),
    ("FRANCE",     5.2, 48.6),
    ("GERMANY",    7.8, 50.3),
    ("LUXEMBOURG", 6.13, 49.78),
]

cantons = gpd.read_file(CANTON_SHP)
_pad = 0.03
LUX_EXTENT = [
    cantons.total_bounds[0] - _pad, cantons.total_bounds[2] + _pad,
    cantons.total_bounds[1] - _pad, cantons.total_bounds[3] + _pad,
]


def build_timestamps():
    out, t = [], TS_START
    while t <= TS_END:
        out.append(t)
        t += timedelta(hours=DT_HOURS)
    return out


def gather_all_frames(timestamps):
    frames = []
    for t in timestamps:
        print(f"  {t:%Y-%m-%d %H UTC}")
        rad, gt, wkt, files = aggregate_radar_6h(t)
        r_lat = r_lon = None
        if rad is not None:
            r_lat, r_lon = radar_grid_to_latlon(gt, wkt, rad.shape)
            print(f"      RADAR {len(files)} files  max={np.nanmax(rad):6.1f}")
        else:
            print("      RADAR  no data")

        w, w_lat, w_lon = wrf_6h(t)
        g, g_lat, g_lon = gc_6h(t)
        a, a_lat, a_lon = aifs_6h(t)

        for name, arr in zip(["WRF", "GC", "AIFS"], [w, g, a]):
            if arr is not None:
                print(f"      {name:4s}                 max={np.nanmax(arr):6.1f}")
            else:
                print(f"      {name:4s}   no data")

        frames.append({
            "t":   t,
            "RAD": (rad, r_lat, r_lon),
            "WRF": (w,    w_lat, w_lon),
            "GC":  (g,    g_lat, g_lon),
            "AIFS":(a,    a_lat, a_lon),
        })
    return frames


def shared_colour_scale(frames):
    all_max = []
    for fr in frames:
        for key in ROW_KEYS:
            arr = fr[key][0]
            if arr is not None:
                m = float(np.nanmax(arr))
                if np.isfinite(m):
                    all_max.append(m)
    vmax = float(np.ceil(max(all_max) / 10.0) * 10.0) if all_max else 50.0
    levels = np.arange(0, vmax + 0.001, max(2.0, vmax / 20))
    return vmax, levels


def fit_label_fontsize(fig, ax, text_str, point, poly, proj, max_fs=9.5, min_fs=4.0):
    """Shrink the font size until the rendered label's bbox (converted back to
    data/degrees) fits inside the polygon's bounds, so no label spills out of
    its own canton."""
    minx, miny, maxx, maxy = poly.bounds
    avail_w = (maxx - minx) * 0.92
    fs = max_fs
    renderer = fig.canvas.get_renderer()
    while fs >= min_fs:
        t = ax.text(point.x, point.y, text_str, transform=proj, fontsize=fs,
                    ha="center", va="center", color="#1a1a1a", fontweight="bold",
                    zorder=6)
        fig.canvas.draw()
        bbox = t.get_window_extent(renderer=renderer)
        inv = ax.transData.inverted()
        (x0, _), (x1, _) = inv.transform([[bbox.x0, bbox.y0], [bbox.x1, bbox.y1]])
        rendered_w = abs(x1 - x0)
        if rendered_w <= avail_w:
            return t
        t.remove()
        fs -= 0.5
    # fallback at minimum size even if slightly tight
    return ax.text(point.x, point.y, text_str, transform=proj, fontsize=min_fs,
                   ha="center", va="center", color="#1a1a1a", fontweight="bold",
                   zorder=6)


def make_animation(frames, vmax, levels):
    cmap = make_colormap()
    norm = BoundaryNorm(levels, ncolors=cmap.N, clip=True)
    proj = ccrs.PlateCarree()

    extent = LUX_EXTENT if MODE == "zoomed" else [LON_MIN, LON_MAX, LAT_MIN, LAT_MAX]
    figsize = (11.5, 10.2) if MODE == "zoomed" else (11.0, 9.6)

    fig, axes2d = plt.subplots(2, 2, figsize=figsize, subplot_kw={"projection": proj})
    axes = axes2d.ravel()

    for ax, label in zip(axes, ROW_LABELS):
        ax.set_extent(extent, crs=proj)
        ax.add_feature(cfeature.BORDERS,   linewidth=0.7, edgecolor="black")
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5, edgecolor="black")
        ax.add_feature(cfeature.RIVERS,    linewidth=0.3, edgecolor="#5b8db8", alpha=0.6)

        # canton boundaries on every panel
        for geom in cantons.geometry:
            ax.add_geometries([geom], crs=proj, facecolor="none",
                              edgecolor="#333333", linewidth=0.9, zorder=5)

        gl = ax.gridlines(draw_labels=True, alpha=0.25, linewidth=0.4)
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabel_style = {"size": 8}
        gl.ylabel_style = {"size": 8}
        ax.set_title(label, fontsize=12, fontweight="bold", pad=8)

        if MODE == "full":
            for name, lon_c, lat_c in COUNTRY_LABELS:
                ax.text(lon_c, lat_c, name, transform=proj,
                        color="#444444", fontsize=7, fontweight="bold",
                        ha="center", va="center", alpha=0.7)
        else:
            # canton labels, auto-shrunk to fit inside each polygon
            for _, row in cantons.iterrows():
                poly = row.geometry
                pt = poly.representative_point()
                fit_label_fontsize(fig, ax, row["Name"], pt, poly, proj)

    plt.subplots_adjust(left=0.06, right=0.90, top=0.90, bottom=0.05,
                        wspace=0.10, hspace=0.16)
    cbar_ax = fig.add_axes([0.925, 0.12, 0.018, 0.72])
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cbar = fig.colorbar(sm, cax=cbar_ax, extend="max")
    cbar.set_label("6-hour precipitation (mm)", fontsize=10)
    cbar.ax.tick_params(labelsize=8)

    time_text = fig.text(0.5, 0.955, "", ha="center", va="bottom",
                         fontsize=13, fontweight="bold")

    contour_handles = [None] * len(ROW_KEYS)
    no_data_text    = [None] * len(ROW_KEYS)

    def draw_frame(i):
        fr = frames[i]
        time_text.set_text(f"Valid:  {fr['t']:%Y-%m-%d  %H:%M UTC}  (6-h accumulation)")

        for ax_idx, key in enumerate(ROW_KEYS):
            ax = axes[ax_idx]
            if contour_handles[ax_idx] is not None:
                for coll in contour_handles[ax_idx].collections:
                    coll.remove()
                contour_handles[ax_idx] = None
            if no_data_text[ax_idx] is not None:
                no_data_text[ax_idx].remove()
                no_data_text[ax_idx] = None

            arr, lat, lon = fr[key]
            if arr is None or lat is None or lon is None:
                no_data_text[ax_idx] = ax.text(
                    0.5, 0.5, "no data", transform=ax.transAxes,
                    ha="center", va="center", color="grey", fontsize=11)
                continue
            cf = ax.contourf(lon, lat, arr, levels=levels, cmap=cmap,
                             norm=norm, transform=proj, extend="max", alpha=0.75,
                             zorder=1)
            contour_handles[ax_idx] = cf

        return [time_text]

    anim = FuncAnimation(fig, draw_frame, frames=len(frames),
                         interval=1000 / FPS, blit=False, repeat=False)
    return fig, anim


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        print("ERROR: ffmpeg not found in PATH.")
        print("Install it with:  brew install ffmpeg")
        sys.exit(1)

    print(f"Mode: {MODE}")
    timestamps = build_timestamps()
    frames = gather_all_frames(timestamps)
    vmax, levels = shared_colour_scale(frames)

    fig, anim = make_animation(frames, vmax, levels)

    writer = FFMpegWriter(fps=FPS, codec="libx264", bitrate=2500,
                          extra_args=["-pix_fmt", "yuv420p", "-preset", "medium", "-tune", "stillimage"])
    anim.save(OUTPUT_FILE, writer=writer, dpi=160)
    plt.close(fig)
    print(f"\nSaved -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
