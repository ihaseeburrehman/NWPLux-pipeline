#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

# -*- coding: utf-8 -*-
"""
Created on Wed Sep 17 16:22:25 2025
@author: haseeb.rehman
"""

# Ask user what to plot
print("What would you like to plot?")
print("1. Precipitation only")
print("2. Both Precipitation and Temperature")
choice = input("Enter choice (1 or 2): ").strip()
plot_both = (choice == '2')
import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
# Scientific styling with minimal look
plt.style.use('seaborn-white')
# Colors for the two cases
colors = {
    'No DA': '#707577', # grey
    'After DA': '#1990d8' # blue
}
# Define paths and cases
case_paths = {
    "No DA": "/Users/haseeb.rehman/Desktop/For_Animation/4th_year/2021_ERA5_cv5/statistics_analysis/metrics_tables.xlsx",
    "After DA": "/Users/haseeb.rehman/Desktop/For_Animation/4th_year/2021_ERA5_cv5/statistics_analysis/metrics_tables.xlsx"
}
# Variables and metrics
variables = ['Precipitation (mm)', 'Temperature (°C)']
metrics = ['RMSE', 'MAE', 'SMAPE', 'Bias'] # SMAPE means MAPE/100 in Excel
# Create result DataFrame for metrics
multi_index = pd.MultiIndex.from_product([variables, metrics + ['POD', 'FAR']], names=['Variable', 'Metric'])
result = pd.DataFrame(index=case_paths.keys(), columns=multi_index)
# Extract data from Excel
for case, path in case_paths.items():
    try:
        df = pd.read_excel(path, sheet_name="Summary")
        for var in variables:
            for metric in metrics:
                excel_metric = 'MAPE' if metric == 'SMAPE' else metric
                row = df[(df['Variable'] == var) & (df['Metric'] == excel_metric)]
                if not row.empty:
                    col = 'Before' if 'No DA' in case else 'After'
                    value = pd.to_numeric(row[col].iloc[0], errors='coerce')
                    if var == 'Precipitation (mm)' and metric == 'SMAPE':
                        value = value / 100 # Convert to SMAPE fraction
                    result.loc[case, (var, metric)] = value
                else:
                    result.loc[case, (var, metric)] = np.nan
    except Exception as e:
        print(f"Error processing {case} Summary: {e}")
    try:
        df_pod_far = pd.read_excel(path, sheet_name="Precipitation_POD_FAR")
        prefix = 'Before_' if 'No DA' in case else 'After_'
        pod_cols = [col for col in df_pod_far.columns if col.startswith(prefix + 'POD')]
        far_cols = [col for col in df_pod_far.columns if col.startswith(prefix + 'FAR')]
        pod = df_pod_far[pod_cols].stack().dropna().mean()
        far = df_pod_far[far_cols].stack().dropna().mean()
        result.loc[case, ('Precipitation (mm)', 'POD')] = pod
        result.loc[case, ('Precipitation (mm)', 'FAR')] = far
    except Exception as e:
        print(f"Error extracting POD/FAR for {case}: {e}")
        result.loc[case, ('Precipitation (mm)', 'POD')] = np.nan
        result.loc[case, ('Precipitation (mm)', 'FAR')] = np.nan
# Create improvement DataFrame
improvement = pd.DataFrame(index=["After DA"], columns=multi_index)
# Calculate improvements only between No DA and After DA
try:
    df_no = pd.read_excel(case_paths['No DA'], sheet_name="Summary")
    df_after = pd.read_excel(case_paths['After DA'], sheet_name="Summary")
    for var in variables:
        for metric in metrics:
            excel_metric = 'MAPE' if metric == 'SMAPE' else metric
            before_row = df_no[(df_no['Variable'] == var) & (df_no['Metric'] == excel_metric)]
            after_row = df_after[(df_after['Variable'] == var) & (df_after['Metric'] == excel_metric)]
            if not before_row.empty and not after_row.empty:
                before = pd.to_numeric(before_row['Before'].iloc[0], errors='coerce')
                after = pd.to_numeric(after_row['After'].iloc[0], errors='coerce')
                if metric in ['RMSE', 'MAE', 'SMAPE']:
                    imp = ((before - after) / abs(before)) * 100 if before != 0 else 0
                else: # Bias improvement
                    imp = ((abs(before) - abs(after)) / abs(before)) * 100 if before != 0 else 0
                improvement.loc['After DA', (var, metric)] = imp
    # POD & FAR improvements
    df_no_podfar = pd.read_excel(case_paths['No DA'], sheet_name="Precipitation_POD_FAR")
    df_after_podfar = pd.read_excel(case_paths['After DA'], sheet_name="Precipitation_POD_FAR")
    before_pod = df_no_podfar[[c for c in df_no_podfar.columns if c.startswith('Before_POD')]].stack().dropna().mean()
    after_pod = df_after_podfar[[c for c in df_after_podfar.columns if c.startswith('After_POD')]].stack().dropna().mean()
    before_far = df_no_podfar[[c for c in df_no_podfar.columns if c.startswith('Before_FAR')]].stack().dropna().mean()
    after_far = df_after_podfar[[c for c in df_after_podfar.columns if c.startswith('After_FAR')]].stack().dropna().mean()
    imp_pod = ((after_pod - before_pod) / abs(before_pod)) * 100 if before_pod != 0 else 0
    imp_far = ((before_far - after_far) / abs(before_far)) * 100 if before_far != 0 else 0
    improvement.loc['After DA', ('Precipitation (mm)', 'POD')] = imp_pod
    improvement.loc['After DA', ('Precipitation (mm)', 'FAR')] = imp_far
except Exception as e:
    print(f"Error calculating improvement: {e}")
