import rasterio
import numpy as np
from scipy.ndimage import median_filter

# ---------------------------------------------------------
# 1. Load DEM
# ---------------------------------------------------------
dem_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Alzette_sub_basin_5m.asc"
out_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Walferdange/Alzette_river_basin/sub_basins/5m/Alzette_sub_basin_5m_fixed.asc"

with rasterio.open(dem_path) as src:
    dem = src.read(1).astype(np.float32)
    profile = src.profile
    res = src.res[0] 
    nodata = src.nodata

# ---------------------------------------------------------
# 2. Precision Slope Function (Rise/Run) with NoData handling
# ---------------------------------------------------------
def get_slope_ratio(data, res, nodata_val=None):
    """Calculates slope as m/m (Rise/Run), masking NoData areas"""
    # Create a copy and mask NoData
    data_masked = np.copy(data)
    if nodata_val is not None:
        # Set NoData areas to NaN so they don't contribute to gradient
        data_masked[data == nodata_val] = np.nan
    
    gy, gx = np.gradient(data_masked, res)
    slope = np.sqrt(gx**2 + gy**2)
    
    # Mask out slopes at NoData boundaries (they're artifacts)
    if nodata_val is not None:
        # Any cell with a NoData neighbor gets invalid slope
        from scipy.ndimage import binary_dilation
        nodata_mask = (data == nodata_val)
        boundary_mask = binary_dilation(nodata_mask, iterations=2)
        slope[boundary_mask] = 0.0
    
    return slope

# ---------------------------------------------------------
# 3. Multi-Pass Aggressive Repair
# ---------------------------------------------------------
# At 5m resolution, slopes up to 2.0 m/m (63° or 200%) are realistic
# Anything above that is likely data artifacts or sub-grid features
max_allowed_slope = 2.0 
current_slope = get_slope_ratio(dem, res, nodata)

# Identify extreme pixels
steep_mask = (current_slope > max_allowed_slope) & (dem != nodata)
print(f"Detected {np.sum(steep_mask)} pixels with extreme slopes (> {max_allowed_slope} m/m).")
print(f"Maximum slope detected: {np.max(current_slope):.2f} m/m")

# When slopes are >2000, you have data artifacts (vertical cliffs or NoData spikes)
# Need aggressive multi-pass smoothing
dem_fixed = np.copy(dem)

# Pass 1: Fill obvious artifacts with median filter (size 5x5)
print("\nPass 1: Removing data artifacts with median filter (5x5)...")
artifact_mask = (current_slope > 100) & (dem != nodata)
if np.sum(artifact_mask) > 0:
    smoothed_5x5 = median_filter(dem, size=5)
    dem_fixed[artifact_mask] = smoothed_5x5[artifact_mask]
    print(f"  Fixed {np.sum(artifact_mask)} extreme artifact pixels")

# Pass 2: Smooth moderately steep areas (3x3)
print("Pass 2: Smoothing steep slopes (3x3)...")
current_slope = get_slope_ratio(dem_fixed, res, nodata)
steep_mask = (current_slope > max_allowed_slope) & (dem_fixed != nodata)
if np.sum(steep_mask) > 0:
    smoothed_3x3 = median_filter(dem_fixed, size=3)
    dem_fixed[steep_mask] = smoothed_3x3[steep_mask]
    print(f"  Smoothed {np.sum(steep_mask)} steep pixels")

# Pass 3: Final polish - if still issues, use larger kernel
print("Pass 3: Final verification pass...")
iteration = 0
max_iterations = 5
while iteration < max_iterations:
    current_slope = get_slope_ratio(dem_fixed, res, nodata)
    steep_mask = (current_slope > max_allowed_slope) & (dem_fixed != nodata)
    
    if np.sum(steep_mask) == 0:
        print(f"  Converged after {iteration} iterations!")
        break
    
    # Iteratively smooth remaining steep areas
    smoothed = median_filter(dem_fixed, size=3)
    dem_fixed[steep_mask] = smoothed[steep_mask]
    iteration += 1
    print(f"  Iteration {iteration}: {np.sum(steep_mask)} pixels remaining")

# ---------------------------------------------------------
# 4. Final Verification (The "Everything OK" Check)
# ---------------------------------------------------------
final_slope = get_slope_ratio(dem_fixed, res, nodata)
extreme_count = np.sum((final_slope > max_allowed_slope) & (dem_fixed != nodata))

print("\n" + "="*50)
print("VERIFICATION REPORT")
print("="*50)
print(f"Original Max Slope: {np.max(current_slope):.2f} m/m")
print(f"Fixed Max Slope:    {np.max(final_slope):.2f} m/m")
print(f"Pixels Modified:    {np.sum(dem != dem_fixed)}")

if extreme_count == 0:
    print("\n✓ STATUS: SUCCESS - No extreme slopes detected.")
    print("  Your LISFLOOD time-step (dt) should now be stable (~5-10s).")
else:
    print(f"\n⚠ STATUS: WARNING - {extreme_count} pixels still exceed {max_allowed_slope} m/m.")
    print("  These may be legitimate features (cliffs, dams).")
    print("  Consider manual inspection or setting max_allowed_slope = 2.0")
print("="*50)

# ---------------------------------------------------------
# 5. Save Results
# ---------------------------------------------------------
with rasterio.open(out_path, "w", **profile) as dst:
    dst.write(dem_fixed, 1)

print(f"\nCorrected DEM saved to: {out_path}")