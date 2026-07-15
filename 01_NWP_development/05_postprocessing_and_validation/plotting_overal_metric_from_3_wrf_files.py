#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Script to compare WRF Before DA, After DA CV3, and After DA CV5 with observed meteorological
and ZTD data, including NOAA ISD stations. Generates overall plots with a minimal scientific
style, using softened colors, bar widths, and text on bars consistent with the reference script.
Includes a separate figure for POD and FAR metrics for precipitation.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
import seaborn as sns
import os
import warnings
# Suppress all warnings
warnings.filterwarnings("ignore")
# ------------------------------------------------------------------------
# 0) Basic Setup
# ------------------------------------------------------------------------
plt.style.use('seaborn-white')
sns.set_context("paper", font_scale=1.2)
base_dir = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5"
met_dir = os.path.join(base_dir, "Meteorological_variables")
ztd_dir = os.path.join(base_dir, "ztd_variable")
os.makedirs(met_dir, exist_ok=True)
os.makedirs(ztd_dir, exist_ok=True)
# Specify bar width and colors from reference script
bar_width = 0.10
colors = {
    'before': '#A52A2A', # muted red for No DA
    'after_cv3': '#DAA520', # muted yellow for CONV
    'after_cv5': '#20B2AA', # muted cyan for ZTD
}
label_fontsize = 10
grid_alpha = 0.6
# ------------------------------------------------------------------------
# 1) File Paths (Meteorological)
# ------------------------------------------------------------------------
file_observed_general = '/Users/haseeb.rehman/Documents/Misc/Luxembourg_stations_for_validation/2021_Event/stations_6hr_cumulative.xlsx'
file_observed_noaa = '/Users/haseeb.rehman/Documents/Misc/Luxembourg_stations_for_validation/2021_Event/Stations_other_than_lux/station_weather_data_june_july_2021_6hr.xlsx'
file_before_DA = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/Before_DA/general_station_data_before.xlsx'
file_after_DA_cv5 = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/After_DA/general_station_data_after.xlsx'
file_after_DA_cv3 = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000/After_DA/general_station_data_after.xlsx'
# ------------------------------------------------------------------------
# 2) File Paths (ZTD)
# ------------------------------------------------------------------------
ztd_file_observed = '/Users/haseeb.rehman/WRF/WRFDA/DAT_DIR/ztd_data_June_july_2021/for_validation/ztd_data.xlsx'
ztd_file_before_DA = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/Before_DA/ztd_station_data_before.xlsx'
ztd_file_after_DA_cv5 = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/After_DA/ztd_station_data_after.xlsx'
ztd_file_after_DA_cv3 = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000/After_DA/ztd_station_data_after.xlsx'
# ------------------------------------------------------------------------
# 3) Station Names
# ------------------------------------------------------------------------
station_names_general = pd.ExcelFile(file_observed_general).sheet_names
station_names_noaa = pd.ExcelFile(file_observed_noaa).sheet_names
ztd_station_names = pd.ExcelFile(ztd_file_observed).sheet_names
# ------------------------------------------------------------------------
# 4) Read Meteorological Data
# ------------------------------------------------------------------------
def read_station_data(file_path, station, is_observed=False, is_noaa=False):
    try:
        df = pd.read_excel(file_path, sheet_name=station)
    except ValueError:
        return None
    if is_observed:
        df.rename(columns={'Precip(mm)': 'Obs_Precip(mm)', 'Temp(2m)': 'Obs_T2(C)', 'RH(%)': 'Obs_RH(%)'}, inplace=True)
        if is_noaa:
            df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], dayfirst=False, errors='coerce')
        else:
            df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], format='%m/%d/%Y %I:%M:%S %p', errors='coerce')
    else:
        df.rename(columns={'UTC_Datetime': 'UTC_Datetime',
                          'Precipitation (mm)': 'Sim_Precip(mm)',
                          'Temperature (°C)': 'Sim_T2(C)',
                          'Relative Humidity (%)': 'Sim_RH(%)'}, inplace=True)
        df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], format='%Y-%m-%d %H', errors='coerce')
    return df
