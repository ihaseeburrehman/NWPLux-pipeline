"""LISFLOOD-FP 8.4 inputs identical to the HiPIMS cases: 50 m block-mean forecast rain on the 10 m grid,
and Green-Ampt grids (Ks mm/h, psi mm, porosity, theta_init) from the same soil file."""
# Usage: python lf84_inputs.py
# Inputs: the 10 m DEM .asc (header and active cells), the HiPIMS soil file green_ampt_10m.npz, and the rain NetCDFs in src below.
# Outputs in O: ga_ks_mmh, ga_psi_mm, ga_porosity, ga_theta_init .asc and rain_<case>_b50.nc.
# Settings to change: W, H and O (ECMWF HPC scratch paths) and the case list src.
import numpy as np, netCDF4, os
# --- Paths: work folder W, HiPIMS folder H, output folder O ---
W = "/ec/res4/scratch/lux0804/radar_scale_2026"; H = "/ec/res4/scratch/lux0804/hipims"; O = "/ec/res4/scratch/lux0804/lf84_cases/inputs"
os.makedirs(O, exist_ok=True)
# DEM header: the second read (6 lines) is the one used
hdr = "".join(open(W + "/inputs/Alzette_sub_basin_10m_bridge_burn.asc").readline() for _ in range(1))
with open(W + "/inputs/Alzette_sub_basin_10m_bridge_burn.asc") as f: hdr = "".join(f.readline() for _ in range(6))
NR, NC = 4362, 2440
dem_nd = None
# --- Green-Ampt grids from the HiPIMS soil file, in LISFLOOD-FP units (Ks mm/h, psi mm) ---
ga = np.load(H + "/soil/green_ampt_10m.npz")
for name, arr, fmt in [("ga_ks_mmh", ga["Ks"] * 3.6e6, "%.5g"), ("ga_psi_mm", ga["psi"] * 1000, "%.5g"),
                       ("ga_porosity", ga["porosity"], "%.4f"), ("ga_theta_init", ga["theta_i"], "%.4f")]:
    np.savetxt(O + f"/{name}.asc", arr, fmt=fmt, header=hdr.rstrip("\n"), comments="")
    print(name, "written, mean %.4g" % arr.mean(), flush=True)
act = np.loadtxt  # placeholder to keep namespace simple
# --- 50 m blocks: index of the 5 x 5 block of 10 m cells that each cell belongs to ---
B = 5; bi, bj = np.arange(NR) // B, np.arange(NC) // B
blk = bi[:, None] * (NC // B + 1) + bj[None, :]
# Active cells = DEM cells with data; number of active cells per block
import pandas as pd
dem = pd.read_csv(W + "/inputs/Alzette_sub_basin_10m_bridge_burn.asc", skiprows=6, sep=r"\s+", header=None, dtype=np.float32, engine="c").values
act = dem > -9000
u, inv = np.unique(blk[act], return_inverse=True); cnt = np.bincount(inv)
# --- Rain files to convert (case -> path under W) ---
src = {"F_graphcast": "inputs_18utc/rain_graphcast_v2_96h.nc", "F_aifs": "inputs_18utc/rain_aifs_96h.nc",
       "VM_graphcast": "forcing/rain_VM_graphcast.nc", "VM_aifs": "forcing/rain_VM_aifs.nc"}
for case, f in src.items():
    # Copy dimensions, coordinates and attributes from the source file
    a = netCDF4.Dataset(W + "/" + f); out = netCDF4.Dataset(O + f"/rain_{case}_b50.nc", "w", format="NETCDF4")
    for d in a.dimensions: out.createDimension(d, len(a.dimensions[d]))
    for vn in ("time", "x", "y"):
        v = out.createVariable(vn, a[vn].dtype, a[vn].dimensions); v.setncatts({k: a[vn].getncattr(k) for k in a[vn].ncattrs()}); v[:] = a[vn][:]
    r = out.createVariable("rainfall_depth", "f4", ("time", "y", "x"), zlib=True, complevel=1, chunksizes=(1, NR, NC))
    r.setncatts({k: a["rainfall_depth"].getncattr(k) for k in a["rainfall_depth"].ncattrs() if k != "_FillValue"})
    # Replace each rain layer by its 50 m block mean over active cells (other cells 0); sum the basin mean
    tot = 0.0
    for i in range(a["rainfall_depth"].shape[0]):
        x = np.asarray(a["rainfall_depth"][i], dtype=np.float64)
        m = np.bincount(inv, x[act]) / cnt; g = np.zeros((NR, NC), np.float32); g[act] = m[inv]
        r[i] = g; tot += m[inv].mean()
    out.close(); print(case, "basin mean %.2f mm" % tot, flush=True)
