"""
Study-area / validation-stations map for the Greater Region.

Background : multi-directional hill-shade blended with a soft elevation tint.
Foreground : Greater-Region polygons labelled with region names, country
             borders, main rivers with rotated labels, ALL validation MET
             stations (small red dots), and the four SYNOP stations used for
             the time-series plots (large distinct markers).

Output: validation_stations_with_topo.png
"""

import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib import patheffects
from matplotlib.lines import Line2D

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import linemerge

import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader

import rasterio
from rasterio.warp import transform_bounds, reproject, Resampling
from rasterio.transform import from_bounds

warnings.filterwarnings("ignore")

# ───────────────────────────────────────────────────────────────────────────
# PATHS
# ───────────────────────────────────────────────────────────────────────────
DOMAIN_SHP = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region_Domain.shp"
GR_SHP     = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Greater_Region.shp"
RIVERS_SHP = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/merged_rivers/merged_rivers.shp"
DEM_FILE   = "/Users/haseeb.rehman/Documents/SRTM_DEM_for_study_area/DEM_SRTM_30m.tif"
OUT_PNG    = "/Users/haseeb.rehman/Desktop/For_Animation/4th_Year/Miscs/validation_stations_with_topo.png"

# ───────────────────────────────────────────────────────────────────────────
# PROJECTION  +  EXTENT (from domain shapefile in EPSG:3857)
# ───────────────────────────────────────────────────────────────────────────
DATA_CRS = ccrs.epsg(3857)
PLATE    = ccrs.PlateCarree()

domain_gdf            = gpd.read_file(DOMAIN_SHP).to_crs(epsg=3857)
x_min, y_min, x_max, y_max = domain_gdf.total_bounds
# No extra padding: the domain already equals the DEM extent, so padding
# would push into blank ocean/sea that lacks terrain colour.

fig = plt.figure(figsize=(11, 11))
ax  = plt.axes(projection=DATA_CRS)
ax.set_extent([x_min, x_max, y_min, y_max], crs=DATA_CRS)

# ───────────────────────────────────────────────────────────────────────────
# BACKGROUND  — ocean fill so edges never show white
# ───────────────────────────────────────────────────────────────────────────
ax.set_facecolor("#a8c8e0")           # ocean-blue fallback
ax.add_feature(cfeature.OCEAN.with_scale("10m"),
               facecolor="#a8c8e0", edgecolor="none", zorder=0)
ax.add_feature(cfeature.LAND.with_scale("10m"),
               facecolor="#e8e4d8", edgecolor="none", zorder=0)

# ───────────────────────────────────────────────────────────────────────────
# DEM  —  reproject to Web Mercator, multi-directional hillshade + tint
# ───────────────────────────────────────────────────────────────────────────
def multi_hillshade(elev, azimuths=(225, 270, 315, 360), altitude=40, z_factor=2.5):
    dy, dx = np.gradient(elev * z_factor)
    slope  = np.pi / 2 - np.arctan(np.hypot(dx, dy))
    aspect = np.arctan2(-dx, dy)
    alt    = np.radians(altitude)
    stack  = [np.sin(alt)*np.sin(slope)
              + np.cos(alt)*np.cos(slope)*np.cos(np.radians(az) - aspect)
              for az in azimuths]
    hs = np.mean(stack, axis=0)
    return (hs - hs.min()) / (hs.max() - hs.min() + 1e-9)

with rasterio.open(DEM_FILE) as src:
    dem_left, dem_bot, dem_right, dem_top = transform_bounds(
        src.crs, "EPSG:3857", *src.bounds)
    tw = 2400
    th = int(tw * (dem_top - dem_bot) / (dem_right - dem_left))
    dst = np.zeros((th, tw), dtype=np.float32)
    dst_tf = from_bounds(dem_left, dem_bot, dem_right, dem_top, tw, th)
    reproject(
        source=rasterio.band(src, 1), destination=dst,
        src_transform=src.transform, src_crs=src.crs,
        dst_transform=dst_tf, dst_crs="EPSG:3857",
        resampling=Resampling.bilinear,
    )

# Mask nodata, clip negatives to 0 (ocean/below-sea-level pixels)
elev      = np.where(dst < -500, np.nan, dst.astype(float))
elev_clip = np.clip(elev, 0, None)

hs  = multi_hillshade(np.nan_to_num(elev_clip, nan=0.0))

