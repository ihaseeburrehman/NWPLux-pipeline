import os
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import numpy as np
from datetime import datetime

def manual_crop(img, top=0, bottom=0, left=0, right=0):
    h, w = img.shape[0], img.shape[1]
    return img[top:h-bottom, left:w-right]

# Define folders
base_path = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2018_GFS_000_cv5"
gpm_folder = os.path.join(base_path, "GPM_IMERG")
before_folder = os.path.join(base_path, "Before_DA")
after_folder = os.path.join(base_path, "After_DA")
output_folder = os.path.join(base_path, "Combined_Plots")

# Ensure output folder exists
os.makedirs(output_folder, exist_ok=True)

# Loop over GPM images
for gpm_file in os.listdir(gpm_folder):
    if gpm_file.endswith(".png") and "GPM_IMERG" in gpm_file:
        try:
            # Extract and parse date from GPM filename
            raw_date = gpm_file.split("GPM_IMERG_")[1].replace(".png", "")
            dt = datetime.strptime(raw_date, "%Y_%m_%d_%H%M")  # <--- FIXED
            wrf_timestamp = dt.strftime("%Y-%m-%d_%H_%M_00")   # <--- FIXED
        except Exception as e:
            print(f"Failed to parse date from {gpm_file}: {e}")
            continue

        # Build full paths
        wrf_filename = f"wrfout_d01_{wrf_timestamp}.png"
        gpm_path = os.path.join(gpm_folder, gpm_file)
        before_path = os.path.join(before_folder, wrf_filename)
        after_path = os.path.join(after_folder, wrf_filename)

        if not os.path.exists(before_path) or not os.path.exists(after_path):
            print(f"Missing files for timestamp {wrf_timestamp}, skipping.")
            continue

        # Load and crop
        img_gpm = manual_crop(mpimg.imread(gpm_path), top=100, bottom=20, left=40, right=50)
        img_before = manual_crop(mpimg.imread(before_path), top=140, bottom=20, left=40, right=50)
        img_after = manual_crop(mpimg.imread(after_path), top=140, bottom=20, left=40, right=50)

        # Plot
        fig = plt.figure(figsize=(8, 4))
        ax1 = fig.add_axes([0.05, 0.55, 0.4, 0.4])
        ax2 = fig.add_axes([0.55, 0.55, 0.4, 0.4])
        ax3 = fig.add_axes([0.275, 0.05, 0.45, 0.4])
        ax1.imshow(img_gpm)
        ax2.imshow(img_before)
        ax3.imshow(img_after)
        for ax in [ax1, ax2, ax3]:
            ax.axis('off')

        # Labels
        ax1.text(0.5, -0.08, "(a) GPM (IMERG)", fontsize=10, color='black', ha='center', va='top', transform=ax1.transAxes)
        ax2.text(0.5, -0.08, "(b) WRF (Before DA)", fontsize=10, color='black', ha='center', va='top', transform=ax2.transAxes)
        ax3.text(0.5, -0.08, "(c) WRF (After DA)", fontsize=10, color='black', ha='center', va='top', transform=ax3.transAxes)

        # Save
        save_path = os.path.join(output_folder, f"GPM_vs_WRF_{wrf_timestamp}.png")
        plt.savefig(save_path, dpi=600, bbox_inches='tight')
        plt.close(fig)

print("✅ All matching image sets processed and saved.")
