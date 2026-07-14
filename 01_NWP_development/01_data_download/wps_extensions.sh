#!/bin/bash
# WPS pipeline for the extension downloads — appends to existing
# 2018_metgrid_files_era5/ and 2016_metgrid_files_era5/, producing
# ONLY the in-obs-range timesteps (no waste).

set -uo pipefail
WPS=/Users/haseeb.rehman/WRF/WPS-4.5
LOG=/tmp/wps_extensions.log

cd "$WPS"
ulimit -s unlimited

# Format: NAME|START|END|PL_FILE|SL_FILE|OUT_DIR
EVENTS=(
  "2018_ext|2018-06-10_06:00:00|2018-06-20_06:00:00|/Users/haseeb.rehman/Documents/gis4wrf/datasets/met/20180510_20180610_ECMWF/pressure_level/2018_june_10_to_20_pressure_level|/Users/haseeb.rehman/Documents/gis4wrf/datasets/met/20180510_20180610_ECMWF/single_level/single_level_ext.grib|$WPS/2018_metgrid_files_era5"
  "2016_ext|2016-07-31_06:00:00|2016-08-08_06:00:00|/Users/haseeb.rehman/Documents/gis4wrf/datasets/met/20160701_20160731_ECMWF/pressure_level/2016_jul_31_to_aug_09_pressure_level|/Users/haseeb.rehman/Documents/gis4wrf/datasets/met/20160701_20160731_ECMWF/single_level/single_level_ext.grib|$WPS/2016_metgrid_files_era5"
)

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

patch_dates() {
  local f=$1 s=$2 e=$3
  python3 - "$f" "$s" "$e" <<'PY'
import re, sys
fp, s, e = sys.argv[1], sys.argv[2], sys.argv[3]
txt = open(fp).read()
txt = re.sub(r"^( *max_dom *=).*$",     r"\1 1",            txt, flags=re.M)
txt = re.sub(r"^( *start_date *=).*$",  r"\1 '%s'," % s,    txt, flags=re.M)
txt = re.sub(r"^( *end_date *=).*$",    r"\1 '%s'," % e,    txt, flags=re.M)
open(fp, "w").write(txt)
PY
}
select_namelist() { rm -f namelist.wps; ln -sf namelist_$1.wps namelist.wps; }
clean_grib_links() { rm -f GRIBFILE.[A-Z][A-Z][A-Z]; }

run_event() {
  local NAME=$1 START=$2 END=$3 PL=$4 SL=$5 OUT_DIR=$6
  log "================================================================"
  log "EVENT $NAME : $START -> $END"
  log "  PL: $PL"
  log "  SL: $SL"
  log "  OUT: $OUT_DIR"
  log "================================================================"

  for f in "$PL" "$SL"; do
    [ -f "$f" ] || { log "MISSING: $f"; return 1; }
  done

  patch_dates namelist_1.wps "$START" "$END"
  patch_dates namelist_2.wps "$START" "$END"

  log "[$NAME] ungrib PRESSURE"
  clean_grib_links
  ./link_grib.csh "$PL" >> "$LOG" 2>&1
  select_namelist 2
  ./ungrib.exe >> "$LOG" 2>&1
  grep -q "Successful completion of ungrib" "$LOG" || { log "[$NAME] FAIL pressure ungrib"; return 1; }
  log "[$NAME] -> $(ls Pressure_file:* 2>/dev/null | wc -l | tr -d ' ') Pressure_file intermediates"
  sed -i.tmp '/Successful completion of ungrib/d' "$LOG"; rm -f "$LOG.tmp"

  log "[$NAME] ungrib SURFACE"
  clean_grib_links
  ./link_grib.csh "$SL" >> "$LOG" 2>&1
  select_namelist 1
  ./ungrib.exe >> "$LOG" 2>&1
  grep -q "Successful completion of ungrib" "$LOG" || { log "[$NAME] FAIL surface ungrib"; return 1; }
  log "[$NAME] -> $(ls Surface_file:* 2>/dev/null | wc -l | tr -d ' ') Surface_file intermediates"
  sed -i.tmp '/Successful completion of ungrib/d' "$LOG"; rm -f "$LOG.tmp"

  log "[$NAME] metgrid"
  select_namelist 2
  ./metgrid.exe >> "$LOG" 2>&1
  grep -q "Successful completion of metgrid" "$LOG" || { log "[$NAME] FAIL metgrid"; return 1; }
  local n_new=$(ls met_em.d01.*.nc 2>/dev/null | wc -l | tr -d ' ')
  log "[$NAME] -> $n_new new met_em files"
  sed -i.tmp '/Successful completion of metgrid/d' "$LOG"; rm -f "$LOG.tmp"

  # Rename : -> _ then move into existing folder
  for f in met_em.d01.*:*:*.nc; do
    [ -e "$f" ] || continue
    mv "$f" "${f//:/_}"
  done
  mv met_em.d01.*.nc "$OUT_DIR/"
  log "[$NAME] moved $n_new files into $OUT_DIR  (total now: $(ls $OUT_DIR | wc -l | tr -d ' '))"

  rm -f Pressure_file:* Surface_file:*
  clean_grib_links
  log "[$NAME] DONE.  Disk free: $(df -h /Users/haseeb.rehman | awk 'NR==2{print $4}')"
}

log "================================================================"
log "EXTENSION WPS PIPELINE"
log "Disk free at start: $(df -h /Users/haseeb.rehman | awk 'NR==2{print $4}')"
log "================================================================"

for EV in "${EVENTS[@]}"; do
  IFS="|" read -r NAME START END PL SL OUT <<< "$EV"
  if ! run_event "$NAME" "$START" "$END" "$PL" "$SL" "$OUT"; then
    log "FATAL: $NAME failed"; exit 1
  fi
done

log "================================================================"
log "ALL EXTENSIONS DONE."
log "2018 final: $(ls $WPS/2018_metgrid_files_era5 | wc -l | tr -d ' ') files"
log "2016 final: $(ls $WPS/2016_metgrid_files_era5 | wc -l | tr -d ' ') files"
log "================================================================"
