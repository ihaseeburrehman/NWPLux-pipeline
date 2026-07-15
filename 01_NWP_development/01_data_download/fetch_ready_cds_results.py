#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Download the 4 ERA5 PL chunks that are already 'successful' on CDS,
bypassing cdsapi (which would re-poll). Uses the asset URLs directly.

Downloads in parallel; each chunk writes to <out>.partial then renames.
Idempotent: re-running will skip any file already on disk.
"""
import os
import sys
import threading
import time
from datetime import datetime
import requests

MET = "/Users/haseeb.rehman/Documents/gis4wrf/datasets/met"

JOBS = [
    {
        "label": "2018 PL Jun 01-10",
        "url":   "https://object-store.os-api.cci2.ecmwf.int:443/cci2-prod-cache-1/2026-05-30/7a25d1280ef92a3c335719d17284d937.grib",
        "size":  38708387280,
        "out":   f"{MET}/20180510_20180610_ECMWF/pressure_level/2018_june_01_to_10_pressure_level",
    },
    {
        "label": "2016 PL Jul 01-10",
        "url":   "https://object-store.os-api.cci2.ecmwf.int:443/cci2-prod-cache-3/2026-05-30/73cb158356b5030b387d02c3949cd6dc.grib",
        "size":  38856336480,
        "out":   f"{MET}/20160701_20160731_ECMWF/pressure_level/2016_july_01_to_10_pressure_level",
    },
    {
        "label": "2016 PL Jul 11-20",
        "url":   "https://object-store.os-api.cci2.ecmwf.int:443/cci2-prod-cache-2/2026-05-30/cd877a48789256a8fd1f5013d14121c9.grib",
        "size":  38908767600,
        "out":   f"{MET}/20160701_20160731_ECMWF/pressure_level/2016_july_11_to_20_pressure_level",
    },
    {
        "label": "2016 PL Jul 21-31",
        "url":   "https://object-store.os-api.cci2.ecmwf.int:443/cci2-prod-cache-2/2026-05-30/94611c6bf2c49aefd2c18cb9471aab09.grib",
        "size":  42707915856,
        "out":   f"{MET}/20160701_20160731_ECMWF/pressure_level/2016_july_21_to_31_pressure_level",
    },
]

PRINT_LOCK = threading.Lock()
def log(msg):
    with PRINT_LOCK:
        print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def stream_download(job):
    label, url, expected, out = job["label"], job["url"], job["size"], job["out"]
    partial = out + ".partial"

    if os.path.exists(out) and os.path.getsize(out) > 0:
        log(f"{label}: SKIP (already exists, {os.path.getsize(out)/1e9:.2f} GB)")
        return True

    os.makedirs(os.path.dirname(out), exist_ok=True)
    log(f"{label}: starting ({expected/1e9:.2f} GB)")
    t0 = time.time()
    bytes_done = 0
    last_report = t0
    try:
        with requests.get(url, stream=True, timeout=(30, 120)) as r:
            r.raise_for_status()
            with open(partial, "wb") as f:
                for chunk in r.iter_content(chunk_size=8 * 1024 * 1024):  # 8 MB chunks
                    if not chunk:
                        continue
                    f.write(chunk)
                    bytes_done += len(chunk)
                    now = time.time()
                    if now - last_report >= 60:
                        pct = 100 * bytes_done / expected if expected else 0
                        rate = bytes_done / (now - t0) / 1e6  # MB/s
                        log(f"{label}: {bytes_done/1e9:.2f}/{expected/1e9:.2f} GB ({pct:.1f}%) @ {rate:.1f} MB/s")
                        last_report = now
        sz = os.path.getsize(partial)
        if expected and abs(sz - expected) > 1024:
            log(f"{label}: WARN size mismatch got={sz} expected={expected}")
        os.replace(partial, out)
        dt = time.time() - t0
        log(f"{label}: DONE  ({sz/1e9:.2f} GB in {dt/60:.1f} min, avg {sz/dt/1e6:.1f} MB/s)")
        return True
    except Exception as e:
        log(f"{label}: FAIL {e}")
        return False


def main():
    log(f"launching {len(JOBS)} parallel downloads from CDS object-store")
    threads, results = [], {}
    def runner(j):
        results[j["label"]] = stream_download(j)
    for j in JOBS:
        t = threading.Thread(target=runner, args=(j,), name=j["label"])
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    log("--- SUMMARY ---")
    for label, ok in results.items():
        log(f"  [{'OK' if ok else 'FAIL'}] {label}")
    n_ok = sum(1 for ok in results.values() if ok)
    log(f"{n_ok}/{len(JOBS)} succeeded")
    sys.exit(0 if n_ok == len(JOBS) else 1)


if __name__ == "__main__":
    main()
