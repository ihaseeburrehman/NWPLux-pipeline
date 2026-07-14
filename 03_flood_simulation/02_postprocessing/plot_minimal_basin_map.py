#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Standalone Map Generator for Presentation (Minimalist Design).
Plots Luxembourg, neighboring country boundaries, Alzette big basin,
and Alzette sub-basin (highlighted in red) with professional labeling.

Saves directly to:
/Users/haseeb.rehman/Desktop/For_Animation/4th_year/Miscs/GGE_22_may_2026/minimal_basin_map.png
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import geopandas as gpd
import rasterio
from rasterio.features import shapes as rasterio_shapes
from shapely.geometry import shape
from shapely.ops import unary_union

def main():
    print("==================================================")
    print("GENERATING MINIMAL Basin & SUB-Basin STANDALONE MAP")
    print("==================================================")

    # 1. Paths configuration
    output_dir = "/Users/haseeb.rehman/Desktop/For_Animation/4th_year/Miscs/GGE_22_may_2026"
    output_path = os.path.join(output_dir, "minimal_basin_map.png")
    
    countries_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Countries_near_Lux.shp"
    lux_boundary_path = "/Users/haseeb.rehman/Documents/gis4wrf/projects/2021_07_Luxembourg/Luxembourg_Regions.shp"
    full_basin_path = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/Alzette_basin_cleaned.shp"
    dem_path_for_boundary = "/Users/haseeb.rehman/Documents/Misc/Lisflood_Simulations/Lisflood_Alzette_river_basin/sub_basins/10m/ready_for_simulation/Alzette_sub_basin_10m_bridge_burn.asc"

    # 2. Load shapefiles
    print("📂 Loading shapefiles...")
    try:
        countries_gdf = gpd.read_file(countries_path).to_crs(epsg=4326)
        print("   ✓ Loaded neighboring countries shapefile")
    except Exception as e:
        print(f"   [ERROR] Could not load countries: {e}")
        return

    try:
        lux_boundary_gdf = gpd.read_file(lux_boundary_path).to_crs(epsg=4326)
        print("   ✓ Loaded Luxembourg boundary shapefile")
    except Exception as e:
        print(f"   [ERROR] Could not load Luxembourg: {e}")
        return

    try:
        full_basin_gdf = gpd.read_file(full_basin_path)
        if full_basin_gdf.crs is None:
            full_basin_gdf = full_basin_gdf.set_crs(epsg=2169)
        full_basin_gdf = full_basin_gdf.to_crs(epsg=4326)
        print("   ✓ Loaded Alzette full basin shapefile")
    except Exception as e:
        print(f"   [ERROR] Could not load full basin: {e}")
        return

    # 3. Extract sub-basin boundary from DEM
    print("📍 Extracting sub-basin boundary from DEM...")
    try:
        with rasterio.open(dem_path_for_boundary) as src:
            dem_data = src.read(1)
            transform = src.transform
            src_crs = src.crs if src.crs else 'EPSG:2169'
            valid_mask = (dem_data != -9999).astype('uint8')
            
            polygons = []
            for geom, value in rasterio_shapes(valid_mask, transform=transform):
                if value == 1:
                    polygons.append(shape(geom))
            
            basin_polygon = unary_union(polygons) if len(polygons) > 1 else polygons[0]
            sub_basin_gdf = gpd.GeoDataFrame({'id': [1]}, geometry=[basin_polygon], crs=src_crs)
            sub_basin_gdf = sub_basin_gdf.to_crs(epsg=4326)
            print("   ✓ Extracted sub-basin boundary successfully")
    except Exception as e:
        print(f"   [ERROR] Could not extract sub-basin from DEM: {e}")
        return

    # 4. Set up Plotting Loop
    projection = ccrs.PlateCarree()
    
    map_configs = [
        {"show_subbasin": False, "filename": "minimal_basin_map_without_subbasin.png"},
        {"show_subbasin": True, "filename": "minimal_basin_map_with_subbasin.png"}
    ]
    
    os.makedirs(output_dir, exist_ok=True)
    
    for cfg_map in map_configs:
        show_sub = cfg_map["show_subbasin"]
        fname = cfg_map["filename"]
        out_path = os.path.join(output_dir, fname)
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': projection})
        
        # Define tight, clean coordinates focusing on Luxembourg and surroundings
        lon_min, lon_max = 5.0, 7.2
        lat_min, lat_max = 49.0, 50.7
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=projection)
        ax.set_facecolor('white')

        # Fix aspect ratio for Latitude distortion
        mean_lat = (lat_min + lat_max) / 2
        aspect_ratio = 1.0 / np.cos(np.radians(mean_lat))
        ax.set_aspect(aspect_ratio, adjustable='box')

        # 5. Plot Layers
        # a) Plot neighboring countries with borders only (no fill, removing grey border slivers)
        countries_gdf.plot(ax=ax, facecolor='none', edgecolor='#d3d3d3', linewidth=1.0, zorder=1)
        
        # b) Plot Luxembourg boundary dissolved as solid white with clean dark border to make it POP
        lux_boundary_dissolved = lux_boundary_gdf.dissolve()
        lux_boundary_dissolved.plot(ax=ax, facecolor='#ffffff', edgecolor='#2c3e50', linewidth=1.5, zorder=2)

        # c) Plot full Alzette big basin (soft, modern pastel blue)
        full_basin_gdf.plot(ax=ax, facecolor='#a9cce3', edgecolor='#7fb3d5', linewidth=0.5, alpha=0.7, zorder=3)

        # d) Highlight Alzette sub-basin study area (bold, vibrant red with dark red border) if enabled
        if show_sub:
            sub_basin_gdf.plot(ax=ax, facecolor='#ff3333', edgecolor='#8b0000', linewidth=1.8, alpha=0.85, zorder=4)

        # 6. Add minimal labels for neighboring countries in Georgia (LaTeX-like elegant font)
        # Belgium (North-West)
        ax.text(5.35, 50.4, 'BELGIUM', transform=projection, fontsize=12, fontweight='bold',
                fontfamily='serif', color='#555555', alpha=0.8, ha='center', va='center')
        
        # Germany (East)
        ax.text(6.85, 49.9, 'GERMANY', transform=projection, fontsize=12, fontweight='bold',
                fontfamily='serif', color='#555555', alpha=0.8, ha='center', va='center')
        
        # France (South)
        ax.text(5.9, 49.15, 'FRANCE', transform=projection, fontsize=12, fontweight='bold',
                fontfamily='serif', color='#555555', alpha=0.8, ha='center', va='center')

        # 7. Style the map completely minimal (no titles, no axes, no ticks per request)
        ax.axis('off')
        for spine in ax.spines.values():
            spine.set_visible(False)

        # 8. Save output
        try:
            plt.savefig(out_path, dpi=300, bbox_inches="tight", pad_inches=0)
            plt.close()
            print(f"   ✓ Saved map to: {out_path}")
        except Exception as e:
            print(f"   [ERROR] Could not save map to {out_path}: {e}")

if __name__ == "__main__":
    main()
