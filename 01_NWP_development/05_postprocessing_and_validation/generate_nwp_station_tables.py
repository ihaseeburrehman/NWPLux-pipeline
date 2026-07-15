# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Generate the per-station NWP verification tables (Supplementary Data, Chapter 4)
directly from the authoritative statistics_analysis/metrics_tables.xlsx files, so
that the supplementary per-station values are guaranteed to aggregate to the
figures published in the main text (Chapter 4, Section on DA sensitivity /
background-error covariance / global-forcing sensitivity).

Source workbooks (one per experiment, all July 2021 event):
  * No DA (baseline)   : "Before DA" columns of the CONV+ZTD/GFS/CV3 workbook
  * ZTD only  (CV3)    : 2021_with_ZTD_only_cv3
  * CONV only (CV3)    : 2021_without_ZTD_cv3
  * CONV+ZTD  (GFS/CV3): 1_month_simulation_2021_new_GFS_000
  * CONV+ZTD  (GFS/CV5): 1_month_simulation_2021_new_GFS_000_cv5
  * CONV+ZTD  (ERA5/CV5, optimal): 2021_ERA5_cv5

Each workbook has:
  - "Precipitation"          : Bias/MAE/RMSE/MAPE, Before & After DA
  - "Temperature"            : Bias/MAE/RMSE/MAPE, Before & After DA
  - "Precipitation_POD_FAR"  : POD/FAR (General = Luxembourg gauges, NOAA ISD = surrounding)

