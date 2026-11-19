"""Full-valley transects: same centres/normals as transects400.json, but the along-line extent covers the whole
flooded floodplain at the peak (Livange, Walferdange were 400 m and missed overbank flow), stopping short of
neighbouring tributaries. Then extract q.n for LISFLOOD-FP 8.4 and HiPIMS (1-GPU or 4-GPU) runs in parallel.
usage: xs_fullvalley.py build | lf <run_dir> | hp <run_dir>"""
# Inputs: build -> CODE/transects400.json; lf/hp -> CODE/transects_fullvalley.json and the run's hourly .asc output
#   (LISFLOOD-FP: results/1hr-NNNN.Qx, .Qy, .wd; HiPIMS: hUx_, hUy_, h_ files in output/ or <gpu>/output/).
# Outputs: build -> CODE/transects_fullvalley.json; lf/hp -> <run_dir>/segflux_fv.npz (q.n and depth per segment and step).
# Runs in parallel with SLURM_CPUS_PER_TASK processes. Settings to change: the sys.path entry and CODE (ECMWF HPC paths);
# EXT sets the along-line extent (m, from-to relative to the transect centre) of each station.
import sys, os, glob, re, json, numpy as np, multiprocessing as mp
sys.path.insert(0, "/ec/res4/scratch/lux0804/radar_scale_2026/code")
import seg_extract as se
CODE = "/ec/res4/scratch/lux0804/radar_scale_2026/code/"
# 10 m grid: west edge, top edge, cell size, rows, columns
X0, YTOP, CS, NR, NC = 59799.3, 49254.0 + 4362 * 10.0, 10.0, 4362, 2440
# Along-line extent (m) of each full-valley transect
EXT = {"Livange": (-700, 400), "Walferdange": (-400, 800), "Steinsel": (-400, 300),
       "Pfaffenthal": (-200, 200), "Hesperange": (-200, 200)}

def build():
    T = se.load(CODE + "transects400.json"); N = {}
    # Sample each line every 5 cm and split it into segments, one per 10 m cell crossed
    for n, v in T.items():
        a, b = EXT[n]; ds = 0.05; s = np.arange(a, b, ds) + ds / 2
        # Points along the transect, perpendicular to the flow normal (ux, uy)
        px, py = v["x"] - v["uy"] * s, v["y"] + v["ux"] * s
        # Grid row/column of each point; a new segment starts where the cell changes
        r = np.floor((YTOP - py) / CS).astype(int); c = np.floor((px - X0) / CS).astype(int)
        cut = np.flatnonzero((np.diff(r) != 0) | (np.diff(c) != 0)) + 1
        segs = [[int(r[i]), int(c[i]), float(s[i] - ds / 2), float(s[j - 1] + ds / 2)]
                for i, j in zip(np.r_[0, cut], np.r_[cut, len(s)])]
        N[n] = dict(v, segs=segs)
    # Save the segments; print segment count and total length per station
    json.dump(N, open(CODE + "transects_fullvalley.json", "w"))
    print({n: (len(v["segs"]), round(sum(q[3] - q[2] for q in v["segs"]))) for n, v in N.items()})

# Load the full-valley transects once they have been built
T = se.load(CODE + "transects_fullvalley.json") if os.path.exists(CODE + "transects_fullvalley.json") else None

# --- Output times and a row reader for a LISFLOOD-FP (lf) or HiPIMS (hp) run ---
def readers(run, kind):
    if kind == "lf":
        # LISFLOOD-FP: hourly 1hr-NNNN.Qx/.Qy/.wd files in results/
        R = run + "/results/"
        ts = sorted(int(re.search(r"-(\d+)\.Qx", p).group(1)) for p in glob.glob(R + "1hr-*.Qx"))
        f = lambda t, v: R + f"1hr-{t:04d}." + {"x": "Qx", "y": "Qy", "h": "wd"}[v]
        return ts, (lambda t, v, need: se.read_rows(f(t, v), need))
    # HiPIMS: one output folder per GPU subdomain (or one folder); find each subdomain's row offset in the full grid
    MG = sorted(glob.glob(run + "/[0-9]/output/")) or [run + "/output/"]
    name = {"x": "hUx", "y": "hUy", "h": "h"}
    DOM = []
    for d in MG:
        with open(glob.glob(d + "h_*.asc")[0]) as fh: h = {k: float(x) for k, x in (fh.readline().split() for _ in range(6))}
        nr = int(h["nrows"]); off = int(round((YTOP - (h["yllcorner"] + nr * CS)) / CS))
        DOM.append((d, off, 0 if off == 0 else 1, nr if off + nr == NR else nr - 1))   # skip halo rows
    # Read the needed full-grid rows from the subdomain files that hold them
    def rd(t, v, need):
        out = {}
        for d, off, lo, hi in DOM:
            loc = [g - off for g in need if lo <= g - off < hi]
            if loc: out.update({l + off: x for l, x in se.read_rows(f"{d}{name[v]}_{t}.asc", loc).items()})
        return out
    # Output times in s; keep hourly times after t = 0
    ts = sorted(int(re.search(r"hUx_(\d+)\.asc", p).group(1)) for p in glob.glob(DOM[0][0] + "hUx_*.asc"))
    return [t for t in ts if t % 3600 == 0 and t > 0], rd

# --- Flux q.n and depth on every segment at one output time ---
def one(args):
    t, = args
    QX, QY, WD = (RD(t, v, NEED) for v in "xyh")
    return se.seg_flux(T, QX, QY, WD)

# --- Main: build the transects, or extract one run in parallel and save segflux_fv.npz ---
if __name__ == "__main__":
    if sys.argv[1] == "build": build(); sys.exit()
    kind, run = sys.argv[1], sys.argv[2].rstrip("/")
    NEED = se.rows_needed(T); TS, RD = readers(run, kind)
    with mp.Pool(int(os.environ.get("SLURM_CPUS_PER_TASK", 1))) as pool: RES = pool.map(one, [(t,) for t in TS])
    # Save the steps (HiPIMS converted from s to hours), segment positions and lengths, and q.n and depth per step
    save = {"steps": np.array([t if kind == "lf" else t // 3600 for t in TS])}
    for n in T:
        save[f"{n}_t"] = RES[-1][n]["t"]; save[f"{n}_L"] = RES[-1][n]["L"]
        save[f"{n}_qn"] = np.array([r[n]["qn"] for r in RES]); save[f"{n}_wd"] = np.array([r[n]["wd"] for r in RES])
    np.savez_compressed(run + "/segflux_fv.npz", **save)
    print(run, len(TS), "steps")
