#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Script to compare WRF Before/After DA with observed meteorological and ZTD data,
including new NOAA ISD stations. Handles NaN values by skipping them.
Modified to suppress warnings, save tables to Excel, optimize performance, overlay improved stations on maps,
and add a summary table. Added section for POD and FAR calculation and plotting for precipitation
with formatting inspired by the provided comparison script (muted colors, minimal styling).
Updated to save POD/FAR in metrics_tables.xlsx and reduce bar spacing in metrics and POD/FAR graphs.
Fixed bar_data scoping issue. Standardized bar_width=0.01 and spacing across all graphs.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
import seaborn as sns
import os
import warnings
import contextlib
import contextily as ctx
import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import Normalize, ListedColormap
from matplotlib.cm import ScalarMappable
import rasterio
from rasterio.warp import transform_bounds

# Suppress all warnings
warnings.filterwarnings("ignore")

# ------------------------------------------------------------------------
# 0) Basic Setup
# ------------------------------------------------------------------------
plt.style.use('seaborn-white')  # Use same minimal style as second script

base_dir = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/statistics_analysis"
met_dir = os.path.join(base_dir, "Meteorological_variables")
ztd_dir = os.path.join(base_dir, "ztd_variable")

os.makedirs(met_dir, exist_ok=True)
os.makedirs(ztd_dir, exist_ok=True)

# Cache basemap tiles
ctx.cache_dir = os.path.join(base_dir, "basemap_cache")
os.makedirs(ctx.cache_dir, exist_ok=True)

# Use softened colors from second script
colors = {
    'before': '#A52A2A',  # Muted red
    'after': '#228B22'    # Muted green
}

# Standardized thin bar width for all graphs
bar_width = 0.01

# Standardized spacing multiplier for groups
spacing_mult = 0.15

# Small gap between before and after bars
small_gap = 0.01

# ------------------------------------------------------------------------
# 1) File Paths (Meteorological)
# ------------------------------------------------------------------------
file_observed_general = '/Users/haseeb.rehman/Documents/Misc/Luxembourg_stations_for_validation/2021_Event/stations_6hr_cumulative.xlsx'
file_observed_noaa    = '/Users/haseeb.rehman/Documents/Misc/Luxembourg_stations_for_validation/2021_Event/Stations_other_than_lux/station_weather_data_june_july_2021_6hr.xlsx'
file_before_DA        = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/Before_DA/general_station_data_before.xlsx'
file_after_DA         = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/After_DA/general_station_data_after.xlsx'

# ------------------------------------------------------------------------
# 2) File Paths (ZTD)
# ------------------------------------------------------------------------
ztd_file_observed   = '/Users/haseeb.rehman/WRF/WRFDA/DAT_DIR/ztd_data_June_july_2021/for_validation/ztd_data.xlsx'
ztd_file_before_DA  = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/Before_DA/ztd_station_data_before.xlsx'
ztd_file_after_DA   = '/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/2021_ERA5_cv5/After_DA/ztd_station_data_after.xlsx'

# ------------------------------------------------------------------------
# 3) Station Names
# ------------------------------------------------------------------------
station_names_general = pd.ExcelFile(file_observed_general).sheet_names
station_names_noaa    = pd.ExcelFile(file_observed_noaa).sheet_names
ztd_station_names     = pd.ExcelFile(ztd_file_observed).sheet_names

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
        return np.nan, np.nan, np.nan, np.nan, np.nan
    
    correlation = valid_df[sim_col].corr(valid_df[obs_col])
    rmse = np.sqrt(mean_squared_error(valid_df[sim_col], valid_df[obs_col]))
    mae = np.mean(np.abs(valid_df[sim_col] - valid_df[obs_col]))
    safe_obs = valid_df[obs_col].replace({0: np.nan})
    numerator = np.abs(valid_df[sim_col] - valid_df[obs_col])
    denominator = (np.abs(valid_df[sim_col]) + np.abs(valid_df[obs_col])) / 2
    nonzero = denominator != 0
    mape = np.mean((numerator[nonzero] / denominator[nonzero])) * 100 if np.any(nonzero) else np.nan
    bias = np.mean(valid_df[sim_col] - valid_df[obs_col])
    return correlation, rmse, mae, mape, bias

# Added: Compute POD and FAR for precipitation
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
# 7) MET DATA: Loop Over Stations
# ------------------------------------------------------------------------
variables = [
    ('Sim_Precip(mm)', 'Obs_Precip(mm)', 'Precipitation (mm)'),
    ('Sim_T2(C)',      'Obs_T2(C)',      'Temperature (°C)'),
    ('Sim_RH(%)',      'Obs_RH(%)',      'Relative Humidity (%)')
]

