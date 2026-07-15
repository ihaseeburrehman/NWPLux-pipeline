# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Per-day, 6-hourly precipitation comparison maps in the same style as the
Chapter-4 spatial-validation figures (custom white-at-zero GnBu colormap,
Greater-Region extent, country borders).

  * 2021 event : rows = Belgium RADAR, WRF Before DA, WRF CONV, WRF ZTD,
                 WRF CONV+ZTD  -- one figure per day across the flood week.
                 (GPM IMERG is only available for the 14 Jul peak and is
                 already shown in the main text, so the weekly series is
                 RADAR-anchored.)
  * 2016/2018  : rows = WRF Before DA, WRF After DA (CONV+ZTD) -- one figure
                 per peak day (no radar/GPM comparison data available).

Each 6-hourly wrfout file already holds its own Rapid Update Cycle accumulation
(precip = RAINNC + RAINC + RAINSH). Radar is aggregated over the 6 h ending at
each timestamp. Output PNGs go to the thesis figures/ folder.
"""

import os
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.colors import BoundaryNorm
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import geopandas as gpd
import h5py
from osgeo import gdal
from pyproj import Transformer

FIG_DIR = "/Users/haseeb.rehman/Documents/Phd_thesis/thesis/figures"
SHP = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp"
HPC = "/Users/haseeb.rehman/Documents/Misc/From_HPC_and_WRF/WRF_from_HPC"
RADAR_ROOT = ("/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Radar_and_Weather/"
              "Belgium_Radar_data_2021/2021/07")

proj = ccrs.PlateCarree()
gdal.UseExceptions()

# ---- custom colormap: white at 0, then GnBu ----
_orig = matplotlib.colormaps["GnBu"]
CMAP = mcolors.LinearSegmentedColormap.from_list(
    "Custom_GnBu", [(1, 1, 1)] + [_orig(i) for i in range(1, 256)], N=256)

# ---- Greater-Region extent ----
_gdf = gpd.read_file(SHP).to_crs(epsg=4326)
X_MIN, Y_MIN, X_MAX, Y_MAX = _gdf.total_bounds

COUNTRIES = [
    {"name": "Lux", "lon": 6.13, "lat": 49.81},
    {"name": "Belgium", "lon": 5.5, "lat": 50.5},
    {"name": "Germany", "lon": 7.5, "lat": 49.8},
    {"name": "France", "lon": 5.9, "lat": 48.5},
]

# ---- radar grid (EPSG:3812 -> 4326) ----
_tr = Transformer.from_crs("EPSG:3812", "EPSG:4326", always_xy=True)
_ULx, _ULy, _sx, _sy, _nx, _ny = 300000.0, 1000000.0, 1000.0, 1000.0, 700, 700
_ULlon, _ULlat = _tr.transform(_ULx, _ULy)
_LRlon, _LRlat = _tr.transform(_ULx + _sx * _nx, _ULy - _sy * _ny)
RADAR_EXTENT = (
    _ULlon - (_sx / 2) * (_LRlon - _ULlon) / (_sx * _nx),
    _LRlon + (_sx / 2) * (_LRlon - _ULlon) / (_sx * _nx),
    _LRlat - (_sy / 2) * (_ULlat - _LRlat) / (_sy * _ny),
    _ULlat + (_sy / 2) * (_ULlat - _LRlat) / (_sy * _ny),
)
_rlon = np.linspace(RADAR_EXTENT[0], RADAR_EXTENT[1], _nx)
_rlat = np.linspace(RADAR_EXTENT[3], RADAR_EXTENT[2], _ny)
RLON, RLAT = np.meshgrid(_rlon, _rlat)


def read_wrf(path):
    ds = gdal.Open(path)
    if ds is None:
        return None, None, None
    subs = ds.GetSubDatasets()
    try:
        def sub(v):
            return gdal.Open([s for s in subs if v in s[0]][0][0]).ReadAsArray()
        p = sub("RAINNC") + sub("RAINC") + sub("RAINSH")
        lat = sub("XLAT")
        lon = sub("XLONG")
        p = np.where(np.isnan(p) | np.isinf(p), 0, p)
        if p.ndim == 3:
            p, lat, lon = p[0], lat[0], lon[0]
        return p, lat, lon
    except Exception:
        return None, None, None


def radar_6h(target):
    acc = np.zeros((700, 700), float)
    n = 0
    for h in range(6):
        t = target - timedelta(hours=h)
        f = os.path.join(RADAR_ROOT, f"{t.day:02d}", "accum1h", "hdf",
                         t.strftime("%Y%m%d%H%M%S") + ".radclim.accum1h.hdf")
        if not os.path.exists(f):
            continue
        try:
            with h5py.File(f, "r") as hdf:
                d = hdf["dataset1"]["data1"]["data"][:].astype(float)
                acc += np.where(d < 0, 0, d)
                n += 1
        except Exception:
            continue
    return acc if n else None


def panel(ax, lon, lat, precip, levels, norm, is_radar):
    ax.add_feature(cfeature.LAND, facecolor="#f5f2eb", zorder=0)
    ax.add_feature(cfeature.OCEAN, facecolor="#b8d4e8", zorder=0)
    if is_radar:
        cf = ax.contourf(lon, lat, precip, levels=levels, cmap=CMAP, norm=norm,
                         transform=proj, zorder=1, extend="max",
                         origin="upper", extent=RADAR_EXTENT)
    else:
        cf = ax.contourf(lon, lat, precip, levels=levels, cmap=CMAP, norm=norm,
                         transform=proj, zorder=1, extend="max")
    ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.6,
                   edgecolor="black", zorder=2, alpha=0.8)
    ax.set_extent([X_MIN, X_MAX, Y_MIN, Y_MAX], crs=proj)
    for c in COUNTRIES:
        ax.text(c["lon"], c["lat"], c["name"], fontsize=7, ha="center",
                va="center", transform=proj, zorder=3)
    return cf


def make_day_figure(day, rows, out_png, title):
    """rows: list of (label, kind, path_or_None). kind in {radar, wrf}."""
    stamps = [day + timedelta(hours=h) for h in (0, 6, 12, 18)]
    # gather data
    grid = {}       # (r,c) -> (lon,lat,precip,is_radar)
    gmax = 0.0
    for ci, st in enumerate(stamps):
        for ri, (label, kind, base) in enumerate(rows):
            if kind == "radar":
                p = radar_6h(st)
                grid[(ri, ci)] = (RLON, RLAT, p, True) if p is not None else None
            else:
                f = os.path.join(base, f"wrfout_d01_{st.strftime('%Y-%m-%d_%H_%M_%S')}")
                p, lat, lon = read_wrf(f)
                grid[(ri, ci)] = (lon, lat, p, False) if p is not None else None
            if grid[(ri, ci)] is not None:
                gmax = max(gmax, float(np.nanpercentile(grid[(ri, ci)][2], 99.5)))

    # single shared scale across the whole figure (rounded up to a 5 mm step)
    vmax = max(10.0, float(np.ceil(gmax / 5.0) * 5.0))
    levels = np.linspace(0, vmax, 11)
    norm = BoundaryNorm(levels, ncolors=CMAP.N, clip=True)

    nrow, ncol = len(rows), len(stamps)
    aspect = (X_MAX - X_MIN) / (Y_MAX - Y_MIN)
    fig, axes = plt.subplots(nrow, ncol, figsize=(aspect * 3.0 * ncol, 3.0 * nrow),
                             subplot_kw={"projection": proj}, squeeze=False)
    fig.subplots_adjust(hspace=0.06, wspace=0.02, left=0.10, right=0.90,
                        bottom=0.06, top=0.93)
    last_cf = None
    for ci, st in enumerate(stamps):
        axes[0][ci].set_title(st.strftime("%d %b %H:%M UTC"), fontsize=9)
        for ri, (label, kind, base) in enumerate(rows):
            ax = axes[ri][ci]
            cell = grid[(ri, ci)]
            if cell is None:
                ax.set_extent([X_MIN, X_MAX, Y_MIN, Y_MAX], crs=proj)
                ax.add_feature(cfeature.LAND, facecolor="#f5f2eb")
                ax.text(0.5, 0.5, "no data", transform=ax.transAxes,
                        ha="center", va="center", fontsize=7, color="grey")
            else:
                lon, lat, precip, is_radar = cell
                last_cf = panel(ax, lon, lat, precip, levels, norm, is_radar)
            gl = ax.gridlines(draw_labels=True, alpha=0.25)
            gl.top_labels = gl.right_labels = False
            gl.xlabel_style = gl.ylabel_style = {"size": 6}
            if ci > 0:
                gl.left_labels = False
            if ri < nrow - 1:
                gl.bottom_labels = False
            if ci == 0:
                ax.text(-0.32, 0.5, label, transform=ax.transAxes, rotation=90,
                        va="center", ha="center", fontsize=9, fontweight="bold")
    if last_cf is not None:
        cax = fig.add_axes([0.915, 0.15, 0.014, 0.7])
        cb = fig.colorbar(last_cf, cax=cax)
        cb.set_label("6-hourly accumulated precipitation (mm)", fontsize=9)
    fig.suptitle(title, fontsize=12)
    fig.savefig(out_png, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("Wrote", out_png)


def main():
    p2021 = {
        "Before": f"{HPC}/3rd_year/1_month_simulation_2021_new_GFS_000_cv5/Before_DA",
        "CONV":   f"{HPC}/4th_year/2021_without_ZTD_cv3/After_DA",
        "ZTD":    f"{HPC}/4th_year/2021_with_ZTD_only_cv3/After_DA",
        "CONVZTD": f"{HPC}/3rd_year/1_month_simulation_2021_new_GFS_000/After_DA",
    }
    rows2021 = [
        ("(a) Belgium RADAR", "radar", None),
        ("(b) WRF Before DA", "wrf", p2021["Before"]),
        ("(c) WRF CONV", "wrf", p2021["CONV"]),
        ("(d) WRF ZTD", "wrf", p2021["ZTD"]),
        ("(e) WRF CONV+ZTD", "wrf", p2021["CONVZTD"]),
    ]
    for d in range(13, 18):  # 13-17 July
        day = datetime(2021, 7, d)
        make_day_figure(
            day, rows2021,
            os.path.join(FIG_DIR, f"week2021_maps_{day.strftime('%Y%m%d')}.png"),
            f"WRF precipitation vs Belgium RADAR -- {day.strftime('%d %B %Y')} "
            "(6-hourly accumulation, mm)")

    # 2018 Mullerthal (peak ~1 June): Before vs After (CONV+ZTD, CV5)
    rows_ba_2018 = [
        ("(a) WRF Before DA", "wrf", f"{HPC}/3rd_year/1_month_simulation_2018_GFS_000_cv5/Before_DA"),
        ("(b) WRF After DA (CONV+ZTD)", "wrf", f"{HPC}/3rd_year/1_month_simulation_2018_GFS_000_cv5/After_DA"),
    ]
    for m, d in [(5, 31), (6, 1), (6, 2)]:
        day = datetime(2018, m, d)
        make_day_figure(
            day, rows_ba_2018,
            os.path.join(FIG_DIR, f"event2018_maps_{day.strftime('%Y%m%d')}.png"),
            f"WRF precipitation, 2018 Mullerthal event -- {day.strftime('%d %B %Y')} "
            "(6-hourly accumulation, mm)")

    # 2016 event (peak 21-23 July): Before vs After (CONV+ZTD, CV5)
    rows_ba_2016 = [
        ("(a) WRF Before DA", "wrf", f"{HPC}/3rd_year/1_month_simulation_2016_GFS_000_cv5/Before_DA"),
        ("(b) WRF After DA (CONV+ZTD)", "wrf", f"{HPC}/3rd_year/1_month_simulation_2016_GFS_000_cv5/After_DA"),
    ]
    for d in [21, 22, 23]:
        day = datetime(2016, 7, d)
        make_day_figure(
            day, rows_ba_2016,
            os.path.join(FIG_DIR, f"event2016_maps_{day.strftime('%Y%m%d')}.png"),
            f"WRF precipitation, 2016 event -- {day.strftime('%d %B %Y')} "
            "(6-hourly accumulation, mm)")


if __name__ == "__main__":
    main()