terrain_cmap = mcolors.LinearSegmentedColormap.from_list(
    "soft_terrain",
    [(0.00, "#eef3e2"), (0.20, "#d8e0bb"),
     (0.50, "#c9bf86"), (0.72, "#b08a5a"), (1.00, "#6f4b2c")],
)
rgb   = terrain_cmap(mcolors.Normalize(0, 900)(np.nan_to_num(elev_clip, nan=0.0)))[..., :3]
shade = (hs * 0.85 + 0.15)[..., None]
rgb   = np.clip(rgb * shade, 0, 1)

# Mask ocean pixels (elev was NaN = nodata) → make transparent so ocean
# background shows through
alpha = np.where(np.isnan(elev), 0.0, 1.0)
rgba  = np.dstack([rgb, alpha])

ax.imshow(
    rgba,
    extent=[dem_left, dem_right, dem_bot, dem_top],
    transform=DATA_CRS,
    origin="upper",
    interpolation="bilinear",
    zorder=1,
)

# ───────────────────────────────────────────────────────────────────────────
# COUNTRY BORDERS  — highly visible: thick white halo + dark line
# ───────────────────────────────────────────────────────────────────────────
BORDER_PE = [patheffects.Stroke(linewidth=3.5, foreground="white"),
             patheffects.Normal()]

ax.add_feature(
    cfeature.BORDERS.with_scale("10m"),
    linestyle="-", linewidth=1.6, edgecolor="#1a1a1a",
    zorder=5,
)
ax.add_feature(
    cfeature.COASTLINE.with_scale("10m"),
    linewidth=1.2, edgecolor="#1a1a1a", zorder=5,
)
ax.add_feature(
    cfeature.LAKES.with_scale("10m"),
    facecolor="#a8c8e0", edgecolor="none", alpha=0.8, zorder=3,
)

# ───────────────────────────────────────────────────────────────────────────
# GREATER REGION BOUNDARY  —  use ax.add_geometries so cartopy handles the
# transform correctly (avoids any geopandas/cartopy CRS mismatch)
# ───────────────────────────────────────────────────────────────────────────
gr_4326 = gpd.read_file(GR_SHP)   # original CRS is EPSG:4326

# Luxembourg geometry from NaturalEarth 10m (not in the GR shapefile)
_ne_countries = gpd.read_file(
    shpreader.natural_earth(resolution="10m", category="cultural",
                            name="admin_0_countries")
)
_lux_geom = _ne_countries.loc[
    _ne_countries["NAME"] == "Luxembourg", "geometry"
].values[0]

# Draw each sub-region WITH Luxembourg — faint fill so regions read as distinct
region_fills = {
    "Lorraine":        "#fff7e6",   # light amber
    "Rheinland-Pfalz": "#e6f0ff",   # light blue
    "Saarland":        "#e6ffe6",   # light green
    "Wallonie":        "#ffe6f0",   # light pink
    "_Luxembourg":     "#f0e6ff",   # light lavender
}

# Sub-regions from shapefile
for _, row in gr_4326.iterrows():
    name = row.get("NAME_1") or row.get("Name")
    fc   = region_fills.get(name, "none")
    ax.add_geometries(
        [row.geometry], crs=PLATE,
        facecolor=fc, edgecolor="#cc3300",
        linewidth=1.6, linestyle="--",
        alpha=0.30 if fc != "none" else 1.0,
        zorder=4,
    )

# Luxembourg fill
ax.add_geometries(
    [_lux_geom], crs=PLATE,
    facecolor=region_fills["_Luxembourg"], edgecolor="#cc3300",
    linewidth=1.6, linestyle="--", alpha=0.30, zorder=4,
)

# Bright dashed outlines on top of fills (no fill, with white halo)
GR_OUTLINE_PE = [patheffects.Stroke(linewidth=3.5, foreground="white"),
                 patheffects.Normal()]

for _, row in gr_4326.iterrows():
    ax.add_geometries(
        [row.geometry], crs=PLATE,
        facecolor="none", edgecolor="#cc3300",
        linewidth=1.6, linestyle="--", zorder=6,
        path_effects=GR_OUTLINE_PE,
    )

# Luxembourg outline
ax.add_geometries(
    [_lux_geom], crs=PLATE,
    facecolor="none", edgecolor="#cc3300",
    linewidth=1.6, linestyle="--", zorder=6,
    path_effects=GR_OUTLINE_PE,
)

# ───────────────────────────────────────────────────────────────────────────
# REGION LABELS  (from the Greater Region shapefile NAME_1 field)
# ───────────────────────────────────────────────────────────────────────────
region_display = {
    "Lorraine":        "Lorraine",
    "Rheinland-Pfalz": "Rhineland-\nPalatinate",
    "Saarland":        "Saarland",
    "Wallonie":        "Wallonia",
}
region_label_pos = {
    "Lorraine":        (5.80, 48.85),
    "Rheinland-Pfalz": (7.30, 49.90),
    "Saarland":        (6.95, 49.38),
    "Wallonie":        (5.20, 50.28),
}
txt_pe = [patheffects.withStroke(linewidth=2.5, foreground="white")]

