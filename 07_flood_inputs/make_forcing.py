#!/usr/bin/env python3
"""Build radar-derived and volume-matched LISFLOOD-FP dynamicrainfile forcings.

Grid, units and timestamp convention are identical to the six published forcings:
10 m EPSG:2169 grid of the DEM, variables time,x,y,rainfall_depth (mm accumulated over
[t, t+dt)), time in hours from 2021-07-13 18:00 UTC, closing zero layer at 96 h.

Radar: RMI RADCLIM (QPE_EDK), 1 km, EPSG:3812. The hourly gauge-merged accumulation is
the volume reference; 5-min fields only distribute each pixel-hour's volume in time
(NaN in the 5-min product = no echo = 0). Every radar case therefore carries the same
hourly water at every 1 km pixel (temporal cases) or the same basin-mask water in every
interval (spatial cases, rescaled).
"""
# Usage: python make_forcing.py <work dir> <case>
#   case: R_1km_5min, R_1km_1h, R_1km_6h, R_025_6h, R_025_1h, R_12km_6h, R_uniform_6h, or VM_<model> (see the VM_ table below)
# Inputs in <work dir>: basin_mask.npy, radclim_crop.npz (from radclim_crop.py), and inputs_18utc/rain_*.nc for the VM_ cases.
# Outputs: <work dir>/forcing/rain_<case>.nc and rain_<case>.json (basin-mean series and total). The forcing/ folder must exist.
# Settings: the 10 m grid (NC, NR, XLL, YLL, C) must match the DEM; the 96 h window (1152 5 min steps) is fixed in the code.
import sys, json, numpy as np
from pyproj import Transformer
from scipy.interpolate import griddata

W = sys.argv[1]                         # work dir
CASE = sys.argv[2]
# --- 10 m EPSG:2169 target grid (cell centres, y descending) and the basin mask ---
NC, NR, XLL, YLL, C = 2440, 4362, 59799.282445142424, 49254.0, 10.0
x = XLL + (np.arange(NC) + 0.5) * C
y = YLL + NR * C - (np.arange(NR) + 0.5) * C           # descending
basin = np.load(f"{W}/basin_mask.npy").astype(bool)
assert basin.shape == (NR, NC), basin.shape
# Projection string written to the output attributes
PROJ4_2169 = ("+proj=tmerc +lat_0=49.8333333333333 +lon_0=6.16666666666667 "
              "+k=1 +x_0=80000 +y_0=100000 +ellps=intl "
              "+towgs84=-189.681,18.3463,-42.7695,-0.33746,-3.09264,2.53861,0.4598 +units=m +no_defs")

# --- Load the cropped radar; NaN (no echo) set to 0 ---
d = np.load(f"{W}/radclim_crop.npz")
r5 = np.nan_to_num(d["r5"], nan=0.0).astype(np.float64)          # (1152, ny, nx)
h1 = np.nan_to_num(d["r1h"], nan=0.0).astype(np.float64)         # (96, ny, nx)
rx, ry = d["x3812"], d["y3812"]
ny, nx = h1.shape[1:]

# 5-min fields rescaled so each pixel-hour sums to the gauge-merged hourly value
r5h = r5.reshape(96, 12, ny, nx); s = r5h.sum(axis=1)
w = np.where(s[:, None] > 0, r5h / np.where(s > 0, s, 1)[:, None], 1.0 / 12)
r5c = (w * h1[:, None]).reshape(1152, ny, nx)

# map every 10 m cell centre to its 1 km radar pixel (block representation, no interpolation)
X, Y = np.meshgrid(x, y)
t23 = Transformer.from_crs("EPSG:2169", "EPSG:3812", always_xy=True)
px, py = t23.transform(X.ravel(), Y.ravel())
ci = np.floor((px - (rx[0] - 500)) / 1000).astype(int)
ri = np.floor(((ry[0] + 500) - py) / 1000).astype(int)
assert ci.min() >= 0 and ri.min() >= 0 and ci.max() < nx and ri.max() < ny
flat = (ri * nx + ci).reshape(NR, NC)