met_before_table = []
met_after_table = []
overall_metrics_met = []
precip_metrics = []  # For POD and FAR
improved_stations_met = {var_name: {'Correlation': [], 'RMSE': [], 'MAE': [], 'MAPE': [], 'Bias': []} 
                         for _, _, var_name in variables}
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
    df_after  = read_station_data(file_after_DA, station, is_observed=False)

    if df_before is None or df_after is None:
        continue

    df_merged_before = pd.merge(df_before, df_obs, on='UTC_Datetime', how='inner')
    df_merged_after  = pd.merge(df_after,  df_obs, on='UTC_Datetime', how='inner')

    if df_merged_before.empty or df_merged_after.empty:
        continue

    metrics_before = {}
    metrics_after = {}

    for sim_col, obs_col, var_name in variables:
        corr_b, rmse_b, mae_b, mape_b, bias_b = compute_metrics(df_merged_before, sim_col, obs_col)
        corr_a, rmse_a, mae_a, mape_a, bias_a = compute_metrics(df_merged_after, sim_col, obs_col)

        met_before_table.append({
            'Station': station,
            'Variable': var_name,
            'RMSE': rmse_b,
            'MAE': mae_b,
            'MAPE': mape_b,
            'Bias': bias_b
        })
        met_after_table.append({
            'Station': station,
            'Variable': var_name,
            'RMSE': rmse_a,
            'MAE': mae_a,
            'MAPE': mape_a,
            'Bias': bias_a
        })

        metrics_before[var_name] = (corr_b, rmse_b, mae_b, mape_b, bias_b)
        metrics_after[var_name]  = (corr_a, rmse_a, mae_a, mape_a, bias_a)

        if not pd.isna(corr_a) and not pd.isna(corr_b) and corr_a > corr_b:
            improved_stations_met[var_name]['Correlation'].append(station)
        if not pd.isna(rmse_a) and not pd.isna(rmse_b) and rmse_a < rmse_b:
            improved_stations_met[var_name]['RMSE'].append(station)
        if not pd.isna(mae_a) and not pd.isna(mae_b) and mae_a < mae_b:
            improved_stations_met[var_name]['MAE'].append(station)
        if not pd.isna(mape_a) and not pd.isna(mape_b) and mape_a < mape_b:
            improved_stations_met[var_name]['MAPE'].append(station)
        if not pd.isna(bias_a) and not pd.isna(bias_b) and abs(bias_a) < abs(bias_b):
            improved_stations_met[var_name]['Bias'].append(station)

        overall_metrics_met.append({
            'Station': station, 
            'Variable': var_name,
            'Before_Corr': corr_b, 'Before_RMSE': rmse_b, 'Before_MAE': mae_b, 'Before_MAPE': mape_b, 'Before_Bias': bias_b,
            'After_Corr': corr_a, 'After_RMSE': rmse_a, 'After_MAE': mae_a, 'After_MAPE': mape_a, 'After_Bias': bias_a,
            'Source': 'NOAA ISD' if station in station_names_noaa else 'General'
        })

        # Compute POD/FAR for precipitation
        if var_name == 'Precipitation (mm)':
            pod_b, far_b = compute_pod_far(df_merged_before, sim_col, obs_col)
            pod_a, far_a = compute_pod_far(df_merged_after, sim_col, obs_col)
            precip_metrics.append({
                'Station': station,
                'Before_POD': pod_b,
                'Before_FAR': far_b,
                'After_POD': pod_a,
                'After_FAR': far_a,
                'Source': 'NOAA ISD' if station in station_names_noaa else 'General'
            })

    fig, ax = plt.subplots(nrows=len(variables), ncols=3, figsize=(18, 5 * len(variables)))
    fig.suptitle(f'Station: {station} - Meteorological Variables', fontsize=12)

    for i, (sim_col, obs_col, var_name) in enumerate(variables):
        corr_b, rmse_b, mae_b, mape_b, bias_b = metrics_before[var_name]
        corr_a, rmse_a, mae_a, mape_a, bias_a = metrics_after[var_name]

        df_before_valid = df_merged_before[[sim_col, obs_col, 'UTC_Datetime']].dropna()
        df_after_valid = df_merged_after[[sim_col, obs_col, 'UTC_Datetime']].dropna()

        if not df_before_valid.empty and not df_after_valid.empty:
            ax[i, 0].scatter(df_before_valid[sim_col], df_before_valid[obs_col],
                            color=colors['before'], alpha=0.6, label='Before DA')
            ax[i, 0].scatter(df_after_valid[sim_col], df_after_valid[obs_col],
                            color=colors['after'], alpha=0.6, label='After DA')
            min_val = min(df_before_valid[obs_col].min(), df_after_valid[obs_col].min())
            max_val = max(df_before_valid[obs_col].max(), df_after_valid[obs_col].max())
            ax[i, 0].plot([min_val, max_val], [min_val, max_val], 'k--', label='1:1 line')
            ax[i, 0].set_title(f'{var_name} Correlation', fontsize=12)
            ax[i, 0].set_xlabel('Simulated', fontsize=10)
            ax[i, 0].set_ylabel('Observed', fontsize=10)
            ax[i, 0].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
            ax[i, 0].tick_params(axis='both', length=4, width=0.5)
            ax[i, 0].spines['top'].set_visible(False)
            ax[i, 0].spines['right'].set_visible(False)

        bar_data = [rmse_b, rmse_a, mae_b, mae_a, mape_b/100 if not pd.isna(mape_b) else 0, 
                    mape_a/100 if not pd.isna(mape_a) else 0, bias_b, bias_a]
        bar_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']
        x_pos = np.arange(4) * spacing_mult
        bars_before = ax[i, 1].bar(x_pos, [bar_data[0], bar_data[2], bar_data[4], bar_data[6]], bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
        bars_after = ax[i, 1].bar(x_pos + bar_width + small_gap, [bar_data[1], bar_data[3], bar_data[5], bar_data[7]], bar_width, label='After DA', color=colors['after'], alpha=0.7, edgecolor='black')
        ax[i, 1].set_xticks(x_pos + (bar_width + small_gap)/2)
        ax[i, 1].set_xticklabels(bar_labels, rotation=0, fontsize=10)
        ax[i, 1].set_title(f'{var_name} Metrics', fontsize=12)
        ax[i, 1].set_ylabel('Value', fontsize=10)
        ax[i, 1].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
        ax[i, 1].tick_params(axis='both', length=4, width=0.5)
        ax[i, 1].spines['top'].set_visible(False)
        ax[i, 1].spines['right'].set_visible(False)
        for bars, offset in zip([bars_before, bars_after], [0, bar_width + small_gap]):
            for j, bar in enumerate(bars):
                height = bar.get_height()
                if not pd.isna(height):
                    ax[i, 1].text(bar.get_x() + bar_width/2., height/2, f'{height:.2f}',
                                  ha='center', va='center', color='black', fontsize=8, rotation=90)

        ax[i, 2].plot(df_before_valid['UTC_Datetime'], df_before_valid[sim_col],
                    label='Sim Before DA', color=colors['before'], alpha=0.7)
        ax[i, 2].plot(df_after_valid['UTC_Datetime'], df_after_valid[sim_col],
                    label='Sim After DA', color=colors['after'], alpha=0.7)
        ax[i, 2].plot(df_before_valid['UTC_Datetime'], df_before_valid[obs_col],
                    label='Observed', color='#6BAED6', linestyle='dotted', alpha=0.7)
        ax[i, 2].set_title(f'{var_name} Time Series', fontsize=12)
        ax[i, 2].set_xlabel('Datetime', fontsize=10)
        ax[i, 2].set_ylabel(var_name, fontsize=10)
        ax[i, 2].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
        ax[i, 2].tick_params(axis='both', length=4, width=0.5)
        ax[i, 2].spines['top'].set_visible(False)
        ax[i, 2].spines['right'].set_visible(False)
        ax[i, 2].xaxis.set_major_locator(plt.MaxNLocator(nbins=7))
        plt.setp(ax[i, 2].xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=10)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(met_dir, f'{station}_met_analysis.png'), dpi=300, bbox_inches='tight')
    plt.close()

