#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Calculate discharge and water depth at specific points from LISFLOOD output files.
Outputs a text file with discharge and depth values for each timestep.
"""

# =============================================================================
# CONFIGURATION - EDIT THESE VALUES
# =============================================================================

# Default directory containing Qx/Qy/wd files
DEFAULT_INPUT_DIR = "/Users/haseeb.rehman/Documents/Misc/Lisflood_walferdange/10m/walferdange_QVAR_ERA5_without_rain"

# Default DEM cell size (meters)
DEFAULT_CELL_SIZE = 10.0

# Discharge measurement points
# Add or modify points here: {'x': X_coord, 'y': Y_coord, 'width': river_width_m, 'name': 'Point_Name'}
DISCHARGE_POINTS = [
    {'x': 77207, 'y': 82073, 'width': 16, 'name': 'Steinsel_Outlet'},
    {'x': 77256, 'y': 81571, 'width': 24, 'name': 'Walferdange_station'}
]

# =============================================================================
# CODE BELOW - NO NEED TO EDIT
# =============================================================================

import os
import glob
import numpy as np
import rasterio
from pathlib import Path
import re

def calculate_discharge_and_depth(qx_file, qy_file, wd_file, points, cell_size):
    """Calculate discharge and water depth at specified points."""
    results = {}
    
    with rasterio.open(qx_file) as qx_src:
        for i, point in enumerate(points):
            x, y = point['x'], point['y']
            width = point.get('width', cell_size)
            
            # Get row/col from coordinates
            row, col = qx_src.index(x, y)
            
            # Read values
            qx = qx_src.read(1)[row, col]
            
            with rasterio.open(qy_file) as qy_src:
                qy = qy_src.read(1)[row, col]
            
            with rasterio.open(wd_file) as wd_src:
                depth = wd_src.read(1)[row, col]
            
            # Calculate discharge
            q_unit = np.sqrt(qx**2 + qy**2)  # m²/s
            Q_volumetric = q_unit * width     # m³/s
            
            results[f'Point_{i+1}'] = {
                'coords': (x, y),
                'width': width,
                'qx': qx,
                'qy': qy,
                'q_unit': q_unit,
                'discharge': Q_volumetric,
                'depth': depth
            }
    
    return results

def extract_timestep(filename):
    """Extract timestep number from filename."""
    match = re.search(r'-(\d+)', filename)
    if match:
        return int(match.group(1))
    return 0

def main():
    print("=" * 80)
    print("LISFLOOD Discharge & Depth Calculator")
    print("=" * 80)
    
    # Get input directory
    input_dir = input(f"\nEnter directory containing Qx/Qy/wd files\n[default: {DEFAULT_INPUT_DIR}]: ").strip()
    if not input_dir:
        input_dir = DEFAULT_INPUT_DIR
    
    if not os.path.exists(input_dir):
        print(f"Error: Directory not found: {input_dir}")
        return
    
    # Get cell size
    cell_size_input = input(f"\nEnter DEM cell size (meters) [default: {DEFAULT_CELL_SIZE}]: ").strip()
    cell_size = float(cell_size_input) if cell_size_input else DEFAULT_CELL_SIZE
    
    # Use points from configuration
    points = DISCHARGE_POINTS
    
    print(f"\n{'Point Name':<30} {'X':<12} {'Y':<12} {'Width (m)':<12}")
    print("-" * 70)
    for pt in points:
        print(f"{pt.get('name', 'Point'):<30} {pt['x']:<12.1f} {pt['y']:<12.1f} {pt['width']:<12.1f}")
    
    # Find all Qx files
    qx_pattern = os.path.join(input_dir, "*Qx")
    qx_files = sorted(glob.glob(qx_pattern), key=lambda x: extract_timestep(os.path.basename(x)))
    
    if not qx_files:
        print(f"\nError: No Qx files found in {input_dir}")
        return
    
    print(f"\nFound {len(qx_files)} timesteps")
    
    # Process all files
    all_results = []
    
    print("\nProcessing files...")
    for qx_file in qx_files:
        qy_file = qx_file.replace('.Qx', '.Qy')
        wd_file = qx_file.replace('.Qx', '.wd')
        
        if not os.path.exists(qy_file):
            print(f"Warning: Missing Qy file for {os.path.basename(qx_file)}")
            continue
        
        if not os.path.exists(wd_file):
            print(f"Warning: Missing .wd file for {os.path.basename(qx_file)}")
            continue
        
        filename = os.path.basename(qx_file).replace('.Qx', '')
        
        try:
            results = calculate_discharge_and_depth(qx_file, qy_file, wd_file, points, cell_size)
            
            row_data = {'filename': filename}
            for idx, (point_name, point_data) in enumerate(results.items()):
                pt_name = points[idx].get('name', point_name)
                row_data[f"{pt_name}_Q"] = point_data['discharge']
                row_data[f"{pt_name}_Depth"] = point_data['depth']
            
            all_results.append(row_data)
            
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")
            continue
    
    # Write output file
    output_file = os.path.join(input_dir, "discharge_depth_timeseries.txt")
    
    with open(output_file, 'w') as f:
        # Write header
        f.write(f"# Discharge and Water Depth from LISFLOOD output\n")
        f.write(f"# DEM cell size: {cell_size} m\n")
        f.write(f"# Points:\n")
        for pt in points:
            f.write(f"#   {pt.get('name', 'Point')}: X={pt['x']}, Y={pt['y']}, Width={pt['width']}m\n")
        f.write("#\n")
        
        # Column headers - Fixed width for proper alignment
        headers = [f"{'Filename':<20}"]
        for pt in points:
            pt_name = pt.get('name', 'Point')
            headers.append(f"{pt_name}_Q_m3s")
            headers.append(f"{pt_name}_Depth_m")
        f.write('\t'.join(headers) + '\n')
        
        # Write data with proper formatting
        for row in all_results:
            data_row = [f"{row['filename']:<20}"]
            for pt in points:
                pt_name = pt.get('name', 'Point')
                data_row.append(f"{row[f'{pt_name}_Q']:>12.4f}")
                data_row.append(f"{row[f'{pt_name}_Depth']:>12.4f}")
            f.write('\t'.join(data_row) + '\n')
    
    print(f"\n{'='*80}")
    print(f"SUCCESS! Results saved to:")
    print(f"{output_file}")
    print(f"{'='*80}")
    print(f"\nSummary:")
    print(f"  Total timesteps: {len(all_results)}")
    print(f"  Points analyzed: {len(points)}")
    
    # Show sample results
    if all_results:
        print(f"\nSample results (first 3 timesteps):")
        print(f"{'Filename':<20} {'Point':<30} {'Q (m³/s)':>12} {'Depth (m)':>12}")
        print("-" * 80)
        for row in all_results[:3]:
            for pt in points:
                pt_name = pt.get('name', 'Point')
                q = row[f'{pt_name}_Q']
                d = row[f'{pt_name}_Depth']
                print(f"{row['filename']:<20} {pt_name:<30} {q:>12.4f} {d:>12.4f}")
        if len(all_results) > 3:
            print(f"... ({len(all_results) - 3} more timesteps)")

if __name__ == "__main__":
    main()
