#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to compare GFS vs ERA5 for No DA and After DA scenarios.
Computes and plots meteorological and ZTD metrics with improvement percentages.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
import seaborn as sns
import os
import warnings
warnings.filterwarnings("ignore")

# ------------------------------------------------------------------------
# Setup
# ------------------------------------------------------------------------
plt.style.use('seaborn-white')
sns.set_context("paper", font_scale=1.4)

# Output directory
output_dir = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/GFS_vs_ERA5_vs_RADAR_vs_Observed"
os.makedirs(output_dir, exist_ok=True)

# Colors - matching wrf_vs_radar_stats_computation.py
colors = {
    'observed': '#ca252a',      # dark red
    'radar': 'black',           # Black
    'era5_after': '#4366f5',    # Dark Blue
    'era5_no_da': '#5a5a5a',    # Grey
    'gfs_after': 'green',       # Dark Green
    'gfs_no_da': '#717171',     # Grey
}


bar_width = 0.10  # Matching original script
label_fontsize = 10  # Match reference script
title_fontsize = 12

# ------------------------------------------------------------------------
# File Paths
# ------------------------------------------------------------------------
# Observed data
file_observed_general = '/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Stations_and_Observations/Luxembourg_stations_for_validation/2021_Event/stations_6hr_cumulative.xlsx'
file_observed_noaa = '/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Stations_and_Observations/Luxembourg_stations_for_validation/2021_Event/Stations_other_than_lux/station_weather_data_june_july_2021_6hr.xlsx'
ztd_file_observed = '/Users/haseeb.rehman/WRF/WRFDA/DAT_DIR/ztd_data_June_july_2021/for_validation/ztd_data.xlsx'

# GFS data (cv5)
gfs_before_DA = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/Before_DA/general_station_data_before.xlsx'
gfs_after_DA = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/After_DA/general_station_data_after.xlsx'
gfs_ztd_before_DA = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/Before_DA/ztd_station_data_before.xlsx'
gfs_ztd_after_DA = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/After_DA/ztd_station_data_after.xlsx'

# ERA5 data
era5_before_DA = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/Before_DA/general_station_data_before.xlsx'
era5_after_DA = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/After_DA/general_station_data_after.xlsx'
era5_ztd_before_DA = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/Before_DA/ztd_station_data_before.xlsx'
era5_ztd_after_DA = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/After_DA/ztd_station_data_after.xlsx'

# ------------------------------------------------------------------------
# Helper Functions
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

def read_ztd_data(file_path, station, is_observed=False):
    try:
        df = pd.read_excel(file_path, sheet_name=station)
    except ValueError:
        return None
    if is_observed:
        df.rename(columns={'UTC_Datetime': 'UTC_Datetime', 'ZTD (m)': 'Obs_ZTD(m)'}, inplace=True)
    else:
        df.rename(columns={'UTC_Datetime': 'UTC_Datetime', 'ZTD (m)': 'Sim_ZTD(m)'}, inplace=True)
    df['UTC_Datetime'] = pd.to_datetime(df['UTC_Datetime'], errors='coerce')
    return df

def compute_metrics(df, sim_col, obs_col):
    valid_df = df[[sim_col, obs_col]].dropna()
    if valid_df.empty:
        return np.nan, np.nan, np.nan, np.nan
    rmse = np.sqrt(mean_squared_error(valid_df[sim_col], valid_df[obs_col]))
    mae = np.mean(np.abs(valid_df[sim_col] - valid_df[obs_col]))
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

# ------------------------------------------------------------------------
# Read Station Names
# ------------------------------------------------------------------------
station_names_general = pd.ExcelFile(file_observed_general).sheet_names
station_names_noaa = pd.ExcelFile(file_observed_noaa).sheet_names
ztd_station_names = pd.ExcelFile(ztd_file_observed).sheet_names

# ------------------------------------------------------------------------
# Process Meteorological Data
# ------------------------------------------------------------------------
variables = [
    ('Sim_Precip(mm)', 'Obs_Precip(mm)', 'Precipitation (mm)'),
    ('Sim_T2(C)', 'Obs_T2(C)', 'Temperature (°C)'),
    ('Sim_RH(%)', 'Obs_RH(%)', 'Relative Humidity (%)')
]