met_before_df = pd.DataFrame(met_before_table)
met_after_df = pd.DataFrame(met_after_table)

met_before_pivot = met_before_df.pivot_table(index='Station', columns='Variable', 
                                             values=['RMSE', 'MAE', 'MAPE', 'Bias'], aggfunc='first')
met_after_pivot = met_after_df.pivot_table(index='Station', columns='Variable', 
                                           values=['RMSE', 'MAE', 'MAPE', 'Bias'], aggfunc='first')

met_before_pivot.columns = [f'{var}_{stat}' for stat, var in met_before_pivot.columns]
met_after_pivot.columns = [f'{var}_{stat}' for stat, var in met_after_pivot.columns]

# ------------------------------------------------------------------------
# 8) MET DATA: Overall Aggregated Metrics
# ------------------------------------------------------------------------
df_overall_met = pd.DataFrame(overall_metrics_met)
agg_metrics_general = df_overall_met[df_overall_met['Source'] == 'General'].groupby('Variable').mean(numeric_only=True)
agg_metrics_noaa = df_overall_met[df_overall_met['Source'] == 'NOAA ISD'].groupby('Variable').mean(numeric_only=True)

metrics = ['RMSE', 'MAE', 'MAPE', 'Bias']
variables_met = ['Precipitation (mm)', 'Temperature (°C)', 'Relative Humidity (%)']
x = np.arange(len(metrics)) * spacing_mult

fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 12))
fig.suptitle('Overall Meteorological Metrics (Mean Across General Stations)', fontsize=12)

for i, var in enumerate(variables_met):
    if var in agg_metrics_general.index:
        before_values = [agg_metrics_general.loc[var, 'Before_RMSE'],
                        agg_metrics_general.loc[var, 'Before_MAE'],
                        agg_metrics_general.loc[var, 'Before_MAPE'] / 100,
                        agg_metrics_general.loc[var, 'Before_Bias']]
        after_values = [agg_metrics_general.loc[var, 'After_RMSE'],
                        agg_metrics_general.loc[var, 'After_MAE'],
                        agg_metrics_general.loc[var, 'After_MAPE'] / 100,
                        agg_metrics_general.loc[var, 'After_Bias']]

        bars1 = axes[i].bar(x, before_values, bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
        bars2 = axes[i].bar(x + bar_width + small_gap, after_values, bar_width, label='After DA', color=colors['after'], alpha=0.7, edgecolor='black')

        axes[i].set_xticks(x + (bar_width + small_gap)/2)
        axes[i].set_xticklabels(['RMSE', 'MAE', 'SMAPE/100', 'Bias'], rotation=0, fontsize=10)
        axes[i].set_title(f'{var}', fontsize=12)
        axes[i].set_ylabel('Metric Value', fontsize=10)
        axes[i].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
        axes[i].tick_params(axis='both', length=4, width=0.5)
        axes[i].spines['top'].set_visible(False)
        axes[i].spines['right'].set_visible(False)

        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if not pd.isna(height):
                    axes[i].text(bar.get_x() + bar_width/2., height/2, f'{height:.2f}',
                                ha='center', va='center', color='black', fontsize=8, rotation=90)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(met_dir, 'overall_met_metrics_general.png'), dpi=300, bbox_inches='tight')
plt.close()

fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 12))
fig.suptitle('Overall Meteorological Metrics (Mean Across NOAA ISD Stations)', fontsize=12)

