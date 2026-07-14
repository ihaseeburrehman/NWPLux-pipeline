#!/bin/bash
# WPS pipeline for the 2016 event (2016-07-01 -> 2016-07-31), d01 only, ERA5.
# Same logic as wps_2018_event.sh, different inputs/output.
#
# Output: /Users/haseeb.rehman/WRF/WPS-4.5/2016_metgrid_files_era5/

set -uo pipefail

WPS=/Users/haseeb.rehman/WRF/WPS-4.5
GRIB_PL_DIR=/Users/haseeb.rehman/Documents/gis4wrf/datasets/met/20160701_20160731_ECMWF/pressure_level
GRIB_SL=/Users/haseeb.rehman/Documents/gis4wrf/datasets/met/20160701_20160731_ECMWF/single_level/single_level.grib
OUT_DIR=$WPS/2016_metgrid_files_era5
LOG=/tmp/wps_2016.log

cd "$WPS"
ulimit -s unlimited
mkdir -p "$OUT_DIR"

# Format: NAME|START|END|PL_FILE
CHUNKS=(
  "jul01_10|2016-07-01_00:00:00|2016-07-10_18:00:00|$GRIB_PL_DIR/2016_july_01_to_10_pressure_level"
  "jul11_20|2016-07-11_00:00:00|2016-07-20_18:00:00|$GRIB_PL_DIR/2016_july_11_to_20_pressure_level"
  "jul21_31|2016-07-21_00:00:00|2016-07-31_00:00:00|$GRIB_PL_DIR/2016_july_21_to_31_pressure_level"
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

select_namelist() {
  rm -f namelist.wps
  ln -sf namelist_$1.wps namelist.wps
}

clean_grib_links() { rm -f GRIBFILE.[A-Z][A-Z][A-Z]; }

run_chunk() {
  local NAME=$1 START=$2 END=$3 PL=$4
  log "================================================================"
  log "CHUNK $NAME : $START -> $END"
  log "  PL grib: $PL"
  log "  SL grib: $GRIB_SL"
  log "================================================================"

  patch_dates namelist_1.wps "$START" "$END"
  patch_dates namelist_2.wps "$START" "$END"

  # ---- ungrib pressure ----
  log "[$NAME] ungrib PRESSURE"
  clean_grib_links
  ./link_grib.csh "$PL" >> "$LOG" 2>&1
  ls GRIBFILE.* >> "$LOG"
  select_namelist 2
  ./ungrib.exe >> "$LOG" 2>&1
  if ! grep -q "Successful completion of ungrib" "$LOG"; then
    log "[$NAME] ERROR: pressure ungrib failed"; return 1
  fi
  local n_pf=$(ls Pressure_file:* 2>/dev/null | wc -l | tr -d ' ')
  log "[$NAME] -> $n_pf Pressure_file:* intermediates produced"
  sed -i.tmp '/Successful completion of ungrib/d' "$LOG"; rm -f "$LOG.tmp"

  # ---- ungrib surface ----
  log "[$NAME] ungrib SURFACE"
  clean_grib_links
  ./link_grib.csh "$GRIB_SL" >> "$LOG" 2>&1
  select_namelist 1
  ./ungrib.exe >> "$LOG" 2>&1
  if ! grep -q "Successful completion of ungrib" "$LOG"; then
    log "[$NAME] ERROR: surface ungrib failed"; return 1
  fi
  local n_sf=$(ls Surface_file:* 2>/dev/null | wc -l | tr -d ' ')
  log "[$NAME] -> $n_sf Surface_file:* intermediates produced"
  sed -i.tmp '/Successful completion of ungrib/d' "$LOG"; rm -f "$LOG.tmp"

  # ---- metgrid ----
  log "[$NAME] metgrid"
  select_namelist 2
  ./metgrid.exe >> "$LOG" 2>&1
  if ! grep -q "Successful completion of metgrid" "$LOG"; then
    log "[$NAME] ERROR: metgrid failed"; return 1
  fi
  local n_me=$(ls met_em.d01.*.nc 2>/dev/null | wc -l | tr -d ' ')
  log "[$NAME] -> $n_me met_em.d01.*.nc files produced"
  sed -i.tmp '/Successful completion of metgrid/d' "$LOG"; rm -f "$LOG.tmp"

  mv met_em.d01.*.nc "$OUT_DIR/"
  log "[$NAME] moved met_em files to $OUT_DIR"

  rm -f Pressure_file:* Surface_file:*
  clean_grib_links
  log "[$NAME] cleaned intermediates"

  log "[$NAME] DONE.  Disk free: $(df -h /Users/haseeb.rehman | awk 'NR==2{print $4}')"
}

log "================================================================"
log "2016 EVENT WPS PIPELINE  (d01 only, ERA5)"
log "Output: $OUT_DIR"
log "Disk free at start: $(df -h /Users/haseeb.rehman | awk 'NR==2{print $4}')"
log "================================================================"

for CH in "${CHUNKS[@]}"; do
  IFS="|" read -r NAME START END PL <<< "$CH"
  if ! run_chunk "$NAME" "$START" "$END" "$PL"; then
    log "FATAL: chunk $NAME failed; stopping"
    exit 1
  fi
done

log "================================================================"
log "ALL CHUNKS DONE."
log "Total met_em files in $OUT_DIR: $(ls $OUT_DIR | wc -l | tr -d ' ')"
log "Total size: $(du -sh $OUT_DIR | awk '{print $1}')"
log "================================================================"
