"""Score every run (4 model sets x 9 rainfall cases) at the four discharge gauges.
Discharge = integral of q.n over the station section (width "full" in the CSVs, primary): the whole wetted valley at Pfaffenthal,
Hesperange and Steinsel, but 400 m centred on the gauge at Livange, where a separate ditch 350 m south east of the station carries
bypass flow that the gauge cannot record. Sensitivities: "valley" = the whole transect at every gauge, "surveyed" = the surveyed channel width.
Observations: native AGE records, clock UTC+1 all year, shifted to UTC (clock 'utc1' in obs_hourly.csv).
Writes scores.csv and hydrographs.csv (hourly Q per run, gauge and width)."""
# Usage: python score_all.py
# Inputs: transects_fullvalley.json, segflux_fv.npz of every run (from xs_fullvalley.py), hipims/obs_hourly.csv.
# Outputs in S/hipims/: scores.csv, hydrographs.csv and obs_utc.csv (the observations used).
# Settings to change: S (ECMWF HPC scratch root) and the run-folder patterns in SET.
import numpy as np, csv, json, os
S = "/ec/res4/scratch/lux0804/"
T = json.load(open(S + "radar_scale_2026/code/transects_fullvalley.json"))
# Gauges and rainfall cases
G = ["Pfaffenthal", "Steinsel", "Hesperange", "Livange"]
C = ["R_1km_5min", "R_1km_6h", "F_graphcast", "F_aifs", "F_fuxi", "F_wrf12noda", "F_wrf12", "VM_graphcast", "VM_aifs", "VM_fuxi", "VM_wrf12noda", "VM_wrf12", "F_wrf1p3", "VM_wrf1p3"]   # WRF 12 km dropped (minimal design)
# Run sets: (model, infiltration, path pattern of segflux_fv.npz)
SET = [("LISFLOOD-FP", "none", S + "radar_scale_2026/runs/L84_{c}_noinf_dp_1g/segflux_fv.npz"),
       ("LISFLOOD-FP", "GA", S + "radar_scale_2026/runs/L84_{c}_ga3b_dp/segflux_fv.npz"),
       ("HiPIMS", "none", S + "hipims/runs/{c}_mg4/segflux_fv.npz"),
       ("HiPIMS", "GA", S + "hipims/runs/{c}_inf_mg4/segflux_fv.npz")]
# Ks sensitivity (radar and GraphCast only): Ks x0.5 and x2
SET += [(m, f"GA_{k}", p) for k in ("ks05", "ks2") for m, p in
        (("LISFLOOD-FP", S + f"radar_scale_2026/runs/L84_{{c}}_ga3b_{k}_dp/segflux_fv.npz"), ("HiPIMS", S + f"hipims/runs/{{c}}_inf_{k}_mg4/segflux_fv.npz"))]
# ERA5-Land wet start (radar and the three ML forecasts); runs made with the final 8.4 build (dpn)
SET += [("LISFLOOD-FP", "GA_sm", S + "radar_scale_2026/runs/L84_{c}_ga3b_sm_dpn/segflux_fv.npz"), ("HiPIMS", "GA_sm", S + "hipims/runs/{c}_inf_sm_mg4/segflux_fv.npz")]
# --- Observed hourly discharge per gauge: only rows with clock 'utc1' (AGE UTC+1 records shifted to UTC) ---
obs = {}
for r in csv.DictReader(open(S + "hipims/obs_hourly.csv")):
    if r["clock"] == "utc1": obs.setdefault(r["gauge"], {})[int(r["h"])] = float(r["Q"])
# --- Discharge for a section width W centred on the gauge (None = whole transect):
# sum of q.n times the overlap of each segment with [-W/2, W/2] ---
def qwidth(z, g, W):
    t, L, qn = z[g + "_t"], z[g + "_L"], z[g + "_qn"]
    a, b = (-W / 2, W / 2) if W else (-1e9, 1e9)
    ov = np.clip(np.minimum(t + L / 2, b) - np.maximum(t - L / 2, a), 0, None)
    return dict(zip(z["steps"].tolist(), (qn * ov).sum(1)))
# --- Scores over hours 1-96 where both exist: NSE, KGE (r, beta, gamma), peak, peak ratio, peak timing error (h) ---
def score(qs, qo):
    h = [k for k in range(1, 97) if k in qs and not np.isnan(qo.get(k, np.nan))]
    s = np.array([qs[k] for k in h]); o = np.array([qo[k] for k in h])
    nse = 1 - ((s - o) ** 2).sum() / ((o - o.mean()) ** 2).sum()
    r = np.corrcoef(s, o)[0, 1]; beta = s.mean() / o.mean(); gam = (s.std() / s.mean()) / (o.std() / o.mean())
    kge = 1 - np.sqrt((r - 1) ** 2 + (beta - 1) ** 2 + (gam - 1) ** 2)
    ho = h[int(o.argmax())]
    return dict(peak=s.max(), peak_obs=o.max(), peak_ratio=s.max() / o.max(), t_peak=h[int(s.argmax())], dt_peak=h[int(s.argmax())] - ho,
                beta=beta, r=r, gamma=gam, nse=nse, kge=kge)
# --- Loop over cases and run sets; list missing runs only where a run is expected ---
rows, hyd, missing = [], [], []
for c in C:
    for m, inf, p in SET:
        p = p.format(c=c)
        if not os.path.exists(p) and "_dp" in p: p = p.replace("_dp", "_dpn")   # FuXi runs exist only with the final build
        if not os.path.exists(p):
            if ("_ks" not in inf or c in ("R_1km_5min", "F_graphcast")) and (inf != "GA_sm" or c in ("R_1km_5min", "F_graphcast", "F_aifs", "F_fuxi")): missing.append(p)
            continue
        z = np.load(p)
        # Score each gauge for the three section widths and keep the hourly hydrographs
        for g in G:
            for wname, W in (("full", 400.0 if g == "Livange" else None), ("valley", None), ("surveyed", T[g]["W0"])):
                q = qwidth(z, g, W)
                rows.append(dict(case=c, model=m, infiltration=inf, gauge=g, width=wname, **{k: round(float(v), 4) for k, v in score(q, obs[g]).items()}))
                hyd += [(c, m, inf, g, wname, k, round(float(v), 3)) for k, v in sorted(q.items())]
# --- Write scores, hydrographs and the observations used ---
with open(S + "hipims/scores.csv", "w") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
with open(S + "hipims/hydrographs.csv", "w") as f:
    w = csv.writer(f); w.writerow(["case", "model", "infiltration", "gauge", "width", "h", "Q"]); w.writerows(hyd)
with open(S + "hipims/obs_utc.csv", "w") as f:
    w = csv.writer(f); w.writerow(["gauge", "h", "Q"]); w.writerows((g, k, obs[g][k]) for g in G for k in sorted(obs[g]))
print(len(rows), "score rows;", "missing:", len(missing)); [print(" ", p) for p in missing]