overall_metrics_met = []
precip_pod_far = {'gfs_before': [], 'gfs_after': [], 'era5_before': [], 'era5_after': []}

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
    
    # Read all datasets
    df_gfs_before = read_station_data(gfs_before_DA, station, is_observed=False)
    df_gfs_after = read_station_data(gfs_after_DA, station, is_observed=False)
    df_era5_before = read_station_data(era5_before_DA, station, is_observed=False)
    df_era5_after = read_station_data(era5_after_DA, station, is_observed=False)
    
    if any(df is None for df in [df_gfs_before, df_gfs_after, df_era5_before, df_era5_after]):
        continue
    
    # Merge with observations
    df_merged_gfs_before = pd.merge(df_gfs_before, df_obs, on='UTC_Datetime', how='inner')
    df_merged_gfs_after = pd.merge(df_gfs_after, df_obs, on='UTC_Datetime', how='inner')
    df_merged_era5_before = pd.merge(df_era5_before, df_obs, on='UTC_Datetime', how='inner')
    df_merged_era5_after = pd.merge(df_era5_after, df_obs, on='UTC_Datetime', how='inner')
    
    if any(df.empty for df in [df_merged_gfs_before, df_merged_gfs_after, df_merged_era5_before, df_merged_era5_after]):
        continue
    
    for sim_col, obs_col, var_name in variables:
        # Compute metrics for all cases
        rmse_gfs_b, mae_gfs_b, mape_gfs_b, bias_gfs_b = compute_metrics(df_merged_gfs_before, sim_col, obs_col)
        rmse_gfs_a, mae_gfs_a, mape_gfs_a, bias_gfs_a = compute_metrics(df_merged_gfs_after, sim_col, obs_col)
        rmse_era5_b, mae_era5_b, mape_era5_b, bias_era5_b = compute_metrics(df_merged_era5_before, sim_col, obs_col)
        rmse_era5_a, mae_era5_a, mape_era5_a, bias_era5_a = compute_metrics(df_merged_era5_after, sim_col, obs_col)
        
        overall_metrics_met.append({
            'Station': station,
            'Variable': var_name,
            'GFS_Before_RMSE': rmse_gfs_b, 'GFS_Before_MAE': mae_gfs_b, 'GFS_Before_MAPE': mape_gfs_b, 'GFS_Before_Bias': bias_gfs_b,
            'GFS_After_RMSE': rmse_gfs_a, 'GFS_After_MAE': mae_gfs_a, 'GFS_After_MAPE': mape_gfs_a, 'GFS_After_Bias': bias_gfs_a,
            'ERA5_Before_RMSE': rmse_era5_b, 'ERA5_Before_MAE': mae_era5_b, 'ERA5_Before_MAPE': mape_era5_b, 'ERA5_Before_Bias': bias_era5_b,
            'ERA5_After_RMSE': rmse_era5_a, 'ERA5_After_MAE': mae_era5_a, 'ERA5_After_MAPE': mape_era5_a, 'ERA5_After_Bias': bias_era5_a,
            'Source': 'NOAA ISD' if station in station_names_noaa else 'General'
        })
        
        # POD/FAR for precipitation
        if var_name == 'Precipitation (mm)':
            pod_gfs_b, far_gfs_b = compute_pod_far(df_merged_gfs_before, sim_col, obs_col)
            pod_gfs_a, far_gfs_a = compute_pod_far(df_merged_gfs_after, sim_col, obs_col)
            pod_era5_b, far_era5_b = compute_pod_far(df_merged_era5_before, sim_col, obs_col)
            pod_era5_a, far_era5_a = compute_pod_far(df_merged_era5_after, sim_col, obs_col)
            
            precip_pod_far['gfs_before'].append((pod_gfs_b, far_gfs_b))
            precip_pod_far['gfs_after'].append((pod_gfs_a, far_gfs_a))
            precip_pod_far['era5_before'].append((pod_era5_b, far_era5_b))
            precip_pod_far['era5_after'].append((pod_era5_a, far_era5_a))

df_overall_met = pd.DataFrame(overall_metrics_met)
agg_metrics_all = df_overall_met.groupby('Variable').mean(numeric_only=True)

print("Meteorological data processing complete!")

# ------------------------------------------------------------------------
# Process ZTD Data
# ------------------------------------------------------------------------
overall_metrics_ztd = []