for i, var in enumerate(variables_met):
    if var in agg_metrics_noaa.index:
        before_values = [agg_metrics_noaa.loc[var, 'Before_RMSE'],
                        agg_metrics_noaa.loc[var, 'Before_MAE'],
                        agg_metrics_noaa.loc[var, 'Before_MAPE'] / 100,
                        agg_metrics_noaa.loc[var, 'Before_Bias']]
        after_values = [agg_metrics_noaa.loc[var, 'After_RMSE'],
                        agg_metrics_noaa.loc[var, 'After_MAE'],
                        agg_metrics_noaa.loc[var, 'After_MAPE'] / 100,
                        agg_metrics_noaa.loc[var, 'After_Bias']]

        bars1 = axes[i].bar(x, before_values, bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
        bars2 = axes[i].bar(x + bar_width + small_gap, after_values, bar_width, label='After DA', color=colors['after'], alpha=0.7, edgecolor='black')

        axes[i].set_xticks(x + (bar_width + small_gap)/2)
        axes[i].set_xticklabels(['RMSE', 'MAE', 'SMAPE/100', 'Bias'], rotation=0, fontsize=10)
        axes[i].set_title(f'{var}', fontsize=12)
        axes[i].set_ylabel('Metric Value', fontsize=10)
        axes[i].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
        axes[i].tick_params(axis='both', length=4, width=0.5)
        axes[i].spines['top'].set_visible(False)
        axes[i].spines['right'].set_visible(False)

        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if not pd.isna(height):
                    axes[i].text(bar.get_x() + bar_width/2., height/2, f'{height:.2f}',
                                ha='center', va='center', color='black', fontsize=8, rotation=90)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(met_dir, 'overall_met_metrics_noaa.png'), dpi=300, bbox_inches='tight')
plt.close()

# Added: POD and FAR graph (average over all stations)
df_precip = pd.DataFrame(precip_metrics)
mean_precip = df_precip.mean(numeric_only=True)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(6, 6), sharex=False)
fig.subplots_adjust(hspace=0.1)  # Reduced vertical spacing between POD and FAR

# POD graph
x = np.arange(2) * spacing_mult
bars_pod = ax1.bar(x, [mean_precip['Before_POD'], mean_precip['After_POD']], 
                   bar_width, label=['Before DA', 'After DA'], color=[colors['before'], colors['after']], 
                   alpha=0.7, edgecolor='black')
ax1.set_ylabel('POD', fontsize=10)
ax1.set_title('Probability of Detection (Precipitation)', fontsize=12)
ax1.set_xticks(x)
ax1.set_xticklabels([])  # Remove x-axis labels
ax1.set_ylim(0, 1)
ax1.tick_params(axis='both', length=4, width=0.5)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
for bar in bars_pod:
    height = bar.get_height()
    if not pd.isna(height):
        ax1.text(bar.get_x() + bar_width/2., height/2, f'{height:.2f}', 
                 ha='center', va='center', color='black', fontsize=8, rotation=90)

# FAR graph
bars_far = ax2.bar(x, [mean_precip['Before_FAR'], mean_precip['After_FAR']], 
                   bar_width, label=['Before DA', 'After DA'], color=[colors['before'], colors['after']], 
                   alpha=0.7, edgecolor='black')
ax2.set_ylabel('FAR', fontsize=10)
ax2.set_title('False Alarm Ratio (Precipitation)', fontsize=12)
ax2.set_xticks(x)
ax2.set_xticklabels([])  # Remove x-axis labels
ax2.set_ylim(0, 1)
ax2.tick_params(axis='both', length=4, width=0.5)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
for bar in bars_far:
    height = bar.get_height()
    if not pd.isna(height):
        ax2.text(bar.get_x() + bar_width/2., height/2, f'{height:.2f}', 
                 ha='center', va='center', color='black', fontsize=8, rotation=90)

plt.tight_layout()
plt.savefig(os.path.join(met_dir, 'pod_far_average.png'), dpi=300, bbox_inches='tight')
plt.close()

# ------------------------------------------------------------------------
# 9) ZTD: Loop Over Stations
# ------------------------------------------------------------------------
ztd_before_table = []
ztd_after_table = []
overall_metrics_ztd = []

