"""GraphCast Rapid Update Cycle - MARS NetCDF (CDO converted)"""
# Runs GraphCast in a rapid update cycle: every 6 h from START to END, one 6 h
# forecast is made from ERA5 at t-6 h and t0, and total_precipitation_6hr and
# 2m_temperature at t+6 h are saved.
#
# Input:  ERA5 single-level NetCDF (era5_sl_instant.nc) and pressure-level GRIB
#         (era5_pl.grib) in BASE/data/<EVENT>/era5_mars; the 6 h accumulation NetCDF
#         from graphcast_01_era5_precip_accumulation.py; the GraphCast weights and
#         normalisation statistics in BASE/weights.
# Output: forecast_YYYYMMDDTHH.nc in OUT_DIR, one per cycle, named by valid time.
#         Existing files are skipped, so a stopped run can be restarted.
# Run:    python3 graphcast_02_run_inference.py <EVENT> "<YYYY-MM-DD HH>" "<YYYY-MM-DD HH>" <ACCUM_NC> <OUT_DIR>
# Change: BASE and WEIGHTS in the configuration block, and the sys.path line
#         below, which points to the JAX environment on the HPC.
import sys, os, time, warnings, dataclasses, glob
# Quiet warnings and log messages; add the HPC JAX environment to the import path
warnings.filterwarnings("ignore")
os.environ["JAX_TRACEBACK_FILTERING"] = "off"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
sys.path.insert(0, "/usr/local/apps/ai-models/0.49/env-jax/lib/python3.11/site-packages")

import numpy as np, xarray as xr, haiku as hk, jax
from pathlib import Path
from datetime import datetime, timedelta
from graphcast import (graphcast, normalization, data_utils, checkpoint, rollout,
                       autoregressive, casting)

# Terminal colours for the progress output
G="\033[92m"; R="\033[91m"; Y="\033[93m"; B="\033[1m"; RS="\033[0m"

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
# usage: run_graphcast.py <EVENT> <START "YYYY-MM-DD HH"> <END> <ACCUM_NC> <OUT_DIR>
EVENT      = sys.argv[1]
START_DATE = datetime.strptime(sys.argv[2].replace("T", " "), "%Y-%m-%d %H")
END_DATE   = datetime.strptime(sys.argv[3].replace("T", " "), "%Y-%m-%d %H")
ACCUM_NC   = sys.argv[4]
BASE       = Path("/ec/res4/scratch/lux0804/ai_rerun_2026")
ERA5_DIR   = BASE / "data" / EVENT / "era5_mars"
WEIGHTS    = BASE / "weights/GraphCast_1979-2017_precip_in_out.npz"
STATS_DIR  = BASE / "weights"
OUT_DIR    = Path(sys.argv[5])
OUT_DIR.mkdir(parents=True, exist_ok=True)

# CDO renames variables to varXXX using GRIB param IDs
SL_RENAME = {
    "t2m":"2m_temperature", "msl":"mean_sea_level_pressure",
    "u10":"10m_u_component_of_wind", "v10":"10m_v_component_of_wind",
    "sst":"sea_surface_temperature", "siconc":"sea_ice_cover",
    "tcwv":"total_column_water_vapour", "z":"geopotential_at_surface",
    "lsm":"land_sea_mask",
}
ACCUM_RENAME = {}  # build_accum.py already writes GraphCast names
# Pressure-level short names to GraphCast names
PL_RENAME = {
    "z":"geopotential", "q":"specific_humidity", "t":"temperature",
    "u":"u_component_of_wind", "v":"v_component_of_wind", "w":"vertical_velocity",
}

print(f"\n{B}GraphCast Rapid Cycle (MARS-NC) - {EVENT}{RS}\n")

# --- Load the GraphCast checkpoint and the normalisation statistics ---
print(f"  {Y}[1/4]{RS} Loading model...", flush=True)
with open(WEIGHTS, "rb") as f:
    ckpt = checkpoint.load(f, graphcast.CheckPoint)
params, state = ckpt.params, {}
model_config, task_config = ckpt.model_config, ckpt.task_config
diffs_stddev  = xr.load_dataset(STATS_DIR/"diffs_stddev_by_level.nc").compute()
mean_by_level = xr.load_dataset(STATS_DIR/"mean_by_level.nc").compute()
stddev        = xr.load_dataset(STATS_DIR/"stddev_by_level.nc").compute()
print(f"  {G}[OK]{RS} Model loaded", flush=True)