for station in ztd_station_names:
    df_ztd_obs = read_ztd_data(ztd_file_observed, station, is_observed=True)
    df_ztd_gfs_before = read_ztd_data(gfs_ztd_before_DA, station, is_observed=False)
    df_ztd_gfs_after = read_ztd_data(gfs_ztd_after_DA, station, is_observed=False)
    df_ztd_era5_before = read_ztd_data(era5_ztd_before_DA, station, is_observed=False)
    df_ztd_era5_after = read_ztd_data(era5_ztd_after_DA, station, is_observed=False)
    
    if any(df is None for df in [df_ztd_obs, df_ztd_gfs_before, df_ztd_gfs_after, df_ztd_era5_before, df_ztd_era5_after]):
        continue
    
    df_merged_gfs_before_ztd = pd.merge(df_ztd_gfs_before, df_ztd_obs, on='UTC_Datetime', how='inner')
    df_merged_gfs_after_ztd = pd.merge(df_ztd_gfs_after, df_ztd_obs, on='UTC_Datetime', how='inner')
    df_merged_era5_before_ztd = pd.merge(df_ztd_era5_before, df_ztd_obs, on='UTC_Datetime', how='inner')
    df_merged_era5_after_ztd = pd.merge(df_ztd_era5_after, df_ztd_obs, on='UTC_Datetime', how='inner')
    
    if any(df.empty for df in [df_merged_gfs_before_ztd, df_merged_gfs_after_ztd, df_merged_era5_before_ztd, df_merged_era5_after_ztd]):
        continue
    
    sim_col, obs_col = 'Sim_ZTD(m)', 'Obs_ZTD(m)'
    
    rmse_gfs_b, mae_gfs_b, mape_gfs_b, bias_gfs_b = compute_metrics(df_merged_gfs_before_ztd, sim_col, obs_col)
    rmse_gfs_a, mae_gfs_a, mape_gfs_a, bias_gfs_a = compute_metrics(df_merged_gfs_after_ztd, sim_col, obs_col)
    rmse_era5_b, mae_era5_b, mape_era5_b, bias_era5_b = compute_metrics(df_merged_era5_before_ztd, sim_col, obs_col)
    rmse_era5_a, mae_era5_a, mape_era5_a, bias_era5_a = compute_metrics(df_merged_era5_after_ztd, sim_col, obs_col)
    
    overall_metrics_ztd.append({
        'Station': station,
        'GFS_Before_RMSE': rmse_gfs_b, 'GFS_Before_MAE': mae_gfs_b, 'GFS_Before_MAPE': mape_gfs_b, 'GFS_Before_Bias': bias_gfs_b,
        'GFS_After_RMSE': rmse_gfs_a, 'GFS_After_MAE': mae_gfs_a, 'GFS_After_MAPE': mape_gfs_a, 'GFS_After_Bias': bias_gfs_a,
        'ERA5_Before_RMSE': rmse_era5_b, 'ERA5_Before_MAE': mae_era5_b, 'ERA5_Before_MAPE': mape_era5_b, 'ERA5_Before_Bias': bias_era5_b,
        'ERA5_After_RMSE': rmse_era5_a, 'ERA5_After_MAE': mae_era5_a, 'ERA5_After_MAPE': mape_era5_a, 'ERA5_After_Bias': bias_era5_a
    })

df_overall_ztd = pd.DataFrame(overall_metrics_ztd)
mean_ztd = df_overall_ztd.mean(numeric_only=True)

print("ZTD data processing complete!")

# Calculate POD/FAR means for improvement calculation
mean_pod_gfs_before = np.nanmean([p[0] for p in precip_pod_far['gfs_before']])
mean_far_gfs_before = np.nanmean([p[1] for p in precip_pod_far['gfs_before']])
mean_pod_gfs_after = np.nanmean([p[0] for p in precip_pod_far['gfs_after']])
mean_far_gfs_after = np.nanmean([p[1] for p in precip_pod_far['gfs_after']])
mean_pod_era5_before = np.nanmean([p[0] for p in precip_pod_far['era5_before']])
mean_far_era5_before = np.nanmean([p[1] for p in precip_pod_far['era5_before']])
mean_pod_era5_after = np.nanmean([p[0] for p in precip_pod_far['era5_after']])
mean_far_era5_after = np.nanmean([p[1] for p in precip_pod_far['era5_after']])

# ------------------------------------------------------------------------
# Plot 1: Meteorological Metrics Comparison
# ------------------------------------------------------------------------
variables_met = ['Precipitation (mm)', 'Temperature (°C)', 'Relative Humidity (%)']
metrics = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']

fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(12, 14))
fig.suptitle('GFS vs ERA5: Meteorological Metrics Comparison', fontsize=title_fontsize, fontweight='bold')

x = np.arange(len(metrics)) * 0.6

