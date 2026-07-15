#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Created on Wed Sep 17 16:22:25 2025
@author: haseeb.rehman
Script to generate a summary table and improvement percentage graphs for WRF data across 2016, 2018, and 2021.
"""
import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
# Scientific styling with minimal look
plt.style.use('seaborn-white')
# Colors for the three years
colors = {
    2016: '#A52A2A',  # muted red for 2016
    2018: '#DAA520',  # muted yellow for 2018
    2021: '#20B2AA'   # muted cyan for 2021
}
# File paths and years
paths = [
    "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2016_GFS_000_cv5/statistics_analysis/metrics_tables.xlsx",
    "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2018_GFS_000_cv5/statistics_analysis/metrics_tables.xlsx",
    "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2021_new_GFS_000_cv5/statistics_analysis/metrics_tables.xlsx"
]
years = [2016, 2018, 2021]
variables = ['Precipitation (mm)', 'Temperature (°C)']
metrics = ['RMSE', 'MAE', 'MAPE', 'Bias']  # MAPE will be treated as SMAPE/100 for consistency
# Final result table
result = pd.DataFrame(index=years)
# Function to calculate improvement (% closer to zero)
def calculate_improvement(before, after):
    if pd.isna(before) or pd.isna(after) or before == 0:
        return 0.0
    return round((abs(before) - abs(after)) / abs(before) * 100, 2)
# Main loop to populate summary table
for var in variables:
    for metric in metrics:
        improvement_series = []
        for path, year in zip(paths, years):
            try:
                df = pd.read_excel(path, sheet_name="Summary")
                row = df[(df['Variable'] == var) & (df['Metric'] == metric)]
                if not row.empty:
                    before = pd.to_numeric(row['Before'].iloc[0], errors='coerce')
                    after = pd.to_numeric(row['After'].iloc[0], errors='coerce')
                    print(f"{year} | {var} | {metric} -> Before: {before}, After: {after}")
                    improvement = calculate_improvement(before, after)
                else:
                    improvement = 0.0
            except:
                improvement = 0.0
            improvement_series.append(improvement)
        col_name = f"{var}_{metric}"
        result[col_name] = improvement_series
# Rearranging columns into desired layout
final_columns = [f"{var}_{metric}" for var in variables for metric in metrics]
result = result[final_columns]
# Renaming columns using MultiIndex
result.columns = pd.MultiIndex.from_product([['Precipitation', 'Temperature'], metrics])
# Saving to Excel
output_path = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/for_meteo_lux/Improvement_Table_Formatted.xlsx"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
result.to_excel(output_path)
print("\n✅ Output saved ")
# Plotting Improvement Metrics
output_dir = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/for_meteo_lux"
os.makedirs(output_dir, exist_ok=True)
# Plot for Precipitation Improvement
fig_precip, ax_precip = plt.subplots(1, 1, figsize=(10, 6))
metrics_improv = metrics + ['POD', 'FAR']
x = np.arange(len(metrics_improv)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE', 'Bias', 'POD', 'FAR']
all_values = []
for i, year in enumerate(years):
    try:
        df = pd.read_excel(paths[i], sheet_name="Summary")
        df_pod_far = pd.read_excel(paths[i], sheet_name="Precipitation_POD_FAR")
        before_rmse = pd.to_numeric(df[(df['Variable'] == 'Precipitation (mm)') & (df['Metric'] == 'RMSE')]['Before'].iloc[0], errors='coerce')
        after_rmse = pd.to_numeric(df[(df['Variable'] == 'Precipitation (mm)') & (df['Metric'] == 'RMSE')]['After'].iloc[0], errors='coerce')
        before_mae = pd.to_numeric(df[(df['Variable'] == 'Precipitation (mm)') & (df['Metric'] == 'MAE')]['Before'].iloc[0], errors='coerce')
        after_mae = pd.to_numeric(df[(df['Variable'] == 'Precipitation (mm)') & (df['Metric'] == 'MAE')]['After'].iloc[0], errors='coerce')
        before_mape = pd.to_numeric(df[(df['Variable'] == 'Precipitation (mm)') & (df['Metric'] == 'MAPE')]['Before'].iloc[0], errors='coerce') / 100
        after_mape = pd.to_numeric(df[(df['Variable'] == 'Precipitation (mm)') & (df['Metric'] == 'MAPE')]['After'].iloc[0], errors='coerce') / 100
        before_bias = pd.to_numeric(df[(df['Variable'] == 'Precipitation (mm)') & (df['Metric'] == 'Bias')]['Before'].iloc[0], errors='coerce')
        after_bias = pd.to_numeric(df[(df['Variable'] == 'Precipitation (mm)') & (df['Metric'] == 'Bias')]['After'].iloc[0], errors='coerce')
        before_pod = df_pod_far[[c for c in df_pod_far.columns if c.startswith('Before_POD')]].stack().dropna().mean()
        after_pod = df_pod_far[[c for c in df_pod_far.columns if c.startswith('After_POD')]].stack().dropna().mean()
        before_far = df_pod_far[[c for c in df_pod_far.columns if c.startswith('Before_FAR')]].stack().dropna().mean()
        after_far = df_pod_far[[c for c in df_pod_far.columns if c.startswith('After_FAR')]].stack().dropna().mean()
        values = [
            calculate_improvement(before_rmse, after_rmse) if not pd.isna(before_rmse) and not pd.isna(after_rmse) else 0.0,
            calculate_improvement(before_mae, after_mae) if not pd.isna(before_mae) and not pd.isna(after_mae) else 0.0,
            calculate_improvement(before_mape, after_mape) if not pd.isna(before_mape) and not pd.isna(after_mape) else 0.0,
            calculate_improvement(before_bias, after_bias) if not pd.isna(before_bias) and not pd.isna(after_bias) else 0.0,
            ((after_pod - before_pod) / abs(before_pod) * 100 if before_pod != 0 and not pd.isna(before_pod) and not pd.isna(after_pod) else 0.0),
            ((before_far - after_far) / abs(before_far) * 100 if before_far != 0 and not pd.isna(before_far) and not pd.isna(after_far) else 0.0)
        ]
        all_values.extend([v for v in values if np.isfinite(v)])
        bar_width = 0.10
        bars = ax_precip.bar(x + i * (bar_width + 0.01), values, bar_width, label=f'Year {year}', color=colors[year], edgecolor='black')
        for bar, val in zip(bars, values):
            if np.isfinite(val):
                label = f'{val:+.1f}%' if val >= 0 else f'{val:.1f}%'
                x_text = bar.get_x() + bar.get_width() / 2
                y_text = bar.get_y() + bar.get_height() / 2 if val >= 0 else bar.get_y() + bar.get_height() / 2
                ax_precip.text(x_text, y_text, label, ha='center', va='center', rotation=90, color='black', fontsize=8)
    except Exception as e:
        print(f"Error processing precipitation improvement for {year}: {e}")
ax_precip.axhline(0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Add horizontal line at y=0
ax_precip.set_ylabel('Improvement (%)', fontsize=10)
ax_precip.set_xticks(x + (len(years) - 1) * (bar_width + 0.01) / 2)
ax_precip.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax_precip.tick_params(axis='x', length=4, width=0.5)
ax_precip.tick_params(axis='y', length=4, width=0.5)
ax_precip.spines['top'].set_visible(False)
ax_precip.spines['right'].set_visible(False)
ax_precip.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
# Set y-limits to include zero
y_min = min(all_values, default=-10) - 10
y_max = max(all_values, default=10) + 10
ax_precip.set_ylim(y_min, y_max)
plt.tight_layout()
output_file_precip = os.path.join(output_dir, "precipitation_improvement_comparison.png")
plt.savefig(output_file_precip, dpi=1200, bbox_inches='tight')
plt.close(fig_precip)
print(f"Graph for Precipitation improvement saved to {output_file_precip}")
# Plot for Temperature Improvement
fig_temp, ax_temp = plt.subplots(1, 1, figsize=(10, 6))
metrics_improv_temp = metrics
x = np.arange(len(metrics_improv_temp)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE', 'Bias']
all_values = []
for i, year in enumerate(years):
    try:
        df = pd.read_excel(paths[i], sheet_name="Summary")
        before_rmse = pd.to_numeric(df[(df['Variable'] == 'Temperature (°C)') & (df['Metric'] == 'RMSE')]['Before'].iloc[0], errors='coerce')
        after_rmse = pd.to_numeric(df[(df['Variable'] == 'Temperature (°C)') & (df['Metric'] == 'RMSE')]['After'].iloc[0], errors='coerce')
        before_mae = pd.to_numeric(df[(df['Variable'] == 'Temperature (°C)') & (df['Metric'] == 'MAE')]['Before'].iloc[0], errors='coerce')
        after_mae = pd.to_numeric(df[(df['Variable'] == 'Temperature (°C)') & (df['Metric'] == 'MAE')]['After'].iloc[0], errors='coerce')
        before_mape = pd.to_numeric(df[(df['Variable'] == 'Temperature (°C)') & (df['Metric'] == 'MAPE')]['Before'].iloc[0], errors='coerce') / 100
        after_mape = pd.to_numeric(df[(df['Variable'] == 'Temperature (°C)') & (df['Metric'] == 'MAPE')]['After'].iloc[0], errors='coerce') / 100
        before_bias = pd.to_numeric(df[(df['Variable'] == 'Temperature (°C)') & (df['Metric'] == 'Bias')]['Before'].iloc[0], errors='coerce')
        after_bias = pd.to_numeric(df[(df['Variable'] == 'Temperature (°C)') & (df['Metric'] == 'Bias')]['After'].iloc[0], errors='coerce')
        values = [
            calculate_improvement(before_rmse, after_rmse) if not pd.isna(before_rmse) and not pd.isna(after_rmse) else 0.0,
            calculate_improvement(before_mae, after_mae) if not pd.isna(before_mae) and not pd.isna(after_mae) else 0.0,
            calculate_improvement(before_mape, after_mape) if not pd.isna(before_mape) and not pd.isna(after_mape) else 0.0,
            calculate_improvement(before_bias, after_bias) if not pd.isna(before_bias) and not pd.isna(after_bias) else 0.0
        ]
        all_values.extend([v for v in values if np.isfinite(v)])
        bar_width = 0.10
        bars = ax_temp.bar(x + i * (bar_width + 0.01), values, bar_width, label=f'Year {year}', color=colors[year], edgecolor='black')
        for bar, val in zip(bars, values):
            if np.isfinite(val):
                label = f'{val:+.1f}%' if val >= 0 else f'{val:.1f}%'
                x_text = bar.get_x() + bar.get_width() / 2
                y_text = bar.get_y() + bar.get_height() / 2 if val >= 0 else bar.get_y() + bar.get_height() / 2
                ax_temp.text(x_text, y_text, label, ha='center', va='center', rotation=90, color='black', fontsize=8)
    except Exception as e:
        print(f"Error processing temperature improvement for {year}: {e}")
ax_temp.axhline(0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Add horizontal line at y=0
ax_temp.set_ylabel('Improvement (%)', fontsize=10)
ax_temp.set_xticks(x + (len(years) - 1) * (bar_width + 0.01) / 2)
ax_temp.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax_temp.tick_params(axis='x', length=4, width=0.5)
ax_temp.tick_params(axis='y', length=4, width=0.5)
ax_temp.spines['top'].set_visible(False)
ax_temp.spines['right'].set_visible(False)
ax_temp.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
# Set y-limits to include zero
y_min = min(all_values, default=-10) - 10
y_max = max(all_values, default=10) + 10
ax_temp.set_ylim(y_min, y_max)
plt.tight_layout()
output_file_temp = os.path.join(output_dir, "temperature_improvement_comparison.png")
plt.savefig(output_file_temp, dpi=1200, bbox_inches='tight')
plt.close(fig_temp)
print(f"Graph for Temperature improvement saved to {output_file_temp}")