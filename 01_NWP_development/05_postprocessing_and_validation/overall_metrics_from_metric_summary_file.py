import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
# Scientific styling with minimal look
plt.style.use('seaborn-white')
# Specify softened (less bright) colors
colors = {
    'No DA': '#A52A2A', # muted red
    'CONV': '#DAA520', # muted yellow
    'ZTD': '#20B2AA', # muted cyan
    'CONV + ZTD': '#228B22' # muted green
}
# Define paths and cases
case_paths = {
    "No DA": "/Users/haseeb.rehman/Desktop/For_Animation/3rd_year/1_month_simulation_2021_new_GFS_000_cv5/statistics_analysis/metrics_tables.xlsx",
    "CONV": "/Users/haseeb.rehman/Desktop/For_Animation/4th_year/2021_without_ZTD_cv3/statistics_analysis/metrics_tables.xlsx",
    "ZTD": "/Users/haseeb.rehman/Desktop/For_Animation/4th_year/2021_with_ZTD_only_cv3/statistics_analysis/metrics_tables.xlsx",
    "CONV + ZTD": "/Users/haseeb.rehman/Desktop/For_Animation/3rd_year/1_month_simulation_2021_new_GFS_000/statistics_analysis/metrics_tables.xlsx"
}
variables = ['Precipitation (mm)', 'Temperature (°C)']
metrics = ['RMSE', 'MAE', 'SMAPE', 'Bias'] # Display as SMAPE, but read MAPE from Excel
# Create result DataFrame for metrics
multi_index = pd.MultiIndex.from_product([variables, metrics + ['POD', 'FAR']], names=['Variable', 'Metric'])
result = pd.DataFrame(index=case_paths.keys(), columns=multi_index)
# Extract data from Summary and Precipitation_POD_FAR
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
                        value = value / 100
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
# Create result DataFrame for improvement
improvement = pd.DataFrame(index=case_paths.keys(), columns=multi_index)
for case, path in case_paths.items():
    try:
        df = pd.read_excel(path, sheet_name="Summary")
        for var in variables:
            for metric in metrics:
                excel_metric = 'MAPE' if metric == 'SMAPE' else metric
                row = df[(df['Variable'] == var) & (df['Metric'] == excel_metric)]
                if not row.empty:
                    before = pd.to_numeric(row['Before'].iloc[0], errors='coerce')
                    after = pd.to_numeric(row['After'].iloc[0], errors='coerce')
                    if np.isnan(before) or np.isnan(after):
                        imp = np.nan
                    else:
                        if metric in ['RMSE', 'MAE', 'SMAPE']:
                            imp = ((before - after) / abs(before)) * 100 if before != 0 else 0
                        else: # Bias
                            imp = ((abs(before) - abs(after)) / abs(before)) * 100 if before != 0 else 0
                    improvement.loc[case, (var, metric)] = imp
    except Exception as e:
        print(f"Error processing improvement for {case} Summary: {e}")
    try:
        df_pod_far = pd.read_excel(path, sheet_name="Precipitation_POD_FAR")
        pod_cols_b = [col for col in df_pod_far.columns if col.startswith('Before_POD')]
        far_cols_b = [col for col in df_pod_far.columns if col.startswith('Before_FAR')]
        pod_cols_a = [col for col in df_pod_far.columns if col.startswith('After_POD')]
        far_cols_a = [col for col in df_pod_far.columns if col.startswith('After_FAR')]
        before_pod = df_pod_far[pod_cols_b].stack().dropna().mean() if pod_cols_b else np.nan
        after_pod = df_pod_far[pod_cols_a].stack().dropna().mean() if pod_cols_a else np.nan
        before_far = df_pod_far[far_cols_b].stack().dropna().mean() if far_cols_b else np.nan
        after_far = df_pod_far[far_cols_a].stack().dropna().mean() if far_cols_a else np.nan
        print(f"Debug - {case}: Before POD = {before_pod}, After POD = {after_pod}, Before FAR = {before_far}, After FAR = {after_far}")
        if not np.isnan(before_pod) and not np.isnan(after_pod):
            imp_pod = ((after_pod - before_pod) / abs(before_pod)) * 100 if before_pod != 0 else 0
        else:
            imp_pod = np.nan
        if not np.isnan(before_far) and not np.isnan(after_far):
            imp_far = ((before_far - after_far) / abs(before_far)) * 100 if before_far != 0 else 0
        else:
            imp_far = np.nan
        print(f"Debug - {case}: POD Improvement = {imp_pod}%, FAR Improvement = {imp_far}%")
        improvement.loc[case, ('Precipitation (mm)', 'POD')] = imp_pod
        improvement.loc[case, ('Precipitation (mm)', 'FAR')] = imp_far
    except Exception as e:
        print(f"Error processing POD/FAR improvement for {case}: {e}")
        improvement.loc[case, ('Precipitation (mm)', 'POD')] = np.nan
        improvement.loc[case, ('Precipitation (mm)', 'FAR')] = np.nan
