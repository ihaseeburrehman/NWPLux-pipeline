"""Green-Ampt v3b: Ks and saturated water content from EU-SoilHydroGrids 250 m (Toth et al., 2017), 0-30 cm
(sl1-sl4 = 0, 5, 15, 30 cm; trapezoid weights). Ks: harmonic mean (vertical flow); THS reduced by SoilGrids coarse
fragments. Suction head from v3a (Saxton and Rawls 2006). Impervious, initially wet cells and v2 wet mask as in v2."""
# Usage: python soil_v3b.py, run from the folder that holds soil/.
# Inputs: soil/esh_KS_M_sl1-4_alz.tif, soil/esh_THS_M_sl1-4_alz.tif, soil/sg_cfvo_*.tif, soil/green_ampt_10m_v2.npz,
#   soil/green_ampt_10m_v3a.npz, the basin mask and the 10 m DEM (header only).
# Outputs: soil/green_ampt_10m_v3b.npz and ga_ks_mmh, ga_psi_mm, ga_porosity, ga_theta_init .asc grids in O.
# Settings to change: S, O and the basin mask and DEM paths below (ECMWF HPC scratch paths).
import numpy as np, os, rasterio
from rasterio.warp import reproject, Resampling
from affine import Affine
# --- Soil folder S and output folder O ---
S = "soil/"; O = "/ec/res4/scratch/lux0804/lf84_cases/inputs_v3b"; os.makedirs(O, exist_ok=True)
# 10 m EPSG:2169 target grid (rows, columns, lower-left corner, cell size) and its affine transform
NR, NC, X0, Y0, C = 4362, 2440, 59799.282445142424, 49254.0, 10.0
tf = Affine(C, 0, X0, 0, -C, Y0 + NR * C)
W = np.array([2.5, 7.5, 12.5, 7.5])                                     # cm represented by 0, 5, 15, 30 cm points
# --- Reproject a 250 m soil raster to the 10 m grid (nearest); nodata and negatives -> NaN, then scale ---
def to10(path, scale, nod):
    with rasterio.open(path) as r:
        a = r.read(1).astype("float32"); a[(a == nod) | (a < 0)] = np.nan; a *= scale
        o = np.full((NR, NC), np.nan, "float32")
        reproject(a, o, src_transform=r.transform, src_crs=r.crs, dst_transform=tf, dst_crs="EPSG:2169",
                  resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan); return o
# --- Ks (mm/h) and saturated water content at the four depths; coarse fragments averaged over 0-30 cm ---
KS = [to10(S + f"esh_KS_M_sl{i}_alz.tif", 0.01 * 10 / 24, -32767) for i in (1, 2, 3, 4)]   # cm/d x100 -> mm/h
TH = [to10(S + f"esh_THS_M_sl{i}_alz.tif", 0.01, 255) for i in (1, 2, 3, 4)]
CF = np.nanmean([to10(S + f"sg_cfvo_{d}.tif", 0.001, -32768) for d in ("0-5cm", "5-15cm", "15-30cm")], axis=0)
# Depth-weighted harmonic mean of Ks; weighted mean THS times (1 - coarse fragments) = porosity
Ks = W.sum() / sum(w / k for w, k in zip(W, KS)); por = sum(w * t for w, t in zip(W, TH)) / W.sum() * (1 - np.nan_to_num(CF))
# Load the v2 and v3a grids and the basin mask; active = cells with v2 Ks > 0 and valid v3b values
ga = dict(np.load(S + "green_ampt_10m_v2.npz")); v3a = np.load(S + "green_ampt_10m_v3a.npz")
b = np.load("/ec/res4/scratch/lux0804/radar_scale_2026/basin_mask.npy").astype(bool)
act = (ga["Ks"] > 0) & np.isfinite(Ks) & np.isfinite(por)
# Report the active share, Ks and porosity percentiles, then mean Ks per soil class (v2 vs v3b)
print("active %.1f%% of basin; Ks p10/50/90 %s mm/h; porosity %s" % (100*act[b].mean(), np.percentile(Ks[act & b], [10, 50, 90]).round(3), np.percentile(por[act & b], [10, 50, 90]).round(3)))
for c in np.unique(ga["cls"][act & b]):
    m = act & b & (ga["cls"] == c); print("   class %2d  %4.1f%%  Ks v2 %6.2f  v3b %6.2f mm/h" % (c, 100*m.sum()/b.sum(), ga["Ks"][m].mean()*3.6e6, Ks[m].mean()))
# --- At active cells: replace Ks (m/s), porosity and suction head; cap the initial water content at porosity ---
ga["Ks"][act] = Ks[act]/3.6e6; ga["porosity"][act] = por[act]; ga["psi"][act] = v3a["psi"][act]
ga["theta_i"][act] = np.minimum(ga["theta_i"][act], ga["porosity"][act])
# Recompute the moisture deficit dtheta (0 where Ks = 0)
ga["dtheta"] = np.where(ga["Ks"] > 0, np.clip(ga["porosity"] - ga["theta_i"], 0, None), 0).astype("float32")
print("basin-mean Ks v3b %.2f mm/h; mean dtheta %.3f" % (ga["Ks"][b].mean()*3.6e6, ga["dtheta"][b].mean()))
# --- Save the v3b npz and write the four .asc grids with the DEM header for LISFLOOD-FP ---
np.savez_compressed(S + "green_ampt_10m_v3b.npz", **ga)
with open("/ec/res4/scratch/lux0804/radar_scale_2026/inputs/Alzette_sub_basin_10m_bridge_burn.asc") as f: hdr = "".join(f.readline() for _ in range(6))
for name, arr, fmt in [("ga_ks_mmh", ga["Ks"]*3.6e6, "%.5g"), ("ga_psi_mm", ga["psi"]*1000, "%.5g"),
                       ("ga_porosity", ga["porosity"], "%.4f"), ("ga_theta_init", ga["theta_i"], "%.4f")]:
    np.savetxt(O + f"/{name}.asc", arr, fmt=fmt, header=hdr.rstrip("\n"), comments="")
print("written", O)
