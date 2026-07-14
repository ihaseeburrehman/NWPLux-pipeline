#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to process WRF data for Luxembourg stations, plot meteorological metrics, and count improved stations.
"""

import glob
from osgeo import gdal
import numpy as np
import os
import pandas as pd
import time
from scipy.spatial import cKDTree
from netCDF4 import Dataset
from wrf import getvar, rh, to_np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
import seaborn as sns
import warnings

# Suppress all warnings
warnings.filterwarnings("ignore")

# Base directory
base_dir = "/Users/haseeb.rehman/Documents/wrfout_from_local_machine/3rd_year/1_day_simulation_2021_3_domains_cv5"
before_da_path = os.path.join(base_dir, "Before_DA")
after_da_path = os.path.join(base_dir, "After_DA")
output_before_folder = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_day_simulation_2021_3_domains_cv5/Before_DA/"
output_after_folder = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_day_simulation_2021_3_domains_cv5/After_DA/"
met_plot_dir = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_day_simulation_2021_3_domains_cv5/"

# Create output directories
os.makedirs(output_before_folder, exist_ok=True)
os.makedirs(output_after_folder, exist_ok=True)
os.makedirs(met_plot_dir, exist_ok=True)

# Output file paths
general_excel_file_before = os.path.join(output_before_folder, "general_station_data_before.xlsx")
general_excel_file_after_d01 = os.path.join(output_after_folder, "general_station_data_after_d01.xlsx")
general_excel_file_after_d02 = os.path.join(output_after_folder, "general_station_data_after_d02.xlsx")
general_excel_file_after_d03 = os.path.join(output_after_folder, "general_station_data_after_d03.xlsx")

# Luxembourg stations
lux_stations = [
    ("Briedfeld", 50.12385000, 6.06622000),
    ("Echternach", 49.80310000, 6.44337000),
    ("Ettelbruck", 49.85172000, 6.09754000),
    ("Oberkorn", 49.51220000, 5.90110000),
    ("Remerschen", 49.49100000, 6.34900000),
    ("Findel", 49.63265182, 6.23292867),
    ("Roodt", 49.79450000, 5.82020000),
    ("Hosingen", 49.99314000, 6.10147000),
    ("Useldange", 49.76739000, 5.96748000),
    ("Mamer", 49.63353000, 6.01930000),
    ("Arsdorf", 49.85891000, 5.84868000),
    ("Asselborn", 50.09685689, 5.96960753),
    ("Grevenmacher", 49.68087000, 6.43541000),
    ("Schimpach", 50.00930000, 5.84750000),
    ("Waldbillig", 49.79806000, 6.27730000),
    ("Bettendorf", 49.87410000, 6.20950000),
    ("Fouhren", 49.91445000, 6.19508000),
    ("Beringen", 49.76200000, 6.11179000),
    ("Dahl", 49.93595000, 5.98093000),
]

# Initialize dataframes
dataframes_general_before = {st[0]: [] for st in lux_stations}
dataframes_general_after_d01 = {st[0]: [] for st in lux_stations}
dataframes_general_after_d02 = {st[0]: [] for st in lux_stations}
dataframes_general_after_d03 = {st[0]: [] for st in lux_stations}

def read_subdataset_explicit(subdatasets, var_name):
    desired_ending = f":{var_name}"
    for s in subdatasets:
        if s[0].endswith(desired_ending):
            ds = gdal.Open(s[0])
            if ds is not None:
                return ds.ReadAsArray()
    return None

def slice_3d_to_2d(arr):
    if arr is None:
        return None
    if arr.ndim == 4:
        return arr[0, 0, :, :]
    elif arr.ndim == 3:
        return arr[0, :, :]
    return arr

def find_nearest_grid_point(xlat, xlong, lat, lon):
    points = np.column_stack((xlat.flatten(), xlong.flatten()))
    tree = cKDTree(points)
    dist, idx = tree.query([lat, lon])
    ny, nx = xlat.shape
    i, j = np.unravel_index(idx, (ny, nx))
    return i, j

def process_domain(path, domain, dataframes_general, folder_label):
    all_files = sorted(glob.glob(os.path.join(path, f"wrfout_{domain}_*")))
    total_files = len(all_files)
    start_time = time.time()

    for idx, filename in enumerate(all_files, start=1):
        try:
            print(f"\n[{folder_label}] Processing file: {filename}\n")

            ds = gdal.Open(filename)
            if ds is None:
                print(f"[ERROR] Could not open file: {filename}")
                continue
            subdatasets = ds.GetSubDatasets()
            ncfile = Dataset(filename, 'r')

            # Read required arrays
            raw_xlat = read_subdataset_explicit(subdatasets, "XLAT")
            raw_xlong = read_subdataset_explicit(subdatasets, "XLONG")
            raw_t2 = read_subdataset_explicit(subdatasets, "T2")
            raw_psfc = read_subdataset_explicit(subdatasets, "PSFC")
            raw_rainnc = read_subdataset_explicit(subdatasets, "RAINNC")
            raw_rainc = read_subdataset_explicit(subdatasets, "RAINC")
            raw_rainsh = read_subdataset_explicit(subdatasets, "RAINSH")
            raw_u10 = read_subdataset_explicit(subdatasets, "U10")
            raw_v10 = read_subdataset_explicit(subdatasets, "V10")

            # Convert to 2D
            xlat = slice_3d_to_2d(raw_xlat)
            xlong = slice_3d_to_2d(raw_xlong)
            t2 = slice_3d_to_2d(raw_t2)
            psfc = slice_3d_to_2d(raw_psfc)
            rainnc = slice_3d_to_2d(raw_rainnc)
            rainc = slice_3d_to_2d(raw_rainc)
            rainsh = slice_3d_to_2d(raw_rainsh) if raw_rainsh is not None else np.zeros_like(rainnc)
            u10 = slice_3d_to_2d(raw_u10)
            v10 = slice_3d_to_2d(raw_v10)

            if xlat is None or xlong is None or t2 is None or psfc is None or rainnc is None or rainc is None:
                print(f"[WARNING] Essential arrays missing for file: {filename}")
                continue

            # Extract date and time
            file_basename = os.path.basename(filename)
            parts = file_basename.split("_")
            if len(parts) > 3:
                utc_date = parts[2]
                utc_time = parts[3].replace("_", ":")
                utc_datetime = f"{utc_date} {utc_time}"
            else:
                utc_datetime = "UNKNOWN_DATETIME"

            # Process Luxembourg stations
            for st_name, lat, lon in lux_stations:
                i, j = find_nearest_grid_point(xlat, xlong, lat, lon)

                t2_val = t2[i, j] if t2 is not None else None
                psfc_val = psfc[i, j] if psfc is not None else None
                rainnc_val = rainnc[i, j] if rainnc is not None else None
                rainc_val = rainc[i, j] if rainc is not None else None
                rainsh_val = rainsh[i, j] if rainsh is not None else None
                u10_val = u10[i, j] if u10 is not None else None
                v10_val = v10[i, j] if v10 is not None else None

                out_t2 = t2_val - 273.15 if t2_val is not None else None
                out_precip = (rainnc_val + rainc_val + rainsh_val) if (rainnc_val is not None and rainc_val is not None and rainsh_val is not None) else None
                out_pres = psfc_val if psfc_val is not None else None
                out_wind = np.sqrt(u10_val**2 + v10_val**2) if (u10_val is not None and v10_val is not None) else None

                dataframes_general[st_name].append({
                    "UTC_Datetime": utc_datetime,
                    "Precipitation (mm)": out_precip,
                    "Temperature (°C)": out_t2,
                    "Wind Speed (m/s)": out_wind,
                    "Pressure (Pa)": out_pres,
                })

            # Progress and time estimation
            elapsed_time = time.time() - start_time
            progress = idx / total_files * 100
            estimated_total_time = elapsed_time / idx * total_files
            remaining_time = estimated_total_time - elapsed_time
            elapsed_mins, elapsed_secs = divmod(elapsed_time, 60)
            remaining_mins, remaining_secs = divmod(remaining_time, 60)

            print(f"[INFO] Progress: {progress:.2f}% ({idx}/{total_files})")
            print(f"[INFO] Elapsed Time: {int(elapsed_mins)}m {int(elapsed_secs)}s")
            print(f"[INFO] Estimated Remaining Time: {int(remaining_mins)}m {int(remaining_secs)}s")

            ncfile.close()

        except Exception as e:
            print(f"[ERROR] Error processing {filename}: {e}")

# Process Before_DA
print("\nProcessing Before_DA folder...")
process_domain(before_da_path, 'd01', dataframes_general_before, "Before_DA")

# Process After_DA for each domain
print("\nProcessing After_DA folder for d01...")
process_domain(after_da_path, 'd01', dataframes_general_after_d01, "After_DA_d01")

print("\nProcessing After_DA folder for d02...")
process_domain(after_da_path, 'd02', dataframes_general_after_d02, "Before_DA_d02")

print("\nProcessing After_DA folder for d03...")
process_domain(after_da_path, 'd03', dataframes_general_after_d03, "After_DA_d03")

# Write Before_DA data
print("\n[INFO] Writing Before_DA General station data to Excel...")
with pd.ExcelWriter(general_excel_file_before) as writer:
    for station, records in dataframes_general_before.items():
        pd.DataFrame(records).to_excel(writer, sheet_name=station, index=False)
print(f"[INFO] Excel file saved to {general_excel_file_before}")

# Write After_DA data for each domain
print("\n[INFO] Writing After_DA General station data for d01 to Excel...")
with pd.ExcelWriter(general_excel_file_after_d01) as writer:
    for station, records in dataframes_general_after_d01.items():
        pd.DataFrame(records).to_excel(writer, sheet_name=station, index=False)
print(f"[INFO] Excel file saved to {general_excel_file_after_d01}")

# Write After_DA data for d02
print("\n[INFO] Writing After_DA General station data for d02 to Excel...")
with pd.ExcelWriter(general_excel_file_after_d02) as writer:
    for station, records in dataframes_general_after_d02.items():
        pd.DataFrame(records).to_excel(writer, sheet_name=station, index=False)
print(f"[INFO] Excel file saved to {general_excel_file_after_d02}")

# Write After_DA data for d03
print("\n[INFO] Writing After_DA General station data for d03 to Excel...")
with pd.ExcelWriter(general_excel_file_after_d03) as writer:
    for station, records in dataframes_general_after_d03.items():
        pd.DataFrame(records).to_excel(writer, sheet_name=station, index=False)
print(f"[INFO] Excel file saved to {general_excel_file_after_d03}")

# --- Plotting and Improvement Analysis ---
print("\nGenerating comparison plots and analyzing improvements...")

# Plotting setup
plt.style.use('seaborn-white')
sns.set_context("paper", font_scale=1.2)
bar_width = 0.10
spacing = 0.01  # Space between bars
colors = {
    'No DA': '#A52A2A', # muted red
    'After_DA_d01': '#DAA520', # muted yellow
    'After_DA_d02': '#20B2AA', # muted cyan
    'After_DA_d03': '#228B22' # muted green
}
label_fontsize = 10
grid_alpha = 0.6

# Observed data file
file_observed_general = '/Users/haseeb.rehman/Documents/Misc/Luxembourg_stations_for_validation/2021_Event/stations_6hr_cumulative.xlsx'

# Station names
station_names_general = pd.ExcelFile(file_observed_general).sheet_names

def read_station_data(file_path, station, is_observed=False):
    try:
        df = pd.read_excel(file_path, sheet_name=station)
    except ValueError:
        return None
    if is_observed:
        df.rename(columns={'Precip(mm)': 'Obs_Precip(mm)', 'Temp(2m)': 'Obs_T2(C)'}, inplace=True)
        df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
    else:
        df.rename(columns={'UTC_Datetime': 'UTC_Datetime',
                           'Precipitation (mm)': 'Sim_Precip(mm)',
                           'Temperature (°C)': 'Sim_T2(C)'}, inplace=True)
        df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], format='%Y-%m-%d %H', errors='coerce')
    return df

def compute_metrics(df, sim_col, obs_col):
    valid_df = df[[sim_col, obs_col]].dropna()
    if valid_df.empty:
        return np.nan, np.nan, np.nan, np.nan
    rmse = np.sqrt(mean_squared_error(valid_df[sim_col], valid_df[obs_col]))
    mae = np.mean(np.abs(valid_df[sim_col] - valid_df[obs_col]))
    safe_obs = valid_df[obs_col].replace({0: np.nan})
    numerator = np.abs(valid_df[sim_col] - valid_df[obs_col])
    denominator = (np.abs(valid_df[sim_col]) + np.abs(valid_df[obs_col])) / 2
    nonzero = denominator != 0
    mape = np.mean((numerator[nonzero] / denominator[nonzero])) * 100 if np.any(nonzero) else np.nan
    bias = np.mean(valid_df[sim_col] - valid_df[obs_col])
    return rmse, mae, mape, bias

def compute_pod_far(df, sim_col, obs_col, threshold=0.1):
    valid_df = df[[sim_col, obs_col]].dropna()
    if valid_df.empty:
        return np.nan, np.nan
    obs_rain = valid_df[obs_col] > threshold
    sim_rain = valid_df[sim_col] > threshold
    hits = ((sim_rain) & (obs_rain)).sum()
    misses = ((~sim_rain) & (obs_rain)).sum()
    false_alarms = ((sim_rain) & (~obs_rain)).sum()
    pod = hits / (hits + misses) if (hits + misses) > 0 else np.nan
    far = false_alarms / (hits + false_alarms) if (hits + false_alarms) > 0 else np.nan
    return pod, far

# Compute metrics and track improvements
variables = [
    ('Sim_Precip(mm)', 'Obs_Precip(mm)', 'Precipitation (mm)'),
    ('Sim_T2(C)', 'Obs_T2(C)', 'Temperature (°C)')
]
case_paths = {
    "No DA": general_excel_file_before,
    "After_DA_d01": general_excel_file_after_d01,
    "After_DA_d02": general_excel_file_after_d02,
    "After_DA_d03": general_excel_file_after_d03
}

overall_metrics_met = []
precip_pod_far = {'No DA': [], 'After_DA_d01': [], 'After_DA_d02': [], 'After_DA_d03': []}
improved_counts = {
    'Precipitation (mm)': {'After_DA_d01': 0, 'After_DA_d02': 0, 'After_DA_d03': 0},
    'Temperature (°C)': {'After_DA_d01': 0, 'After_DA_d02': 0, 'After_DA_d03': 0}
}

for station in station_names_general:
    df_obs = read_station_data(file_observed_general, station, is_observed=True)
    if df_obs is None:
        continue

    df_before = read_station_data(general_excel_file_before, station, is_observed=False)
    df_after_d01 = read_station_data(general_excel_file_after_d01, station, is_observed=False)
    df_after_d02 = read_station_data(general_excel_file_after_d02, station, is_observed=False)
    df_after_d03 = read_station_data(general_excel_file_after_d03, station, is_observed=False)

    if any(df is None for df in [df_before, df_after_d01, df_after_d02, df_after_d03]):
        continue

    df_merged_before = pd.merge(df_before, df_obs, on='UTC_Datetime', how='inner')
    df_merged_after_d01 = pd.merge(df_after_d01, df_obs, on='UTC_Datetime', how='inner')
    df_merged_after_d02 = pd.merge(df_after_d02, df_obs, on='UTC_Datetime', how='inner')
    df_merged_after_d03 = pd.merge(df_after_d03, df_obs, on='UTC_Datetime', how='inner')

    if any(df.empty for df in [df_merged_before, df_merged_after_d01, df_merged_after_d02, df_merged_after_d03]):
        continue

    for sim_col, obs_col, var_name in variables:
        rmse_b, mae_b, mape_b, bias_b = compute_metrics(df_merged_before, sim_col, obs_col)
        rmse_a_d01, mae_a_d01, mape_a_d01, bias_a_d01 = compute_metrics(df_merged_after_d01, sim_col, obs_col)
        rmse_a_d02, mae_a_d02, mape_a_d02, bias_a_d02 = compute_metrics(df_merged_after_d02, sim_col, obs_col)
        rmse_a_d03, mae_a_d03, mape_a_d03, bias_a_d03 = compute_metrics(df_merged_after_d03, sim_col, obs_col)

        # Count improvements (RMSE decrease)
        if not np.isnan(rmse_b) and not np.isnan(rmse_a_d01) and rmse_a_d01 < rmse_b:
            improved_counts[var_name]['After_DA_d01'] += 1
        if not np.isnan(rmse_b) and not np.isnan(rmse_a_d02) and rmse_a_d02 < rmse_b:
            improved_counts[var_name]['After_DA_d02'] += 1
        if not np.isnan(rmse_b) and not np.isnan(rmse_a_d03) and rmse_a_d03 < rmse_b:
            improved_counts[var_name]['After_DA_d03'] += 1

        overall_metrics_met.append({
            'Station': station,
            'Variable': var_name,
            'Before_RMSE': rmse_b, 'Before_MAE': mae_b, 'Before_MAPE': mape_b, 'Before_Bias': bias_b,
            'After_d01_RMSE': rmse_a_d01, 'After_d01_MAE': mae_a_d01, 'After_d01_MAPE': mape_a_d01, 'After_d01_Bias': bias_a_d01,
            'After_d02_RMSE': rmse_a_d02, 'After_d02_MAE': mae_a_d02, 'After_d02_MAPE': mape_a_d02, 'After_d02_Bias': bias_a_d02,
            'After_d03_RMSE': rmse_a_d03, 'After_d03_MAE': mae_a_d03, 'After_d03_MAPE': mape_a_d03, 'After_d03_Bias': bias_a_d03,
        })

        # Compute POD/FAR for Precipitation
        if var_name == 'Precipitation (mm)':
            pod_b, far_b = compute_pod_far(df_merged_before, sim_col, obs_col)
            pod_a_d01, far_a_d01 = compute_pod_far(df_merged_after_d01, sim_col, obs_col)
            pod_a_d02, far_a_d02 = compute_pod_far(df_merged_after_d02, sim_col, obs_col)
            pod_a_d03, far_a_d03 = compute_pod_far(df_merged_after_d03, sim_col, obs_col)
            precip_pod_far['No DA'].append((pod_b, far_b))
            precip_pod_far['After_DA_d01'].append((pod_a_d01, far_a_d01))
            precip_pod_far['After_DA_d02'].append((pod_a_d02, far_a_d02))
            precip_pod_far['After_DA_d03'].append((pod_a_d03, far_a_d03))

# Print improvement counts
print("\nNumber of stations with improved RMSE after DA:")
for var_name in improved_counts:
    print(f"\n{var_name}:")
    print(f"  After_DA_d01: {improved_counts[var_name]['After_DA_d01']} stations")
    print(f"  After_DA_d02: {improved_counts[var_name]['After_DA_d02']} stations")
    print(f"  After_DA_d03: {improved_counts[var_name]['After_DA_d03']} stations")

# Plot metrics
df_overall_met = pd.DataFrame(overall_metrics_met)
agg_metrics_general = df_overall_met.groupby('Variable').mean(numeric_only=True)

metrics_precip = ['RMSE', 'MAE', 'MAPE', 'Bias', 'POD', 'FAR']
metrics_temp = ['RMSE', 'MAE', 'MAPE', 'Bias']
variables_met = ['Precipitation (mm)', 'Temperature (°C)']

# Plot 1: Overall Comparison Metrics
fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12), sharex=False)
fig1.subplots_adjust(hspace=0.3)

# Precipitation Metrics
var = 'Precipitation (mm)'
mean_pod_before = np.nanmean([p[0] for p in precip_pod_far['No DA']])
mean_far_before = np.nanmean([p[1] for p in precip_pod_far['No DA']])
mean_pod_d01 = np.nanmean([p[0] for p in precip_pod_far['After_DA_d01']])
mean_far_d01 = np.nanmean([p[1] for p in precip_pod_far['After_DA_d01']])
mean_pod_d02 = np.nanmean([p[0] for p in precip_pod_far['After_DA_d02']])
mean_far_d02 = np.nanmean([p[1] for p in precip_pod_far['After_DA_d02']])
mean_pod_d03 = np.nanmean([p[0] for p in precip_pod_far['After_DA_d03']])
mean_far_d03 = np.nanmean([p[1] for p in precip_pod_far['After_DA_d03']])

# Debug print for FAR and Bias values
print("\nDebug - Precipitation Metrics:")
print(f"No DA Bias: {agg_metrics_general.loc[var, 'Before_Bias']}")
print(f"After_DA_d01 Bias: {agg_metrics_general.loc[var, 'After_d01_Bias']}")
print(f"After_DA_d02 Bias: {agg_metrics_general.loc[var, 'After_d02_Bias']}")
print(f"After_DA_d03 Bias: {agg_metrics_general.loc[var, 'After_d03_Bias']}")
print(f"No DA FAR: {mean_far_before}")
print(f"After_DA_d01 FAR: {mean_far_d01}")
print(f"After_DA_d02 FAR: {mean_far_d02}")
print(f"After_DA_d03 FAR: {mean_far_d03}")

x = np.arange(len(metrics_precip)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias', 'POD', 'FAR']
domain_map = {'No DA': 'Before', 'After_DA_d01': 'After_d01', 'After_DA_d02': 'After_d02', 'After_DA_d03': 'After_d03'}
for i, case in enumerate(case_paths.keys()):
    prefix = domain_map[case]
    values = [agg_metrics_general.loc[var, f'{prefix}_{m}'] / (100 if m == 'MAPE' else 1) for m in metrics_precip[:4]] + ([mean_pod_before, mean_far_before] if case == 'No DA' else [mean_pod_d01, mean_far_d01] if case == 'After_DA_d01' else [mean_pod_d02, mean_far_d02] if case == 'After_DA_d02' else [mean_pod_d03, mean_far_d03])
    bars = ax1.bar(x + i * (bar_width + spacing), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            ax1.text(bar.get_x() + bar.get_width()/2, height/2, f'{height:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)

ax1.set_ylabel('Metric Value (mm)', fontsize=label_fontsize)
ax1.set_xticks(x + (len(case_paths) - 1) * (bar_width + spacing) / 2)
ax1.set_xticklabels(custom_labels, rotation=0, fontsize=label_fontsize)
ax1.tick_params(axis='both', length=4, width=0.5)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)

# Temperature Metrics
var = 'Temperature (°C)'
x = np.arange(len(metrics_temp)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']
for i, case in enumerate(case_paths.keys()):
    prefix = domain_map[case]
    values = [agg_metrics_general.loc[var, f'{prefix}_{m}'] / (100 if m == 'MAPE' else 1) for m in metrics_temp]
    bars = ax2.bar(x + i * (bar_width + spacing), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            ax2.text(bar.get_x() + bar.get_width()/2, height/2, f'{height:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)

ax2.set_ylabel('Metric Value (°C)', fontsize=label_fontsize)
ax2.set_xticks(x + (len(case_paths) - 1) * (bar_width + spacing) / 2)
ax2.set_xticklabels(custom_labels, rotation=0, fontsize=label_fontsize)
ax2.tick_params(axis='both', length=4, width=0.5)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(met_plot_dir, "overall_metrics_comparison.png"), dpi=300, bbox_inches='tight')
plt.close(fig1)
print(f"Graph 1 saved to {os.path.join(met_plot_dir, 'overall_metrics_comparison.png')}")

# Plot 2: Improvement Metrics for Precipitation
fig2, ax4 = plt.subplots(1, 1, figsize=(10, 6))
var = 'Precipitation (mm)'
metrics_improv = ['RMSE', 'MAE', 'MAPE', 'Bias', 'POD', 'FAR']
x = np.arange(len(metrics_improv)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias', 'POD', 'FAR']
cases_for_improvement = [case for case in case_paths.keys() if case != 'No DA']

for i, case in enumerate(cases_for_improvement):
    prefix = domain_map[case]
    mean_far = mean_far_d01 if case == 'After_DA_d01' else mean_far_d02 if case == 'After_DA_d02' else mean_far_d03
    values = [
        ((agg_metrics_general.loc[var, f'Before_{m}'] - agg_metrics_general.loc[var, f'{prefix}_{m}']) / abs(agg_metrics_general.loc[var, f'Before_{m}']) * 100) if not np.isnan(agg_metrics_general.loc[var, f'Before_{m}']) and not np.isnan(agg_metrics_general.loc[var, f'{prefix}_{m}']) and agg_metrics_general.loc[var, f'Before_{m}'] != 0 else np.nan for m in metrics_improv[:3]
    ] + [
        ((abs(agg_metrics_general.loc[var, f'Before_Bias']) - abs(agg_metrics_general.loc[var, f'{prefix}_Bias'])) / abs(agg_metrics_general.loc[var, f'Before_Bias']) * 100) if not np.isnan(agg_metrics_general.loc[var, f'Before_Bias']) and not np.isnan(agg_metrics_general.loc[var, f'{prefix}_Bias']) and agg_metrics_general.loc[var, f'Before_Bias'] != 0 else np.nan,
        ((mean_pod_d01 if case == 'After_DA_d01' else mean_pod_d02 if case == 'After_DA_d02' else mean_pod_d03 - mean_pod_before) / abs(mean_pod_before) * 100) if not np.isnan(mean_pod_before) and not np.isnan(mean_pod_d01 if case == 'After_DA_d01' else mean_pod_d02 if case == 'After_DA_d02' else mean_pod_d03) and mean_pod_before != 0 else np.nan,
        (-mean_far * 100) if mean_far_before == 0 and not np.isnan(mean_far) else ((mean_far_before - mean_far) / abs(mean_far_before) * 100) if not np.isnan(mean_far_before) and not np.isnan(mean_far) and mean_far_before != 0 else np.nan
    ]
    print(f"\nDebug - Improvement for {case}:")
    print(f"Values: {values}")
    bars = ax4.bar(x + i * (bar_width + spacing), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            label = f'{height:+.1f}%' if height >= 0 else f'{height:.1f}%'
            ax4.text(bar.get_x() + bar.get_width()/2, height/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)

ax4.set_ylabel('Improvement (%)', fontsize=label_fontsize)
ax4.set_xticks(x + (len(cases_for_improvement) - 1) * (bar_width + spacing) / 2)
ax4.set_xticklabels(custom_labels, rotation=0, fontsize=label_fontsize)
ax4.tick_params(axis='both', length=4, width=0.5)
ax4.spines['top'].set_visible(False)
ax4.spines['right'].set_visible(False)
ax4.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(met_plot_dir, "precipitation_improvement_comparison.png"), dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f"Graph 2 saved to {os.path.join(met_plot_dir, 'precipitation_improvement_comparison.png')}")

# Plot 3: Improvement Metrics for Temperature
fig3, ax5 = plt.subplots(1, 1, figsize=(10, 6))
var = 'Temperature (°C)'
metrics_improv_temp = ['RMSE', 'MAE', 'MAPE', 'Bias']
x = np.arange(len(metrics_improv_temp)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']

for i, case in enumerate(cases_for_improvement):
    prefix = domain_map[case]
    values = [
        ((agg_metrics_general.loc[var, f'Before_{m}'] - agg_metrics_general.loc[var, f'{prefix}_{m}']) / abs(agg_metrics_general.loc[var, f'Before_{m}']) * 100) if not np.isnan(agg_metrics_general.loc[var, f'Before_{m}']) and not np.isnan(agg_metrics_general.loc[var, f'{prefix}_{m}']) and agg_metrics_general.loc[var, f'Before_{m}'] != 0 else np.nan for m in metrics_improv_temp[:3]
    ] + [
        ((abs(agg_metrics_general.loc[var, f'Before_Bias']) - abs(agg_metrics_general.loc[var, f'{prefix}_Bias'])) / abs(agg_metrics_general.loc[var, f'Before_Bias']) * 100) if not np.isnan(agg_metrics_general.loc[var, f'Before_Bias']) and not np.isnan(agg_metrics_general.loc[var, f'{prefix}_Bias']) and agg_metrics_general.loc[var, f'Before_Bias'] != 0 else np.nan
    ]
    bars = ax5.bar(x + i * (bar_width + spacing), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            label = f'{height:+.1f}%' if height >= 0 else f'{height:.1f}%'
            ax5.text(bar.get_x() + bar.get_width()/2, height/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)

ax5.set_ylabel('Improvement (%)', fontsize=label_fontsize)
ax5.set_xticks(x + (len(cases_for_improvement) - 1) * (bar_width + spacing) / 2)
ax5.set_xticklabels(custom_labels, rotation=0, fontsize=label_fontsize)
ax5.tick_params(axis='both', length=4, width=0.5)
ax5.spines['top'].set_visible(False)
ax5.spines['right'].set_visible(False)
ax5.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(met_plot_dir, "temperature_improvement_comparison.png"), dpi=300, bbox_inches='tight')
plt.close(fig3)
print(f"Graph 3 saved to {os.path.join(met_plot_dir, 'temperature_improvement_comparison.png')}")

print(f"\nDone! Excel files saved in:\n  {output_before_folder}\n  {output_after_folder}")
print(f"Plots saved in: {met_plot_dir}")