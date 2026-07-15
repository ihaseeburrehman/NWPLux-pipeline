#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract per-station metrics for 2016, 2018, and 2021 events.
Reuses loaders from compare_wrf_gc_fuxi_aifs.py.
Outputs LaTeX tables directly.
"""

import sys
import os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compare_wrf_gc_fuxi_aifs as C

GC_XLSX  = "/Users/haseeb.rehman/Documents/Misc/AI_Models/GraphCast/graphcast_all_variables.xlsx"
FUXI_CSV = "/Users/haseeb.rehman/Documents/Misc/AI_Models/FuXi/fuxi_all_variables.csv"
AIFS_CSV = "/Users/haseeb.rehman/Documents/Misc/AI_Models/AIFS/aifs_all_variables.csv"

def load_model_csv(csv_path, year, out_precip, out_t2m):
    df = pd.read_csv(csv_path)
    df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
    df = df[df["Event"].astype(str) == year]
    if df.empty:
        return pd.DataFrame()
    df["Station"] = df["Station"].map(lambda s: C.MODEL_ALIAS.get(s, s))
    out = pd.DataFrame({
        "Station":      df["Station"].values,
        "UTC_Datetime": pd.to_datetime(df["Valid_Time"], format="%Y%m%dT%H", errors="coerce"),
        out_precip:     pd.to_numeric(df["Precip_mm"], errors="coerce").values,
        out_t2m:        pd.to_numeric(df["T2m_C"],     errors="coerce").values,
    }).dropna(subset=["UTC_Datetime"])
    return out

# Load merged data for each event
merged_by_event = {}
for year, cfg in C.EVENTS.items():
    obs = C.load_obs(cfg)
    gc  = C.load_model_xlsx(GC_XLSX, year, out_precip="GC_Precip", out_t2m="GC_T2m")
    fx  = load_model_csv(FUXI_CSV, year, "FuXi_Precip", "FuXi_T2m")
    af  = load_model_csv(AIFS_CSV, year, "AIFS_Precip", "AIFS_T2m")
    common = sorted(set(obs["Station"]) & set(gc["Station"]) & set(fx["Station"])
                    & set(af["Station"]) & set(C.STATION_COORDS))
    latlon = [C.STATION_COORDS[s] for s in common]
    wrf = C.extract_wrf(cfg["wrf_dir"], common, latlon)
    m = (wrf[["Station","UTC_Datetime","WRF_Precip","WRF_T2m"]]
         .merge(obs[obs["Station"].isin(common)][["Station","UTC_Datetime","Obs_Precip","Obs_T2m"]],
                on=["Station","UTC_Datetime"])
         .merge(gc[gc["Station"].isin(common)][["Station","UTC_Datetime","GC_Precip","GC_T2m"]],
                on=["Station","UTC_Datetime"])
         .merge(fx[fx["Station"].isin(common)][["Station","UTC_Datetime","FuXi_Precip","FuXi_T2m"]],
                on=["Station","UTC_Datetime"])
         .merge(af[af["Station"].isin(common)][["Station","UTC_Datetime","AIFS_Precip","AIFS_T2m"]],
                on=["Station","UTC_Datetime"])
         .dropna())
    merged_by_event[year] = m

SYS_KEYS = ["WRF", "GC", "FuXi", "AIFS"]

def fmt(val):
    if pd.isna(val) or np.isnan(val):
        return "-"
    return f"{val:.3f}"

# Generate tables
for year in ["2016", "2018", "2021"]:
    df_event = merged_by_event[year]
    stations = sorted(df_event["Station"].unique())
    
    # 1. Precipitation Table
    print(f"\n% ==================== {year} PRECIPITATION TABLE ====================")
    print(r"\begin{table}[htbp]")
    print(r"\centering")
    print(r"\scriptsize")
    print(f"\\caption{{Per-station precipitation categorical verification scores (threshold 1.0\\,mm/6\\,h) for the {year} event. $N$ indicates the number of 6-hourly verification pairs per station.}}")
    print(f"\\label{{tab:station_precip_{year}}}")
    print(r"\begin{tabular}{l c ccc ccc ccc ccc}")
    print(r"\toprule")
    print(r" & & \multicolumn{3}{c}{\textbf{WRF (After DA)}} & \multicolumn{3}{c}{\textbf{GraphCast}} & \multicolumn{3}{c}{\textbf{FuXi}} & \multicolumn{3}{c}{\textbf{AIFS}} \\")
    print(r"\cmidrule(lr){3-5}\cmidrule(lr){6-8}\cmidrule(lr){9-11}\cmidrule(lr){12-14}")
    print(r"Station & $N$ & POD & FAR & CSI & POD & FAR & CSI & POD & FAR & CSI & POD & FAR & CSI \\")
    print(r"\midrule")
    
    for stn in stations:
        stn_df = df_event[df_event["Station"] == stn]
        n_pairs = len(stn_df)
        
        metrics = {}
        for key in SYS_KEYS:
            res = C.calc_metrics(stn_df[f"{key}_Precip"], stn_df["Obs_Precip"], is_precip=True)
            metrics[key] = res
            
        row_str = f"{stn} & {n_pairs}"
        for key in SYS_KEYS:
            row_str += f" & {fmt(metrics[key]['POD'])} & {fmt(metrics[key]['FAR'])} & {fmt(metrics[key]['CSI'])}"
        row_str += r" \\"
        print(row_str)
        
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")
    
    # 2. Temperature Table
    print(f"\n% ==================== {year} TEMPERATURE TABLE ====================")
    print(r"\begin{table}[htbp]")
    print(r"\centering")
    print(r"\scriptsize")
    print(f"\\caption{{Per-station 2\\,m temperature continuous verification scores (RMSE in $^{{\circ}}$C, correlation $r$, and Bias in $^{{\circ}}$C) for the {year} event.}}")
    print(f"\\label{{tab:station_temp_{year}}}")
    print(r"\begin{tabular}{l ccc ccc ccc ccc}")
    print(r"\toprule")
    print(r" & \multicolumn{3}{c}{\textbf{WRF (After DA)}} & \multicolumn{3}{c}{\textbf{GraphCast}} & \multicolumn{3}{c}{\textbf{FuXi}} & \multicolumn{3}{c}{\textbf{AIFS}} \\")
    print(r"\cmidrule(lr){2-4}\cmidrule(lr){5-7}\cmidrule(lr){8-10}\cmidrule(lr){11-13}")
    print(r"Station & RMSE & $r$ & Bias & RMSE & $r$ & Bias & RMSE & $r$ & Bias & RMSE & $r$ & Bias \\")
    print(r"\midrule")
    
    for stn in stations:
        stn_df = df_event[df_event["Station"] == stn]
        
        metrics = {}
        for key in SYS_KEYS:
            res = C.calc_metrics(stn_df[f"{key}_T2m"], stn_df["Obs_T2m"], is_precip=False)
            metrics[key] = res
            
        row_str = f"{stn}"
        for key in SYS_KEYS:
            row_str += f" & {fmt(metrics[key]['RMSE'])} & {fmt(metrics[key]['Corr'])} & {fmt(metrics[key]['Bias'])}"
        row_str += r" \\"
        print(row_str)
        
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")