for i, var in enumerate(variables_met):
    if var in agg_metrics_all.index:
        gfs_before_values = [agg_metrics_all.loc[var, 'GFS_Before_RMSE'],
                            agg_metrics_all.loc[var, 'GFS_Before_MAE'],
                            agg_metrics_all.loc[var, 'GFS_Before_MAPE'] / 100,
                            agg_metrics_all.loc[var, 'GFS_Before_Bias']]
        gfs_after_values = [agg_metrics_all.loc[var, 'GFS_After_RMSE'],
                           agg_metrics_all.loc[var, 'GFS_After_MAE'],
                           agg_metrics_all.loc[var, 'GFS_After_MAPE'] / 100,
                           agg_metrics_all.loc[var, 'GFS_After_Bias']]
        era5_before_values = [agg_metrics_all.loc[var, 'ERA5_Before_RMSE'],
                             agg_metrics_all.loc[var, 'ERA5_Before_MAE'],
                             agg_metrics_all.loc[var, 'ERA5_Before_MAPE'] / 100,
                             agg_metrics_all.loc[var, 'ERA5_Before_Bias']]
        era5_after_values = [agg_metrics_all.loc[var, 'ERA5_After_RMSE'],
                            agg_metrics_all.loc[var, 'ERA5_After_MAE'],
                             agg_metrics_all.loc[var, 'ERA5_After_MAPE'] / 100,
                             agg_metrics_all.loc[var, 'ERA5_After_Bias']]
        
        # Bar positioning - EXACTLY like reference script
        bars1 = axes[i].bar(x + 0 * (bar_width + 0.01), gfs_before_values, bar_width, label='GFS No DA', color=colors['gfs_no_da'], alpha=0.7, edgecolor='black')
        bars2 = axes[i].bar(x + 1 * (bar_width + 0.01), gfs_after_values, bar_width, label='GFS After DA', color=colors['gfs_after'], alpha=0.7, edgecolor='black')
        bars3 = axes[i].bar(x + 2 * (bar_width + 0.01), era5_before_values, bar_width, label='ERA5 No DA', color=colors['era5_no_da'], alpha=0.7, edgecolor='black')
        bars4 = axes[i].bar(x + 3 * (bar_width + 0.01), era5_after_values, bar_width, label='ERA5 After DA', color=colors['era5_after'], alpha=0.7, edgecolor='black')
        
        # Add text inside bars - match reference
        for bar, val in zip(bars1, gfs_before_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        for bar, val in zip(bars2, gfs_after_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        for bar, val in zip(bars3, era5_before_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        for bar, val in zip(bars4, era5_after_values):
            if not pd.isna(val):
                axes[i].text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
        
        # X-tick centering for 4 bars - match reference style
        axes[i].set_xticks(x + (3 * (bar_width + 0.01)) / 2)
        axes[i].set_xticklabels(metrics, fontsize=label_fontsize)
        axes[i].set_title(f'{var}', fontsize=label_fontsize, fontweight='bold')
        axes[i].set_ylabel('Metric Value', fontsize=label_fontsize)
        axes[i].tick_params(axis='both', labelsize=label_fontsize-1)
        axes[i].spines['top'].set_visible(False)
        axes[i].spines['right'].set_visible(False)
        axes[i].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=9, ncol=2)

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(os.path.join(output_dir, 'gfs_vs_era5_meteorological_metrics.png'), dpi=300, bbox_inches='tight')
plt.close()
print("Saved: gfs_vs_era5_meteorological_metrics.png")

# ------------------------------------------------------------------------
# Plot 2: ZTD Metrics Comparison
# ------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 6))
fig.suptitle('GFS vs ERA5: ZTD Metrics Comparison', fontsize=title_fontsize, fontweight='bold')

labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']
x = np.arange(len(labels)) * 0.6

gfs_before_ztd = [mean_ztd['GFS_Before_RMSE'], mean_ztd['GFS_Before_MAE'], mean_ztd['GFS_Before_MAPE']/100, mean_ztd['GFS_Before_Bias']]
gfs_after_ztd = [mean_ztd['GFS_After_RMSE'], mean_ztd['GFS_After_MAE'], mean_ztd['GFS_After_MAPE']/100, mean_ztd['GFS_After_Bias']]
era5_before_ztd = [mean_ztd['ERA5_Before_RMSE'], mean_ztd['ERA5_Before_MAE'], mean_ztd['ERA5_Before_MAPE']/100, mean_ztd['ERA5_Before_Bias']]
era5_after_ztd = [mean_ztd['ERA5_After_RMSE'], mean_ztd['ERA5_After_MAE'], mean_ztd['ERA5_After_MAPE']/100, mean_ztd['ERA5_After_Bias']]

# Group bars by data source: [GFS Before][GFS After] gap [ERA5 Before][ERA5 After]
gap = 0.15
bars1 = ax.bar(x - gap/2 - bar_width, gfs_before_ztd, bar_width, label='GFS No DA', color=colors['gfs_no_da'], alpha=0.7, edgecolor='black')
bars2 = ax.bar(x - gap/2, gfs_after_ztd, bar_width, label='GFS After DA', color=colors['gfs_after'], alpha=0.7, edgecolor='black')
bars3 = ax.bar(x + gap/2, era5_before_ztd, bar_width, label='ERA5 No DA', color=colors['era5_no_da'], alpha=0.7, edgecolor='black')
bars4 = ax.bar(x + gap/2 + bar_width, era5_after_ztd, bar_width, label='ERA5 After DA', color=colors['era5_after'], alpha=0.7, edgecolor='black')

# Add text inside bars
for bar, val in zip(bars1, gfs_before_ztd):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='white', fontsize=8, fontweight='bold')
for bar, val in zip(bars2, gfs_after_ztd):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
for bar, val in zip(bars3, era5_before_ztd):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='white', fontsize=8, fontweight='bold')
for bar, val in zip(bars4, era5_after_ztd):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=label_fontsize)
ax.set_ylabel('Metric Value', fontsize=label_fontsize)
ax.tick_params(axis='both', labelsize=label_fontsize-1)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=10, ncol=2)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(output_dir, 'gfs_vs_era5_ztd_metrics.png'), dpi=300, bbox_inches='tight')
plt.close()
print("Saved: gfs_vs_era5_ztd_metrics.png")

# ------------------------------------------------------------------------
# Plot 3: POD and FAR for Precipitation
# ------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(10, 6))
fig.suptitle('GFS vs ERA5: POD and FAR for Precipitation', fontsize=title_fontsize, fontweight='bold')

metrics_podfar = ['POD', 'FAR']
x_podfar = np.arange(len(metrics_podfar)) * 0.6