# ------------------------------------------------------------------------
# 5) Read ZTD Data
# ------------------------------------------------------------------------
def read_ztd_data(file_path, station, is_observed=False):
    try:
        df = pd.read_excel(file_path, sheet_name=station)
    except ValueError:
        return None
    if is_observed:
        df.rename(columns={'UTC_Datetime': 'UTC_Datetime', 'ZTD (m)': 'Obs_ZTD(m)'}, inplace=True)
        df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], errors='coerce')
    else:
        df.rename(columns={'UTC_Datetime': 'UTC_Datetime', 'ZTD (m)': 'Sim_ZTD(m)'}, inplace=True)
        df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], errors='coerce')
    return df
# ------------------------------------------------------------------------
# 6) Compute Metrics (Handle NaN Values)
# ------------------------------------------------------------------------
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
# ------------------------------------------------------------------------
# 7) Compute POD and FAR
# ------------------------------------------------------------------------
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
# ------------------------------------------------------------------------
# 8) MET DATA: Compute Overall Metrics
# ------------------------------------------------------------------------
variables = [
    ('Sim_Precip(mm)', 'Obs_Precip(mm)', 'Precipitation (mm)'),
    ('Sim_T2(C)', 'Obs_T2(C)', 'Temperature (°C)'),
    ('Sim_RH(%)', 'Obs_RH(%)', 'Relative Humidity (%)')
]
overall_metrics_met = []
precip_pod_far = {'before': [], 'after_cv3': [], 'after_cv5': []}
all_station_names = station_names_general + station_names_noaa
for station in all_station_names:
    if station in station_names_general:
        df_obs = read_station_data(file_observed_general, station, is_observed=True, is_noaa=False)
    elif station in station_names_noaa:
        df_obs = read_station_data(file_observed_noaa, station, is_observed=True, is_noaa=True)
    else:
        continue
    if df_obs is None:
        continue
    df_before = read_station_data(file_before_DA, station, is_observed=False)
    df_after_cv3 = read_station_data(file_after_DA_cv3, station, is_observed=False)
    df_after_cv5 = read_station_data(file_after_DA_cv5, station, is_observed=False)
    if df_before is None or df_after_cv3 is None or df_after_cv5 is None:
        continue
    df_merged_before = pd.merge(df_before, df_obs, on='UTC_Datetime', how='inner')
    df_merged_after_cv3 = pd.merge(df_after_cv3, df_obs, on='UTC_Datetime', how='inner')
    df_merged_after_cv5 = pd.merge(df_after_cv5, df_obs, on='UTC_Datetime', how='inner')
    if df_merged_before.empty or df_merged_after_cv3.empty or df_merged_after_cv5.empty:
        continue
    for sim_col, obs_col, var_name in variables:
        rmse_b, mae_b, mape_b, bias_b = compute_metrics(df_merged_before, sim_col, obs_col)
        rmse_a_cv3, mae_a_cv3, mape_a_cv3, bias_a_cv3 = compute_metrics(df_merged_after_cv3, sim_col, obs_col)
        rmse_a_cv5, mae_a_cv5, mape_a_cv5, bias_a_cv5 = compute_metrics(df_merged_after_cv5, sim_col, obs_col)
        overall_metrics_met.append({
            'Station': station,
            'Variable': var_name,
            'Before_RMSE': rmse_b, 'Before_MAE': mae_b, 'Before_MAPE': mape_b, 'Before_Bias': bias_b,
            'After_CV3_RMSE': rmse_a_cv3, 'After_CV3_MAE': mae_a_cv3, 'After_CV3_MAPE': mape_a_cv3, 'After_CV3_Bias': bias_a_cv3,
            'After_CV5_RMSE': rmse_a_cv5, 'After_CV5_MAE': mae_a_cv5, 'After_CV5_MAPE': mape_a_cv5, 'After_CV5_Bias': bias_a_cv5,
            'Source': 'NOAA ISD' if station in station_names_noaa else 'General'
        })
        if var_name == 'Precipitation (mm)':
            pod_b, far_b = compute_pod_far(df_merged_before, sim_col, obs_col)
            pod_a_cv3, far_a_cv3 = compute_pod_far(df_merged_after_cv3, sim_col, obs_col)
            pod_a_cv5, far_a_cv5 = compute_pod_far(df_merged_after_cv5, sim_col, obs_col)
            precip_pod_far['before'].append((pod_b, far_b))
            precip_pod_far['after_cv3'].append((pod_a_cv3, far_a_cv3))
            precip_pod_far['after_cv5'].append((pod_a_cv5, far_a_cv5))