The aggregate (simple mean over all stations, Luxembourg "General" + surrounding
"NOAA ISD") of the ERA5/CV5 workbook reproduces the published headline values
(No DA -> After DA: FAR 0.47 -> 0.45, POD 0.68 -> 0.73; RMSE/MAE/Bias per Summary).
"""

import os
import numpy as np
import pandas as pd

BASE = "/Users/haseeb.rehman/Desktop/For_Animation"
OUT = os.path.join(os.path.dirname(__file__), "nwp_station_tables.tex")

WB = {
    "convztd_gfs_cv3": f"{BASE}/3rd_Year/1_month_simulation_2021_new_GFS_000/statistics_analysis/metrics_tables.xlsx",
    "convztd_gfs_cv5": f"{BASE}/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/statistics_analysis/metrics_tables.xlsx",
    "conv_only_cv3":   f"{BASE}/4th_year/2021_without_ZTD_cv3/statistics_analysis/metrics_tables.xlsx",
    "ztd_only_cv3":    f"{BASE}/4th_year/2021_with_ZTD_only_cv3/statistics_analysis/metrics_tables.xlsx",
    "convztd_era5_cv5": f"{BASE}/4th_year/2021_ERA5_cv5/statistics_analysis/metrics_tables.xlsx",
}

# Station display order (matches the published tables)
STATION_ORDER = [
    "Arsdorf", "Asselborn", "Bale mulhouse", "Beitem", "Beringen", "Bettendorf",
    "Branches", "Briedfeld", "Dahl", "Dusseldorf", "Echternach", "Ernage",
    "Ettelbruck", "Fouhren", "Frankfurt main", "Fritzlar", "Grevenmacher",
    "Hosingen", "Kassel calden", "Liege", "Mamer", "Meyenheim", "Mirecourt",
    "Oberkorn", "Oostende", "Remerschen", "Roodt", "Schimpach", "Spangdahlem ab",
    "Useldange", "Vatry", "Waldbillig", "Zeebrugge",
]


def load(wb_key):
    f = WB[wb_key]
    precip = pd.read_excel(f, sheet_name="Precipitation").set_index("Station")
    temp = pd.read_excel(f, sheet_name="Temperature").set_index("Station")
    pf = pd.read_excel(f, sheet_name="Precipitation_POD_FAR").set_index("Station")
    # merge General + NOAA ISD POD/FAR into single columns
    for base in ["After_FAR", "After_POD", "Before_FAR", "Before_POD"]:
        pf[base] = pf[base + "_General"].fillna(pf[base + "_NOAA ISD"])
    return precip, temp, pf


DATA = {k: load(k) for k in WB}


# ---------- colour map (green = best, yellow = mid, red = worst) ----------
def rgb_for(t):
    """t in [0,1]; 0 -> green (best), 1 -> red (worst)."""
    t = max(0.0, min(1.0, float(t)))
    if t < 0.5:
        r = 0.39 + (t / 0.5) * (1.00 - 0.39)
        g = 1.00
    else:
        r = 1.00
        g = 1.00 - ((t - 0.5) / 0.5) * (1.00 - 0.39)
    return f"{r:.2f},{g:.2f},0.39"


def norm_series(values, lower_is_better=True, use_abs=False):
    """Return normalized t in [0,1] (0=best) with robust 5-95 pct clipping."""
    v = np.array([np.abs(x) if use_abs else x for x in values], dtype=float)
    finite = v[np.isfinite(v)]
    if finite.size == 0:
        return {i: None for i in range(len(values))}
    lo, hi = np.nanpercentile(finite, 5), np.nanpercentile(finite, 95)
    if hi <= lo:
        lo, hi = finite.min(), finite.max()
    if hi <= lo:
        hi = lo + 1e-9
    out = {}
    for i, x in enumerate(v):
        if not np.isfinite(x):
            out[i] = None
            continue
        f = (x - lo) / (hi - lo)
        f = max(0.0, min(1.0, f))
        out[i] = f if lower_is_better else (1.0 - f)
    return out


def cell(value, t, fmt="{:.3f}"):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "-"
    col = rgb_for(t) if t is not None else "1.00,1.00,0.39"
    return f"\\cellcolor[rgb]{{{col}}} {fmt.format(value)}"


def get(wb_key, station, sheet, col):
    precip, temp, pf = DATA[wb_key]
    try:
        if sheet == "precip":
            return float(precip.loc[station, col])
        if sheet == "temp":
            return float(temp.loc[station, col])
        if sheet == "pf":
            return float(pf.loc[station, col])
    except (KeyError, ValueError, TypeError):
        return np.nan
    return np.nan


# ---------- Table 1: DA sensitivity (precip: RMSE, POD, FAR) ----------
def table_da_sensitivity():
    # config -> (wb_key, when)   where when in {"Before","After"}
    configs = [
        ("No DA",              "convztd_gfs_cv3", "Before"),
        ("ZTD Only",           "ztd_only_cv3",    "After"),
        ("CONV Only",          "conv_only_cv3",   "After"),
        ("CONV + ZTD (GFS)",   "convztd_gfs_cv3", "After"),
    ]
    metrics = [
        ("RMSE", "precip", "RMSE (Precipitation) {when} DA", True, False, "{:.3f}"),
        ("POD",  "pf",     "{when}_POD", False, False, "{:.3f}"),
        ("FAR",  "pf",     "{when}_FAR", True, False, "{:.3f}"),
    ]
    # gather raw values [config][metric][station]
    raw = {}
    for (_, wb, when) in configs:
        for (mname, sheet, coltmpl, lower, absv, _) in metrics:
            col = coltmpl.format(when=when)
            raw[(wb, when, mname)] = [get(wb, st, sheet, col) for st in STATION_ORDER]
    # normalize each metric jointly across all configs
    tnorm = {}
    for (mname, sheet, coltmpl, lower, absv, _) in metrics:
        allvals, keymap = [], []
        for (_, wb, when) in configs:
            vals = raw[(wb, when, mname)]
            for i, v in enumerate(vals):
                allvals.append(v); keymap.append((wb, when, mname, i))
        tt = norm_series(allvals, lower_is_better=lower, use_abs=absv)
        for j, key in enumerate(keymap):
            tnorm[key] = tt[j]

    lines = []
    lines.append("% ==================== DA SENSITIVITY TABLE (PRECIP) ====================")
    lines.append("% AUTO-GENERATED by generate_nwp_station_tables.py from statistics_analysis/metrics_tables.xlsx")
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append("\\caption{Per-station precipitation verification metrics for data assimilation "
                 "sensitivity experiments (No DA, ZTD-only DA, CONV-only DA, and CONV+ZTD DA; "
                 "the No~DA column is the common Before-DA baseline, and the ZTD/CONV subsets are "
                 "CV3-based whereas CONV+ZTD is shown for the GFS/CV3 run). Averaged over all "
                 "stations these values reproduce the aggregate figures reported in "
                 "Chapter~\\ref{ch:nwp}. Cells are color-coded: green represents better performance "
                 "(lower RMSE/FAR, higher POD), and red represents poorer performance.} "
                 "\\label{tab:nwp_da_sens_precip}")
    lines.append("\\begin{tabular}{l ccc ccc ccc ccc}")
    lines.append("\\toprule")
    lines.append(" & \\multicolumn{3}{c}{\\textbf{No DA}} & \\multicolumn{3}{c}{\\textbf{ZTD Only}} "
                 "& \\multicolumn{3}{c}{\\textbf{CONV Only}} & \\multicolumn{3}{c}{\\textbf{CONV + ZTD (GFS)}} \\\\")
    lines.append("\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\\cmidrule(lr){8-10}\\cmidrule(lr){11-13}")
    lines.append("Station & RMSE & POD & FAR & RMSE & POD & FAR & RMSE & POD & FAR & RMSE & POD & FAR \\\\")
    lines.append("\\midrule")
    for i, st in enumerate(STATION_ORDER):
        cells = []
        for (_, wb, when) in configs:
            for (mname, sheet, coltmpl, lower, absv, fmt) in metrics:
                v = raw[(wb, when, mname)][i]
                t = tnorm[(wb, when, mname, i)]
                cells.append(cell(v, t, fmt))
        lines.append(f"{st} & " + " & ".join(cells) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    return "\n".join(lines)


# ---------- Tables 2 & 3: two-config precip(RMSE,POD,FAR)+temp(RMSE,MAE,Bias) ----------
def table_two_config(cfgA, cfgB, labelA, labelB, caption, label, title_group):
    """cfgX = (wb_key, when)."""
    groups = [(labelA, cfgA), (labelB, cfgB)]
    metrics = [
        ("p_rmse", "precip", "RMSE (Precipitation) {when} DA", True, False, "{:.3f}"),
        ("p_pod",  "pf",     "{when}_POD", False, False, "{:.3f}"),
        ("p_far",  "pf",     "{when}_FAR", True, False, "{:.3f}"),
        ("t_rmse", "temp",   "RMSE (Temperature) {when} DA", True, False, "{:.3f}"),
        ("t_mae",  "temp",   "MAE (Temperature) {when} DA", True, False, "{:.3f}"),
        ("t_bias", "temp",   "Bias (Temperature) {when} DA", True, True, "{:.3f}"),
    ]
    raw = {}
    for (_, (wb, when)) in groups:
        for (mname, sheet, coltmpl, lower, absv, _) in metrics:
            col = coltmpl.format(when=when)
            raw[(wb, when, mname)] = [get(wb, st, sheet, col) for st in STATION_ORDER]
    tnorm = {}
    for (mname, sheet, coltmpl, lower, absv, _) in metrics:
        allvals, keymap = [], []
        for (_, (wb, when)) in groups:
            for i, v in enumerate(raw[(wb, when, mname)]):
                allvals.append(v); keymap.append((wb, when, mname, i))
        tt = norm_series(allvals, lower_is_better=lower, use_abs=absv)
        for j, key in enumerate(keymap):
            tnorm[key] = tt[j]

    lines = []
    lines.append(f"% ==================== {label} TABLE ====================")
    lines.append("% AUTO-GENERATED by generate_nwp_station_tables.py from statistics_analysis/metrics_tables.xlsx")
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\scriptsize")
    lines.append(f"\\caption{{{caption}}} \\label{{{label}}}")
    lines.append("\\begin{tabular}{l ccc ccc ccc ccc}")
    lines.append("\\toprule")
    lines.append(f" & \\multicolumn{{6}}{{c}}{{\\textbf{{{title_group[0]}}}}} "
                 f"& \\multicolumn{{6}}{{c}}{{\\textbf{{{title_group[1]}}}}} \\\\")
    lines.append("\\cmidrule(lr){2-7}\\cmidrule(lr){8-13}")
    lines.append(" & \\multicolumn{3}{c}{Precipitation} & \\multicolumn{3}{c}{2\\,m Temperature} "
                 "& \\multicolumn{3}{c}{Precipitation} & \\multicolumn{3}{c}{2\\,m Temperature} \\\\")
    lines.append("\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\\cmidrule(lr){8-10}\\cmidrule(lr){11-13}")
    lines.append("Station & RMSE & POD & FAR & RMSE & MAE & Bias & RMSE & POD & FAR & RMSE & MAE & Bias \\\\")
    lines.append("\\midrule")
    for i, st in enumerate(STATION_ORDER):
        cells = []
        for (_, (wb, when)) in groups:
            for (mname, sheet, coltmpl, lower, absv, fmt) in metrics:
                v = raw[(wb, when, mname)][i]
                t = tnorm[(wb, when, mname, i)]
                cells.append(cell(v, t, fmt))
        lines.append(f"{st} & " + " & ".join(cells) + " \\\\")
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def main():
    blocks = []
    blocks.append(table_da_sensitivity())
    blocks.append("")
    blocks.append(table_two_config(
        ("convztd_gfs_cv3", "After"), ("convztd_gfs_cv5", "After"),
        "CV3", "CV5",
        "Per-station background error covariance sensitivity comparison "
        "(CV3 vs CV5, both GFS-forced CONV+ZTD). Cells are color-coded: green represents "
        "better performance (lower RMSE/MAE/FAR/absolute Bias, higher POD), and red represents "
        "poorer performance.",
        "tab:nwp_cv3_cv5",
        ("Background Error CV3", "Background Error CV5")))
    blocks.append("")
    blocks.append(table_two_config(
        ("convztd_gfs_cv5", "After"), ("convztd_era5_cv5", "After"),
        "GFS", "ERA5",
        "Per-station global meteorological forcing sensitivity comparison "
        "(GFS vs ERA5, both CONV+ZTD under CV5). Cells are color-coded: green represents "
        "better performance (lower RMSE/MAE/FAR/absolute Bias, higher POD), and red represents "
        "poorer performance.",
        "tab:nwp_gfs_era5",
        ("GFS Forcing (CV5)", "ERA5 Forcing (CV5)")))
    with open(OUT, "w") as f:
        f.write("\n".join(blocks) + "\n")
    print("Wrote", OUT)

    # sanity: print aggregate means used in the chapter
    _, _, pf = DATA["convztd_era5_cv5"]
    print("ERA5/CV5 aggregate  No DA FAR=%.3f After FAR=%.3f  No DA POD=%.3f After POD=%.3f" % (
        pf["Before_FAR"].mean(), pf["After_FAR"].mean(),
        pf["Before_POD"].mean(), pf["After_POD"].mean()))


if __name__ == "__main__":
    main()