# --- Open the ERA5 inputs (lazily) and rename variables and dimensions to GraphCast names ---
print(f"  {Y}[2/4]{RS} Opening ERA5 files (lazy)...", flush=True)

# Single-level fields
sl_raw = xr.open_dataset(ERA5_DIR/"era5_sl_instant.nc", engine="netcdf4")
sl_raw = sl_raw.rename({k:v for k,v in SL_RENAME.items() if k in sl_raw})
if "latitude" in sl_raw.dims: sl_raw = sl_raw.rename({"latitude":"lat","longitude":"lon"})

# GraphCast identifies static fields by the ABSENCE of a time dimension. MARS
# returns geopotential_at_surface and land_sea_mask at every analysis time, so
# they must be collapsed to a single slice; leaving the time axis on makes each
# contribute one feature per input step and the encoder shape overruns by 2.
for _v in ("geopotential_at_surface", "land_sea_mask"):
    if _v in sl_raw and "time" in sl_raw[_v].dims:
        sl_raw[_v] = sl_raw[_v].isel(time=0, drop=True)

# 6 h accumulations from graphcast_01 (precipitation and TOA solar radiation)
accum_raw = xr.open_dataset(ACCUM_NC, engine="netcdf4")
accum_raw = accum_raw.rename({k:v for k,v in ACCUM_RENAME.items() if k in accum_raw})
if "latitude" in accum_raw.dims: accum_raw = accum_raw.rename({"latitude":"lat","longitude":"lon"})

# PL is read straight from GRIB: grib_to_netcdf on a 55 GB pressure-level file is
# wasteful and the cfgrib path was verified equivalent on the flood window.
pl_raw = xr.open_dataset(str(ERA5_DIR/"era5_pl.grib"), engine="cfgrib",
                         backend_kwargs={"indexpath": ""})
pl_raw = pl_raw.drop_vars(["valid_time", "step", "number"], errors="ignore")
pl_raw = pl_raw.rename({k:v for k,v in PL_RENAME.items() if k in pl_raw})
if "latitude" in pl_raw.dims: pl_raw = pl_raw.rename({"latitude":"lat","longitude":"lon"})

# Latitude must be ASCENDING (S->N), matching the original run's outputs and the
# DeepMind example batches. grib_to_netcdf delivers N->S, so flip once here.
def _ascending(d):
    return d.isel(lat=slice(None, None, -1)) if float(d.lat[0]) > float(d.lat[-1]) else d
sl_raw, accum_raw, pl_raw = _ascending(sl_raw), _ascending(accum_raw), _ascending(pl_raw)
# Name the vertical coordinate 'level', in hPa, stored as integers
if "plev" in pl_raw.dims: pl_raw = pl_raw.rename({"plev":"level"})
if "isobaricInhPa" in pl_raw.dims: pl_raw = pl_raw.rename({"isobaricInhPa":"level"})
if float(pl_raw.level.max()) > 2000: pl_raw = pl_raw.assign_coords(level=(pl_raw.level/100))
pl_raw = pl_raw.assign_coords(level=pl_raw.level.astype(np.int32))

print(f"  {G}[OK]{RS} ERA5 opened - SL:{dict(sl_raw.sizes)} PL:{dict(pl_raw.sizes)}", flush=True)

# Build cycles
init_times = []
t = START_DATE
while t + timedelta(hours=6) <= END_DATE:
    init_times.append(t)
    t += timedelta(hours=6)
print(f"  {Y}[3/4]{RS} {len(init_times)} cycles: {START_DATE} to {END_DATE}", flush=True)

# --- Build the GraphCast model function and compile it with JAX ---
print(f"  {Y}[4/4]{RS} Setting up model (first cycle compiles ~2min)...", flush=True)

def construct_wrapped_graphcast(model_config, task_config):
    """Wrap the bare GraphCast core exactly as the DeepMind reference does.

    The core operates in NORMALISED space: it expects normalised inputs and emits
    normalised residuals. Applying it directly returns meaningless values (we saw
    precipitation of -3000 mm). InputsAndResiduals restores physical units using
    the three stats files loaded above, which the earlier draft of this script
    loaded but never used.
    """
    predictor = graphcast.GraphCast(model_config, task_config)
    predictor = casting.Bfloat16Cast(predictor)
    predictor = normalization.InputsAndResiduals(
        predictor,
        diffs_stddev_by_level=diffs_stddev,
        mean_by_level=mean_by_level,
        stddev_by_level=stddev)
    predictor = autoregressive.Predictor(predictor, gradient_checkpointing=True)
    return predictor