# Plotting
output_dir = "/Users/haseeb.rehman/Desktop/For_Animation/4th_year/Miscs/2021_ERA5_cv5"
os.makedirs(output_dir, exist_ok=True)
# Plot 1: Metrics Comparison (Precip + Temp)
fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
fig1.subplots_adjust(hspace=0.3)
bar_width = 0.17  # Reduced by 30%
spacing = 0.0  # No space between adjacent bars
metric_spacing = 0.65  # Reduced by 30% (default is 1.0)
# Precipitation
var = 'Precipitation (mm)'
metrics_precip = ['RMSE', 'MAE', 'SMAPE', 'Bias', 'POD', 'FAR']
x = np.arange(len(metrics_precip)) * metric_spacing
for i, case in enumerate(case_paths.keys()):
    values = [result.loc[case, (var, metric)] for metric in metrics_precip]
    ax1.bar(x + i * (bar_width + spacing), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar, val in zip(ax1.patches[i*len(metrics_precip):(i+1)*len(metrics_precip)], values):
        if not pd.isna(val):
            ax1.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=13)
ax1.set_xticks(x + (len(case_paths.keys()) - 1) * (bar_width + spacing) / 2)
ax1.set_xticklabels(metrics_precip, fontsize=14)
ax1.set_ylabel('Precip Metrics', fontsize=16)
ax1.tick_params(axis='both', labelsize=14)
ax1.axhline(y=0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Hash line at y=0
ax1.legend()

# Temperature (only if plotting both)
if plot_both:
    var = 'Temperature (°C)'
    metrics_temp = ['RMSE', 'MAE', 'SMAPE', 'Bias']
    x = np.arange(len(metrics_temp)) * metric_spacing
    for i, case in enumerate(case_paths.keys()):
        values = [result.loc[case, (var, metric)] for metric in metrics_temp]
        ax2.bar(x + i * (bar_width + spacing), values, bar_width, label=case, color=colors[case], edgecolor='black')
        for bar, val in zip(ax2.patches[i*len(metrics_temp):(i+1)*len(metrics_temp)], values):
            if not pd.isna(val):
                ax2.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=13)
    ax2.set_xticks(x + (len(case_paths.keys()) - 1) * (bar_width + spacing) / 2)
    ax2.set_xticklabels(metrics_temp)
    ax2.set_ylabel('Temp Metrics')
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Hash line at y=0
    ax2.legend()
else:
    ax2.axis('off')  # Hide temperature subplot if only precipitation
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "metrics_comparison.png"), dpi=1200, bbox_inches='tight')
plt.close(fig1)
# Plot 2: POD & FAR Comparison
fig2, ax3 = plt.subplots(figsize=(6, 6))
metrics_podfar = ['POD', 'FAR']
x = np.arange(len(metrics_podfar))
for i, case in enumerate(case_paths.keys()):
    values = [result.loc[case, ('Precipitation (mm)', metric)] for metric in metrics_podfar]
    ax3.bar(x + i * (bar_width + spacing), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar, val in zip(ax3.patches[i*len(metrics_podfar):(i+1)*len(metrics_podfar)], values):
        if not pd.isna(val):
            ax3.text(bar.get_x() + bar.get_width()/2, val/2, f'{val:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=13)
ax3.set_xticks(x + (len(case_paths.keys()) - 1) * (bar_width + spacing) / 2)
ax3.set_xticklabels(metrics_podfar)
ax3.set_ylabel('Detection Metrics')
ax3.axhline(y=0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Hash line at y=0
ax3.legend()
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "POD_FAR_comparison.png"), dpi=1200, bbox_inches='tight')
plt.close(fig2)
# Plot 3: Improvements
fig3, (ax4, ax5) = plt.subplots(2, 1, figsize=(10, 10))
fig3.subplots_adjust(hspace=0.3)
# Precipitation Improvements
var = 'Precipitation (mm)'
metrics_improv = metrics + ['POD', 'FAR']
x = np.arange(len(metrics_improv))
values = [improvement.loc['After DA', (var, metric)] for metric in metrics_improv]
ax4.bar(x, values, bar_width, color=colors['After DA'], edgecolor='black')
for bar, val in zip(ax4.patches, values):
    if np.isfinite(val):
        label = f'{val:+.1f}%' if val >= 0 else f'{val:.1f}%'
        ax4.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=13)
ax4.set_xticks(x)
ax4.set_xticklabels(metrics_improv)
ax4.set_ylabel('Precip Improvement (%)')
ax4.axhline(y=0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Hash line at y=0

# Temperature Improvements (only if plotting both)
if plot_both:
    var = 'Temperature (°C)'
    metrics_improv_temp = metrics
    x = np.arange(len(metrics_improv_temp))
    values = [improvement.loc['After DA', (var, metric)] for metric in metrics_improv_temp]
    ax5.bar(x, values, bar_width, color=colors['After DA'], edgecolor='black')
    for bar, val in zip(ax5.patches, values):
        if np.isfinite(val):
            label = f'{val:+.1f}%' if val >= 0 else f'{val:.1f}%'
            ax5.text(bar.get_x() + bar.get_width()/2, val/2, label, ha='center', va='center', rotation=90, color='black', fontsize=13)
    ax5.set_xticks(x)
    ax5.set_xticklabels(metrics_improv_temp)
    ax5.set_ylabel('Temp Improvement (%)')
    ax5.axhline(y=0, color='black', linestyle='--', linewidth=0.8, zorder=0)  # Hash line at y=0
else:
    ax5.axis('off')  # Hide temperature subplot if only precipitation
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "improvement_comparison.png"), dpi=1200, bbox_inches='tight')
plt.close(fig3)
print("All plots saved to", output_dir)