gfs_before_podfar = [mean_pod_gfs_before, mean_far_gfs_before]
gfs_after_podfar = [mean_pod_gfs_after, mean_far_gfs_after]
era5_before_podfar = [mean_pod_era5_before, mean_far_era5_before]
era5_after_podfar = [mean_pod_era5_after, mean_far_era5_after]

# Group bars by data source: [GFS Before][GFS After] gap [ERA5 Before][ERA5 After]
gap = 0.15
bars1 = ax.bar(x_podfar - gap/2 - bar_width, gfs_before_podfar, bar_width, label='GFS No DA', color=colors['gfs_no_da'], alpha=0.7, edgecolor='black')
bars2 = ax.bar(x_podfar - gap/2, gfs_after_podfar, bar_width, label='GFS After DA', color=colors['gfs_after'], alpha=0.7, edgecolor='black')
bars3 = ax.bar(x_podfar + gap/2, era5_before_podfar, bar_width, label='ERA5 No DA', color=colors['era5_no_da'], alpha=0.7, edgecolor='black')
bars4 = ax.bar(x_podfar + gap/2 + bar_width, era5_after_podfar, bar_width, label='ERA5 After DA', color=colors['era5_after'], alpha=0.7, edgecolor='black')

# Add text inside bars
for bar, val in zip(bars1, gfs_before_podfar):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='white', fontsize=8, fontweight='bold')
for bar, val in zip(bars2, gfs_after_podfar):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
for bar, val in zip(bars3, era5_before_podfar):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='white', fontsize=8, fontweight='bold')
for bar, val in zip(bars4, era5_after_podfar):
    if not pd.isna(val):
        ax.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)

ax.set_ylabel('Value', fontsize=label_fontsize)
ax.set_xticks(x_podfar)
ax.set_xticklabels(metrics_podfar, fontsize=label_fontsize)
ax.tick_params(axis='both', labelsize=label_fontsize-1)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=10, ncol=2)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(output_dir, 'gfs_vs_era5_pod_far.png'), dpi=300, bbox_inches='tight')
plt.close()
print("Saved: gfs_vs_era5_pod_far.png")

# ------------------------------------------------------------------------
# Plot 4: Time Series for Select Stations (2x2 Layout with Radar)
# ------------------------------------------------------------------------
# 8 stations for two 2x2 subplot layouts (matching wrf_vs_radar_stats_computation.py)
select_stations = ['Ettelbruck', 'Remerschen', 'Oberkorn', 'Bettendorf', 'Echternach', 'Hosingen', 'Mamer', 'Arsdorf']

# Date range for radar data
from datetime import datetime, timedelta
import matplotlib.dates as mdates

# Radar data configuration (from wrf_vs_radar_stats_computation.py)
radar_base_dir = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Radar_and_Weather/Belgium_Radar_data_2021"
radar_start_date = datetime(2021, 7, 11, 0)
radar_end_date = datetime(2021, 7, 18, 18)

# Station coordinates for radar extraction
met_stations = [
    ("Briedfeld", 50.12385, 6.06622), ("Echternach", 49.8031, 6.44337), ("Ettelbruck", 49.85172, 6.09754),
    ("Oberkorn", 49.5122, 5.9011), ("Remerschen", 49.491, 6.349), ("Findel", 49.63265182, 6.23292867),
    ("Roodt", 49.7945, 5.8202), ("Hosingen", 49.99314, 6.10147), ("Useldange", 49.76739, 5.96748),
    ("Mamer", 49.63353, 6.0193), ("Arsdorf", 49.85891, 5.84868), ("Asselborn", 50.09685689, 5.96960753),
    ("Grevenmacher", 49.68087, 6.43541), ("Schimpach", 50.0093, 5.8475), ("Waldbillig", 49.79806, 6.2773),
    ("Bettendorf", 49.8741, 6.2095), ("Fouhren", 49.91445, 6.19508), ("Beringen", 49.762, 6.11179),
    ("Dahl", 49.93595, 5.98093)
]
station_coords = {name: (lat, lon) for name, lat, lon in met_stations}

