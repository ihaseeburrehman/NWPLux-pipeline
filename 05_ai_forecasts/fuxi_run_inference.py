"""FuXi Rapid Update Cycle - event-parameterised.
Structure and channel ordering are unchanged from the production script
run_rapid_cycle_2021_month.py; only paths, window and accumulation file are
arguments, and completed cycles are skipped so a job can resume.

usage: run_fuxi.py <EVENT> <START "YYYY-MM-DD HH"> <END> <ACCUM_NC> <OUT_DIR>
"""
# Corrected FuXi run (23 Oct 2026, HPC file ai_rerun_2026/scripts/run_fuxi_noflip.py). The first version
# (run_fuxi.py) reversed the latitude axis of the ERA5 input, so rain fell at the mirrored latitude; this
# version keeps the ERA5 latitude order (north to south). Its output is the FuXi used in the thesis.
# What it does: for every 6 h ERA5 pair (t-6 h, t) it runs FuXi one step and saves the 6 h precipitation
#   and 2 m temperature valid at t+6 h.
# Inputs: ERA5 single-level (era5_sl_instant.nc) and pressure-level (era5_pl.grib) fields from MARS,
#   the 6 h precipitation accumulation file (from graphcast_01_era5_precip_accumulation.py), FuXi short.onnx.
# Outputs: <OUT_DIR>/forecast_<YYYYMMDDTHH>.nc, one file per valid time (precipitation in metres).
# Run (GPU node, ECMWF ai-models ONNX environment), e.g. for 2021:
#   python fuxi_run_inference.py 2021_event '2021-06-20 06' '2021-07-19 18' 2021_event_accum_v2.nc fuxi_noflip/output
# Settings to change: BASE, ERA5_DIR and ASSETS paths.
import sys, os, time, warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import numpy as np, xarray as xr, pandas as pd, onnxruntime as ort
from pathlib import Path
from datetime import datetime

# --- Command-line arguments: event, time window, accumulation file, output folder ---
EVENT   = sys.argv[1]
START   = np.datetime64(datetime.strptime(sys.argv[2].replace("T", " "), "%Y-%m-%d %H"))
END     = np.datetime64(datetime.strptime(sys.argv[3].replace("T", " "), "%Y-%m-%d %H"))
ACCUM   = sys.argv[4]
OUT_DIR = Path(sys.argv[5]); OUT_DIR.mkdir(parents=True, exist_ok=True)
# Fixed paths on the ECMWF HPC
BASE     = Path("/ec/res4/scratch/lux0804/ai_rerun_2026")
ERA5_DIR = BASE / "data" / EVENT / "era5_mars"
ASSETS   = Path("/usr/local/apps/ai-models/0.49/assets/fuxi")

# FuXi input variables: 5 pressure-level fields on 13 levels plus 5 surface fields (70 channels)
LEVELS = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000]
PLP    = ["z", "t", "u", "v", "r"]
SFC    = ["2t", "10u", "10v", "msl", "tp"]