for _, row in gr_4326.iterrows():
    name = row.get("NAME_1") or row.get("Name")
    if name not in region_display:
        continue
    lon, lat = region_label_pos[name]
    ax.text(lon, lat, region_display[name],
            transform=PLATE, fontsize=9.5, fontstyle="italic",
            color="#1a1a1a", ha="center", va="center",
            zorder=8, path_effects=txt_pe, linespacing=1.3)

# Luxembourg region label — two lines so it fits inside the small country
ax.text(6.10, 49.70, "Luxem-\nbourg",
        transform=PLATE, fontsize=9.5, fontweight="bold", fontstyle="italic",
        color="#1a1a1a", ha="center", va="center", linespacing=1.2,
        zorder=8, path_effects=txt_pe)

# Surrounding country labels
for name, (lon, lat) in {
        "FRANCE":       (4.20, 48.20),
        "GERMANY":      (8.40, 50.55),
        "BELGIUM":      (4.40, 50.85),
        "NETHERLANDS":  (5.30, 51.55),
}.items():
    ax.text(lon, lat, name, transform=PLATE,
            fontsize=11, fontweight="bold", color="#111111",
            ha="center", va="center", zorder=8, path_effects=txt_pe)

# ───────────────────────────────────────────────────────────────────────────
# RIVERS  —  plot + rotated labels
# ───────────────────────────────────────────────────────────────────────────
rivers = gpd.read_file(RIVERS_SHP).to_crs(epsg=3857)

MAIN_RIVERS  = ["Rhine", "Moselle", "Meuse"]
STUDY_RIVERS = ["Sauer", "Our", "Alzette"]
LABELLED     = MAIN_RIVERS + STUDY_RIVERS

rivers[~rivers["river_name"].isin(LABELLED)].plot(
    ax=ax, color="#3b6fb6", linewidth=0.4, alpha=0.65, zorder=3)
rivers[rivers["river_name"].isin(MAIN_RIVERS)].plot(
    ax=ax, color="#1b4a9a", linewidth=1.2, zorder=4)
rivers[rivers["river_name"].isin(STUDY_RIVERS)].plot(
    ax=ax, color="#1b4a9a", linewidth=0.9, zorder=4)

RIVER_KW = dict(
    color="#0a3070", fontstyle="italic",
    ha="center", va="center", zorder=10,
    path_effects=[patheffects.withStroke(linewidth=2.0, foreground="white")],
)

def _longest_visible(geoms, ax):
    xlim, ylim = ax.get_xlim(), ax.get_ylim()
    best, best_len = None, 0
    for g in geoms:
        if isinstance(g, LineString):
            ln = g
        elif isinstance(g, MultiLineString):
            m = linemerge(g)
            ln = m if isinstance(m, LineString) else max(m.geoms, key=lambda x: x.length)
        else:
            continue
        pts = [(x, y) for x, y in ln.coords
               if xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]]
        if len(pts) < 2:
            continue
        seg = LineString(pts)
        if seg.length > best_len:
            best, best_len = seg, seg.length
    return best

def _angle(seg, frac):
    a = seg.interpolate(max(frac - 0.015, 0.0), normalized=True)
    b = seg.interpolate(min(frac + 0.015, 1.0), normalized=True)
    ang = np.degrees(np.arctan2(b.y - a.y, b.x - a.x))
    if ang >  90: ang -= 180
    if ang < -90: ang += 180
    return ang

def label_at_frac(name, size, frac):
    sub = rivers[rivers["river_name"] == name]
    if sub.empty: return
    seg = _longest_visible(list(sub.geometry), ax)
    if seg is None: return
    pt = seg.interpolate(frac, normalized=True)
    ax.text(pt.x, pt.y, name, rotation=_angle(seg, frac),
            fontsize=size, rotation_mode="anchor", **RIVER_KW)

def label_at_lonlat(name, size, lon, lat):
    sub = rivers[rivers["river_name"] == name]
    if sub.empty: return
    seg = _longest_visible(list(sub.geometry), ax)
    px, py = DATA_CRS.transform_point(lon, lat, PLATE)
    ang = _angle(seg, seg.project(Point(px, py)) / seg.length) if seg else 0
    ax.text(px, py, name, rotation=ang,
            fontsize=size, rotation_mode="anchor", **RIVER_KW)