df_overall_met = pd.DataFrame(overall_metrics_met)
agg_metrics_general = df_overall_met[df_overall_met['Source'] == 'General'].groupby('Variable').mean(numeric_only=True)
agg_metrics_noaa = df_overall_met[df_overall_met['Source'] == 'NOAA ISD'].groupby('Variable').mean(numeric_only=True)
metrics = ['RMSE', 'MAE', 'MAPE', 'Bias']
variables_met = ['Precipitation (mm)', 'Temperature (°C)', 'Relative Humidity (%)']
x = np.arange(len(metrics)) * 0.6 # Adjusted spacing to match reference script
# Plot for General Stations
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 12), sharex=False)
fig.suptitle('Overall Meteorological Metrics (Mean Across General Stations)', fontsize=12)
for i, var in enumerate(variables_met):
    if var in agg_metrics_general.index:
        before_values = [agg_metrics_general.loc[var, 'Before_RMSE'],
                        agg_metrics_general.loc[var, 'Before_MAE'],
                        agg_metrics_general.loc[var, 'Before_MAPE'] / 100,
                        agg_metrics_general.loc[var, 'Before_Bias']]
        after_cv3_values = [agg_metrics_general.loc[var, 'After_CV3_RMSE'],
                           agg_metrics_general.loc[var, 'After_CV3_MAE'],
                           agg_metrics_general.loc[var, 'After_CV3_MAPE'] / 100,
                           agg_metrics_general.loc[var, 'After_CV3_Bias']]
        after_cv5_values = [agg_metrics_general.loc[var, 'After_CV5_RMSE'],
                           agg_metrics_general.loc[var, 'After_CV5_MAE'],
                           agg_metrics_general.loc[var, 'After_CV5_MAPE'] / 100,
                           agg_metrics_general.loc[var, 'After_CV5_Bias']]
        bars1 = axes[i].bar(x + 0 * (bar_width + 0.01), before_values, bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
        bars2 = axes[i].bar(x + 1 * (bar_width + 0.01), after_cv3_values, bar_width, label='After DA CV3', color=colors['after_cv3'], alpha=0.7, edgecolor='black')
        bars3 = axes[i].bar(x + 2 * (bar_width + 0.01), after_cv5_values, bar_width, label='After DA CV5', color=colors['after_cv5'], alpha=0.7, edgecolor='black')
        # Add text to bars
        for bar, val in zip(bars1, before_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        for bar, val in zip(bars2, after_cv3_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        for bar, val in zip(bars3, after_cv5_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        axes[i].set_xticks(x + (2 * (bar_width + 0.01)) / 2)
        axes[i].set_xticklabels(['RMSE', 'MAE', 'SMAPE/100', 'Bias'], rotation=0, fontsize=label_fontsize)
        axes[i].set_title(f'{var}', fontsize=label_fontsize)
        axes[i].set_ylabel('Metric Value', fontsize=label_fontsize)
        axes[i].tick_params(axis='both', length=4, width=0.5)
        axes[i].spines['top'].set_visible(False)
        axes[i].spines['right'].set_visible(False)
        axes[i].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(met_dir, 'overall_met_metrics_general.png'), dpi=300, bbox_inches='tight')
plt.close()
# Plot for NOAA ISD Stations
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 12), sharex=False)
fig.suptitle('Overall Meteorological Metrics (Mean Across NOAA ISD Stations)', fontsize=12)
for i, var in enumerate(variables_met):
    if var in agg_metrics_noaa.index:
        before_values = [agg_metrics_noaa.loc[var, 'Before_RMSE'],
                        agg_metrics_noaa.loc[var, 'Before_MAE'],
                        agg_metrics_noaa.loc[var, 'Before_MAPE'] / 100,
                        agg_metrics_noaa.loc[var, 'Before_Bias']]
        after_cv3_values = [agg_metrics_noaa.loc[var, 'After_CV3_RMSE'],
                           agg_metrics_noaa.loc[var, 'After_CV3_MAE'],
                           agg_metrics_noaa.loc[var, 'After_CV3_MAPE'] / 100,
                           agg_metrics_noaa.loc[var, 'After_CV3_Bias']]
        after_cv5_values = [agg_metrics_noaa.loc[var, 'After_CV5_RMSE'],
                           agg_metrics_noaa.loc[var, 'After_CV5_MAE'],
                           agg_metrics_noaa.loc[var, 'After_CV5_MAPE'] / 100,
                           agg_metrics_noaa.loc[var, 'After_CV5_Bias']]
        bars1 = axes[i].bar(x + 0 * (bar_width + 0.01), before_values, bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
        bars2 = axes[i].bar(x + 1 * (bar_width + 0.01), after_cv3_values, bar_width, label='After DA CV3', color=colors['after_cv3'], alpha=0.7, edgecolor='black')
        bars3 = axes[i].bar(x + 2 * (bar_width + 0.01), after_cv5_values, bar_width, label='After DA CV5', color=colors['after_cv5'], alpha=0.7, edgecolor='black')
        # Add text to bars
        for bar, val in zip(bars1, before_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        for bar, val in zip(bars2, after_cv3_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        for bar, val in zip(bars3, after_cv5_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        axes[i].set_xticks(x + (2 * (bar_width + 0.01)) / 2)
        axes[i].set_xticklabels(['RMSE', 'MAE', 'SMAPE/100', 'Bias'], rotation=0, fontsize=label_fontsize)
        axes[i].set_title(f'{var}', fontsize=label_fontsize)
        axes[i].set_ylabel('Metric Value', fontsize=label_fontsize)
        axes[i].tick_params(axis='both', length=4, width=0.5)
        axes[i].spines['top'].set_visible(False)
        axes[i].spines['right'].set_visible(False)
        axes[i].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(met_dir, 'overall_met_metrics_noaa.png'), dpi=300, bbox_inches='tight')
plt.close()
# ------------------------------------------------------------------------
# 9) ZTD DATA: Compute Overall Metrics
# ------------------------------------------------------------------------
overall_metrics_ztd = []
for station in ztd_station_names:
    df_ztd_obs = read_ztd_data(ztd_file_observed, station, is_observed=True)
    df_ztd_before = read_ztd_data(ztd_file_before_DA, station, is_observed=False)
    df_ztd_after_cv3 = read_ztd_data(ztd_file_after_DA_cv3, station, is_observed=False)
    df_ztd_after_cv5 = read_ztd_data(ztd_file_after_DA_cv5, station, is_observed=False)
    if df_ztd_obs is None or df_ztd_before is None or df_ztd_after_cv3 is None or df_ztd_after_cv5 is None:
        continue
    df_merged_before_ztd = pd.merge(df_ztd_before, df_ztd_obs, on='UTC_Datetime', how='inner')
    df_merged_after_cv3_ztd = pd.merge(df_ztd_after_cv3, df_ztd_obs, on='UTC_Datetime', how='inner')
    df_merged_after_cv5_ztd = pd.merge(df_ztd_after_cv5, df_ztd_obs, on='UTC_Datetime', how='inner')
    if df_merged_before_ztd.empty or df_merged_after_cv3_ztd.empty or df_merged_after_cv5_ztd.empty:
        continue
    sim_col, obs_col = 'Sim_ZTD(m)', 'Obs_ZTD(m)'
    rmse_b, mae_b, mape_b, bias_b = compute_metrics(df_merged_before_ztd, sim_col, obs_col)
    rmse_a_cv3, mae_a_cv3, mape_a_cv3, bias_a_cv3 = compute_metrics(df_merged_after_cv3_ztd, sim_col, obs_col)
    rmse_a_cv5, mae_a_cv5, mape_a_cv5, bias_a_cv5 = compute_metrics(df_merged_after_cv5_ztd, sim_col, obs_col)
    overall_metrics_ztd.append({
        'Station': station,
        'Before_RMSE': rmse_b, 'Before_MAE': mae_b, 'Before_MAPE': mape_b, 'Before_Bias': bias_b,
        'After_CV3_RMSE': rmse_a_cv3, 'After_CV3_MAE': mae_a_cv3, 'After_CV3_MAPE': mape_a_cv3, 'After_CV3_Bias': bias_a_cv3,
        'After_CV5_RMSE': rmse_a_cv5, 'After_CV5_MAE': mae_a_cv5, 'After_CV5_MAPE': mape_a_cv5, 'After_CV5_Bias': bias_a_cv5
    })
df_overall_ztd = pd.DataFrame(overall_metrics_ztd)
mean_ztd = df_overall_ztd.mean(numeric_only=True)
labels = ['RMSE', 'MAE', 'SMAPE', 'Bias']
x = np.arange(len(labels)) * 0.6 # Adjusted spacing to match reference script
fig, ax = plt.subplots(figsize=(10, 6))
bars1 = ax.bar(x + 0 * (bar_width + 0.01),
               [mean_ztd['Before_RMSE'], mean_ztd['Before_MAE'], mean_ztd['Before_MAPE']/100, mean_ztd['Before_Bias']],
               bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
bars2 = ax.bar(x + 1 * (bar_width + 0.01),
               [mean_ztd['After_CV3_RMSE'], mean_ztd['After_CV3_MAE'], mean_ztd['After_CV3_MAPE']/100, mean_ztd['After_CV3_Bias']],
               bar_width, label='After DA CV3', color=colors['after_cv3'], alpha=0.7, edgecolor='black')
bars3 = ax.bar(x + 2 * (bar_width + 0.01),
               [mean_ztd['After_CV5_RMSE'], mean_ztd['After_CV5_MAE'], mean_ztd['After_CV5_MAPE']/100, mean_ztd['After_CV5_Bias']],
               bar_width, label='After DA CV5', color=colors['after_cv5'], alpha=0.7, edgecolor='black')
# Add text to bars
for bar, val in zip(bars1, [mean_ztd['Before_RMSE'], mean_ztd['Before_MAE'], mean_ztd['Before_MAPE']/100, mean_ztd['Before_Bias']]):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
for bar, val in zip(bars2, [mean_ztd['After_CV3_RMSE'], mean_ztd['After_CV3_MAE'], mean_ztd['After_CV3_MAPE']/100, mean_ztd['After_CV3_Bias']]):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
for bar, val in zip(bars3, [mean_ztd['After_CV5_RMSE'], mean_ztd['After_CV5_MAE'], mean_ztd['After_CV5_MAPE']/100, mean_ztd['After_CV5_Bias']]):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
ax.set_xticks(x + (2 * (bar_width + 0.01)) / 2)
ax.set_xticklabels(['RMSE', 'MAE', 'SMAPE/100', 'Bias'], rotation=0, fontsize=label_fontsize)
ax.set_ylabel('Metric Value', fontsize=label_fontsize)
ax.set_title('Overall ZTD Metrics (Mean Across Stations)', fontsize=label_fontsize)
ax.tick_params(axis='both', length=4, width=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(ztd_dir, 'overall_ztd_metrics.png'), dpi=300, bbox_inches='tight')
plt.close()
# ------------------------------------------------------------------------
# 9) MET DATA: Compute and Plot POD and FAR for Precipitation
# ------------------------------------------------------------------------
# Calculate mean POD and FAR across all stations
mean_pod_before = np.nanmean([p[0] for p in precip_pod_far['before']])
mean_far_before = np.nanmean([p[1] for p in precip_pod_far['before']])
mean_pod_cv3 = np.nanmean([p[0] for p in precip_pod_far['after_cv3']])
mean_far_cv3 = np.nanmean([p[1] for p in precip_pod_far['after_cv3']])
mean_pod_cv5 = np.nanmean([p[0] for p in precip_pod_far['after_cv5']])
mean_far_cv5 = np.nanmean([p[1] for p in precip_pod_far['after_cv5']])
# Plot POD and FAR
fig_pod_far, ax_pod_far = plt.subplots(1, 1, figsize=(6, 6))
metrics_podfar = ['POD', 'FAR']
x_podfar = np.arange(len(metrics_podfar)) * 0.6
podfar_values_before = [mean_pod_before, mean_far_before]
podfar_values_cv3 = [mean_pod_cv3, mean_far_cv3]
podfar_values_cv5 = [mean_pod_cv5, mean_far_cv5]
bars1 = ax_pod_far.bar(x_podfar + 0 * (bar_width + 0.01), podfar_values_before, bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
bars2 = ax_pod_far.bar(x_podfar + 1 * (bar_width + 0.01), podfar_values_cv3, bar_width, label='After DA CV3', color=colors['after_cv3'], alpha=0.7, edgecolor='black')
bars3 = ax_pod_far.bar(x_podfar + 2 * (bar_width + 0.01), podfar_values_cv5, bar_width, label='After DA CV5', color=colors['after_cv5'], alpha=0.7, edgecolor='black')
# Add text to bars
for bar, val in zip(bars1, podfar_values_before):
    if not pd.isna(val):
        ax_pod_far.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
for bar, val in zip(bars2, podfar_values_cv3):
    if not pd.isna(val):
        ax_pod_far.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
for bar, val in zip(bars3, podfar_values_cv5):
    if not pd.isna(val):
        ax_pod_far.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
ax_pod_far.set_ylabel('Value', fontsize=label_fontsize)
ax_pod_far.set_xticks(x_podfar + (2 * (bar_width + 0.01)) / 2)
ax_pod_far.set_xticklabels(metrics_podfar, rotation=0, fontsize=label_fontsize)
ax_pod_far.tick_params(axis='both', length=4, width=0.5)
ax_pod_far.spines['top'].set_visible(False)
ax_pod_far.spines['right'].set_visible(False)
ax_pod_far.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(met_dir, 'precipitation_pod_far.png'), dpi=300, bbox_inches='tight')
plt.close()
# ------------------------------------------------------------------------
# 10) Compute and Plot Improvements
# ------------------------------------------------------------------------
agg_metrics_all = df_overall_met.groupby('Variable').mean(numeric_only=True)
def calc_improv(before, after, is_bias=False, is_pod=False, is_far=False):
    if pd.isna(before) or pd.isna(after) or before == 0:
        return np.nan
    if is_bias:
        return ((abs(before) - abs(after)) / abs(before)) * 100
    elif is_pod:
        return ((after - before) / before) * 100  # Higher better
    elif is_far:
        return ((before - after) / before) * 100  # Lower better
    else:
        return ((before - after) / before) * 100  # Lower better
# Precipitation improvements
precip_before = agg_metrics_all.loc['Precipitation (mm)', ['Before_RMSE', 'Before_MAE', 'Before_MAPE', 'Before_Bias']]
precip_cv3 = agg_metrics_all.loc['Precipitation (mm)', ['After_CV3_RMSE', 'After_CV3_MAE', 'After_CV3_MAPE', 'After_CV3_Bias']]
precip_cv5 = agg_metrics_all.loc['Precipitation (mm)', ['After_CV5_RMSE', 'After_CV5_MAE', 'After_CV5_MAPE', 'After_CV5_Bias']]
improv_cv3_precip = [calc_improv(precip_before['Before_RMSE'], precip_cv3['After_CV3_RMSE']),
                     calc_improv(precip_before['Before_MAE'], precip_cv3['After_CV3_MAE']),
                     calc_improv(precip_before['Before_MAPE'], precip_cv3['After_CV3_MAPE']),
                     calc_improv(precip_before['Before_Bias'], precip_cv3['After_CV3_Bias'], is_bias=True),
                     calc_improv(mean_pod_before, mean_pod_cv3, is_pod=True),
                     calc_improv(mean_far_before, mean_far_cv3, is_far=True)]
improv_cv5_precip = [calc_improv(precip_before['Before_RMSE'], precip_cv5['After_CV5_RMSE']),
                     calc_improv(precip_before['Before_MAE'], precip_cv5['After_CV5_MAE']),
                     calc_improv(precip_before['Before_MAPE'], precip_cv5['After_CV5_MAPE']),
                     calc_improv(precip_before['Before_Bias'], precip_cv5['After_CV5_Bias'], is_bias=True),
                     calc_improv(mean_pod_before, mean_pod_cv5, is_pod=True),
                     calc_improv(mean_far_before, mean_far_cv5, is_far=True)]
# Temperature improvements
temp_before = agg_metrics_all.loc['Temperature (°C)', ['Before_RMSE', 'Before_MAE', 'Before_MAPE', 'Before_Bias']]
temp_cv3 = agg_metrics_all.loc['Temperature (°C)', ['After_CV3_RMSE', 'After_CV3_MAE', 'After_CV3_MAPE', 'After_CV3_Bias']]
temp_cv5 = agg_metrics_all.loc['Temperature (°C)', ['After_CV5_RMSE', 'After_CV5_MAE', 'After_CV5_MAPE', 'After_CV5_Bias']]
improv_cv3_temp = [calc_improv(temp_before['Before_RMSE'], temp_cv3['After_CV3_RMSE']),
                   calc_improv(temp_before['Before_MAE'], temp_cv3['After_CV3_MAE']),
                   calc_improv(temp_before['Before_MAPE'], temp_cv3['After_CV3_MAPE']),
                   calc_improv(temp_before['Before_Bias'], temp_cv3['After_CV3_Bias'], is_bias=True)]
improv_cv5_temp = [calc_improv(temp_before['Before_RMSE'], temp_cv5['After_CV5_RMSE']),
                   calc_improv(temp_before['Before_MAE'], temp_cv5['After_CV5_MAE']),
                   calc_improv(temp_before['Before_MAPE'], temp_cv5['After_CV5_MAPE']),
                   calc_improv(temp_before['Before_Bias'], temp_cv5['After_CV5_Bias'], is_bias=True)]
# Plot 3: Improvements
fig3, (ax4, ax5) = plt.subplots(2, 1, figsize=(10, 10))
fig3.subplots_adjust(hspace=0.3)
# Precipitation Improvements
metrics_improv = metrics + ['POD', 'FAR']
x = np.arange(len(metrics_improv)) * 0.2  # Reduced spacing between metric groups
bar_width = 0.05
bars_cv3 = ax4.bar(x, improv_cv3_precip, bar_width, label='CV3', color=colors['after_cv3'], edgecolor='black')
bars_cv5 = ax4.bar(x + bar_width, improv_cv5_precip, bar_width, label='CV5', color=colors['after_cv5'], edgecolor='black')
ax4.axhline(0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Black line at y=0
for bar, val in zip(bars_cv3, improv_cv3_precip):
    if np.isfinite(val):
        label = f'{val:+.1f}%' if val >= 0 else f'{val:.1f}%'
        ax4.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)
for bar, val in zip(bars_cv5, improv_cv5_precip):
    if np.isfinite(val):
        label = f'{val:+.1f}%' if val >= 0 else f'{val:.1f}%'
        ax4.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)
ax4.set_xticks(x + bar_width/2)
ax4.set_xticklabels(metrics_improv)
ax4.set_ylabel('Precip Improvement (%)')
ax4.legend()
# Compute y-limits for precipitation
precip_vals = [v for v in improv_cv3_precip + improv_cv5_precip if np.isfinite(v)]
y_min_precip = min(precip_vals, default=-10) - 10
y_max_precip = max(precip_vals, default=10) + 10
ax4.set_ylim(y_min_precip, y_max_precip)  # Ensure y=0 is visible
# Temperature Improvements
metrics_improv_temp = metrics
x = np.arange(len(metrics_improv_temp)) * 0.2  # Reduced spacing between metric groups
bars_cv3 = ax5.bar(x, improv_cv3_temp, bar_width, label='CV3', color=colors['after_cv3'], edgecolor='black')
bars_cv5 = ax5.bar(x + bar_width, improv_cv5_temp, bar_width, label='CV5', color=colors['after_cv5'], edgecolor='black')
ax5.axhline(0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Black line at y=0
for bar, val in zip(bars_cv3, improv_cv3_temp):
    if np.isfinite(val):
        label = f'{val:+.1f}%' if val >= 0 else f'{val:.1f}%'
        ax5.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)
for bar, val in zip(bars_cv5, improv_cv5_temp):
    if np.isfinite(val):
        label = f'{val:+.1f}%' if val >= 0 else f'{val:.1f}%'
        ax5.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)
ax5.set_xticks(x + bar_width/2)
ax5.set_xticklabels(metrics_improv_temp)
ax5.set_ylabel('Temp Improvement (%)')
ax5.legend()
# Compute y-limits for temperature
temp_vals = [v for v in improv_cv3_temp + improv_cv5_temp if np.isfinite(v)]
y_min_temp = min(temp_vals, default=-10) - 10
y_max_temp = max(temp_vals, default=10) + 10
ax5.set_ylim(y_min_temp, y_max_temp)  # Ensure y=0 is visible
plt.tight_layout()
output_file = os.path.join(met_dir, "improvement_comparison.png")
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"Saved improvement plot to: {output_file}")
plt.close(fig3)