for station in ztd_station_names:
    df_ztd_obs    = read_ztd_data(ztd_file_observed,   station, is_observed=True)
    df_ztd_before = read_ztd_data(ztd_file_before_DA,  station, is_observed=False)
    df_ztd_after  = read_ztd_data(ztd_file_after_DA,   station, is_observed=False)

    if df_ztd_obs is None or df_ztd_before is None or df_ztd_after is None:
        continue

    df_merged_before_ztd = pd.merge(df_ztd_before, df_ztd_obs, on='UTC_Datetime', how='inner')
    df_merged_after_ztd  = pd.merge(df_ztd_after,  df_ztd_obs, on='UTC_Datetime', how='inner')

    if df_merged_before_ztd.empty or df_merged_after_ztd.empty:
        continue

    sim_col, obs_col = 'Sim_ZTD(m)', 'Obs_ZTD(m)'
    corr_b, rmse_b, mae_b, mape_b, bias_b = compute_metrics(df_merged_before_ztd, sim_col, obs_col)
    corr_a, rmse_a, mae_a, mape_a, bias_a = compute_metrics(df_merged_after_ztd, sim_col, obs_col)

    ztd_before_table.append({
        'Station': station,
        'RMSE': rmse_b,
        'MAE': mae_b,
        'MAPE': mape_b,
        'Bias': bias_b
    })
    ztd_after_table.append({
        'Station': station,
        'RMSE': rmse_a,
        'MAE': mae_a,
        'MAPE': mape_a,
        'Bias': bias_a
    })
    overall_metrics_ztd.append({
        'Station': station, 
        'Before_Corr': corr_b, 'Before_RMSE': rmse_b, 'Before_MAE': mae_b, 'Before_MAPE': mape_b, 'Before_Bias': bias_b,
        'After_Corr': corr_a, 'After_RMSE': rmse_a, 'After_MAE': mae_a, 'After_MAPE': mape_a, 'After_Bias': bias_a
    })

    fig, ax = plt.subplots(nrows=1, ncols=3, figsize=(18, 5))
    fig.suptitle(f'Station: {station} - ZTD Analysis', fontsize=12)

    df_before_valid_ztd = df_merged_before_ztd[[sim_col, obs_col, 'UTC_Datetime']].dropna()
    df_after_valid_ztd = df_merged_after_ztd[[sim_col, obs_col, 'UTC_Datetime']].dropna()

    if not df_before_valid_ztd.empty and not df_after_valid_ztd.empty:
        ax[0].scatter(df_before_valid_ztd[sim_col], df_before_valid_ztd[obs_col],
                    color=colors['before'], alpha=0.6, label='Before DA')
        ax[0].scatter(df_after_valid_ztd[sim_col], df_after_valid_ztd[obs_col],
                    color=colors['after'], alpha=0.6, label='After DA')
        min_val_ztd = min(df_before_valid_ztd[obs_col].min(), df_after_valid_ztd[obs_col].min())
        max_val_ztd = max(df_before_valid_ztd[obs_col].max(), df_after_valid_ztd[obs_col].max())
        ax[0].plot([min_val_ztd, max_val_ztd], [min_val_ztd, max_val_ztd], 'k--', label='1:1 line')
        ax[0].set_title('ZTD Correlation', fontsize=12)
        ax[0].set_xlabel('Simulated ZTD (m)', fontsize=10)
        ax[0].set_ylabel('Observed ZTD (m)', fontsize=10)
        ax[0].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
        ax[0].tick_params(axis='both', length=4, width=0.5)
        ax[0].spines['top'].set_visible(False)
        ax[0].spines['right'].set_visible(False)

    bar_data = [rmse_b, rmse_a, mae_b, mae_a, mape_b/100 if not pd.isna(mape_b) else 0, 
                mape_a/100 if not pd.isna(mape_a) else 0, bias_b, bias_a]
    bar_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']
    x_pos = np.arange(4) * spacing_mult
    bars1 = ax[1].bar(x_pos, [bar_data[0], bar_data[2], bar_data[4], bar_data[6]], bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
    bars2 = ax[1].bar(x_pos + bar_width + small_gap, [bar_data[1], bar_data[3], bar_data[5], bar_data[7]], bar_width, label='After DA', color=colors['after'], alpha=0.7, edgecolor='black')
    ax[1].set_xticks(x_pos + (bar_width + small_gap)/2)
    ax[1].set_xticklabels(bar_labels, rotation=0, fontsize=10)
    ax[1].set_title('ZTD Metrics', fontsize=12)
    ax[1].set_ylabel('Metric Value', fontsize=10)
    ax[1].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
    ax[1].tick_params(axis='both', length=4, width=0.5)
    ax[1].spines['top'].set_visible(False)
    ax[1].spines['right'].set_visible(False)
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if not pd.isna(height):
                ax[1].text(bar.get_x() + bar_width/2., height/2, f'{height:.2f}',
                           ha='center', va='center', color='black', fontsize=8, rotation=90)

    ax[2].plot(df_before_valid_ztd['UTC_Datetime'], df_before_valid_ztd[sim_col],
            label='Sim Before DA', color=colors['before'], alpha=0.7)
    ax[2].plot(df_after_valid_ztd['UTC_Datetime'], df_after_valid_ztd[sim_col],
            label='Sim After DA', color=colors['after'], alpha=0.7)
    ax[2].plot(df_before_valid_ztd['UTC_Datetime'], df_before_valid_ztd[obs_col],
            label='Observed', color='#6BAED6', linestyle='dotted', alpha=0.7)
    ax[2].set_title('ZTD Time Series', fontsize=12)
    ax[2].set_xlabel('Datetime', fontsize=10)
    ax[2].set_ylabel('ZTD (m)', fontsize=10)
    ax[2].legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
    ax[2].tick_params(axis='both', length=4, width=0.5)
    ax[2].spines['top'].set_visible(False)
    ax[2].spines['right'].set_visible(False)
    ax[2].xaxis.set_major_locator(plt.MaxNLocator(nbins=7))
    plt.setp(ax[2].xaxis.get_majorticklabels(), rotation=45, ha="right", fontsize=10)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(ztd_dir, f'{station}_ztd_analysis.png'), dpi=300, bbox_inches='tight')
    plt.close()

ztd_before_df = pd.DataFrame(ztd_before_table)
ztd_after_df = pd.DataFrame(ztd_after_table)

# ------------------------------------------------------------------------
# Compute Summary Tables by Parameter
# ------------------------------------------------------------------------
variables = {
    'Precipitation (mm)': 'Precipitation',
    'Temperature (°C)': 'Temperature',
    'Relative Humidity (%)': 'Relative Humidity'
}

