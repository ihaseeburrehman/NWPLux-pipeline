# NWPLux Pipeline

Core scripts of the PhD thesis *"A High-Resolution Numerical Weather Prediction Model for Nowcasting Precipitation in the Grand-Duchy of Luxembourg (NWPLux)"*, Haseeb ur Rehman, University of Luxembourg.

The scripts follow the thesis step by step: weather data, WRF with 3D-Var data assimilation, AI forecasts, radar rainfall, and the LISFLOOD-FP flood simulation. Only the core script of each step is kept here. The full script sets of the individual studies are in their own archives (see below).

## Funding

Fonds National de la Recherche Luxembourg (FNR), Industrial Fellowship, Project No. 17130773, in partnership with RSS-Hydro S.a.r.l.

## Steps

```
01_download_data  ->  02_wps  ->  03_observations  ->  04_wrf_wrfda_3dvar
                                                              |
05_ai_forecasts   ------------------------------------------>  |
06_radar          ------------------------------------------>  07_flood_inputs  ->  08_flood_run  ->  09_flood_postprocessing
```

| Step | Script | Purpose | Chapter |
|---|---|---|---|
| 01 Download data | `download_gfs_0p5_from_ncei.sh` | GFS 0.5° files, 6-hourly, from the NOAA NCEI archive | 4 |
| | `download_era5_events_2016_2018.py` | ERA5 pressure- and single-level fields from the Copernicus CDS | 4, 5 |
| | `download_conventional_data_from_NOAA.py` | NCEP PREPBUFR conventional observations, 6-hourly | 5 |
| 02 WPS | `wps_2018_event.sh` | ungrib and metgrid: global fields to WRF input (`met_em`) files | 4, 5 |
| 03 Observations | `extracting_ZTD_from_zip_files_and_fixing_ellp_height.py` | GNSS ZTD (Nevada Geodetic Laboratory) to WRFDA ASCII, ellipsoidal to orthometric height (EGM2008) | 4, 5 |
| | `rebuild_2018_obs.sh` | PREPBUFR to little_r, OBSPROC filtering, then adds the ZTD reports, per cycle | 5 |
| | `merge_ztd.py` | appends the ZTD reports to the OBSPROC file and fixes its header (called by `rebuild_2018_obs.sh`) | 5 |
| 04 WRF and WRFDA 3D-Var | `run_ruc_HPC_CV5.sh` | rapid update cycle: real, first-guess WRF, WRFDA 3D-Var (conventional + ZTD, CV5), boundary update, 6 h forecast, on SLURM | 4, 5 |
| 05 AI forecasts | `graphcast_01_era5_precip_accumulation.py` | ERA5 input for GraphCast: 6 h precipitation accumulation (only precipitation is summed) | 5, 6 |
| | `graphcast_02_run_inference.py` | GraphCast 6 h forecasts in a rapid update cycle | 5, 6 |
| | `aifs_run_inference.py` | AIFS 6 h forecast for one cycle | 5, 6 |
| | `fuxi_run_inference.py` | FuXi 6 h forecasts in a rapid update cycle (corrected latitude order) | 5, 6 |
| 06 Radar | `radclim_crop.py` | RMI RADCLIM radar (hourly gauge-merged and 5 min) cropped to the Alzette basin | 6 |
| 07 Flood inputs | `wrf_to_lisflood_rain.py` | WRF rainfall to a LISFLOOD-FP rain file on the 10 m grid | 6 |
| | `ai_to_lisflood_rain.py` | GraphCast, AIFS or FuXi rainfall to a LISFLOOD-FP rain file on the 10 m grid | 6 |
| | `make_forcing.py` | radar rain files and volume-matched (VM) forecast rain files | 6 |
| | `soil_v3b.py` | Green–Ampt soil grids: Ks and porosity from EU-SoilHydroGrids and SoilGrids, suction head after Saxton and Rawls (2006) | 6 |
| | `soil_sm.py` | wet start: initial soil water from ERA5-Land soil moisture | 6 |
| | `lf84_inputs.py` | final LISFLOOD-FP 8.4 rain and Green–Ampt input files | 6 |
| 08 Flood run | `run_case84.sh` | runs LISFLOOD-FP 8.4 (CUDA FV1, 1–4 GPUs) without infiltration, with infiltration (dry start) or with the wet start | 6 |
| 09 Flood post-processing | `xs_fullvalley.py` | discharge across the gauge sections from the LISFLOOD-FP results | 6 |
| | `seg_extract.py` | helper: integrates the flow over the section segments (used by `xs_fullvalley.py`) | 6 |
| | `score_all.py` | NSE, KGE, peak ratio and peak timing against the AGE gauges (AGE clock shifted to UTC) | 6 |
| | `sar_extent.py` | simulated flood extent against the Sentinel-1 flood map (EMSN139) | 6 |

`09_flood_postprocessing/transects_fullvalley.json` holds the gauge sections used by the extraction.
`bibliometric_analysis/` holds the workbook of the literature review (Chapter 2).

## Notes

- The scripts keep the paths and dates of the machines they ran on (a local Mac, the University of Luxembourg HPC and the ECMWF HPC). Set the paths and dates at the top of each script before use.
- `run_ruc_HPC_CV5.sh` uses the domain-specific background error (CV5). For the global background error (CV3), set `CV_OPTIONS=3` and put the CV3 `be.dat` in the WRFDA work folder that the script links into each cycle.
- `wps_2018_event.sh` and `rebuild_2018_obs.sh` are written for the 2018 event; the 2016 and 2021 events use the same steps with other dates. The conventional observations of Chapter 4 were ECMWF BUFR records; the PREPBUFR scripts here are those of Chapter 5.
- `soil_v3b.py` updates the earlier soil grids (v2 and v3a) of the infiltration archive; the full soil chain is in that archive.
- `fuxi_run_inference.py` is the corrected FuXi run of October 2026. The first FuXi script reversed the latitude axis of the input; its output is not used in the thesis.
- `run_case84.sh` is the final version from the ECMWF HPC (24 Oct 2026). The thesis runs use the `dpn` build (final double-precision LISFLOOD-FP 8.4).
- Third-party models (WRF, WRFDA, WPS, GraphCast, AIFS, FuXi, LISFLOOD-FP) are not included and keep their own licences.

## Full script sets of the individual studies

| Study | Chapter | Archive |
|---|---|---|
| Data assimilation (NHESS) | 4 | this repository |
| Physics vs AI (GMD) | 5 | https://doi.org/10.5281/zenodo.20794936 |
| WRF–LISFLOOD-FP coupling and FV1-CUDA patches | 6 | https://doi.org/10.5281/zenodo.20776731 |
| Infiltration (HESS) | 6 | https://doi.org/10.5281/zenodo.23691438 |
| Initial-state sensitivity | 7 | https://doi.org/10.5281/zenodo.23270690 |

## Data

No raw data are included. ERA5, GFS, PREPBUFR and GNSS ZTD are public. Radar (RMI RADCLIM), soil (EU-SoilHydroGrids, SoilGrids), LiDAR terrain (ACT Luxembourg) and the Sentinel-1 flood map (Copernicus EMS EMSN139) come from their providers. River discharge and water level are from the Administration de la gestion de l'eau (AGE), Luxembourg, and are not redistributed.

## License

PolyForm Noncommercial License 1.0.0 (see `LICENSE`). The code may be used, changed and shared for research, teaching and other noncommercial purposes. Commercial use is not permitted. For commercial use, contact the author.