@hk.transform_with_state
def run_forward(model_config, task_config, inputs, targets_template, forcings):
    predictor = construct_wrapped_graphcast(model_config, task_config)
    return predictor(inputs, targets_template=targets_template, forcings=forcings)

# Helpers that fill in configs, parameters and state, so the compiled function only needs data
def with_configs(fn): return lambda **kw: fn(model_config=model_config, task_config=task_config, **kw)
def with_params(fn):  return lambda **kw: fn(params=params, state=state, **kw)
def drop_state(fn):   return lambda **kw: fn(**kw)[0]

run_forward_jit = drop_state(with_params(jax.jit(with_configs(run_forward.apply))))
print(f"  {G}[OK]{RS} Model ready - starting cycles", flush=True)

# --- Run the cycles ---
print(f"\n  {'#':>4}  {'Init':<20} {'Valid':<20} {'Time':>7}  Result")
print(f"  {'-'*68}")

results = []
for i, t_zero in enumerate(init_times):
    t_minus6 = t_zero - timedelta(hours=6)
    t_plus6  = t_zero + timedelta(hours=6)
    out_file = OUT_DIR / f"forecast_{t_plus6.strftime('%Y%m%dT%H')}.nc"

    # Skip cycles whose output file already exists
    if out_file.exists():
        results.append(str(out_file)); continue
    t0 = time.time()
    try:
        # GraphCast needs TWO input steps; extract_inputs_targets_forcings
        # consumes the last time as the +6h target slot, so the dataset must
        # carry three times (t-6, t0, t+6). Target values are nulled below.
        times = [np.datetime64(t_minus6), np.datetime64(t_zero), np.datetime64(t_plus6)]

        # Load the three times for the single-level, accumulation and pressure-level data
        sl_i    = sl_raw.sel(time=times).compute()
        accum_i = accum_raw.sel(time=times).compute()
        pl_i    = pl_raw.sel(time=times).compute()


        # Replace missing (NaN) SST and sea-ice values with 0
        sl_i["sea_surface_temperature"] = sl_i["sea_surface_temperature"].fillna(0.0)
        sl_i["sea_ice_cover"]           = sl_i["sea_ice_cover"].fillna(0.0)

        # Merge into one dataset with a batch dimension and a datetime coordinate
        merged = xr.merge([sl_i, accum_i, pl_i], compat="override")
        merged = merged.expand_dims("batch")
        datetimes = np.array([np.datetime64(t_minus6), np.datetime64(t_zero), np.datetime64(t_plus6)])
        merged = merged.assign_coords(datetime=(("batch","time"), datetimes.reshape(1,-1)))

        # Split into inputs, targets and forcings for one +6 h step
        eval_inputs, eval_targets, eval_forcings = data_utils.extract_inputs_targets_forcings(
            merged, target_lead_times=["6h"], **dataclasses.asdict(task_config))

        # Run the model and save only precipitation and 2 m temperature
        predictions = rollout.chunked_prediction(
            run_forward_jit, rng=jax.random.PRNGKey(0),
            inputs=eval_inputs, targets_template=eval_targets * np.nan,
            forcings=eval_forcings, num_steps_per_chunk=1, verbose=False,
        )
        keep = [v for v in ["total_precipitation_6hr", "2m_temperature"] if v in predictions]
        predictions[keep].to_netcdf(out_file)

    except Exception as e:
        import traceback; traceback.print_exc()
        print(f"  {i+1:>4}  {t_zero.strftime('%Y-%m-%dT%H'):<20} {t_plus6.strftime('%Y-%m-%dT%H'):<20} {R}FAILED{RS}")
        continue

    # Print the cycle run time and the maximum 6 h precipitation (mm)
    total_time = time.time() - t0
    precip_max = float(predictions["total_precipitation_6hr"].max()) * 1000
    results.append(str(out_file))
    print(f"  {i+1:>4}  {t_zero.strftime('%Y-%m-%dT%H'):<20} {t_plus6.strftime('%Y-%m-%dT%H'):<20} {total_time:>6.1f}s  {G}max={precip_max:.1f}mm{RS}")

print(f"\n  {G}{B}Done: {len(results)}/{len(init_times)} cycles - {OUT_DIR}{RS}\n")