# --- Helpers: 1 km field to the 10 m grid via the pixel index, and the basin-mask mean ---
def to10(field): return field.ravel()[flat].astype(np.float32)

def bmean(g): return float(g[basin].mean())

def coarse_ai(field_1km, kind):
    """Emulate the AI-forcing pipeline: area means on a coarse grid, then linear
    interpolation of the coarse-cell centres to the 10 m grid."""
    # 1 km pixel-centre coordinates (EPSG:3812)
    RXg, RYg = np.meshgrid(rx, ry)
    if kind == "025":
        # 0.25 deg case: group the 1 km pixels by nearest 0.25 deg lat/lon point and average them
        tl = Transformer.from_crs("EPSG:3812", "EPSG:4326", always_xy=True)
        lon, lat = tl.transform(RXg, RYg)
        ki, kj = np.round(lat / 0.25).astype(int), np.round(lon / 0.25).astype(int)
        keys = ki * 100000 + kj
        u, inv = np.unique(keys.ravel(), return_inverse=True)
        cnt = np.bincount(inv); val = np.bincount(inv, field_1km.ravel()) / cnt
        ok = cnt >= 300                                    # only fully-covered cells
        clat, clon = (u // 100000) * 0.25, (u % 100000) * 0.25
        tc = Transformer.from_crs("EPSG:4326", "EPSG:2169", always_xy=True)
        cx, cy = tc.transform(clon[ok], clat[ok]); cv = val[ok]
    elif kind == "12km":
        # 12 km case: average 12 x 12 blocks of 1 km pixels; block centre = mean pixel position
        bi, bj = (np.arange(ny) // 12), (np.arange(nx) // 12)
        BI, BJ = np.meshgrid(bi, bj, indexing="ij")
        keys = (BI * 1000 + BJ).ravel()
        u, inv = np.unique(keys, return_inverse=True)
        cnt = np.bincount(inv); val = np.bincount(inv, field_1km.ravel()) / cnt
        sx = np.bincount(inv, RXg.ravel()) / cnt; sy = np.bincount(inv, RYg.ravel()) / cnt
        ok = cnt == 144
        tc = Transformer.from_crs("EPSG:3812", "EPSG:2169", always_xy=True)
        cx, cy = tc.transform(sx[ok], sy[ok]); cv = val[ok]
    # Linear interpolation of the coarse-cell values to the 10 m grid, 0 outside, no negatives
    g = griddata((cx, cy), cv, (X, Y), method="linear", fill_value=0.0)
    return np.clip(g, 0, None).astype(np.float32)

def aggregate(r, k):     # sum consecutive intervals
    return r.reshape(-1, k, ny, nx).sum(axis=1)

# --- Build the frames of the chosen case; dt_h is the interval length in hours ---
frames, dt_h, note = [], None, ""
if CASE == "R_1km_5min":
    # Rescaled 5 min radar on 1 km blocks
    dt_h = 5 / 60; frames = (to10(f) for f in r5c)
elif CASE == "R_1km_1h":
    # Hourly gauge-merged radar on 1 km blocks
    dt_h = 1; frames = (to10(f) for f in h1)
elif CASE == "R_1km_6h":
    # Hourly radar summed to 6 h
    dt_h = 6; frames = (to10(f) for f in aggregate(h1, 6))
elif CASE in ("R_025_6h", "R_025_1h", "R_12km_6h"):
    # Radar smoothed like the 0.25 deg AI or 12 km forcing, then rescaled to the 10 m basin-mask mean of each interval
    kind = "12km" if CASE.startswith("R_12km") else "025"
    src = aggregate(h1, 6) if CASE.endswith("6h") else h1
    dt_h = 6 if CASE.endswith("6h") else 1
    for f in src:
        fine = to10(f); g = coarse_ai(f, kind)
        bt, bg = bmean(fine), bmean(g)
        frames.append(g * (bt / bg) if bg > 0 else g + bt)   # conserve basin water per interval
    note = f"coarse={kind}; linear interpolation of coarse-cell area means; basin-mask volume rescaled per interval"
elif CASE == "R_uniform_6h":
    # One basin-mean value spread over the whole grid in each 6 h interval
    dt_h = 6
    frames = [np.full((NR, NC), bmean(to10(f)), np.float32) for f in aggregate(h1, 6)]
    note = "spatially uniform field equal to the basin-mask mean in each interval"
elif CASE.startswith("VM_"):
    # Volume matched: a forecast rain file scaled by one factor so its basin total equals the radar total
    src = {"VM_graphcast": "rain_graphcast_v2_96h.nc", "VM_aifs": "rain_aifs_96h.nc",
           "VM_wrf1p3": "rain_wrf1p3_afterda_96h.nc", "VM_fuxi": "rain_fuxi_96h.nc", "VM_fuxi2": "rain_fuxi_noflip_96h.nc",
           "VM_wrf12": "rain_wrf12_afterda_96h.nc", "VM_wrf12noda": "rain_wrf12_beforeda_96h.nc"}[CASE]
    import netCDF4 as _nc
    with _nc.Dataset(f"{W}/inputs_18utc/{src}") as _d:
        rf = _d["rainfall_depth"][:].filled(0.0).astype(np.float32)
    # Event factor k = radar basin total / forecast basin total (closing zero layer of the forecast left out)
    target = sum(bmean(to10(f)) for f in h1)
    k = target / sum(float(f[basin].mean()) for f in rf[:-1])
    dt_h = 6; frames = [(f * k).astype(np.float32) for f in rf[:-1]]
    note = f"{src} scaled by a single event factor k={k:.4f} so its 96 h basin-mask total equals the radar total {target:.2f} mm"
else:
    raise SystemExit(f"unknown case {CASE}")

# --- Write the NetCDF: dimensions, coordinate variables and compressed rain variable ---
import netCDF4, itertools
out = f"{W}/forcing/rain_{CASE}.nc"
nc = netCDF4.Dataset(out, "w", format="NETCDF4")
nc.createDimension("time", int(round(96 / dt_h)) + 1); nc.createDimension("x", NC); nc.createDimension("y", NR)
vt = nc.createVariable("time", "f8", ("time",)); vt.units = "hour"; vt.long_name = "time"; vt.axis = "T"
vx = nc.createVariable("x", "f8", ("x",)); vx.units = "m"; vx.long_name = "x"; vx.axis = "X"; vx.spatial_ref = "EPSG:2169"
vy = nc.createVariable("y", "f8", ("y",)); vy.units = "m"; vy.long_name = "y"; vy.axis = "Y"; vy.spatial_ref = "EPSG:2169"
vr = nc.createVariable("rainfall_depth", "f4", ("time", "y", "x"), zlib=True, complevel=1, chunksizes=(1, NR, NC))
vr.units = "mm"; vr.long_name = "rainfall_depth"
vx[:] = x; vy[:] = y
# Write each frame plus a closing zero layer; keep the basin-mean depth of each interval
series = []
for i, f in enumerate(itertools.chain(frames, [np.zeros((NR, NC), np.float32)])):
    vr[i] = f; vt[i] = i * dt_h; series.append(bmean(f))
series = series[:-1]; tot = float(sum(series))
# Global attributes: grid, case, timestamp convention, window and basin total
nc.setncatts({"crs": "EPSG:2169", "spatial_ref": PROJ4_2169, "source_case": CASE,
              "time_stamp_convention": "interval_start",
              "window_start_utc": "2021-07-13T18:00:00Z", "window_end_utc": "2021-07-17T18:00:00Z",
              "note": note or "radar 1 km block mapping", "basin_total_mm": tot})
nc.close()
# --- Write the JSON summary and print a short report ---
n_frames = len(series) + 1
json.dump({"case": CASE, "dt_h": dt_h, "n": n_frames, "basin_total_mm": tot,
           "basin_series_mm": series, "note": note}, open(f"{W}/forcing/rain_{CASE}.json", "w"))
print(CASE, "dt_h", dt_h, "frames", n_frames, "basin total mm", round(tot, 3),
      "max interval", round(max(series), 2), note)
