#!/opt/homebrew/Caskroom/miniconda/base/bin/python
"""
LISFLOOD Hydrograph Comparison Script
Clean and minimal implementation
"""

import os
import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import rasterio
from datetime import datetime, timedelta
import re
import math
import xarray as xr
from pyproj import Transformer

def get_lcm(a, b):
    """Calculate Least Common Multiple of two numbers"""
    return abs(a * b) // math.gcd(int(a), int(b)) if a and b else 0

def filter_df_by_interval(df, start_time, interval_hours):
    """Filter dataframe to keep only rows that match the benchmark interval"""
    if df is None or df.empty:
        return df
    
    df = df.copy()
    # Calculate hours from start_time
    df['elapsed_h'] = (df['Time'] - start_time).dt.total_seconds() / 3600.0
    
    # Keep rows where elapsed_h is a multiple of interval_hours
    # Use a tolerance for floating point comparison
    tol = 1e-5
    df = df[np.abs((df['elapsed_h'] / interval_hours) - np.round(df['elapsed_h'] / interval_hours)) < tol].copy()
    
    return df.drop(columns=['elapsed_h'])

# Configuration
NWPLUX_DIR = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/on_hpc/manning_default/nwplux_alzette_sub_basin"
ECMWF_DIR = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/on_hpc/manning_default/nwplux_alzette_sub_basin_ecmwf"
OUTPUT_DIR = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/on_hpc/manning_default/plots/hydrographs"
OBS_FILE = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Stations_and_Observations/Discharge_data_walferdange_2021/Alzette_gauges_data_2021.xlsx"

EFAS_DIR = "/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Stations_and_Observations/EFAS_River_Discharge_forecasted_202107"
EFAS_ECMWF_FILE = os.path.join(EFAS_DIR, "driven_by_ECMWF.nc")
EFAS_DWD_FILE = os.path.join(EFAS_DIR, "driven_by_DWD.nc")

# START_TIME is now defined in main() interactively
RIVER_WIDTH = 20.0  # meters
CELL_SIZE = 10.0  # meters

STATIONS = {
    'Walferdange': {'x': 77256, 'y': 81571, 'type': 'water_level', 'sheet': 'Walferdange W15 07 2021'},
    'Steinsel': {'x': 77432, 'y': 82659, 'type': 'discharge', 'sheet': 'Steinsel Q15 VO 07 2021'},
    'Pfaffenthal': {'x': 77409, 'y': 76226, 'type': 'discharge', 'sheet': 'Pfaffenthal Q15 VO 07 2021'},
    'Livange': {'x': 76151, 'y': 65753, 'type': 'discharge', 'sheet': 'Livange Q60_07 2021'},
    'Hesperange': {'x': 78623, 'y': 72404, 'type': 'discharge', 'sheet': 'Hesperange Q60_07 2021'}
}

def extract_timestep(filename):
    """Extract timestep from filename (e.g., 6hr-0001 -> 1)"""
    match = re.search(r'-(\d+)', filename)
    return int(match.group(1)) if match else 0

