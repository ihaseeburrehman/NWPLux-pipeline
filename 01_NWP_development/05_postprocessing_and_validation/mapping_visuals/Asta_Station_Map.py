import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Define projection
data_crs = ccrs.epsg(3857)

# Set up figure and axis with proper projection
fig = plt.figure(figsize=(10, 10))
ax = plt.axes(projection=data_crs)

# Load domain shapefile and set extent
domain_shp = '/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_Domain.shp'
domain_gdf = gpd.read_file(domain_shp).to_crs(epsg=3857)
x_min, y_min, x_max, y_max = domain_gdf.total_bounds
ax.set_extent([x_min, x_max, y_min, y_max], crs=data_crs)

# Add basemap and features
try:
    ctx.add_basemap(ax, source=ctx.providers.Esri.WorldPhysical, crs=data_crs, zoom=6, attribution=False, zorder=0)
except Exception as e:
    print("Basemap loading failed:", e)

ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor="black")
ax.add_feature(cfeature.BORDERS, linestyle="--", linewidth=0.8, edgecolor="black")
ax.add_feature(cfeature.LAKES, facecolor="lightblue", alpha=0.5)

# Add gridlines with consistent styling
gl = ax.gridlines(draw_labels=True, alpha=0.3)
gl.xlabels_top = False
gl.ylabels_right = False
gl.xlabel_style = {'size': 10, 'color': 'gray'}
gl.ylabel_style = {'size': 10, 'color': 'gray'}

# ---------------------
# Station Data
# ---------------------
ztd_stations = [("D596", 51.200, 8.524), ("KLEV", 51.768, 6.142), ("FFMJ", 50.091, 8.665),
                ("D624", 50.868, 7.056), ("NIKL", 51.141, 4.151), ("D402", 48.073, 8.528),
                ("LAIG", 47.842, 4.373), ("TRI2", 49.725, 6.618), ("CT58", 49.150, 3.044),
                ("BAT1", 50.637, 5.834), ("VIT2", 50.317, 6.085), ("MABO", 50.075, 5.739),
                ("DBMH", 48.604, 6.364), ("SMSP", 49.115, 4.581), ("REDU", 50.002, 5.145),
                ("D931", 49.314, 6.746)]

met_stations = [("Briedfeld", 50.12385, 6.06622), ("Echternach", 49.8031, 6.44337), ("Ettelbruck", 49.85172, 6.09754),
                ("Oberkorn", 49.5122, 5.9011), ("Remerschen", 49.491, 6.349), ("Findel", 49.63265182, 6.23292867),
                ("Roodt", 49.7945, 5.8202), ("Hosingen", 49.99314, 6.10147), ("Useldange", 49.76739, 5.96748),
                ("Mamer", 49.63353, 6.0193), ("Arsdorf", 49.85891, 5.84868), ("Asselborn", 50.09685689, 5.96960753),
                ("Grevenmacher", 49.68087, 6.43541), ("Schimpach", 50.0093, 5.8475), ("Waldbillig", 49.79806, 6.2773),
                ("Bettendorf", 49.8741, 6.2095), ("Fouhren", 49.91445, 6.19508), ("Beringen", 49.762, 6.11179),
                ("Dahl", 49.93595, 5.98093), ("Beitem", 50.9, 3.117), ("Meyenheim", 47.917, 7.4),
                ("Spangdahlem ab", 49.973, 6.693), ("Kassel calden", 51.408, 9.378), ("Vatry", 48.776, 4.184),
                ("Ernage", 50.583, 4.683), ("Dusseldorf", 51.289, 6.767), ("Liege", 50.637, 5.443),
                ("Mirecourt", 48.325, 6.07), ("Frankfurt main", 50.026, 8.543), ("Oostende", 51.199, 2.862),
                ("Zeebrugge", 51.35, 3.2), ("Fritzlar", 51.115, 9.286), ("Branches", 47.85, 3.497),
                ("Bale mulhouse", 47.59, 7.53)]

# ---------------------
# Plot function
# ---------------------
def plot_stations(stations, marker, color, label, ax, add_legend=False):
    names = [s[0] for s in stations]
    lats = [s[1] for s in stations]
    lons = [s[2] for s in stations]
    sc = ax.scatter(lons, lats,
                    transform=ccrs.PlateCarree(),
                    marker=marker,
                    color=color,
                    label=label if add_legend else "",
                    s=15,
                    zorder=5,
                    alpha=0.7)
    return sc

# Plot both types of stations
plot_stations(ztd_stations, marker='s', color='brown', label='GNSS Stations', ax=ax, add_legend=True)
plot_stations(met_stations, marker='o', color='blue', label='MET Stations', ax=ax, add_legend=True)

# Legend
ax.legend(loc='upper right')

# Save and show
output_file = "/Users/haseeb.rehman/Desktop/For_Animation/3rd_Year/Miscs/validation_stations_map.png"
plt.savefig(output_file, dpi=500, bbox_inches='tight', pad_inches=0.1)
plt.show()

print(f"Map saved at: {output_file}")