label_at_frac("Rhine",   12, 0.60)
label_at_frac("Moselle", 11, 0.30)
label_at_frac("Meuse",   10, 0.55)
label_at_lonlat("Sauer",   9,  6.45, 49.83)
label_at_lonlat("Our",     9,  6.18, 50.05)
label_at_lonlat("Alzette", 9,  5.95, 49.66)

# ───────────────────────────────────────────────────────────────────────────
# STATIONS
# ─  All validation MET stations  (from original script)
# ─  4 time-series SYNOP stations (highlighted)
# ───────────────────────────────────────────────────────────────────────────
met_stations = [
    ("Briedfeld",       50.12385, 6.06622), ("Echternach",     49.8031,  6.44337),
    ("Ettelbruck",      49.85172, 6.09754), ("Oberkorn",       49.5122,  5.9011 ),
    ("Remerschen",      49.491,   6.349  ), ("Findel",         49.63265, 6.23293),
    ("Roodt",           49.7945,  5.8202 ), ("Hosingen",       49.99314, 6.10147),
    ("Useldange",       49.76739, 5.96748), ("Mamer",          49.63353, 6.0193 ),
    ("Arsdorf",         49.85891, 5.84868), ("Asselborn",      50.09686, 5.96961),
    ("Grevenmacher",    49.68087, 6.43541), ("Schimpach",      50.0093,  5.8475 ),
    ("Waldbillig",      49.79806, 6.2773 ), ("Bettendorf",     49.8741,  6.2095 ),
    ("Fouhren",         49.91445, 6.19508), ("Beringen",       49.762,   6.11179),
    ("Dahl",            49.93595, 5.98093), ("Beitem",         50.9,     3.117  ),
    ("Meyenheim",       47.917,   7.4    ), ("Spangdahlem ab", 49.973,   6.693  ),
    ("Kassel calden",   51.408,   9.378  ), ("Vatry",          48.776,   4.184  ),
    ("Ernage",          50.583,   4.683  ), ("Dusseldorf",     51.289,   6.767  ),
    ("Liege",           50.637,   5.443  ), ("Mirecourt",      48.325,   6.07   ),
    ("Frankfurt main",  50.026,   8.543  ), ("Oostende",       51.199,   2.862  ),
    ("Zeebrugge",       51.35,    3.2    ), ("Fritzlar",       51.115,   9.286  ),
    ("Branches",        47.85,    3.497  ), ("Bale mulhouse",  47.59,    7.53   ),
]

# Plot all validation stations first (small, below TS markers)
met_lons = [s[2] for s in met_stations]
met_lats = [s[1] for s in met_stations]
ax.scatter(met_lons, met_lats, transform=PLATE,
           marker="o", s=30, facecolor="#e63232", edgecolor="white",
           linewidth=0.6, zorder=7, label="_nolegend_")

# Four time-series SYNOP stations (larger, distinctive)
# colours match Time_series_graph.py: grey/purple/green/blue
ts_stations = [
    (50.040, 5.400),   # Belgium  6476
    (49.630, 6.230),   # Luxembourg 6590
    (49.750, 6.660),   # Germany 10609
    (48.980, 6.240),   # France  7093
]
ts_lons = [s[1] for s in ts_stations]
ts_lats = [s[0] for s in ts_stations]
ax.scatter(ts_lons, ts_lats, transform=PLATE,
           marker="+", s=160, color="black",
           linewidths=2.0, zorder=9)

# ───────────────────────────────────────────────────────────────────────────
# LEGEND
# ───────────────────────────────────────────────────────────────────────────
handles = [
    Line2D([], [], marker="o", color="w", markerfacecolor="#e63232",
           markeredgecolor="white", markersize=7,  label="Validation stations"),
    Line2D([], [], color="#cc3300", linestyle="--", linewidth=1.5,
           label="Greater Region boundary"),
    Line2D([], [], color="#1b4a9a", linewidth=1.4, label="Rivers"),
]

leg = ax.legend(
    handles=handles, loc="upper right",
    fontsize=9, title_fontsize=10,
    facecolor="white", edgecolor="0.4", framealpha=0.93,
)
leg.set_zorder(20)

# ───────────────────────────────────────────────────────────────────────────
# GRIDLINES
# ───────────────────────────────────────────────────────────────────────────
gl = ax.gridlines(draw_labels=True, alpha=0.2, linewidth=0.4, color="grey")
gl.top_labels   = False
gl.right_labels = False
gl.xlabel_style = {"size": 11}
gl.ylabel_style = {"size": 11}

plt.savefig(OUT_PNG, dpi=400, bbox_inches="tight", pad_inches=0.05)
print(f"Saved → {OUT_PNG}")