# Plot 1: Overall Comparison Metrics
fig1, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 12), sharex=False)
fig1.subplots_adjust(hspace=0.3)
bar_width = 0.10
# Precipitation Metrics
var = 'Precipitation (mm)'
metrics_precip = ['RMSE', 'MAE', 'SMAPE', 'Bias']
x = np.arange(len(metrics_precip)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']
for i, case in enumerate(case_paths.keys()):
    values = [result.loc[case, (var, metric)] for metric in metrics_precip]
    bars = ax1.bar(x + i * (bar_width + 0.01), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            ax1.text(bar.get_x() + bar.get_width()/2, height/2, f'{height:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
ax1.set_ylabel('Metric Value (mm)', fontsize=10)
ax1.set_xticks(x + (len(case_paths.keys()) - 1) * (bar_width + 0.01) / 2)
ax1.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax1.tick_params(axis='x', length=4, width=0.5)
ax1.tick_params(axis='y', length=4, width=0.5)
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
ax1.axhline(0, color='lightgray', linewidth=0.8, linestyle='--', alpha=0.7)
# Temperature Metrics
var = 'Temperature (°C)'
metrics_temp = ['RMSE', 'MAE', 'SMAPE', 'Bias']
x = np.arange(len(metrics_temp)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']
for i, case in enumerate(case_paths.keys()):
    values = [result.loc[case, (var, metric)] for metric in metrics_temp]
    bars = ax2.bar(x + i * (bar_width + 0.01), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            ax2.text(bar.get_x() + bar.get_width()/2, height/2, f'{height:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
ax2.set_ylabel('Metric Value (°C)', fontsize=10)
ax2.set_xticks(x + (len(case_paths.keys()) - 1) * (bar_width + 0.01) / 2)
ax2.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax2.tick_params(axis='x', length=4, width=0.5)
ax2.tick_params(axis='y', length=4, width=0.5)
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
ax2.axhline(0, color='lightgray', linewidth=0.8, linestyle='--', alpha=0.7)
plt.tight_layout()
output_dir = "/Users/haseeb.rehman/Desktop/For_Animation/4th_year/Miscs"
os.makedirs(output_dir, exist_ok=True)
output_file1 = os.path.join(output_dir, "overall_metrics_comparison.png")
plt.savefig(output_file1, dpi=300, bbox_inches='tight')
plt.close(fig1)
print(f"Graph 1 saved to {output_file1}")
# Plot 2: POD and FAR Metrics
fig2, ax3 = plt.subplots(1, 1, figsize=(6, 6))
var = 'Precipitation (mm)'
metrics_podfar = ['POD', 'FAR']
x = np.arange(len(metrics_podfar)) * 0.6
custom_labels = ['POD', 'FAR']
for i, case in enumerate(case_paths.keys()):
    values = [result.loc[case, (var, metric)] for metric in metrics_podfar]
    bars = ax3.bar(x + i * (bar_width + 0.01), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            ax3.text(bar.get_x() + bar.get_width()/2, height/2, f'{height:.2f}', ha='center', va='center', rotation=90, color='black', fontsize=8)
ax3.set_ylabel('Value', fontsize=10)
ax3.set_xticks(x + (len(case_paths.keys()) - 1) * (bar_width + 0.01) / 2)
ax3.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax3.tick_params(axis='x', length=4, width=0.5)
ax3.tick_params(axis='y', length=4, width=0.5)
ax3.spines['top'].set_visible(False)
ax3.spines['right'].set_visible(False)
ax3.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
plt.tight_layout()
output_file2 = os.path.join(output_dir, "precipitation_detection_metrics.png")
plt.savefig(output_file2, dpi=300, bbox_inches='tight')
plt.close(fig2)
print(f"Graph 2 saved to {output_file2}")
# Plot 3: Improvement Metrics for Precipitation
fig3, ax4 = plt.subplots(1, 1, figsize=(10, 6))
var = 'Precipitation (mm)'
metrics_improv = metrics + ['POD', 'FAR']
x = np.arange(len(metrics_improv)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE', 'Bias', 'POD', 'FAR']
cases_for_improvement = [case for case in case_paths.keys() if case != 'No DA'] # Exclude No DA
for i, case in enumerate(cases_for_improvement):
    values = [improvement.loc[case, (var, metric)] for metric in metrics_improv]
    bars = ax4.bar(x + i * (bar_width + 0.01), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            label = f'{height:+.1f}%' if height >= 0 else f'{height:.1f}%'
            ax4.text(bar.get_x() + bar.get_width()/2, height/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)
ax4.set_ylabel('Improvement (%)', fontsize=10)
ax4.set_xticks(x + (len(cases_for_improvement) - 1) * (bar_width + 0.01) / 2)
ax4.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax4.tick_params(axis='x', length=4, width=0.5)
ax4.tick_params(axis='y', length=4, width=0.5)
ax4.spines['top'].set_visible(False)
ax4.spines['right'].set_visible(False)
ax4.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
ax4.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.7)
plt.tight_layout()
output_file3 = os.path.join(output_dir, "precipitation_improvement_comparison.png")
plt.savefig(output_file3, dpi=300, bbox_inches='tight')
plt.close(fig3)
print(f"Graph 3 saved to {output_file3}")
# Plot 4: Improvement Metrics for Temperature
fig4, ax5 = plt.subplots(1, 1, figsize=(10, 6))
var = 'Temperature (°C)'
metrics_improv_temp = metrics  # Only RMSE, MAE, SMAPE, Bias
x = np.arange(len(metrics_improv_temp)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE', 'Bias']
cases_for_improvement = [case for case in case_paths.keys() if case != 'No DA'] # Exclude No DA
for i, case in enumerate(cases_for_improvement):
    values = [improvement.loc[case, (var, metric)] for metric in metrics_improv_temp]
    bars = ax5.bar(x + i * (bar_width + 0.01), values, bar_width, label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            label = f'{height:+.1f}%' if height >= 0 else f'{height:.1f}%'
            ax5.text(bar.get_x() + bar.get_width()/2, height/2, label, ha='center', va='center', rotation=90, color='black', fontsize=8)
ax5.set_ylabel('Improvement (%)', fontsize=10)
ax5.set_xticks(x + (len(cases_for_improvement) - 1) * (bar_width + 0.01) / 2)
ax5.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax5.tick_params(axis='x', length=4, width=0.5)
ax5.tick_params(axis='y', length=4, width=0.5)
ax5.spines['top'].set_visible(False)
ax5.spines['right'].set_visible(False)
ax5.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)
ax5.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.7)
plt.tight_layout()

output_file4 = os.path.join(output_dir, "temperature_improvement_comparison.png")
plt.savefig(output_file4, dpi=300, bbox_inches='tight')
plt.close(fig4)
print(f"Graph 4 saved to {output_file4}")
# ============================================================
# Plot 5: Actual Metrics for Precipitation (All Cases, Absolute Values)
# ============================================================
fig5, ax6 = plt.subplots(1, 1, figsize=(10, 6))
var = 'Precipitation (mm)'
metrics_actual = metrics + ['POD', 'FAR']
x = np.arange(len(metrics_actual)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias', 'POD', 'FAR']

for i, case in enumerate(case_paths.keys()):
    values = [result.loc[case, (var, metric)] for metric in metrics_actual]
    bars = ax6.bar(x + i * (bar_width + 0.01), values, bar_width, 
                   label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            ax6.text(bar.get_x() + bar.get_width()/2, height/2, f'{height:.2f}', 
                     ha='center', va='center', rotation=90, color='black', fontsize=8)

ax6.set_ylabel('Metric Value', fontsize=10)
ax6.set_xticks(x + (len(case_paths.keys()) - 1) * (bar_width + 0.01) / 2)
ax6.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax6.tick_params(axis='x', length=4, width=0.5)
ax6.tick_params(axis='y', length=4, width=0.5)
ax6.spines['top'].set_visible(False)
ax6.spines['right'].set_visible(False)
ax6.axhline(0, color='lightgray', linewidth=0.8, linestyle='--', alpha=0.7)
ax6.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)

plt.tight_layout()
output_file5 = os.path.join(output_dir, "precipitation_actual_metrics_comparison.png")
plt.savefig(output_file5, dpi=300, bbox_inches='tight')
plt.close(fig5)
print(f"Graph 5 saved to {output_file5}")

# ============================================================
# Plot 6: Actual Metrics for Temperature (All Cases, Absolute Values)
# ============================================================
fig6, ax7 = plt.subplots(1, 1, figsize=(10, 6))
var = 'Temperature (°C)'
metrics_actual_temp = metrics  # only RMSE, MAE, SMAPE, Bias
x = np.arange(len(metrics_actual_temp)) * 0.6
custom_labels = ['RMSE', 'MAE', 'SMAPE/100', 'Bias']

for i, case in enumerate(case_paths.keys()):
    values = [result.loc[case, (var, metric)] for metric in metrics_actual_temp]
    bars = ax7.bar(x + i * (bar_width + 0.01), values, bar_width, 
                   label=case, color=colors[case], edgecolor='black')
    for bar in bars:
        height = bar.get_height()
        if np.isfinite(height):
            ax7.text(bar.get_x() + bar.get_width()/2, height/2, f'{height:.2f}', 
                     ha='center', va='center', rotation=90, color='black', fontsize=8)

ax7.set_ylabel('Metric Value (°C)', fontsize=10)
ax7.set_xticks(x + (len(case_paths.keys()) - 1) * (bar_width + 0.01) / 2)
ax7.set_xticklabels(custom_labels, rotation=0, fontsize=10)
ax7.tick_params(axis='x', length=4, width=0.5)
ax7.tick_params(axis='y', length=4, width=0.5)
ax7.spines['top'].set_visible(False)
ax7.spines['right'].set_visible(False)
ax7.axhline(0, color='lightgray', linewidth=0.8, linestyle='--', alpha=0.7)
ax7.legend(loc='upper right', frameon=True, edgecolor='black', fontsize=8)

plt.tight_layout()
output_file6 = os.path.join(output_dir, "temperature_actual_metrics_comparison.png")
plt.savefig(output_file6, dpi=300, bbox_inches='tight')
plt.close(fig6)
print(f"Graph 6 saved to {output_file6}")