def read_model_data_batch(model_dir, stations, interval_hours, start_time, spinup_hours=0):
    """Read data for ALL stations in a single pass through the files - much faster!"""
    qx_files = sorted(glob.glob(os.path.join(model_dir, "*Qx")), key=lambda x: extract_timestep(os.path.basename(x)))
    if not qx_files:
        return {}
    
    print(f"    Batch processing {len(qx_files)} files in {os.path.basename(model_dir)}...")
    
    # Pre-calculate pixel indices for all stations
    station_meta = {}
    with rasterio.open(qx_files[0]) as src:
        for name, info in stations.items():
            try:
                row, col = src.index(info['x'], info['y'])
                station_meta[name] = {
                    'row': row, 'col': col,
                    'transform': src.transform,
                    'shape': src.shape
                }
            except Exception as e:
                print(f"      Error calculating indices for {name}: {e}")
    
    # Initialize results
    results = {name: {'Time': [], 'Discharge': [], 'Depth': []} for name in station_meta.keys()}
    
    for idx, qx_file in enumerate(qx_files):
        elapsed_hours = idx * interval_hours
        
        # Skip spin-up period
        if elapsed_hours < spinup_hours:
            continue
        
        time = start_time + timedelta(hours=elapsed_hours)
        
        qy_file = qx_file.replace('Qx', 'Qy')
        wd_file = qx_file.replace('Qx', 'wd')
        
        if not os.path.exists(qy_file) or not os.path.exists(wd_file):
            continue

        try:
            with rasterio.open(qx_file) as src_qx, \
                 rasterio.open(qy_file) as src_qy, \
                 rasterio.open(wd_file) as src_wd:
                
                qx_data = src_qx.read(1)
                qy_data = src_qy.read(1)
                wd_data = src_wd.read(1)
                nodata = src_wd.nodata
                
                for name, meta in station_meta.items():
                    row, col = meta['row'], meta['col']
                    
                    # Get flow direction at station
                    qx_center = qx_data[row, col]
                    qy_center = qy_data[row, col]
                    
                    # Calculate perpendicular direction to flow
                    # Flow direction: (qx_center, qy_center)
                    # Perpendicular: (-qy_center, qx_center) - rotate 90° CCW
                    flow_mag = np.sqrt(qx_center**2 + qy_center**2)
                    
                    if flow_mag > 0.001:
                        # Use flow-perpendicular cross-section
                        perp_x = -qy_center / flow_mag
                        perp_y = qx_center / flow_mag
                    else:
                        # No flow: use horizontal cross-section (fallback)
                        perp_x = 1.0
                        perp_y = 0.0
                    
                    # Sample cells along perpendicular line (±RIVER_WIDTH/2)
                    half_width = RIVER_WIDTH / 2.0
                    num_samples = int(RIVER_WIDTH / CELL_SIZE) + 1
                    total_discharge = 0.0
                    
                    for i in range(num_samples):
                        # Distance along perpendicular from center
                        dist = -half_width + (i * CELL_SIZE)
                        
                        # Calculate sample position
                        sample_row = int(row + (dist * perp_y / CELL_SIZE))
                        sample_col = int(col + (dist * perp_x / CELL_SIZE))
                        
                        # Check bounds
                        if 0 <= sample_row < meta['shape'][0] and 0 <= sample_col < meta['shape'][1]:
                            qx_sample = qx_data[sample_row, sample_col]
                            qy_sample = qy_data[sample_row, sample_col]
                            
                            # Unit-width discharge magnitude
                            q_mag = np.sqrt(qx_sample**2 + qy_sample**2)
                            
                            # Add contribution: q (m²/s) × cell_width (m) = m³/s
                            total_discharge += q_mag * CELL_SIZE
                    
                    # Depth at station point
                    depth = wd_data[row, col]
                    if depth < 0 or depth == nodata: depth = 0.0
                    
                    results[name]['Time'].append(time)
                    results[name]['Discharge'].append(float(total_discharge))
                    results[name]['Depth'].append(float(depth))
        except Exception as e:
            print(f"      Error reading {os.path.basename(qx_file)}: {e}")
            
    # Convert to DataFrames
    return {name: pd.DataFrame(data) for name, data in results.items()}

def extract_efas_data(file_path, stations, target_times):
    """
    Extract river discharge data from EFAS forecast datasets.
    Handles 4D dis06 variable (step, time, y, x) and 2D valid_time (time, step).
    """
    if not os.path.exists(file_path):
        print(f"    Warning: EFAS file not found: {file_path}")
        return {name: pd.DataFrame(columns=['Time', 'Discharge']) for name in stations}

    print(f"    Processing EFAS file: {os.path.basename(file_path)}...")
    ds = xr.open_dataset(file_path)
    transformer = Transformer.from_crs("EPSG:2169", "EPSG:4326", always_xy=True)

    # Get spatial coordinates (2D)
    efas_lats = ds.latitude.values
    efas_lons = ds.longitude.values

    # Get temporal coordinates
    valid_times = ds.valid_time.values  # (time, step)
    valid_times_flat = valid_times.flatten()

    results = {}
    for name, info in stations.items():
        # 1. Spatial Selection (LUREF to WGS84)
        lon_target, lat_target = transformer.transform(info['x'], info['y'])

        # Calculate Euclidean distance to find nearest grid point
        dist = np.sqrt((efas_lats - lat_target)**2 + (efas_lons - lon_target)**2)
        y_idx, x_idx = np.unravel_index(np.argmin(dist), dist.shape)

        station_times = []
        station_discharges = []

        for t_target in target_times:
            # 2. Time Selection (Search flat 2D valid_time array)
            # Find closest valid_time
            t_diff = np.abs(valid_times_flat - np.datetime64(t_target))
            min_diff_idx = np.argmin(t_diff)

            # Unravel to find (time_idx, step_idx)
            # Note: valid_time is (time, step)
            time_idx, step_idx = np.unravel_index(min_diff_idx, valid_times.shape)

            # Extract dis06 at indices
            # Dimensions: (step, time, y, x)
            val = ds.dis06.isel(step=step_idx, time=time_idx, y=y_idx, x=x_idx).values

            station_times.append(t_target)
            station_discharges.append(float(val))

        results[name] = pd.DataFrame({
            'Time': station_times,
            'Discharge': station_discharges
        })

    ds.close()
    return results