# Function to read radar data at a station coordinate
def read_radar_at_station(radar_base_dir, station_name, station_coords, start_date, end_date):
    """Read 6-hour aggregated radar data at a specific station location."""
    import h5py
    
    if station_name not in station_coords:
        return pd.DataFrame()
    
    lat, lon = station_coords[station_name]
    xsize, ysize = 700, 700
    
    # Approximate radar grid (Belgian Lambert to lat/lon)
    radar_lat_grid = np.linspace(48.5, 51.5, ysize)
    radar_lon_grid = np.linspace(2.5, 8.5, xsize)
    lat_idx = np.argmin(np.abs(radar_lat_grid - lat))
    lon_idx = np.argmin(np.abs(radar_lon_grid - lon))
    
    radar_data = []
    current_time = start_date
    
    while current_time <= end_date:
        if current_time.hour not in [0, 6, 12, 18]:
            current_time += timedelta(hours=6)
            continue
        
        # Aggregate 6 hourly files
        accum_value = 0.0
        file_count = 0
        agg_start = current_time - timedelta(hours=6)
        
        # Collect dates to check
        dates_to_check = set()
        check_time = agg_start
        while check_time <= current_time:
            dates_to_check.add(check_time.strftime("%Y/%m/%d"))
            check_time += timedelta(hours=1)
        
        for date_str in dates_to_check:
            radar_dir = os.path.join(radar_base_dir, date_str, "accum1h/hdf")
            if not os.path.exists(radar_dir):
                continue
            
            try:
                all_files = [f for f in os.listdir(radar_dir) if f.endswith('.accum1h.hdf')]
                for f in all_files:
                    file_timestamp = datetime.strptime(f[:14], '%Y%m%d%H%M%S')
                    if agg_start <= file_timestamp <= current_time:
                        file_path = os.path.join(radar_dir, f)
                        with h5py.File(file_path, 'r') as hdf:
                            data = hdf['dataset1']['data1']['data'][:].astype(float)
                            data = np.where(data < 0, 0, data)
                            # Apply scale factor if needed
                            if np.nanmax(data) > 1000:
                                data = data * 0.001
                            if 0 <= lat_idx < ysize and 0 <= lon_idx < xsize:
                                accum_value += data[lat_idx, lon_idx]
                                file_count += 1
            except Exception as e:
                continue
        
        if file_count > 0:
            radar_data.append({'UTC_Datetime': current_time, 'Radar_Precip': accum_value})
        
        current_time += timedelta(hours=6)
    
    return pd.DataFrame(radar_data)

# Function to create a single 2x2 figure for precipitation time series
def create_precip_ts_figure(stations_subset, figure_number):
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    axes = axes.flatten()
    
    legend_handles = []
    legend_labels = []
    
    for idx, station in enumerate(stations_subset):
        ax = axes[idx]
        
        try:
            # Read observed data
            if station in station_names_general:
                df_obs = read_station_data(file_observed_general, station, is_observed=True, is_noaa=False)
            elif station in station_names_noaa:
                df_obs = read_station_data(file_observed_noaa, station, is_observed=True, is_noaa=True)
            else:
                ax.set_visible(False)
                continue
            
            if df_obs is None:
                ax.set_visible(False)
                continue
            
            # Read WRF data
            df_gfs_before = read_station_data(gfs_before_DA, station, is_observed=False)
            df_gfs_after = read_station_data(gfs_after_DA, station, is_observed=False)
            df_era5_before = read_station_data(era5_before_DA, station, is_observed=False)
            df_era5_after = read_station_data(era5_after_DA, station, is_observed=False)
            
            if any(df is None for df in [df_gfs_before, df_gfs_after, df_era5_before, df_era5_after]):
                ax.set_visible(False)
                continue
            
            # Merge with observations
            df_merged_gfs_before = pd.merge(df_gfs_before, df_obs, on='UTC_Datetime', how='inner')
            df_merged_gfs_after = pd.merge(df_gfs_after, df_obs, on='UTC_Datetime', how='inner')
            df_merged_era5_before = pd.merge(df_era5_before, df_obs, on='UTC_Datetime', how='inner')
            df_merged_era5_after = pd.merge(df_era5_after, df_obs, on='UTC_Datetime', how='inner')
            
            # Read radar data at this station
            df_radar = read_radar_at_station(radar_base_dir, station, station_coords, radar_start_date, radar_end_date)
            
            # Build datasets list (matching wrf_vs_radar_stats_computation.py)
            datasets = []
            ts_colors_list = []
            ts_linestyles = []
            ts_markers = []
            ts_labels_list = []
            
            # GFS
            datasets.extend([
                (df_merged_gfs_before, 'Sim_Precip(mm)'),
                (df_merged_gfs_after, 'Sim_Precip(mm)')
            ])
            ts_colors_list.extend([colors['gfs_no_da'], colors['gfs_after']])
            ts_linestyles.extend(['-', '-'])
            ts_markers.extend(['o', 'o'])  # Circle for GFS
            ts_labels_list.extend(['GFS No DA', 'GFS After DA'])
            
            # ERA5
            datasets.extend([
                (df_merged_era5_before, 'Sim_Precip(mm)'),
                (df_merged_era5_after, 'Sim_Precip(mm)')
            ])
            ts_colors_list.extend([colors['era5_no_da'], colors['era5_after']])
            ts_linestyles.extend(['-', '-'])
            ts_markers.extend(['s', 's'])  # Square for ERA5
            ts_labels_list.extend(['ERA5 No DA', 'ERA5 After DA'])
            
            # Radar and Observed last
            datasets.extend([
                (df_radar, 'Radar_Precip'),
                (df_merged_gfs_before, 'Obs_Precip(mm)')
            ])
            ts_colors_list.extend([colors['radar'], colors['observed']])
            ts_linestyles.extend(['--', '-'])
            ts_markers.extend(['', '^'])  # No marker for radar, triangle for observed
            ts_labels_list.extend(['RADAR', 'Observed'])
            
            # Plot each dataset
            for (df_data, col), color, style, marker, label in zip(datasets, ts_colors_list, ts_linestyles, ts_markers, ts_labels_list):
                if df_data is not None and not df_data.empty and col in df_data.columns:
                    line, = ax.plot(df_data['UTC_Datetime'], df_data[col],
                           label=label, color=color, linestyle=style,
                           marker=marker, markersize=4,
                           alpha=0.8, linewidth=1.5)
                    if idx == 0:
                        legend_handles.append(line)
                        legend_labels.append(label)
            
            # Formatting (matching wrf_vs_radar_stats_computation.py)
            ax.set_title(f'Station: {station}', fontsize=label_fontsize, fontweight='bold')
            ax.set_ylabel('6-hr Precip (mm)', fontsize=label_fontsize)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(axis='both', alpha=0.3, linestyle='--')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            ax.tick_params(axis='both', labelsize=9)
            
        except Exception as e:
            import traceback
            print(f"Could not process station {station}: {e}")
            traceback.print_exc()
            ax.set_visible(False)
            continue
    
    # Add shared legend at the bottom (horizontal with box)
    fig.legend(legend_handles, legend_labels, 
               loc='lower center', 
               bbox_to_anchor=(0.5, 0.02),
               fontsize=11, 
               frameon=True, 
               edgecolor='black',
               fancybox=False,
               ncol=len(legend_labels))
    
    plt.tight_layout(rect=[0, 0.06, 1, 1])
    filename = f'gfs_vs_era5_precip_timeseries_{figure_number}.png'
    plt.savefig(os.path.join(output_dir, filename), dpi=600, bbox_inches='tight')
    plt.close()
    print(f"Saved: {filename} (2x2 layout, 600 DPI)")



