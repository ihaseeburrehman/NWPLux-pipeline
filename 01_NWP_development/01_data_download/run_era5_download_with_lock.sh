#!/bin/bash
# Wrapper for the ERA5 downloader that:
#   - prevents concurrent runs via a flock'd lockfile
#   - wraps the python process in `caffeinate` so the Mac stays awake while it runs
#   - appends to a single rolling log
#
# Designed to be safe to invoke from launchd every hour: if the previous run
# is still going, this exits immediately; otherwise it resumes downloading
# (the python script skips files that already exist on disk).

set -u

LOCK=/tmp/era5_download.lock
LOG=/tmp/era5_download.log
PY=/opt/homebrew/Caskroom/miniconda/base/bin/python3
SCRIPT="/Users/haseeb.rehman/Python scripts/ecmwf_scripts/download_era5_events_2016_2018.py"

exec 9>"$LOCK"
if ! /usr/bin/flock -n 9 ; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] resume-check: another run holds the lock, skipping" >> "$LOG"
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] resume-check: lock acquired, starting/resuming download" >> "$LOG"
exec /usr/bin/caffeinate -dims "$PY" -u "$SCRIPT" >> "$LOG" 2>&1