def read_observed_data(station_name, station_info):
    """Read observed data from Excel"""
    df = pd.read_excel(OBS_FILE, sheet_name=station_info['sheet'], skiprows=16)
    
    # Parse time (columns 0=Date, 1=Time)
    df['DateTime_Local'] = pd.to_datetime(
        df.iloc[:, 0].astype(str) + ' ' + df.iloc[:, 1].astype(str),
        format='%d.%m.%y %H:%M:%S', errors='coerce'
    )
    
    # Convert Luxembourg Summer Time (UTC+2) to UTC
    df['Time'] = df['DateTime_Local'] - timedelta(hours=2)
    
    # Get value (column 2)
    value_str = df.iloc[:, 2].astype(str).str.replace(',', '.').replace('---', '')
    df['Value'] = pd.to_numeric(value_str, errors='coerce')
    
    if station_info['type'] == 'water_level':
        df['Discharge'] = df['Value'] / 100.0  # cm to m
    else:
        df['Discharge'] = df['Value']
    
    return df[['Time', 'Discharge']].dropna()

def calculate_metrics(obs, sim):
    """
    Calculate error metrics (NSE, KGE-2012, RMSE, etc.)
    """
    # 1. Alignment: Merge on Time to ensure strict timestamp matching
    #    obs_clean and sim_clean must contain 'Time' and 'Discharge'
    merged = pd.merge(obs, sim, on='Time', suffixes=('_obs', '_sim'), how='inner')
    
    if len(merged) < 2:
        return {}
    
    # Extract arrays
    o = merged['Discharge_obs'].values
    s = merged['Discharge_sim'].values
    
    # 2. Basic Stats (Use ddof=1 for sample standard deviation)
    mean_o = np.mean(o)
    mean_s = np.mean(s)
    std_o = np.std(o, ddof=1)
    std_s = np.std(s, ddof=1)
    
    # epsilon to avoid division by zero
    eps = 1e-10
    
    # 3. NSE Calculation
    # NSE = 1 - ( MSE / Variance_Obs )
    numerator = np.sum((s - o)**2)
    denominator = np.sum((o - mean_o)**2)
    nse = 1 - (numerator / (denominator + eps))
    
    # 4. KGE' (2012) Calculation
    # r = Correlation coefficient
    # beta = Bias ratio (mu_s / mu_o)
    # gamma = Variability ratio (CV_s / CV_o)
    
    if std_o == 0 or mean_o == 0:
        kge = -np.inf # Undefined if observation is constant or zero mean
    else:
        r = np.corrcoef(o, s)[0, 1] if len(o) > 1 else 0
        beta = mean_s / (mean_o + eps)
        
        # Gamma calculation (CV_s / CV_o)
        cv_s = std_s / (mean_s + eps)
        cv_o = std_o / (mean_o + eps)
        gamma = cv_s / (cv_o + eps)
        
        kge = 1 - np.sqrt((r - 1)**2 + (beta - 1)**2 + (gamma - 1)**2)

    # 5. Other Metrics
    rmse = np.sqrt(np.mean((s - o)**2))
    mae = np.mean(np.abs(s - o))
    bias = mean_s - mean_o # Additive bias
    
    # SMAPE (Symmetric Mean Absolute Percentage Error)
    # Note: Added epsilon to denominator to handle cases where s=0 and o=0
    smape = 100 * np.mean(np.abs(s - o) / ((np.abs(s) + np.abs(o)) / 2 + eps))
    
    # 6. Peak Analysis
    # Note: This finds the global maximum in the window. 
    # Ensure your window is an "Event" window, not a continuous year.
    obs_peak = np.max(o)
    sim_peak = np.max(s)
    
    # Peak Discharge Error (%)
    pde = ((sim_peak - obs_peak) / (obs_peak + eps)) * 100
    
    # Peak Timing Error (hours)
    obs_peak_time = merged['Time'].iloc[np.argmax(o)]
    sim_peak_time = merged['Time'].iloc[np.argmax(s)]
    pte = (sim_peak_time - obs_peak_time).total_seconds() / 3600
    
    # 7. Relative Metrics (%)
    # Normalized by the mean of observations to give context as a percentage
    rrmse = (rmse / (mean_o + eps)) * 100
    rmae = (mae / (mean_o + eps)) * 100

    return {
        'RMSE': rmse, 
        'MAE': mae, 
        'RRMSE': rrmse,
        'RMAE': rmae,
        'Bias': bias, 
        'SMAPE': smape,
        'NSE': nse, 
        'KGE': kge, 
        'PDE': pde, 
        'PTE': pte,
        'obs_peak': obs_peak, 
        'sim_peak': sim_peak
    }