# --- Load the FuXi ONNX model (GPU if available) ---
ort.set_default_logger_severity(3)
o = ort.SessionOptions()
o.enable_cpu_mem_arena = False; o.enable_mem_pattern = False; o.enable_mem_reuse = False
o.intra_op_num_threads = 8
model = ort.InferenceSession(str(ASSETS / "short.onnx"), sess_options=o,
                             providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
print("provider:", model.get_providers()[0], flush=True)

# Relative humidity from specific humidity (FuXi needs RH, ERA5 gives q)
def q_to_rh(q, t, lev):
    p = float(lev) * 100.0; Tc = t - 273.15
    es = 611.2 * np.exp(17.67 * Tc / (Tc + 243.5)); e = q * p / (0.622 + 0.378 * q)
    return np.clip(100.0 * e / es, 0.0, 100.0).astype(np.float32)

# Time embedding of the day of year and hour, as the FuXi model expects
def time_embedding(init, f=6):
    pts = [pd.Period(init + pd.Timedelta(hours=h * f), "h") for h in (-1, 0, 1)]
    v = np.array([(p.day_of_year / 366.0, p.hour / 24.0) for p in pts], dtype=np.float32)
    return np.concatenate([np.sin(v), np.cos(v)], axis=-1).reshape(1, -1)

# Give ERA5 files from different sources the same dimension names
def fix_dims(ds):
    rn = {}
    for a, b in [("valid_time","time"), ("latitude","lat"), ("longitude","lon"),
                 ("pressure_level","level"), ("isobaricInhPa","level")]:
        if a in ds.dims: rn[a] = b
    return ds.rename(rn).drop_vars(["valid_time", "step"], errors="ignore")

# --- Load ERA5 surface, accumulated precipitation and pressure-level fields (latitude order kept) ---
print("loading ERA5 ...", flush=True)
sli = fix_dims(xr.open_dataset(ERA5_DIR/"era5_sl_instant.nc", engine="netcdf4").compute())
sla = fix_dims(xr.open_dataset(ACCUM, engine="netcdf4").compute())
if "total_precipitation_6hr" in sla: sla = sla.rename({"total_precipitation_6hr": "tp"})
# Select the 13 FuXi levels BEFORE computing: the archive holds 37 levels, so a
# blind .compute() decodes ~55 GB when ~19 GB is needed.
pl  = fix_dims(xr.open_dataset(str(ERA5_DIR/"era5_pl.grib"), engine="cfgrib",
                               backend_kwargs={"indexpath": ""}))
pl  = pl.drop_vars(["valid_time", "step", "number"], errors="ignore")
pl  = pl.assign_coords(level=pl.level.astype(np.int32))
plf = pl.sel(level=LEVELS).compute()
# Add relative humidity on every level
r = np.empty_like(plf["q"].values, dtype=np.float32)
for i, l in enumerate(LEVELS):
    r[:, i] = q_to_rh(plf["q"].values[:, i], plf["t"].values[:, i], l)
plf = plf.assign(r=xr.DataArray(r, coords=plf["q"].coords, dims=plf["q"].dims))

# Times present in all three inputs
times = sorted(set(sli.time.values) & set(sla.time.values) & set(plf.time.values))
print(f"{len(times)} common ERA5 timesteps", flush=True)

# Stack the 70 input channels of one time in the FuXi order (precipitation in mm)
def chans(t):
    a, b, c = plf.sel(time=t), sli.sel(time=t), sla.sel(time=t)
    out = [a[p].sel(level=l).values.astype(np.float32) for p in PLP for l in LEVELS]
    out += [b[k].values.astype(np.float32) for k in ("t2m", "u10", "v10", "msl")]
    out.append(c["tp"].values.astype(np.float32) * 1000.0)   # m -> mm
    return np.stack(out, axis=0)

# --- Rapid update cycle: one 6 h forecast per consecutive ERA5 pair inside the window ---
n = ok = 0
for i in range(len(times) - 1):
    t0, t1 = times[i], times[i + 1]
    if (t1 - t0) / np.timedelta64(1, "h") != 6.0: continue
    if not (START <= t1 <= END): continue
    t2 = t1 + np.timedelta64(6, "h")
    if t2 not in sla.time.values: continue
    s = str(np.datetime_as_string(t2, unit="h")).replace(":", "").replace("-", "")
    f = OUT_DIR / f"forecast_{s}.nc"
    # Skip cycles already done, so a stopped job can resume
    n += 1
    if f.exists(): ok += 1; continue
    st = time.time()
    try:
        # Two input times -> one 6 h step; keep precipitation (m, no negative values) and 2 m temperature
        x = np.stack([chans(t0), chans(t1)], axis=0)[np.newaxis]
        (raw,) = model.run(None, {"input": x, "temb": time_embedding(pd.Timestamp(t1))})
        pred = raw[0, -1]
        idx = len(PLP) * len(LEVELS)
        tp = np.maximum(0.0, pred[idx + 4]) / 1000.0
        t2m = pred[idx + 0]
        # Save on the ERA5 latitude/longitude grid
        xr.Dataset(
            {"total_precipitation_6hr": xr.DataArray(tp[np.newaxis, np.newaxis], dims=["batch","time","lat","lon"]),
             "2m_temperature":          xr.DataArray(t2m[np.newaxis, np.newaxis], dims=["batch","time","lat","lon"])},
            coords={"lat": sli.lat.values, "lon": sli.lon.values},
        ).to_netcdf(f)
        ok += 1
        print(f"  {n:>4} {s}  {time.time()-st:5.1f}s  max={float(tp.max())*1000:.1f}mm", flush=True)
    except Exception as e:
        print(f"  {n:>4} {s}  FAILED: {str(e)[:70]}", flush=True)
print(f"Done: {ok}/{n} cycles -> {OUT_DIR}", flush=True)
