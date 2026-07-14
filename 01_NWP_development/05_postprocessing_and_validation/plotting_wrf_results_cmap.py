import os
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import cartopy.feature as cfeature
import contextily as ctx
from matplotlib.colors import BoundaryNorm
from netCDF4 import Dataset

# Define file paths (update these to match your system)
path = "/Users/haseeb.rehman/Documents/Misc/WRF_from_HPC/3rd_year/1_month_simulation_2018_GFS_000_cv5/After_DA"
output_folder = '/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/1_month_simulation_2018_GFS_000_cv5/After_DA'
shpfilename = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_UTM.shp'

# Create custom colormap with white at 0
orig_cmap = cm.get_cmap("GnBu")
colors = [(1, 1, 1)] + [orig_cmap(i) for i in range(1, 256)]
custom_cmap = mcolors.LinearSegmentedColormap.from_list("Custom_GnBu", colors, N=256)

# Process each file in the directory
for filename in os.listdir(path):
    if not filename.startswith('wrfout'):
        continue
    nc_file = os.path.join(path, filename)
    try:
        nc = Dataset(nc_file, 'r')
    except Exception as e:
        print(f"Failed to open {filename}: {e}")
        continue

    # Get variables
    try:
        rainc = nc.variables['RAINC'][:]
        rainnc = nc.variables['RAINNC'][:]
        rainsh = nc.variables['RAINSH'][:]
        xlat = nc.variables['XLAT'][:]
        xlong = nc.variables['XLONG'][:]
    except KeyError as e:
        print(f"Missing variable in {filename}: {e}")
        continue

    # Determine number of time steps
    n_time = rainc.shape[0]

    # Check if XLAT and XLONG have time dimension
    if xlat.shape[0] == n_time:
        xlat_has_time = True
    else:
        xlat_has_time = False
    if xlong.shape[0] == n_time:
        xlong_has_time = True
    else:
        xlong_has_time = False

    for t in range(n_time):
        # Extract data for this time step
        rainc_t = rainc[t, :, :]
        rainnc_t = rainnc[t, :, :]
        rainsh_t = rainsh[t, :, :]
        sum_data_t = rainc_t + rainnc_t + rainsh_t

        if xlat_has_time:
            xlat_t = xlat[t, :, :]
        else:
            xlat_t = xlat[0, :, :] if xlat.ndim == 3 else xlat[:]
        if xlong_has_time:
            xlong_t = xlong[t, :, :]
        else:
            xlong_t = xlong[0, :, :] if xlong.ndim == 3 else xlong[:]

        # Debug prints to verify data
        print(f"File: {filename}, Time step {t}")
        print(f"max RAINNC = {np.max(rainnc_t)}")
        print(f"max RAINC = {np.max(rainc_t)}")
        print(f"max RAINSH = {np.max(rainsh_t)}")
        print(f"max total precipitation = {np.max(sum_data_t)}")

        # Skip if no valid data
        if np.all(sum_data_t == 0) or np.all(np.isnan(sum_data_t)):
            print(f"No valid data to plot for time step {t}")
            continue

        # Define levels for contour plot
        max_val = np.nanmax(sum_data_t)
        levels = np.arange(0, max_val + 5, 5)
        if len(levels) < 2:
            levels = np.array([0, max_val if max_val > 0 else 5])

        # Set up plot
        data_crs = ccrs.PlateCarree()
        fig, ax = plt.subplots(figsize=(12, 6), subplot_kw={'projection': data_crs})

        # Plot shapefile
        gdf = gpd.read_file(shpfilename)
        gdf.to_crs(crs=data_crs, inplace=True)
        gdf.plot(ax=ax, facecolor='none', edgecolor='none', alpha=0.6, zorder=2)

        # Add basemap and features
        try:
            ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor="black")
            ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.8, edgecolor="black")
            ax.add_feature(cfeature.LAKES, facecolor="lightblue", alpha=0.5)
            ctx.add_basemap(
                ax,
                source=ctx.providers.Esri.WorldPhysical,
                crs=ccrs.epsg(3857),
                zoom=6,
                attribution=False,
                zorder=0
            )
        except Exception as e:
            print(f"Failed to load basemap: {e}")

        # Define norm for colormap
        norm = BoundaryNorm(levels, custom_cmap.N)

        # Plot contourf
        contour = ax.contourf(xlong_t, xlat_t, sum_data_t, levels=levels, cmap=custom_cmap, norm=norm, transform=data_crs)

        # Add colorbar
        cbar = plt.colorbar(contour, ax=ax, orientation='vertical', shrink=0.8, pad=0.02)
        cbar.set_label("Precipitation (mm)")

        # Set map extent based on shapefile bounds
        x_min, y_min, x_max, y_max = gdf.total_bounds
        ax.set_extent([x_min, x_max, y_min, y_max], crs=data_crs)

        # Title and annotations
        date = filename[11:21]
        time = filename[22:27]
        title = f"Date: {date} Time: {time} Step: {t}"
        plt.title(title, fontsize=8, color='grey')
        plt.annotate('Precipitation for The Greater Region', xy=(0.5, 1.05), xycoords='axes fraction', ha='center', fontsize=10, color='black')

        # Gridlines
        gl = ax.gridlines(draw_labels=True, alpha=0.3)
        gl.xlabels_top = False
        gl.ylabels_right = False

        # Save plot
        output_file = os.path.join(output_folder, f"{filename}.png")
        plt.savefig(output_file, dpi=400, bbox_inches='tight')
        plt.show()
        plt.close(fig)