def plot_hydrograph(station_name, nwp_df, ecm_df, obs_df, output_dir, benchmark_int=6):
    """Create simple hydrograph plot with consistent time range and interval"""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # All dataframes should already be filtered and aligned in main()
    # But we calculate range here for x-axis limits
    all_times = []
    if not nwp_df.empty: all_times.extend([nwp_df['Time'].min(), nwp_df['Time'].max()])
    if not ecm_df.empty: all_times.extend([ecm_df['Time'].min(), ecm_df['Time'].max()])
    if not obs_df.empty: all_times.extend([obs_df['Time'].min(), obs_df['Time'].max()])
    
    if not all_times:
        return
        
    time_start = min(all_times)
    time_end = max(all_times)
    
    if not obs_df.empty:
        ax.plot(obs_df['Time'], obs_df['Discharge'], 'r-', linewidth=2, label='Observed', alpha=0.8)
    
    if not nwp_df.empty:
        metric = 'Depth' if station_name == 'Walferdange' else 'Discharge'
        ax.plot(nwp_df['Time'], nwp_df[metric], 'g-', marker='o', markersize=4, label='NWPLux', alpha=0.8)
    
    if not ecm_df.empty:
        metric = 'Depth' if station_name == 'Walferdange' else 'Discharge'
        ax.plot(ecm_df['Time'], ecm_df[metric], 'b-', marker='s', markersize=4, label='ECMWF', alpha=0.8)
    
    # Format
    ylabel = 'Water Depth (m)' if station_name == 'Walferdange' else 'Discharge (m³/s)'
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_xlabel('Time (UTC)', fontsize=12)
    ax.set_title(f'{station_name}', fontsize=14, fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Set x-axis formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b-%d\n%H:%M'))
    
    # Dynamic grid lines: use benchmark interval for major grid lines
    # If benchmark interval is small (e.g. 1h), we might want to use a multiple
    grid_interval = benchmark_int
    if grid_interval < 3:
        grid_interval *= 3  # Don't crowd the axis too much
    
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=int(grid_interval)))
    
    # Set x-axis limits to the common range
    ax.set_xlim(time_start, time_end)
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{station_name.lower()}_hydrograph.png'), dpi=200)
    plt.close()

