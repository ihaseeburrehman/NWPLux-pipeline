
import numpy as np
import os

# Configuration
SOURCE_FILE = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/ready_for_simulation/manning.n.ascii"

print("="*60)
print("MANNING COEFFICIENT BATCH PATCHER")
print("="*60)

print(f"\nReading source: {SOURCE_FILE}")
if not os.path.exists(SOURCE_FILE):
    print("Error: Source file not found!")
    exit(1)

# Read header
header_lines = []
with open(SOURCE_FILE, 'r') as f:
    for i in range(6):
        line = f.readline()
        header_lines.append(line)
        
    # Read data
    print("Loading data... (this may take a few seconds)")
    data = np.loadtxt(f)

print(f"Data Loaded. Shape: {data.shape}")

# 1. Identify unique values
unique_vals, counts = np.unique(np.round(data, 4), return_counts=True)
nodata_val = -9999
mask_nodata = unique_vals != nodata_val
unique_vals = unique_vals[mask_nodata]
counts = counts[mask_nodata]

# 2. Sequential input for replacements
print("\n--- Manning Values Modification Table ---")
print("Instructions: Enter a new value for each Manning class, or press [Enter] to keep it as is.")
print("-" * 80)
print(f"{'Current (n)':<15} {'Cell Count':<15} {'New Manning (n)'}")
print("-" * 80)

replacements = {}
any_changes = False

for val, count in zip(unique_vals, counts):
    user_input = input(f"{val:<15.4f} {count:<15,} -> ")
    if user_input.strip():
        try:
            new_val = float(user_input)
            if not np.isclose(val, new_val, atol=1e-5):
                replacements[val] = new_val
                any_changes = True
        except ValueError:
            print(f"  ⚠️ Invalid input '{user_input}', keeping {val}")

# 3. Apply changes and save
if any_changes:
    print("\nApplying changes...")
    for old_v, new_v in replacements.items():
        mask = np.isclose(data, old_v, atol=1e-4)
        data[mask] = new_v
        print(f"  {old_v:.4f} -> {new_v:.4f} ({np.sum(mask):,} cells)")

    # Handle Saving
    default_target = SOURCE_FILE.replace(".ascii", "_updated.ascii")
    print(f"\nTarget File Selection:")
    target_file = input(f"Enter target file path [Default: {default_target}]: ") or default_target
    
    # Ensure target directory exists
    os.makedirs(os.path.dirname(target_file), exist_ok=True)
    
    print(f"Writing to: {target_file}...")
    with open(target_file, 'w') as f:
        for line in header_lines:
            f.write(line)
        np.savetxt(f, data, fmt='%.4f', delimiter=' ')
        
    print("Done. File saved successfully.")
else:
    print("\nNo changes requested. Exiting.")
