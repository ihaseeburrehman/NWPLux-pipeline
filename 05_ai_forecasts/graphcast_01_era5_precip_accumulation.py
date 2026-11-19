"""Build 6-hourly ERA5 accumulation files (tp, tisr) valid at 00/06/12/18 UTC.

ERA5 accumulations from MARS (type=fc, hourly steps) are HOURLY totals for the
hour ENDING at the step -- verified empirically: tisr is constant across all 12
steps (one hour of TOA solar; a cumulative field would grow), and tp is never
negative.

Two modes:
  sum6h   physically correct 6-h total  = sum of six consecutive hourly steps
  hourly  the single hour ending at T   = the CDS "hourly sampled at 00/06/12/18"
          shortcut. This is what the published May-2026 GraphCast run used, and
          it reproduces those forecasts to 0.8 %.

Window mapping (both modes):
  T=12 -> base 06 same day, steps 1..6      T=18 -> base 06 same day, steps 7..12
  T=00 -> base 18 prev day, steps 1..6      T=06 -> base 18 prev day, steps 7..12

usage: build_accum.py <accum_raw.grib> <sum6h|hourly> <out.nc> <T0> <T1>
"""
# Input:  a GRIB file of ERA5 accumulated fields (tp, tisr) from MARS, type=fc,
#         base times 06 and 18 UTC with hourly steps 1..12.
# Output: a NetCDF file with total_precipitation_6hr and toa_incident_solar_radiation
#         every 6 h from T0 to T1. It is the ACCUM_NC input of graphcast_02_run_inference.py.
# Run:    python3 graphcast_01_era5_precip_accumulation.py <accum_raw.grib> <sum6h|hourly> <out.nc> <T0> <T1>
#         (the docstring above and graphcast_02 call this script build_accum.py).
# Change: nothing in the file; all settings are command-line arguments.
#         Only tp is summed over 6 h; tisr is always the last hour of the window.
import sys
import numpy as np
import pandas as pd
import xarray as xr

# --- Read the command-line arguments ---
SRC, MODE, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
T0, T1 = pd.Timestamp(sys.argv[4]), pd.Timestamp(sys.argv[5])
assert MODE in ("sum6h", "hourly"), MODE
ACCUMULATE_ONLY = {"tp"}   # v2 FIX: tisr must NOT be summed (see README)
NAME = {"tp": "total_precipitation_6hr", "tisr": "toa_incident_solar_radiation"}

# --- Open the GRIB file; get the forecast step (hours) and base time of each field ---
ds = xr.open_dataset(SRC, engine="cfgrib",
                     backend_kwargs={"indexpath": "", "filter_by_keys": {"dataType": "fc"}})
hrs = np.array([int(x.total_seconds() // 3600) for x in pd.to_timedelta(ds.step.values)])
base = pd.to_datetime(ds.time.values)

# re-verify the hourly convention rather than trusting the docstring
for v in ds.data_vars:
    assert float(ds[v].min()) >= -1e-9, f"{v} has negative hourly values"
tis = ds["tisr"].isel(time=0)
mx = [float(tis.isel(step=k).max()) for k in range(len(hrs))]
assert max(mx) - min(mx) < 0.05 * max(mx), "tisr grows with step -> cumulative, not hourly"

# Step indices for windows ending at step 6 or 12: all six hours, or only the last hour
win = {6: np.where((hrs >= 1) & (hrs <= 6))[0], 12: np.where((hrs >= 7) & (hrs <= 12))[0]}
last = {6: np.where(hrs == 6)[0], 12: np.where(hrs == 12)[0]}

# --- For each 6-hourly valid time T, pick the base run and steps, then sum over the steps ---
out, kept = {v: [] for v in ds.data_vars}, []
for T in pd.date_range(T0, T1, freq="6h"):
    end = 6 if T.hour in (0, 12) else 12
    b = (T.normalize() + pd.Timedelta(hours=6)) if T.hour in (12, 18) \
        else (T.normalize() - pd.Timedelta(hours=6))
    j = np.where(base == b)[0]
    if len(j) == 0:
        continue
    idx = win[end] if MODE == "sum6h" else last[end]
    for v in ds.data_vars:
        vidx = idx if v in ACCUMULATE_ONLY else last[end]
        out[v].append(ds[v].isel(time=int(j[0])).isel(step=vidx).sum("step").values.astype("float32"))
    kept.append(T)

# --- Write the result to NetCDF and check that precipitation is between 0 and 500 mm ---
res = xr.Dataset(
    {NAME[v]: (("time", "latitude", "longitude"), np.stack(out[v])) for v in out},
    coords={"time": kept, "latitude": ds.latitude.values, "longitude": ds.longitude.values},
)
res.to_netcdf(OUT, encoding={v: {"zlib": True, "complevel": 1, "dtype": "float32"}
                             for v in res.data_vars})
tp = res["total_precipitation_6hr"] * 1000.0
print(f"WROTE {OUT} mode={MODE} steps={len(kept)} "
      f"{kept[0]}..{kept[-1]} tp_global_max={float(tp.max()):.1f}mm")
assert float(tp.max()) < 500 and float(tp.min()) >= 0