def plot_discharge_stations_multi_panel(station_data_dict, output_dir):
    """
    Create a 2x2 multi-panel figure for 4 discharge stations.
    Layout: Row 1: Steinsel, Pfaffenthal | Row 2: Hesperange, Livange
    Single shared legend at bottom, horizontal orientation.
    """
    from matplotlib.gridspec import GridSpec
    
    # Define station order: [top-left, top-right, bottom-left, bottom-right]
    station_order = ['Steinsel', 'Pfaffenthal', 'Hesperange', 'Livange']
    
    # Create figure with GridSpec for better control
    fig = plt.figure(figsize=(14, 10))
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.size'] = 10
    
    # Create 2x2 grid for subplots, leave space at bottom for legend
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.25, bottom=0.12)
    
    axes = []
    for i, station_name in enumerate(station_order):
        row = i // 2
        col = i % 2
        ax = fig.add_subplot(gs[row, col])
        axes.append(ax)
        
        data = station_data_dict.get(station_name, {})
        nwp_df = data.get('nwp', pd.DataFrame())
        ecm_df = data.get('ecm', pd.DataFrame())
        obs_df = data.get('obs', pd.DataFrame())
        
        # Find time range
        all_times = []
        if not nwp_df.empty: all_times.extend([nwp_df['Time'].min(), nwp_df['Time'].max()])
        if not ecm_df.empty: all_times.extend([ecm_df['Time'].min(), ecm_df['Time'].max()])
        if not obs_df.empty: all_times.extend([obs_df['Time'].min(), obs_df['Time'].max()])
        
        if not all_times:
            continue
        
        time_start = min(all_times)
        time_end = max(all_times)
        
        # Plot data
        if not obs_df.empty:
            ax.plot(obs_df['Time'], obs_df['Discharge'], 'r-', linewidth=2, label='Observed', alpha=0.8)
        
        if not nwp_df.empty:
            ax.plot(nwp_df['Time'], nwp_df['Discharge'], 'g-', marker='o', markersize=3, label='NWPLux', alpha=0.8)
        
        if not ecm_df.empty:
            ax.plot(ecm_df['Time'], ecm_df['Discharge'], 'b-', marker='s', markersize=3, label='ECMWF', alpha=0.8)
        
        # Plot EFAS Forecasts
        efas_ecm_df = data.get('efas_ecm', pd.DataFrame())
        efas_dwd_df = data.get('efas_dwd', pd.DataFrame())
        
        if not efas_ecm_df.empty:
            ax.plot(efas_ecm_df['Time'], efas_ecm_df['Discharge'], color='darkorange', linestyle='--', linewidth=1.5, label='EFAS (ECMWF)', alpha=0.8)
        if not efas_dwd_df.empty:
            ax.plot(efas_dwd_df['Time'], efas_dwd_df['Discharge'], color='purple', linestyle='--', linewidth=1.5, label='EFAS (DWD)', alpha=0.8)
        
        # Formatting
        ax.set_title(f'({chr(97+i)}) {station_name}', fontsize=11, fontweight='bold', loc='left')
        ax.set_ylabel('Discharge (m³/s)', fontsize=10)
        
        # Grid lines every 6 hours
        ax.grid(True, alpha=0.3, which='both', linestyle=':')
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))  # Labels every 12h
        ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))   # Grid every 6h
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b\n%H:%M'))
        
        # Only show x-label on bottom row
        if row == 1:
            ax.set_xlabel('Time (UTC)', fontsize=10)
        
        ax.set_xlim(time_start, time_end)
        
        # Rotate x-tick labels for readability
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=9)
    
    # Create single shared legend at the bottom
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=5, fontsize=10, 
               frameon=True, bbox_to_anchor=(0.5, 0.02))
    
    # Save figure
    output_file = os.path.join(output_dir, 'discharge_stations_comparison.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"\n✓ Multi-panel discharge figure saved: {output_file}")

def plot_walferdange_single(station_data_dict, output_dir):
    """
    Create a single panel figure for Walferdange water level station.
    Single horizontal legend at bottom.
    """
    station_name = 'Walferdange'
    data = station_data_dict.get(station_name, {})
    nwp_df = data.get('nwp', pd.DataFrame())
    ecm_df = data.get('ecm', pd.DataFrame())
    obs_df = data.get('obs', pd.DataFrame())
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.size'] = 10
    
    # Find time range
    all_times = []
    if not nwp_df.empty: all_times.extend([nwp_df['Time'].min(), nwp_df['Time'].max()])
    if not ecm_df.empty: all_times.extend([ecm_df['Time'].min(), ecm_df['Time'].max()])
    if not obs_df.empty: all_times.extend([obs_df['Time'].min(), obs_df['Time'].max()])
    
    if not all_times:
        print(f"⚠️  No data for {station_name}")
        plt.close()
        return
    
    time_start = min(all_times)
    time_end = max(all_times)
    
    # Plot data
    if not obs_df.empty:
        ax.plot(obs_df['Time'], obs_df['Discharge'], 'r-', linewidth=2, label='Observed', alpha=0.8)
    
    if not nwp_df.empty:
        ax.plot(nwp_df['Time'], nwp_df['Depth'], 'g-', marker='o', markersize=3, label='NWPLux', alpha=0.8)
    
    if not ecm_df.empty:
        ax.plot(ecm_df['Time'], ecm_df['Depth'], 'b-', marker='s', markersize=3, label='ECMWF', alpha=0.8)
    
    # Formatting
    ax.set_title(f'{station_name}', fontsize=14, fontweight='bold')
    ax.set_ylabel('Water Depth (m)', fontsize=11)
    ax.set_xlabel('Time (UTC)', fontsize=11)
    
    # Grid lines every 6 hours, labels every 12 hours
    ax.grid(True, alpha=0.3, which='both', linestyle=':')
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))
    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b\n%H:%M'))
    
    ax.set_xlim(time_start, time_end)
    
    # Rotate x-tick labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=10)
    
    # Legend at bottom, horizontal
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, 
              fontsize=11, frameon=True)
    
    # Save figure
    output_file = os.path.join(output_dir, 'walferdange_water_level.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✓ Walferdange figure saved: {output_file}")


def main():
    print("="*60)
    print("LISFLOOD HYDROGRAPH COMPARISON")
    print("="*60)

    
    # Get simulation start time
    print("\n--- Simulation Configuration ---")
    start_year = int(input("Start Year [2021]: ") or 2021)
    start_month = int(input("Start Month [7]: ") or 7)
    start_day = int(input("Start Day [13]: ") or 13)
    start_hour = int(input("Start Hour [0]: ") or 0)
    
    start_time = datetime(start_year, start_month, start_day, start_hour)

    # Get intervals
    nwp_int = float(input("NWPLux interval (hours) [3]: ") or 3)
    ecm_int = float(input("ECMWF interval (hours) [6]: ") or 6)
    
    # Get spin-up time
    spinup_input = input("Spin-up time to exclude (hours) [0]: ") or 0
    spinup_hours = float(spinup_input)
    
    # Calculate benchmark interval (use max or LCM if they don't divide)
    if ecm_int % nwp_int == 0:
        benchmark_int = ecm_int
    elif nwp_int % ecm_int == 0:
        benchmark_int = nwp_int
    else:
        benchmark_int = get_lcm(nwp_int, ecm_int)
        
    print(f"\nConfiguration: Start={start_time}, NWPLux={nwp_int}h, ECMWF={ecm_int}h, Spin-up={spinup_hours}h")
    print(f"Benchmark interval for consistent plot: {benchmark_int}h")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Fast Batch Reading
    print("\nReading NWPLux data...")
    all_nwp_data = read_model_data_batch(NWPLUX_DIR, STATIONS, nwp_int, start_time, spinup_hours)
    
    print("\nReading ECMWF data...")
    all_ecm_data = read_model_data_batch(ECMWF_DIR, STATIONS, ecm_int, start_time, spinup_hours)
    
    # EFAS Processing
    print("\nReading EFAS Forecast data...")
    # Generate list of target times based on NWPLux/ECMWF coverage
    # We'll use a 6-hour interval for EFAS to match its dis06 resolution
    all_times_possible = []
    for station_name in STATIONS:
        if station_name in all_nwp_data and not all_nwp_data[station_name].empty:
            all_times_possible.extend(all_nwp_data[station_name]['Time'].tolist())
    
    if all_times_possible:
        min_time = min(all_times_possible)
        max_time = max(all_times_possible)
        target_times_efas = pd.date_range(start=min_time, end=max_time, freq='6H').tolist()
        
        all_efas_ecm_data = extract_efas_data(EFAS_ECMWF_FILE, STATIONS, target_times_efas)
        all_efas_dwd_data = extract_efas_data(EFAS_DWD_FILE, STATIONS, target_times_efas)
    else:
        all_efas_ecm_data = {name: pd.DataFrame() for name in STATIONS}
        all_efas_dwd_data = {name: pd.DataFrame() for name in STATIONS}
    
    all_stats = {}
    all_obs_data = {}  # Store observed data for publication figures

    
    for station_name, station_info in STATIONS.items():
        print(f"\nProcessing {station_name}...")
        
        # Get pre-read data
        nwp = all_nwp_data.get(station_name, pd.DataFrame())
        ecm = all_ecm_data.get(station_name, pd.DataFrame())
        
        # Read observations
        obs = read_observed_data(station_name, station_info)
        
        # 1. Filter all data to the benchmark interval
        nwp = filter_df_by_interval(nwp, start_time, benchmark_int)
        ecm = filter_df_by_interval(ecm, start_time, benchmark_int)
        obs = filter_df_by_interval(obs, start_time, benchmark_int)
        
        # 2. Align start and end times across all three
        available_dfs = [df for df in [nwp, ecm, obs] if not df.empty]
        if len(available_dfs) >= 2:
            common_start = max(df['Time'].min() for df in available_dfs)
            common_end = min(df['Time'].max() for df in available_dfs)
            
            # Filter all to this common historical range
            nwp = nwp[(nwp['Time'] >= common_start) & (nwp['Time'] <= common_end)]
            ecm = ecm[(ecm['Time'] >= common_start) & (ecm['Time'] <= common_end)]
            obs = obs[(obs['Time'] >= common_start) & (obs['Time'] <= common_end)]
            
            print(f"    Aligned range: {common_start} to {common_end}")
        else:
            print(f"    ⚠️ No overlapping data found! Check if start date ({start_time}) matches model and observed data.")
            if not nwp.empty: print(f"      NWPLux range: {nwp['Time'].min()} to {nwp['Time'].max()}")
            if not ecm.empty: print(f"      ECMWF range: {ecm['Time'].min()} to {ecm['Time'].max()}")
            if not obs.empty: print(f"      Observed range: {obs['Time'].min()} to {obs['Time'].max()}")
        
        # Store processed data for publication figures
        all_nwp_data[station_name] = nwp
        all_ecm_data[station_name] = ecm
        all_obs_data[station_name] = obs
        
        # Store EFAS data (already aligned by target_times in extract_efas_data)
        efas_ecm = all_efas_ecm_data.get(station_name, pd.DataFrame())
        efas_dwd = all_efas_dwd_data.get(station_name, pd.DataFrame())
        
        all_efas_ecm_data[station_name] = efas_ecm
        all_efas_dwd_data[station_name] = efas_dwd
        
        # Calculate metrics

        metric_col = 'Depth' if station_info['type'] == 'water_level' else 'Discharge'
        
        # Prepare data for metrics (only Time and Discharge columns)
        nwp_for_metrics = nwp[['Time', metric_col]].rename(columns={metric_col: 'Discharge'}) if not nwp.empty else pd.DataFrame()
        ecm_for_metrics = ecm[['Time', metric_col]].rename(columns={metric_col: 'Discharge'}) if not ecm.empty else pd.DataFrame()
        
        nwp_metrics = calculate_metrics(obs, nwp_for_metrics) if not nwp_for_metrics.empty else {}
        ecm_metrics = calculate_metrics(obs, ecm_for_metrics) if not ecm_for_metrics.empty else {}
        
        # EFAS Metrics
        # Filter EFAS to match observed range for metrics
        obs_times = obs['Time'].unique()
        efas_ecm_aligned = efas_ecm[efas_ecm['Time'].isin(obs_times)]
        efas_dwd_aligned = efas_dwd[efas_dwd['Time'].isin(obs_times)]
        
        # ONLY calculate EFAS metrics for discharge stations
        # (EFAS only provides discharge, comparing it to water level (m) is incorrect)
        if station_info['type'] == 'discharge':
            efas_ecm_metrics = calculate_metrics(obs, efas_ecm_aligned) if not efas_ecm_aligned.empty else {}
            efas_dwd_metrics = calculate_metrics(obs, efas_dwd_aligned) if not efas_dwd_aligned.empty else {}
        else:
            efas_ecm_metrics = {}
            efas_dwd_metrics = {}
        
        all_stats[station_name] = {
            'NWPLux': nwp_metrics, 
            'ECMWF': ecm_metrics,
            'EFAS_ECMWF': efas_ecm_metrics,
            'EFAS_DWD': efas_dwd_metrics
        }
        
        # Metrics calculated and stored

    
    # Create publication-quality multi-panel figures
    print("\n" + "="*60)
    print("CREATING PUBLICATION FIGURES")
    print("="*60)
    
    # Prepare data dictionary for multi-panel plots
    station_data_for_plots = {}
    for station_name in STATIONS:
        nwp = all_nwp_data[station_name]
        ecm = all_ecm_data[station_name]
        obs = all_obs_data[station_name]
        station_data_for_plots[station_name] = {
            'nwp': nwp,
            'ecm': ecm,
            'obs': obs,
            'efas_ecm': all_efas_ecm_data.get(station_name, pd.DataFrame()),
            'efas_dwd': all_efas_dwd_data.get(station_name, pd.DataFrame())
        }

    
    # Create 4-panel discharge stations figure
    plot_discharge_stations_multi_panel(station_data_for_plots, OUTPUT_DIR)
    
    # Create Walferdange single panel figure
    plot_walferdange_single(station_data_for_plots, OUTPUT_DIR)

    
    # Print Individual Summary
    print("\n" + "="*60)
    print("INDIVIDUAL STATION STATISTICS")
    print("="*60)
    
    for station, stats in all_stats.items():
        print(f"\n{station}:")
        for model in ['NWPLux', 'ECMWF', 'EFAS_ECMWF', 'EFAS_DWD']:
            m = stats.get(model, {})
            if m:
                print(f"  {model}: RMSE={m['RMSE']:.2f} ({m['RRMSE']:.1f}%), MAE={m['MAE']:.2f} ({m['RMAE']:.1f}%), NSE={m['NSE']:.3f}, KGE={m['KGE']:.3f}")

    # Time-Series Tables and CSV Export
    print("\n" + "="*80)
    print("STATION TIME-SERIES DATA (MINIMAL)")
    print("="*80)
    
    csv_dir = os.path.join(OUTPUT_DIR, "flood_simulations_csv")
    os.makedirs(csv_dir, exist_ok=True)
    
    for station_name, info in STATIONS.items():
        nwp = all_nwp_data[station_name]
        ecm = all_ecm_data[station_name]
        obs = all_obs_data[station_name]
        
        if nwp.empty and ecm.empty and obs.empty:
            continue
            
        metric_col = 'Depth' if info['type'] == 'water_level' else 'Discharge'
        unit = "m" if info['type'] == 'water_level' else "m3/s"
        
        # Merge data on matchable times (NWPLux, ECMWF, EFAS, and Observed)
        merged_ts = pd.merge(
            nwp[['Time', metric_col]].rename(columns={metric_col: 'NWPLux'}),
            ecm[['Time', metric_col]].rename(columns={metric_col: 'ECMWF'}),
            on='Time', how='outer'
        )
        
        # Add EFAS
        efas_ecm = all_efas_ecm_data.get(station_name, pd.DataFrame())
        efas_dwd = all_efas_dwd_data.get(station_name, pd.DataFrame())
        
        if not efas_ecm.empty:
            merged_ts = pd.merge(merged_ts, efas_ecm[['Time', 'Discharge']].rename(columns={'Discharge': 'EFAS_ECMWF'}), on='Time', how='outer')
        if not efas_dwd.empty:
            merged_ts = pd.merge(merged_ts, efas_dwd[['Time', 'Discharge']].rename(columns={'Discharge': 'EFAS_DWD'}), on='Time', how='outer')
        
        # Use 'Discharge' for obs as per read_observed_data function
        merged_ts = pd.merge(
            merged_ts,
            obs[['Time', 'Discharge']].rename(columns={'Discharge': 'Observed'}),
            on='Time', how='outer'
        ).sort_values('Time')
        
        if merged_ts.empty:
            continue
            
        # Format for display
        merged_ts['Date'] = merged_ts['Time'].dt.strftime('%d %B')
        merged_ts['Time_Str'] = merged_ts['Time'].dt.strftime('%H:%M')
        
        # Print minimal table
        print(f"\n📍 STATION: {station_name} ({unit})")
        cols_to_show = ['Date', 'Time_Str', 'NWPLux', 'ECMWF', 'EFAS_ECMWF', 'EFAS_DWD', 'Observed']
        display_cols = [c for c in cols_to_show if c in merged_ts.columns]
        display_df = merged_ts[display_cols]
        print(display_df.to_string(index=False, float_format=lambda x: f"{x:8.3f}"))
        
        # Save to CSV
        csv_path = os.path.join(csv_dir, f"{station_name.lower()}_timeseries.csv")
        save_cols = ['Time', 'Date', 'NWPLux', 'ECMWF', 'EFAS_ECMWF', 'EFAS_DWD', 'Observed']
        actual_save_cols = [c for c in save_cols if c in merged_ts.columns]
        merged_ts[actual_save_cols].to_csv(csv_path, index=False)
        
    print(f"\n✓ All station CSVs saved to: {csv_dir}")
    
    # Overall Metrics Summary Table 1
    print("\n" + "="*80)
    print("TABLE 1: ERROR MAGNITUDE")
    print("="*80)
    
    summary_rows_1 = []
    summary_rows_2 = []
    for model in ['NWPLux', 'ECMWF', 'EFAS_ECMWF', 'EFAS_DWD']:
        # Metrics for Table 1: Include all available (Water Level + Discharge)
        # Note: EFAS metrics for Walferdange will be empty/excluded here automatically
        metrics_all = [all_stats[s][model] for s in STATIONS if all_stats[s].get(model)]
        
        # Metrics for Table 2: Exclude Walferdange (Water Level)
        metrics_discharge = [all_stats[s][model] for s in STATIONS 
                             if all_stats[s].get(model) and STATIONS[s]['type'] == 'discharge']
        
        if metrics_all:
            row1 = {
                'Model': model,
                'RMSE': np.mean([m['RMSE'] for m in metrics_all]),
                'RRMSE(%)': np.mean([m['RRMSE'] for m in metrics_all]),
                'MAE': np.mean([m['MAE'] for m in metrics_all]),
                'RMAE(%)': np.mean([m['RMAE'] for m in metrics_all]),
                'Bias': np.mean([m['Bias'] for m in metrics_all]),
                'SMAPE/100': np.mean([m['SMAPE'] for m in metrics_all]) / 100.0
            }
            summary_rows_1.append(row1)
            
        if metrics_discharge:
            row2 = {
                'Model': model,
                'NSE': np.mean([m['NSE'] for m in metrics_discharge]),
                'KGE': np.mean([m['KGE'] for m in metrics_discharge]),
                'PDE(%)': np.mean([m['PDE'] for m in metrics_discharge]),
                'PTE(h)': np.mean([m['PTE'] for m in metrics_discharge])
            }
            summary_rows_2.append(row2)
    
    if summary_rows_1:
        df1 = pd.DataFrame(summary_rows_1)
        print(df1[['Model', 'RMSE', 'RRMSE(%)', 'MAE', 'RMAE(%)', 'Bias', 'SMAPE/100']].to_string(index=False, float_format=lambda x: f"{x:8.3f}"))
        print("-" * 80)
        print("Interpretation (Table 1):")
        print("  RMSE/MAE/Bias: Absolute error (Lower is better)")
        print("  RRMSE(%)/RMAE(%): Relative error as % of Mean Flow (Lower is better)")
        print("  SMAPE/100: 0.0=Perf, <0.1=Exc, 0.1-0.2=Good, 0.2-0.5=Satisfactory, >0.5=Poor")
        
    print("\n" + "="*80)
    print("TABLE 2: EFFICIENCY & PEAKS")
    print("="*80)
    
    if summary_rows_2:
        df2 = pd.DataFrame(summary_rows_2)
        print(df2[['Model', 'NSE', 'KGE', 'PDE(%)', 'PTE(h)']].to_string(index=False, float_format=lambda x: f"{x:8.3f}"))
        print("-" * 80)
        print("Interpretation (Table 2):")
        print("  NSE: 1.0=Perf, >0.8=Exc, 0.65-0.8=Good, 0.5-0.65=Satisfactory, <0.5=Poor")
        print("  KGE: 1.0=Perf, >0.8=Exc, 0.6-0.8=Good, 0.4-0.6=Satisfactory, <0.4=Poor")
        print("  PDE(%): 0%=Perf, ±5%=Exc, ±10%=Good, ±20%=Satisfactory")
        print("  PTE(h): 0h=Perf, ±1h=Exc, ±3h=Good, ±6h=Satisfactory")
    
    print("="*80)
    print(f"✓ Analysis complete. Plots saved to: {OUTPUT_DIR}\n")

if __name__ == "__main__":
    main()
