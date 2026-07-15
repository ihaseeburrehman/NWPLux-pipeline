#!/usr/bin/env python3

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

"""
Automatic ECMWF Operational HRES Download
Downloads all 24 files automatically using ECMWF API
"""

import os
import sys
from datetime import datetime, timedelta

# Try to import ECMWF API
try:
    from ecmwfapi import ECMWFService
except ImportError:
    print("ERROR: ecmwf-api-client not installed!")
    print("Installing now...")
    os.system("pip install ecmwf-api-client")
    from ecmwfapi import ECMWFService

# Configuration
output_dir = '/Users/haseeb.rehman/Documents/Misc/Data_Datasets/Radar_and_Weather/ecmwf_operational_forecast/ecmwf_operational_raw_accumulations'
os.makedirs(output_dir, exist_ok=True)

server = ECMWFService("mars")

print("="*70)
print("ECMWF OPERATIONAL HRES AUTO-DOWNLOAD")
print("="*70)
print(f"Period: 2021-07-13 to 2021-07-18")
print(f"Output: {output_dir}")
print("="*70)

# Generate all requests (July 10-18 = 9 days = 36 files)
requests = []
start_date = datetime(2021, 7, 10)  # Fixed: was July 13, should be July 10

for day_offset in range(9):  # 9 days (July 10-18)
    current_date = start_date + timedelta(days=day_offset)
    date_str = current_date.strftime('%Y-%m-%d')
    
    # Run 00: Step 6 (06 UTC) and Step 12 (12 UTC)
    for step in [6, 12]:
        valid_time = current_date + timedelta(hours=step)
        filename = valid_time.strftime('%Y_%m_%d_%H_00_00.nc')
        requests.append({
            'date': date_str, 'time': '00', 'step': str(step),
            'filename': filename, 'valid': valid_time.strftime('%Y-%m-%d %H UTC')
        })
        
    # Run 12: Step 6 (18 UTC) and Step 12 (00 UTC next day)
    for step in [6, 12]:
        valid_time = current_date + timedelta(hours=12 + step)
        filename = valid_time.strftime('%Y_%m_%d_%H_00_00.nc')
        requests.append({
            'date': date_str, 'time': '12', 'step': str(step),
            'filename': filename, 'valid': valid_time.strftime('%Y-%m-%d %H UTC')
        })

# Sort and filter to exactly July 10-18 range (4 per day = 36 files)
requests = [r for r in requests if start_date <= datetime.strptime(r['filename'][:10], '%Y_%m_%d') <= datetime(2021, 7, 19)]
# Filter to keep only valid times up to 2021-07-18 18 UTC and 2021-07-19 00 UTC
requests = [r for r in requests if datetime.strptime(r['filename'][:13], '%Y_%m_%d_%H') <= datetime(2021, 7, 19, 0)]
requests.sort(key=lambda x: x['filename'])

print(f"\nDownloading {len(requests)} files (4 per day)...\n")

success_count = 0
error_count = 0

for idx, req in enumerate(requests, 1):
    output_file = os.path.join(output_dir, req['filename'])
    if os.path.exists(output_file):
        print(f"[{idx}/{len(requests)}] ✓ SKIP: {req['filename']}")
        success_count += 1
        continue
    
    print(f"[{idx}/{len(requests)}] Downloading: {req['filename']}")
    try:
        # Use execute() for ECMWFService("mars")
        server.execute({
            'class': 'od',
            'stream': 'oper',
            'type': 'fc',
            'levtype': 'sfc',
            'param': '228.128',
            'date': req['date'],
            'time': req['time'],
            'step': req['step'],
            'grid': '0.1/0.1',
            'format': 'netcdf'
        }, output_file)
        
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / 1024 / 1024
            print(f"        ✓ Success ({file_size:.2f} MB)\n")
        else:
            print("        ✗ ERROR: Download completed but file not found\n")
        success_count += 1
        
    except Exception as e:
        print(f"        ✗ ERROR: {e}\n")
        error_count += 1

print("="*70)
print("DOWNLOAD COMPLETE")
print("="*70)
print(f"Success: {success_count}/24")
print(f"Errors:  {error_count}/24")
print(f"Output:  {output_dir}")
print("="*70)

# List downloaded files
files = sorted([f for f in os.listdir(output_dir) if f.endswith('.nc')])
print(f"\nDownloaded files ({len(files)}):")
for f in files:
    size = os.path.getsize(os.path.join(output_dir, f)) / 1024 / 1024
    print(f"  {f} ({size:.2f} MB)")