tables = {}
for var_full, var_short in variables.items():
    before_data = met_before_df[met_before_df['Variable'] == var_full].set_index('Station')
    after_data = met_after_df[met_after_df['Variable'] == var_full].set_index('Station')
    
    table_data = pd.DataFrame(index=before_data.index)
    table_data[f'Bias ({var_short}) Before DA'] = before_data['Bias'].round(2)
    table_data[f'Bias ({var_short}) After DA'] = after_data['Bias'].round(2)
    table_data[f'MAE ({var_short}) Before DA'] = before_data['MAE'].round(2)
    table_data[f'MAE ({var_short}) After DA'] = after_data['MAE'].round(2)
    table_data[f'RMSE ({var_short}) Before DA'] = before_data['RMSE'].round(2)
    table_data[f'RMSE ({var_short}) After DA'] = after_data['RMSE'].round(2)
    table_data[f'MAPE ({var_short}) Before DA'] = before_data['MAPE'].round(2)
    table_data[f'MAPE ({var_short}) After DA'] = after_data['MAPE'].round(2)
    
    tables[var_short] = table_data

# Compute original summary table
met_before_means = met_before_df.groupby('Variable').mean(numeric_only=True)
met_after_means = met_after_df.groupby('Variable').mean(numeric_only=True)

# ZTD averages
ztd_before_means = ztd_before_df.mean(numeric_only=True)
ztd_after_means = ztd_after_df.mean(numeric_only=True)

# Prepare summary table data
summary_data = []
variables_summary = ['Precipitation (mm)', 'Temperature (°C)', 'Relative Humidity (%)', 'ZTD']
metrics = ['RMSE', 'MAE', 'MAPE', 'Bias']

for var in variables_summary[:-1]:  # Meteorological variables
    for metric in metrics:
        before = met_before_means.loc[var, metric]
        after = met_after_means.loc[var, metric]
        if metric == 'Bias':
            change = ((abs(before) - abs(after)) / abs(before)) * 100 if before != 0 else 0
            change_str = f'{change:+.1f}%'
        else:
            change = ((after - before) / before) * 100 if before != 0 else 0
            change_str = f'{change:.1f}%'
        summary_data.append({
            'Variable': var,
            'Metric': metric,
            'Before': f'{before:.2f}',
            'After': f'{after:.2f}',
            '% Change': change_str
        })

# ZTD
for metric in metrics:
    before = ztd_before_means[metric]
    after = ztd_after_means[metric]
    if metric == 'Bias':
        change = ((abs(before) - abs(after)) / abs(before)) * 100 if before != 0 else 0
        change_str = f'{change:+.1f}%'
    else:
        change = ((after - before) / before) * 100 if before != 0 else 0
        change_str = f'{change:.1f}%'
    summary_data.append({
        'Variable': 'ZTD',
        'Metric': metric,
        'Before': f'{before:.2f}',
        'After': f'{after:.2f}',
        '% Change': change_str
    })

summary_df = pd.DataFrame(summary_data)

# Prepare improved stations table
improved_data = []
for var_name, metrics_dict in improved_stations_met.items():
    for metric, stations in metrics_dict.items():
        improved_data.append({
            'Variable': var_name,
            'Metric': metric,
            'Improved Stations': ', '.join(stations) if stations else 'None'
        })
improved_df = pd.DataFrame(improved_data)

# Prepare POD/FAR table
precip_df = pd.DataFrame(precip_metrics)
precip_pivot = precip_df.pivot_table(index='Station', columns='Source', 
                                     values=['Before_POD', 'Before_FAR', 'After_POD', 'After_FAR'], aggfunc='mean')
precip_pivot.columns = ['_'.join(col).strip() for col in precip_pivot.columns.values]

# Save tables to Excel
with pd.ExcelWriter(os.path.join(base_dir, 'metrics_tables.xlsx'), engine='openpyxl') as writer:
    for var_short, table_data in tables.items():
        table_data.to_excel(writer, sheet_name=var_short, index=True, na_rep='N/A', float_format='%.2f')
    ztd_before_df.to_excel(writer, sheet_name='ZTD', startrow=0, index=False, na_rep='N/A', float_format='%.3f')
    ztd_after_df.to_excel(writer, sheet_name='ZTD', startrow=len(ztd_before_df) + 2, index=False, na_rep='N/A', float_format='%.3f')
    improved_df.to_excel(writer, sheet_name='Improved_Met', index=False)
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    precip_pivot.to_excel(writer, sheet_name='Precipitation_POD_FAR', index=True, na_rep='N/A', float_format='%.2f')

# ------------------------------------------------------------------------
# 10) ZTD: Overall Aggregated Metrics
# ------------------------------------------------------------------------
df_overall_ztd = pd.DataFrame(overall_metrics_ztd)
mean_ztd = df_overall_ztd.mean(numeric_only=True)

labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']
x = np.arange(len(labels)) * spacing_mult

