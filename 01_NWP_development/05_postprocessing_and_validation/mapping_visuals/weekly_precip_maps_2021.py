# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Weekly (per-day) accumulated-precipitation maps for the July 2021 flood event,
from the optimal After-DA / ERA5 WRF run (d02, 4 km, Greater Region).

WRF RAINNC resets each 6-hourly Rapid Update Cycle, so each 6-hourly wrfout file
holds the accumulation for its own cycle (precip = RAINNC + RAINC + RAINSH). The
daily total for calendar day D is the sum of the files stamped D_06, D_12, D_18
and (D+1)_00 (each labelled by the END of its 6 h window).

Produces figures/weekly_precip_maps_2021.png (one panel per day, shared colorbar).
"""

import glob
import os
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from netCDF4 import Dataset

RUN = ("/Users/haseeb.rehman/Documents/Misc/From_HPC_and_WRF/WRF_Local_machine/"
       "4th_year/2021_ERA5_local_machine_3_domains/After_DA")
DOM = "d02"
DAYS = ["2021-07-13", "2021-07-14", "2021-07-15", "2021-07-16", "2021-07-17"]
OUT = ("/Users/haseeb.rehman/Documents/Phd_thesis/thesis/figures/"
       "weekly_precip_maps_2021.png")


def fname(dt):
    return os.path.join(RUN, f"wrfout_{DOM}_{dt.strftime('%Y-%m-%d_%H_00_00')}")


def precip_field(path):
    with Dataset(path) as nc:
        p = nc.variables["RAINNC"][0]
        for extra in ("RAINC", "RAINSH"):
            if extra in nc.variables:
                p = p + nc.variables[extra][0]
        lon = nc.variables["XLONG"][0]
        lat = nc.variables["XLAT"][0]
    return np.array(p), np.array(lon), np.array(lat)


def daily_total(day):
    d0 = datetime.strptime(day, "%Y-%m-%d")
    stamps = [d0 + timedelta(hours=h) for h in (6, 12, 18, 24)]
    total, lon, lat = None, None, None
    for st in stamps:
        f = fname(st)
        if not os.path.exists(f):
            continue
        p, lon, lat = precip_field(f)
        total = p if total is None else total + p
    return total, lon, lat


def main():
    fields = [(d,) + daily_total(d) for d in DAYS]
    fields = [f for f in fields if f[1] is not None]
    vmax = max(np.nanpercentile(f[1], 99) for f in fields)
    vmax = float(np.ceil(vmax / 10.0) * 10.0)
    levels = np.linspace(0, vmax, 11)
    cmap = plt.get_cmap("YlGnBu")
    norm = BoundaryNorm(levels, cmap.N)

    n = len(fields)
    ncol = min(3, n)
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(4.2 * ncol, 3.6 * nrow),
                             squeeze=False)
    mesh = None
    for k, (day, tot, lon, lat) in enumerate(fields):
        ax = axes[k // ncol][k % ncol]
        mesh = ax.pcolormesh(lon, lat, tot, cmap=cmap, norm=norm, shading="auto")
        ax.set_title(datetime.strptime(day, "%Y-%m-%d").strftime("%d %b %Y"),
                     fontsize=11)
        ax.set_xlabel("Longitude (°E)", fontsize=8)
        ax.set_ylabel("Latitude (°N)", fontsize=8)
        ax.tick_params(labelsize=7)
    for k in range(len(fields), nrow * ncol):
        axes[k // ncol][k % ncol].axis("off")

    cbar = fig.colorbar(mesh, ax=axes, orientation="vertical",
                        fraction=0.025, pad=0.02)
    cbar.set_label("Daily accumulated precipitation (mm)", fontsize=9)
    fig.suptitle("WRF (After-DA, ERA5, 4 km) daily accumulated precipitation – "
                 "July 2021 flood event", fontsize=12)
    fig.savefig(OUT, dpi=200, bbox_inches="tight")
    print("Wrote", OUT, "panels:", len(fields))


if __name__ == "__main__":
    main()
