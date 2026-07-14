#!/usr/bin/env python3
"""
Parallel pre-queue of the 4 remaining ERA5 pressure-level chunks.

Designed to run *alongside* the sequential download script. Each chunk is
submitted in its own thread (CDS processes them concurrently server-side),
saved to <out>.partial, and atomically renamed to <out> only on success.

The sequential script's skip-if-exists check therefore only ever sees
fully-downloaded files; partial files don't cause it to skip.

If the final file already exists (e.g. the sequential script finished it
first), this script skips that chunk.
"""

import os
import sys
import threading
import time
from datetime import datetime

import cdsapi

MET_ROOT = "/Users/haseeb.rehman/Documents/gis4wrf/datasets/met"

PL_VARIABLES = [
    "temperature", "u_component_of_wind", "v_component_of_wind",
    "vertical_velocity", "specific_humidity", "relative_humidity",
    "geopotential", "divergence", "vorticity", "potential_vorticity",
    "fraction_of_cloud_cover", "specific_cloud_ice_water_content",
    "specific_cloud_liquid_water_content", "specific_rain_water_content",
    "specific_snow_water_content", "ozone_mass_mixing_ratio",
]

PL_LEVELS = [
    "7", "10", "20", "30", "50", "70",
    "100", "125", "150", "175", "200", "225", "250", "300", "350", "400",
    "450", "500", "550", "600", "650", "700", "750", "775", "800", "825",
    "850", "875", "900", "925", "950", "975", "1000",
]

TIMES = ["00:00", "06:00", "12:00", "18:00"]
GRID = [0.25, 0.25]


# Chunks to pre-queue. Chunks 1 & 2 of 2018 are already in flight via the
# sequential script, so they're excluded.
CHUNKS = [
    {
        "label": "2018 PL Jun 01-10",
        "date":  "2018-06-01/2018-06-10",
        "out":   f"{MET_ROOT}/20180510_20180610_ECMWF/pressure_level/2018_june_01_to_10_pressure_level",
    },
    {
        "label": "2016 PL Jul 01-10",
        "date":  "2016-07-01/2016-07-10",
        "out":   f"{MET_ROOT}/20160701_20160731_ECMWF/pressure_level/2016_july_01_to_10_pressure_level",
    },
    {
        "label": "2016 PL Jul 11-20",
        "date":  "2016-07-11/2016-07-20",
        "out":   f"{MET_ROOT}/20160701_20160731_ECMWF/pressure_level/2016_july_11_to_20_pressure_level",
    },
    {
        "label": "2016 PL Jul 21-31",
        "date":  "2016-07-21/2016-07-31",
        "out":   f"{MET_ROOT}/20160701_20160731_ECMWF/pressure_level/2016_july_21_to_31_pressure_level",
    },
]

PRINT_LOCK = threading.Lock()
def log(msg):
    with PRINT_LOCK:
        print(f"[{datetime.now():%H:%M:%S}] {msg}", flush=True)


def fetch(chunk):
    label = chunk["label"]
    out = chunk["out"]
    partial = out + ".partial"

    if os.path.exists(out) and os.path.getsize(out) > 0:
        log(f"{label}: final file exists, skip")
        return True

    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Each thread should use its own client instance
    client = cdsapi.Client(quiet=True)
    try:
        log(f"{label}: submitting CDS request")
        client.retrieve(
            "reanalysis-era5-pressure-levels",
            {
                "product_type": "reanalysis",
                "format": "grib",
                "variable": PL_VARIABLES,
                "pressure_level": PL_LEVELS,
                "date": chunk["date"],
                "time": TIMES,
                "grid": GRID,
            },
            partial,
        )
        # Recheck — sequential script may have produced the final file in the meantime
        if os.path.exists(out) and os.path.getsize(out) > 0:
            log(f"{label}: sequential already produced final, discarding parallel copy")
            try:
                os.remove(partial)
            except OSError:
                pass
            return True
        os.replace(partial, out)
        sz = os.path.getsize(out) / 1e9
        log(f"{label}: DONE -> {out} ({sz:.2f} GB)")
        return True
    except Exception as e:
        log(f"{label}: FAIL {e}")
        return False


def main():
    log(f"launching {len(CHUNKS)} parallel CDS requests")
    threads = []
    results = {}
    def runner(c):
        results[c["label"]] = fetch(c)
    for c in CHUNKS:
        t = threading.Thread(target=runner, args=(c,), name=c["label"])
        t.start()
        threads.append(t)
        time.sleep(2)  # small stagger to avoid burst
    for t in threads:
        t.join()
    log("--- SUMMARY ---")
    n_ok = sum(1 for ok in results.values() if ok)
    for label, ok in results.items():
        log(f"  [{'OK' if ok else 'FAIL'}] {label}")
    log(f"{n_ok}/{len(CHUNKS)} succeeded")
    sys.exit(0 if n_ok == len(CHUNKS) else 1)


if __name__ == "__main__":
    main()
