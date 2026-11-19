#!/bin/bash
# usage: sbatch --job-name=l84_<case> run_case84.sh <case> <noinf|ga> [sp|dp] [nGPU, default 4; sbatch --ntasks=n --gres=gpu:n]
#   LISFLOOD-FP 8.4 (single precision, CUDA FV1, MPI on 4 GPUs), inputs identical to the HiPIMS cases
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:4
#SBATCH --mem=128G
#SBATCH --time=12:00:00
#SBATCH --qos=ng
#SBATCH --account=luuni
#SBATCH --output=/ec/res4/scratch/lux0804/radar_scale_2026/logs/run84_%x_%j.log
# What it does: writes a LISFLOOD-FP 8.4 parameter file for one rain case, adds the Green-Ampt grids if asked,
# and runs the model with MPI on NG GPUs.
# Arguments: <case> rain case (R_1km_5min, R_1km_6h, F_<model>, VM_<model>);
#   <infiltration> noinf (none), ga3b (Green-Ampt, dry start), ga3b_sm (Green-Ampt, ERA5-Land wet start),
#   ga3b_ks05 / ga3b_ks2 (conductivity halved / doubled), older versions ga, ga2, ga3;
#   [sp|dp|dpn] build: dpn is the final double-precision 8.4 build used for the thesis runs; [nGPU], default 4.
# Example (thesis runs): sbatch run_case84.sh F_graphcast noinf dpn 1   or   sbatch run_case84.sh R_1km_5min ga3b_sm dpn 4
# Inputs: DEM, Manning, start depth (13 July 18 UTC) and boundary file in $W/inputs; the rain file of the case;
#   the Green-Ampt .asc grids (from lf84_inputs.py, soil_v3b.py and soil_sm.py).
# Outputs: $W/runs/L84_<case>_<infiltration><suffix>/ with run.par, inputs.md5, results/, time.txt.
# Settings to change: the #SBATCH account, qos and log path, W, I, the binary paths (BIN), the Green-Ampt folders
# and the module list (ECMWF HPC paths).
set -euo pipefail
# --- Arguments with defaults: single precision, 4 GPUs ---
CASE=$1; INF=$2; PREC=${3:-sp}; NG=${4:-4}
# Work folder W and 50 m input folder I
W=/ec/res4/scratch/lux0804/radar_scale_2026; I=/ec/res4/scratch/lux0804/lf84_cases/inputs
# --- Rain file: the radar cases use their forcing files directly, other cases the 50 m block-mean file ---
case $CASE in
  R_1km_5min) RAIN=$W/forcing/rain_R_1km_5min.nc ;;
  R_1km_6h)   RAIN=$W/forcing/rain_R_1km_6h.nc ;;
  *)          RAIN=$I/rain_${CASE}_b50.nc ;;
esac
# --- Binary for the chosen build and the run-folder suffix ---
SUF=""; BIN=/ec/res4/scratch/lux0804/lf84_float/build/lisflood
if [ "$PREC" = dp ]; then SUF=_dp; BIN=/ec/res4/scratch/lux0804/LISFLOOD_versions/LISFLOOD-8.4-multigpu/build/lisflood; fi
# dpn: the final 8.4 build (double precision, outflow-only free boundary), used for all thesis runs
NEW=0; if [ "$PREC" = dpn ]; then SUF=_dpn; NEW=1; BIN=/perm/lux0804/LISFLOOD_versions/LISFLOOD-8.4/build_double/lisflood; fi   # rebuilt 24 Oct 2026: outflow-only FREE boundary
# Add the GPU count to the folder name when it is not 4
[ "$NG" != 4 ] && SUF=${SUF}_${NG}g
# --- Run folder and parameter file: FV1 on CUDA, 96 h (345600 s), output every hour ---
R=$W/runs/L84_${CASE}_${INF}${SUF}; mkdir -p $R/results
cat > $R/run.par <<PAR
dirroot                  $R/results
resroot                  1hr
DEMfile                  $W/inputs/Alzette_sub_basin_10m_bridge_burn.asc
manningfile              $W/inputs/manning.n.ascii
dynamicrainfile          $RAIN
startfile                $W/inputs/13_july_18hr.wd
fv1
cuda
GPUs $NG
sim_time                 345600
initial_tstep            10
massint                  600
saveint                  3600
bcifile                  $W/inputs/Border.bci
nodata_elevation         -9999
drain_nodata
qoutput
PAR
# --- Green-Ampt folder for each infiltration setting (ga3b_<x> reads inputs_v3b_<x>, e.g. inputs_v3b_sm for the wet start),
#     then append the Green-Ampt lines to run.par ---
GI=$I; [ "$INF" = ga2 ] && GI=/ec/res4/scratch/lux0804/lf84_cases/inputs_v2; [ "$INF" = ga3 ] && GI=/ec/res4/scratch/lux0804/lf84_cases/inputs_v3a; [ "$INF" = ga3b ] && GI=/ec/res4/scratch/lux0804/lf84_cases/inputs_v3b; case $INF in ga3b_*) GI=/ec/res4/scratch/lux0804/lf84_cases/inputs_v3b_${INF#ga3b_} ;; esac
if [ "$INF" = ga ] || [ "$INF" = ga2 ] || [ "$INF" = ga3 ] || [ "${INF%%_*}" = ga3b ]; then cat >> $R/run.par <<PAR
infiltration             greenampt
greenampt_ks             $GI/ga_ks_mmh.asc
greenampt_psi            $GI/ga_psi_mm.asc
greenampt_porosity       $GI/ga_porosity.asc
greenampt_theta_init     $GI/ga_theta_init.asc
PAR
fi
# --- Record input checksums, load modules, list GPUs ---
md5sum $W/inputs/Alzette_sub_basin_10m_bridge_burn.asc $W/inputs/manning.n.ascii $W/inputs/13_july_18hr.wd $W/inputs/Border.bci $RAIN > $R/inputs.md5
module load prgenv/gnu cuda/12.6 netcdf4/4.9.3 hpcx-openmpi/2.14.0-cuda
nvidia-smi --query-gpu=index,name --format=csv,noheader
# --- Run with timing: the dpn build needs its own MPI modules and core binding ---
if [ $NEW = 1 ]; then unset LD_LIBRARY_PATH; module load cuda/12.6 hpcx-openmpi/2.14.0-cuda netcdf4/4.9.3
  /usr/bin/time -v -o $R/time.txt mpirun --map-by ppr:$NG:node --bind-to core -np $NG $BIN $R/run.par
else
  /usr/bin/time -v -o $R/time.txt mpirun --bind-to none -np $NG $BIN $R/run.par
fi
# Keep a copy of the mass-balance file next to run.par
cp $R/results/*.mass $R/ 2>/dev/null || true