fig, ax = plt.subplots(figsize=(8, 5))
bars1 = ax.bar(x, [mean_ztd['Before_RMSE'], mean_ztd['Before_MAE'], mean_ztd['Before_MAPE']/100, mean_ztd['Before_Bias']], bar_width, label='Before DA', color=colors['before'], alpha=0.7, edgecolor='black')
bars2 = ax.bar(x + bar_width + small_gap, [mean_ztd['After_RMSE'], mean_ztd['After_MAE'], mean_ztd['After_MAPE']/100, mean_ztd['After_Bias']], bar_width, label='After DA', color=colors['after'], alpha=0.7, edgecolor='black')
ax.set_xticks(x + (bar_width + small_gap)/2)
ax.set_xticklabels(labels, rotation=0, fontsize=10)
ax.set_ylabel('Metric Value', fontsize=10)
ax.set_title('Overall ZTD Metrics (Mean Across Stations)', fontsize=12)
ax.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
ax.tick_params(axis='both', length=4, width=0.5)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        if not pd.isna(height):
            ax.text(bar.get_x() + bar_width/2., height/2, f'{height:.2f}',
                    ha='center', va='center', color='black', fontsize=8, rotation=90)

plt.tight_layout()
plt.savefig(os.path.join(ztd_dir, 'overall_ztd_metrics.png'), dpi=300, bbox_inches='tight')
plt.close()

# ------------------------------------------------------------------------
# 11) Mapping Metrics (Updated)
# ------------------------------------------------------------------------
ztd_stations = [("D596", 51.200, 8.524), ("KLEV", 51.768, 6.142), ("FFMJ", 50.091, 8.665),
                ("D624", 50.868, 7.056), ("NIKL", 51.141, 4.151), ("D402", 48.073, 8.528),
                ("LAIG", 47.842, 4.373), ("TRI2", 49.725, 6.618), ("CT58", 49.150, 3.044),
                ("BAT1", 50.637, 5.834), ("VIT2", 50.317, 6.085), ("MABO", 50.075, 5.739),
                ("DBMH", 48.604, 6.364), ("SMSP", 49.115, 4.581), ("REDU", 50.002, 5.145),
                ("D931", 49.314, 6.746)]

met_stations = [("Briedfeld", 50.12385, 6.06622), ("Echternach", 49.8031, 6.44337), ("Ettelbruck", 49.85172, 6.09754),
                ("Oberkorn", 49.5122, 5.9011), ("Remerschen", 49.491, 6.349), ("Findel", 49.63265182, 6.23292867),
                ("Roodt", 49.7945, 5.8202), ("Hosingen", 49.99314, 6.10147), ("Useldange", 49.76739, 5.96748),
                ("Mamer", 49.63353, 6.0193), ("Arsdorf", 49.85891, 5.84868), ("Asselborn", 50.09685689, 5.96960753),
                ("Grevenmacher", 49.68087, 6.43541), ("Schimpach", 50.0093, 5.8475), ("Waldbillig", 49.79806, 6.2773),
                ("Bettendorf", 49.8741, 6.2095), ("Fouhren", 49.91445, 6.19508), ("Beringen", 49.762, 6.11179),
                ("Dahl", 49.93595, 5.98093), 
                ("Beitem", 50.9, 3.117), ("Meyenheim", 47.917, 7.4),
                ("Spangdahlem ab", 49.973, 6.693), ("Kassel calden", 51.408, 9.378), ("Vatry", 48.776, 4.184),
                ("Ernage", 50.583, 4.683), ("Dusseldorf", 51.289, 6.767), ("Liege", 50.637, 5.443),
                ("Mirecourt", 48.325, 6.07), ("Frankfurt main", 50.026, 8.543), ("Oostende", 51.199, 2.862),
                ("Zeebrugge", 51.35, 3.2), ("Fritzlar", 51.115, 9.286), ("Branches", 47.85, 3.497),
                ("Bale mulhouse", 47.59, 7.53)]

met_coords_df = pd.DataFrame(met_stations, columns=['Station', 'Lat', 'Lon'])
ztd_coords_df = pd.DataFrame(ztd_stations, columns=['Station', 'Lat', 'Lon'])

met_before_map = met_before_pivot.reset_index().merge(met_coords_df, on='Station', how='left')
met_after_map = met_after_pivot.reset_index().merge(met_coords_df, on='Station', how='left')
ztd_before_map = ztd_before_df.merge(ztd_coords_df, on='Station', how='left')
ztd_after_map = ztd_after_df.merge(ztd_coords_df, on='Station', how='left')

data_crs = ccrs.epsg(3857)

def setup_map(ax, domain_shp):
    domain_gdf = gpd.read_file(domain_shp).to_crs(epsg=3857)
    x_min, y_min, x_max, y_max = domain_gdf.total_bounds
    ax.set_extent([x_min, x_max, y_min, y_max], crs=data_crs)
    elevation_file = '/Users/haseeb.rehman/Documents/SRTM_DEM_for_study_area/DEM_SRTM_30m.tif'
    with rasterio.open(elevation_file) as src:
        elevation_data = src.read(1)
        elevation_crs = src.crs
        left, bottom, right, top = src.bounds
        left_t, bottom_t, right_t, top_t = transform_bounds(elevation_crs, data_crs, left, bottom, right, top)
        ax.imshow(elevation_data, extent=[left_t, right_t, bottom_t, top_t], transform=data_crs, cmap='gray', zorder=1)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor="black")
    ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.8, edgecolor="black")
    ax.add_feature(cfeature.LAKES, facecolor="lightblue", alpha=0.5)
    gl = ax.gridlines(draw_labels=True, alpha=0.3)
    gl.xlabels_top = False
    gl.ylabels_right = False