# Create two figures with 4 stations each
print("\n" + "="*60)
print("Generating precipitation time series plots (2x2 layout with RADAR)...")
print("="*60)
create_precip_ts_figure(select_stations[:4], 1)
create_precip_ts_figure(select_stations[4:8], 2)

# ------------------------------------------------------------------------
# Plot 3: Improvement Comparison (Before to After)
# ------------------------------------------------------------------------
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
precip_gfs_before = agg_metrics_all.loc['Precipitation (mm)', ['GFS_Before_RMSE', 'GFS_Before_MAE', 'GFS_Before_MAPE', 'GFS_Before_Bias']]
precip_gfs_after = agg_metrics_all.loc['Precipitation (mm)', ['GFS_After_RMSE', 'GFS_After_MAE', 'GFS_After_MAPE', 'GFS_After_Bias']]
precip_era5_before = agg_metrics_all.loc['Precipitation (mm)', ['ERA5_Before_RMSE', 'ERA5_Before_MAE', 'ERA5_Before_MAPE', 'ERA5_Before_Bias']]
precip_era5_after = agg_metrics_all.loc['Precipitation (mm)', ['ERA5_After_RMSE', 'ERA5_After_MAE', 'ERA5_After_MAPE', 'ERA5_After_Bias']]

improv_gfs_precip = [
    calc_improv(precip_gfs_before['GFS_Before_RMSE'], precip_gfs_after['GFS_After_RMSE']),
    calc_improv(precip_gfs_before['GFS_Before_MAE'], precip_gfs_after['GFS_After_MAE']),
    calc_improv(precip_gfs_before['GFS_Before_MAPE'], precip_gfs_after['GFS_After_MAPE']),
    calc_improv(precip_gfs_before['GFS_Before_Bias'], precip_gfs_after['GFS_After_Bias'], is_bias=True),
    calc_improv(mean_pod_gfs_before, mean_pod_gfs_after, is_pod=True),
    calc_improv(mean_far_gfs_before, mean_far_gfs_after, is_far=True)
]

improv_era5_precip = [
    calc_improv(precip_era5_before['ERA5_Before_RMSE'], precip_era5_after['ERA5_After_RMSE']),
    calc_improv(precip_era5_before['ERA5_Before_MAE'], precip_era5_after['ERA5_After_MAE']),
    calc_improv(precip_era5_before['ERA5_Before_MAPE'], precip_era5_after['ERA5_After_MAPE']),
    calc_improv(precip_era5_before['ERA5_Before_Bias'], precip_era5_after['ERA5_After_Bias'], is_bias=True),
    calc_improv(mean_pod_era5_before, mean_pod_era5_after, is_pod=True),
    calc_improv(mean_far_era5_before, mean_far_era5_after, is_far=True)
]

# Temperature improvements
temp_gfs_before = agg_metrics_all.loc['Temperature (°C)', ['GFS_Before_RMSE', 'GFS_Before_MAE', 'GFS_Before_MAPE', 'GFS_Before_Bias']]
temp_gfs_after = agg_metrics_all.loc['Temperature (°C)', ['GFS_After_RMSE', 'GFS_After_MAE', 'GFS_After_MAPE', 'GFS_After_Bias']]
temp_era5_before = agg_metrics_all.loc['Temperature (°C)', ['ERA5_Before_RMSE', 'ERA5_Before_MAE', 'ERA5_Before_MAPE', 'ERA5_Before_Bias']]
temp_era5_after = agg_metrics_all.loc['Temperature (°C)', ['ERA5_After_RMSE', 'ERA5_After_MAE', 'ERA5_After_MAPE', 'ERA5_After_Bias']]

