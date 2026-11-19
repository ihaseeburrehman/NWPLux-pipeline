#!/usr/bin/env python3
"""AIFS Single 1.0 cycle runner.
Runs one 6-hour forecast step and saves latitude, longitude, tp, 2t to NetCDF.

Usage:
    python3 run_aifs_cycle.py <checkpoint> <input_grib> <output_nc> <date_iso> <valid_time> <init_time>
"""
# Input:  the AIFS Single checkpoint and a GRIB file with the initial conditions
#         for date_iso. valid_time and init_time are only stored as attributes.
# Output: a NetCDF file on the N320 reduced Gaussian grid (one "values" dimension)
#         with latitude, longitude, tp (m) and 2t (K).
# Run:    one call per cycle, see Usage above. It runs on a CUDA GPU in bfloat16
#         ("device" and "precision" in the config below).
# Change: nothing in the file; paths and times are command-line arguments.
import sys, os
import numpy as np
import xarray as xr

# Quiet TensorFlow log messages
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# --- Command-line arguments ---
ckpt_path  = sys.argv[1]
in_grib    = sys.argv[2]
out_nc     = sys.argv[3]
date_str   = sys.argv[4]
valid_time = sys.argv[5]
init_time  = sys.argv[6]

from anemoi.inference.runners.default import DefaultRunner
from anemoi.utils.config import DotDict

# --- anemoi-inference settings: one 6 h step, GRIB input, no file output (saved below) ---
config = DotDict({
    "checkpoint": ckpt_path,
    "date": date_str,
    "lead_time": 6,
    "device": "cuda",
    "precision": "bfloat16",
    "allow_nans": False,
    "verbosity": 0,
    "report_error": False,
    "use_grib_paramid": False,
    "patch_metadata": {},
    "development_hacks": {},
    "output_frequency": None,
    "write_initial_state": False,
    "env": {},
    "description": None,
    "input": {
        "grib": {"path": in_grib}
    },
    "output": {
        "none": {}
    },
})

# --- Create the runner and read the initial state from the GRIB file ---
runner = DefaultRunner(config)
inp = runner.create_input()
input_state = inp.create_input_state(date=date_str)

lats = np.asarray(input_state["latitudes"], dtype=np.float32)
lons = np.asarray(input_state["longitudes"], dtype=np.float32)

# --- Run the 6 h forecast and keep tp and 2t ---
tp_val = None
t2_val = None

for state in runner.run(input_state=input_state, lead_time=6):
    fields = state["fields"]
    if "tp" in fields:
        tp_val = np.asarray(fields["tp"], dtype=np.float32)
    if "2t" in fields:
        t2_val = np.asarray(fields["2t"], dtype=np.float32)

if tp_val is None or t2_val is None:
    raise ValueError(f"Missing tp or 2t in model output! Available: {list(fields.keys())}")

# --- Save the fields to NetCDF ---
ds = xr.Dataset(
    {
        "latitude":  ("values", lats),
        "longitude": ("values", lons),
        "tp":        ("values", tp_val),
        "2t":        ("values", t2_val),
    },
    attrs={
        "valid_time": valid_time,
        "init_time":  init_time,
        "model":      "aifs-single-mse-1.0",
        "grid":       "N320 reduced Gaussian",
    }
)

ds.to_netcdf(out_nc, format="NETCDF4")
print(f"OK: wrote {out_nc} (values={lats.size}, tp_max={float(tp_val.max()):.6f}m, 2t_mean={float(t2_val.mean()):.1f}K)")