stats = ['RMSE', 'MAE', 'MAPE', 'Bias']
stat_ranges = {
    'RMSE': {'Precipitation (mm)': (0, 10), 'Temperature (°C)': (0, 10), 'Relative Humidity (%)': (0, 10), 'ZTD': (15, 20)},
    'MAE': {'Precipitation (mm)': (0, 10), 'Temperature (°C)': (0, 10), 'Relative Humidity (%)': (0, 10), 'ZTD': (15, 20)},
    'MAPE': {'Precipitation (mm)': (0, 100), 'Temperature (°C)': (0, 100), 'Relative Humidity (%)': (0, 100), 'ZTD': (150, 160)},
    'Bias': {'Precipitation (mm)': (-10, 10), 'Temperature (°C)': (-5, 5), 'Relative Humidity (%)': (-10, 10), 'ZTD': (15, 20)}
}

colors_map = [
    '#0000FF', '#00CED1', '#00FF00', '#ADFF2F', '#FFFF00', '#FFD700', '#FFA500', '#FF4500',
    '#FF0000', '#DC143C', '#8B0000', '#800000', '#4B0082', '#6A5ACD', '#800080', '#FF00FF',
    '#C71585', '#FF1493', '#FFB6C1', '#F0E68C'
]
custom_cmap = ListedColormap(colors_map)

def plot_stat_map(data_df, stat_col, title, ax, marker='o', size=10, vmin=None, vmax=None, improved_stations=None):
    setup_map(ax, '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_Domain.shp')
    norm = Normalize(vmin=vmin, vmax=vmax)
    boundaries = np.arange(vmin, vmax + 0.25, 0.25)
    if stat_col.endswith('MAPE') or stat_col == 'MAPE':
        ticks = np.arange(vmin, vmax + 10, 10)
        label_step = 20
    else:
        ticks = np.arange(vmin, vmax + 1, 1)
        label_step = 2

    sc = ax.scatter(data_df['Lon'], data_df['Lat'], c=data_df[stat_col], cmap=custom_cmap, norm=norm,
                    transform=ccrs.PlateCarree(), marker=marker, s=size, alpha=0.7, zorder=5)
    
    if improved_stations and "After DA" in title:
        improved_df = data_df[data_df['Station'].isin(improved_stations)]
        ax.scatter(improved_df['Lon'], improved_df['Lat'], c=improved_df[stat_col], cmap=custom_cmap, norm=norm,
                   transform=ccrs.PlateCarree(), marker='*', s=size*0.8, edgecolors='black', linewidth=0.5, zorder=6)

    ax.set_title(title, fontsize=10)
    cbar = plt.colorbar(ScalarMappable(norm=norm, cmap=custom_cmap), ax=ax, shrink=0.6, aspect=20, pad=0.05)
    cbar.set_ticks(ticks)
    cbar.set_label(stat_col, fontsize=8)
    cbar.ax.tick_params(labelsize=8)
    cbar.ax.set_yticklabels([f'{x:.1f}' if (x - vmin) % label_step == 0 else '' for x in ticks])

for var in variables_met:
    fig, axes = plt.subplots(2, 4, figsize=(20, 10), subplot_kw={'projection': data_crs})
    fig.suptitle(f'Meteorological Stations - {var}', fontsize=12)
    
    for i, stat in enumerate(stats):
        col = f'{var}_{stat}'
        vmin = stat_ranges[stat][var][0]
        vmax = stat_ranges[stat][var][1]
        improved_list = improved_stations_met[var][stat]
        
        before_data = met_before_map.dropna(subset=[col])[col].clip(vmin, vmax)
        after_data = met_after_map.dropna(subset=[col])[col].clip(vmin, vmax)
        
        plot_stat_map(met_before_map.dropna(subset=[col]).assign(**{col: before_data}),
                      col, f'Before DA {stat}', axes[0, i], vmin=vmin, vmax=vmax, improved_stations=None)
        plot_stat_map(met_after_map.dropna(subset=[col]).assign(**{col: after_data}),
                      col, f'After DA {stat}', axes[1, i], vmin=vmin, vmax=vmax, improved_stations=improved_list)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.savefig(os.path.join(met_dir, f'met_map_{var.lower().replace(" ", "_")}.png'), dpi=300, bbox_inches='tight')
    plt.close()

# Plot ZTD Maps (no improved stations overlay for ZTD)
fig, axes = plt.subplots(2, 4, figsize=(20, 10), subplot_kw={'projection': data_crs})
fig.suptitle('ZTD Stations', fontsize=12)

for i, stat in enumerate(stats):
    vmin, vmax = stat_ranges[stat]['ZTD']
    before_data = ztd_before_map.dropna(subset=[stat])[stat].clip(vmin, vmax)
    after_data = ztd_after_map.dropna(subset=[stat])[stat].clip(vmin, vmax)
    
    plot_stat_map(ztd_before_map.dropna(subset=[stat]).assign(**{stat: before_data}),
                  stat, f'Before DA {stat}', axes[0, i], marker='s', vmin=vmin, vmax=vmax)
    plot_stat_map(ztd_after_map.dropna(subset=[stat]).assign(**{stat: after_data}),
                  stat, f'After DA {stat}', axes[1, i], marker='s', vmin=vmin, vmax=vmax)

plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(os.path.join(ztd_dir, 'ztd_map.png'), dpi=300, bbox_inches='tight')
plt.close()

# Final message
print(f"\nDone! Figures saved in:\n  {met_dir} (Meteorological)\n  {ztd_dir} (ZTD)\nTables saved in: {os.path.join(base_dir, 'metrics_tables.xlsx')}")