improv_gfs_temp = [
    calc_improv(temp_gfs_before['GFS_Before_RMSE'], temp_gfs_after['GFS_After_RMSE']),
    calc_improv(temp_gfs_before['GFS_Before_MAE'], temp_gfs_after['GFS_After_MAE']),
    calc_improv(temp_gfs_before['GFS_Before_MAPE'], temp_gfs_after['GFS_After_MAPE']),
    calc_improv(temp_gfs_before['GFS_Before_Bias'], temp_gfs_after['GFS_After_Bias'], is_bias=True)
]

improv_era5_temp = [
    calc_improv(temp_era5_before['ERA5_Before_RMSE'], temp_era5_after['ERA5_After_RMSE']),
    calc_improv(temp_era5_before['ERA5_Before_MAE'], temp_era5_after['ERA5_After_MAE']),
    calc_improv(temp_era5_before['ERA5_Before_MAPE'], temp_era5_after['ERA5_After_MAPE']),
    calc_improv(temp_era5_before['ERA5_Before_Bias'], temp_era5_after['ERA5_After_Bias'], is_bias=True)
]

# Plot improvements
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
fig.suptitle('GFS vs ERA5: Improvement from No DA to After DA', fontsize=title_fontsize, fontweight='bold')

# Precipitation
metrics_improv_precip = ['RMSE', 'MAE', 'MAPE', 'Bias', 'POD', 'FAR']
x = np.arange(len(metrics_improv_precip)) * 0.2
bar_w = 0.05

bars1 = ax1.bar(x, improv_gfs_precip, bar_w, label='GFS', color=colors['gfs_after'], edgecolor='black')
bars2 = ax1.bar(x + bar_w + 0.01, improv_era5_precip, bar_w, label='ERA5', color=colors['era5_after'], edgecolor='black')

# Add horizontal line at 0
ax1.axhline(0, color='black', linestyle='--', linewidth=0.8, zorder=0)

for bar, val in zip(bars1, improv_gfs_precip):
    if np.isfinite(val):
        label = f'{val:+.1f}%'
        ax1.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)

for bar, val in zip(bars2, improv_era5_precip):
    if np.isfinite(val):
        label = f'{val:+.1f}%'
        ax1.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)

ax1.set_xticks(x + (bar_w + 0.01) / 2)
ax1.set_xticklabels(metrics_improv_precip, fontsize=label_fontsize)
ax1.set_ylabel('Improvement (%)', fontsize=label_fontsize)
ax1.set_title('Precipitation', fontsize=label_fontsize, fontweight='bold')
ax1.legend(fontsize=11, frameon=True, edgecolor='black')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)

# Compute y-limits for precipitation
precip_vals = [v for v in improv_gfs_precip + improv_era5_precip if np.isfinite(v)]
y_min_precip = min(precip_vals, default=-10) - 10
y_max_precip = max(precip_vals, default=10) + 10
ax1.set_ylim(y_min_precip, y_max_precip)

# Temperature
metrics_improv_temp = ['RMSE', 'MAE', 'MAPE', 'Bias']
x = np.arange(len(metrics_improv_temp)) * 0.2

bars3 = ax2.bar(x, improv_gfs_temp, bar_w, label='GFS', color=colors['gfs_after'], edgecolor='black')
bars4 = ax2.bar(x + bar_w + 0.01, improv_era5_temp, bar_w, label='ERA5', color=colors['era5_after'], edgecolor='black')

# Add horizontal line at 0
ax2.axhline(0, color='black', linestyle='--', linewidth=0.8, zorder=0)

for bar, val in zip(bars3, improv_gfs_temp):
    if np.isfinite(val):
        label = f'{val:+.1f}%'
        ax2.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)

for bar, val in zip(bars4, improv_era5_temp):
    if np.isfinite(val):
        label = f'{val:+.1f}%'
        ax2.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)

ax2.set_xticks(x + bar_w/2)
ax2.set_xticklabels(metrics_improv_temp, fontsize=label_fontsize)
ax2.set_ylabel('Improvement (%)', fontsize=label_fontsize)
ax2.set_title('Temperature', fontsize=label_fontsize, fontweight='bold')
ax2.legend(fontsize=11, frameon=True, edgecolor='black')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)

# Compute y-limits for temperature
temp_vals = [v for v in improv_gfs_temp + improv_era5_temp if np.isfinite(v)]
y_min_temp = min(temp_vals, default=-10) - 10
y_max_temp = max(temp_vals, default=10) + 10
ax2.set_ylim(y_min_temp, y_max_temp)

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(os.path.join(output_dir, 'gfs_vs_era5_improvement_comparison.png'), dpi=300, bbox_inches='tight')
plt.close()
print("Saved: gfs_vs_era5_improvement_comparison.png")

print("\n" + "="*60)
print("All plots generated successfully!")
print(f"Output directory: {output_dir}")
print("="*60)
