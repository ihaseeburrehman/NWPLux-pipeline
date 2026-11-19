"""Crop RMI RADCLIM to the Alzette window and write radclim_crop.npz, the input of make_forcing.py.
Reconstruction of the lost original builder (audit, 24 Oct 2026): it reproduces r1h exactly and r5 within the
0.005 mm rounding of the integer 5 min files.

Raw data (EPSG:3812, 700 x 700, 1 km, origin 300000/1000000):
  <D>/accum1h/hdf/YYYYmmddHHMMSS.radclim.accum1h.hdf  hourly gauge-merged mm, dataset1/data1/data, stamped at interval END
  <D>/accum5m/tif/YYYYmmddHHMMSS.radclim.accum5m.tif  5 min mm x 100 (int16), stamped at interval END
Output layout: r1h (H, 127, 108) for [t, t+1h); r5 (12H, 127, 108) for [t, t+5min); x3812, y3812 pixel centres.
usage: python radclim_crop.py <raw dir with DD/ subfolders> <T0 YYYYmmddHH> <hours> <out.npz>
       (paper: T0 2021071318, 96 h; needs days 13 to 17 July)"""
# Settings: nothing to edit for the paper case; raw folder, T0, hours and output file are command-line arguments.
# The crop window (NX, NY, C0, R0) is fixed to the Alzette area of the 700 x 700 raw grid; change it only for another area.
# Needs numpy and rasterio with GDAL HDF5 support (the hourly files are read as an HDF5 subdataset).
import sys, datetime as dt, numpy as np, rasterio

# --- Command-line arguments: raw folder, start time T0, number of hours, output file ---
RAW, T0, H, OUT = sys.argv[1].rstrip("/") + "/", dt.datetime.strptime(sys.argv[2], "%Y%m%d%H"), int(sys.argv[3]), sys.argv[4]
# --- Crop window and the 1 km pixel-centre coordinates (EPSG:3812) ---
NX, NY, C0, R0 = 108, 127, 418, 406                       # window: columns 418..525, rows 406..532 of the raw grid
x = 300000 + (C0 + np.arange(NX) + 0.5) * 1000             # 718500 ...
y = 1000000 - (R0 + np.arange(NY) + 0.5) * 1000            # 593500 ... (descending)

# --- Read one raw file: cut the window, apply the scale factor, set nodata to NaN ---
def rd(p, scale=1.0):
    with rasterio.open(p) as s:
        a = s.read(1)[R0:R0 + NY, C0:C0 + NX].astype(np.float64); nd = s.nodata
    a = a * scale
    if nd is not None: a[s.read(1)[R0:R0 + NY, C0:C0 + NX] == nd] = np.nan
    return a

# --- For every hour: the hourly file stamped at the hour end, then the twelve 5 min files of that hour ---
r1h, r5 = np.zeros((H, NY, NX)), np.zeros((12 * H, NY, NX))
for h in range(H):
    te = T0 + dt.timedelta(hours=h + 1)
    r1h[h] = rd(f'HDF5:"{RAW}{te:%d}/accum1h/hdf/{te:%Y%m%d%H%M%S}.radclim.accum1h.hdf"://dataset1/data1/data')
    for k in range(12):
        t = T0 + dt.timedelta(hours=h, minutes=5 * k + 5)
        r5[12 * h + k] = rd(f"{RAW}{t:%d}/accum5m/tif/{t:%Y%m%d%H%M%S}.radclim.accum5m.tif", 0.01)
# --- Save the cropped stacks and coordinates; print the window-mean event total ---
np.savez_compressed(OUT, r1h=r1h, r5=r5, x3812=x, y3812=y)
print(OUT, r1h.shape, r5.shape, "window mean total mm", round(float(np.nanmean(np.nansum(r1h, 0))), 2))
