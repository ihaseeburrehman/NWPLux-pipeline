#!/bin/bash
#set -x #(for debugging)

# Check if output is a terminal for color support
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    BLUE=''
    NC=''
fi

# Border drawing functions
print_border() {
    local message=$1
    local width=68
    if [ -z "$message" ]; then
        echo "Error: Empty message in print_border" >&2
        return 1
    fi
    printf "%${width}s\n" | tr ' ' '='
    printf -- "= %-64s =\n" "$message" || {
        echo "Error: printf failed for message: $message" >&2
        return 1
    }
    printf "%${width}s\n" | tr ' ' '='
}

print_sub_border() {
    local message=$1
    if [ -z "$message" ]; then
        echo "Error: Empty message in print_sub_border" >&2
        return 1
    fi
    printf "%45s\n" | tr ' ' '-'
    printf -- "%-44s\n" "$message"
    printf "%45s\n" | tr ' ' '-'
}

print_success() {
    local message=$1
    printf "%s\n" "$message"
}

print_error() {
    local message=$1
    printf "%s\n" "$message" >&2
}

# Verify directories
print_success "Verifying directories:"
ls -ld $WORKDIR $ANALYSISDIR $DAFILES || {
    print_error "Directory verification failed"
    exit 1
}

# Check SLURM configuration
scontrol show hostname $SLURM_JOB_NODELIST | awk '{print $0 " slots=28"}' > /home/users/hrehman/my_hostfile
hostfile="/home/users/hrehman/my_hostfile"
total_slots=$(awk -F 'slots=' '{sum += $2} END {print sum}' $hostfile)

############################################################
# Forecast Script
# Author: Haseeb ur Rehman
############################################################

HOMEDIR=/home/users/hrehman/WRF
WORKDIR=$HOMEDIR/WRFV4.5.2/WORKDIR
WRFDIR=$HOMEDIR/WRFV4.4.2
WRFDADIR=$HOMEDIR/WRFDA
ANALYSISDIR=$WORKDIR/analysis_dir
DAFILES=$ANALYSISDIR/After_DA
MET_EM_FILES=$HOMEDIR/WPS-4.5/met_em_files_GFS_000_2018
OBASCIIDIR=$HOMEDIR/WRFDA/DAT_DIR/concatenate_2018_event
B_MATRIX_DIR=$HOMEDIR/WRFDA/var/run
LOGDIR=${WORKDIR}/log_dir
EMAIL="haseeb.rehman@uni.lu"

RUN_RUC='true'
SKIP_WRF_RUN='false'

# Create directories
test -d $WORKDIR || mkdir -p $WORKDIR
test -d $LOGDIR || mkdir -p $LOGDIR
test -d $ANALYSISDIR || mkdir -p $ANALYSISDIR
test -d $DAFILES || mkdir -p $DAFILES

############################################################
# Time control
############################################################
START_YEAR=2018
START_MONTH=06
START_DAY=13
START_HOUR=00
CYCLE_LENGTH=6
CYCLE_LENGTH_BEGIN=00
CYCLE_LENGTH_INTERVAL=6
MULTIPLE=60

# Date calculations
if [ ${START_HOUR} = 00 ]; then
    START_OBS_DAY=$((START_DAY - 1))
    START_OBS_HOUR=23
    CYCLE_HOUR_MAX=$((START_HOUR + 1))
else
    START_OBS_HOUR=$((START_HOUR - 1))
    START_OBS_DAY=${START_DAY}
    CYCLE_HOUR_MAX=$((START_HOUR + 1))
fi

if [ ${START_HOUR} = 23 ]; then
    START_HOUR_MAX=00
    START_DAY=$((START_DAY + 1))
fi

START_DAY=$(printf "%02d\n" ${START_DAY#0})
START_HOUR=$(printf "%02d\n" ${START_HOUR#0})
START_OBS_DAY=$(printf "%02d\n" ${START_OBS_DAY#0})
START_OBS_HOUR=$(printf "%02d\n" ${START_OBS_HOUR#0})
START_MONTH=$(printf "%02d\n" ${START_MONTH#0})

INITIAL_DATE=${START_YEAR}${START_MONTH}${START_DAY}
INITIAL_HOUR=${START_HOUR}
DFI_OPT_BEFORE=0
INTERVAL_SECONDS=21600

# Validate initial date
print_success "Validating initial date: ${INITIAL_DATE}${INITIAL_HOUR}"
if ! [[ "${INITIAL_DATE}${INITIAL_HOUR}" =~ ^[0-9]{8}[0-9]{2}$ ]]; then
    print_error "Invalid initial date format: ${INITIAL_DATE}${INITIAL_HOUR}"
    echo "Invalid initial date format: ${INITIAL_DATE}${INITIAL_HOUR}" > mail_message
    /usr/bin/mail -s "Initial Date Validation Failed" $EMAIL < mail_message
    exit 1
fi

# Function to safely get date components
get_date_component() {
    local date_str=$1
    local interval=$2
    local sed_pattern=$3
    local output
    output=$($HOMEDIR/date_creator.sh -s"$date_str" -i"$interval" 2>/dev/null | sed -e "$sed_pattern")
    if [ -z "$output" ] || [[ "$output" == *"Usage"* ]]; then
        print_error "date_creator.sh failed for input: -s$date_str -i$interval"
        echo "date_creator.sh failed for input: -s$date_str -i$interval" > mail_message
        /usr/bin/mail -s "Date Calculation Failed" $EMAIL < mail_message
        exit 1
    fi
    echo "$output"
}

############################################################
# Domain settings
############################################################
MAX_DOM=1
PARENT_ID='1,1,2,3,'
PARENT_GRID_RATIO='1,3,3,5'
I_PARENT_START='1,43,34,380'
J_PARENT_START='1,43,44,310'
S_WE='1, 1, 1, 1'
E_WE='120,109,103,1016'
S_SN='1, 1, 1, 1'
E_SN='120,109,103,1016'
DX=12000.0
DY=12000.0
ANALYSIS_INTERVAL=6

# Namelist settings
RUN_DAYS=00
RUN_HOURS=00
INPUT_FROM_FILE='.true., .true., .true., .true.,'
HISTORY_INTERVAL_BEFORE='720, 720, 720, 60'
HISTORY_INTERVAL_AFTER='360,360,360,60'
FRAMES_PER_OUTFILE_BEFORE='1,1000,24,1000'
FRAMES_PER_OUTFILE_AFTER='1,1000,24,1000'
RESTART=.false.
RESTART_INTERVAL=7200
IO_FORM_HISTORY=11
IO_FORM_RESTART=11
IO_FORM_INPUT=11
IO_FORM_BOUNDARY=2
DEBUG_LEVEL=0
INPUT_OUTPUT_INTERVAL=$((CYCLE_LENGTH_INTERVAL * 60))
CYCLING='false'
TIME_STEP=60
TIME_STEP_FRACT_NUM=0
TIME_STEP_FRACT_DEN=1
S_VERT='1, 1, 1, 1'
E_VERT='33, 33, 33, 45'
E_VERT_MATRIX="33"
DX_WRF='12000.0, 4000, 1333.33, 333.333'
DY_WRF='12000.0, 4000, 1333.33, 333.333'
P_TOP=5000
GRID_ID='1, 2, 3, 4'
PARENT_TIME_STEP_RATIO='1, 3, 3, 3'
FEEDBACK=1

# Physics options
MP_PHYSICS='8, 8, 1, 1'
RA_LW_PHYSICS='1, 1, 1, 1'
RA_SW_PHYSICS='1, 1, 1, 1'
RADT='12, 4, 1, 9'
SF_SFCLAY_PHYSICS='1, 1, 1, 1'
SF_SURFACE_PHYSICS='2, 2, 2, 2'
BL_PBL_PHYSICS='1, 1, 1, 1'
BLDT='0, 0, 0, 0'
CU_PHYSICS='3, 3, 3, 1'
CUDT='0, 0, 0, 0'
ISFFLX=1
IFSNOW=1
IFCLOUD=1
SURFACE_INPUT_SOURCE=1
NUM_SOIL_LAYERS=4
UCMCALL=0
DIFF_OPT=2
P_LEV_DIAG=0
NUM_METGRID_LEVELS=32
NIO_TASKS_PER_GROUP=0

if [ $RUN_RUC = 'true' ]; then
cd ${WORKDIR} || { print_error "Cannot cd to $WORKDIR"; exit 1; }
I=00
while [ ${I} -lt ${MULTIPLE} ]; do
    J=$((I + 1))
    K=$((J + 1))
    CYCLE_LENGTH=$((CYCLE_LENGTH_BEGIN + CYCLE_LENGTH_INTERVAL * (J - 1)))
    CYCLE_LENGTH2=$((CYCLE_LENGTH_BEGIN + CYCLE_LENGTH_INTERVAL * (K - 1)))
    CYCLE_LENGTH3=$((CYCLE_LENGTH_BEGIN + CYCLE_LENGTH_INTERVAL * K))

    [ $CYCLE_LENGTH3 -lt 10 ] && CYCLE_LENGTH3=0${CYCLE_LENGTH3}
    [ $CYCLE_LENGTH2 -lt 10 ] && CYCLE_LENGTH2=0${CYCLE_LENGTH2}
    [ $CYCLE_LENGTH -lt 10 ] && CYCLE_LENGTH=0${CYCLE_LENGTH}

    CYCLE_YEAR=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH" 's/^\(....\).*$/\1/')
    CYCLE_MONTH=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH" 's/^....\(..\).*$/\1/')
    CYCLE_DAY=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH" 's/^.*\(..\)..$/\1/')
    CYCLE_HOUR=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH" 's/^.*\(..\)$/\1/')

    CYCLE_YEAR2=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH2" 's/^\(....\).*$/\1/')
    CYCLE_MONTH2=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH2" 's/^....\(..\).*$/\1/')
    CYCLE_DAY2=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH2" 's/^.*\(..\)..$/\1/')
    CYCLE_HOUR2=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH2" 's/^.*\(..\)$/\1/')

    CYCLE_YEAR3=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH3" 's/^\(....\).*$/\1/')
    CYCLE_MONTH3=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH3" 's/^....\(..\).*$/\1/')
    CYCLE_DAY3=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH3" 's/^.*\(..\)..$/\1/')
    CYCLE_HOUR3=$(get_date_component "${INITIAL_DATE}${INITIAL_HOUR}" "$CYCLE_LENGTH3" 's/^.*\(..\)$/\1/')

    print_border "Cycle $J: Assimilation at ${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}"

    [ "$CYCLE_HOUR" = 00 ] && START_OBS_DAY=$((10#$CYCLE_DAY - 1)) && START_OBS_HOUR=23 || START_OBS_DAY=${CYCLE_DAY} && START_OBS_HOUR=$((10#$CYCLE_HOUR - 1))
    [ $START_OBS_HOUR -lt 10 ] && START_OBS_HOUR=0${START_OBS_HOUR}

    VAR_DATE=${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}
    ONE_HOUR='-1'
    ONE_HOUR_PLUS='+1'

    DFI_START_YEAR=$(get_date_component "${CYCLE_YEAR}${CYCLE_MONTH}${CYCLE_DAY}${CYCLE_HOUR}" "$ONE_HOUR" 's/^\(....\).*$/\1/')
    DFI_STOP_YEAR=${CYCLE_YEAR}
    DFI_START_MONTH=$(get_date_component "${CYCLE_YEAR}${CYCLE_MONTH}${CYCLE_DAY}${CYCLE_HOUR}" "$ONE_HOUR" 's/^....\(..\).*$/\1/')
    DFI_STOP_MONTH=${CYCLE_MONTH}
    DFI_START_DAY=$(get_date_component "${CYCLE_YEAR}${CYCLE_MONTH}${CYCLE_DAY}${CYCLE_HOUR}" "$ONE_HOUR" 's/^.*\(..\)..$/\1/')
    DFI_STOP_DAY=${CYCLE_DAY}
    DFI_START_HOUR=$(get_date_component "${CYCLE_YEAR}${CYCLE_MONTH}${CYCLE_DAY}${CYCLE_HOUR}" "$ONE_HOUR" 's/^.*\(..\)$/\1/')
    DFI_STOP_HOUR=${CYCLE_HOUR}

    CYCLE_YEAR_WINDOW_MIN=$(get_date_component "${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}" "$ONE_HOUR" 's/^\(....\).*$/\1/')
    CYCLE_YEAR_WINDOW_MAX=$(get_date_component "${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}" "$ONE_HOUR_PLUS" 's/^\(....\).*$/\1/')
    CYCLE_MONTH_WINDOW_MIN=$(get_date_component "${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}" "$ONE_HOUR" 's/^....\(..\).*$/\1/')
    CYCLE_MONTH_WINDOW_MAX=$(get_date_component "${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}" "$ONE_HOUR_PLUS" 's/^....\(..\).*$/\1/')
    CYCLE_DAY_WINDOW_MIN=$(get_date_component "${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}" "$ONE_HOUR" 's/^.*\(..\)..$/\1/')
    CYCLE_DAY_WINDOW_MAX=$(get_date_component "${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}" "$ONE_HOUR_PLUS" 's/^.*\(..\)..$/\1/')
    CYCLE_HOUR_WINDOW_MIN=$(get_date_component "${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}" "$ONE_HOUR" 's/^.*\(..\)$/\1/')
    CYCLE_HOUR_WINDOW_MAX=$(get_date_component "${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}" "$ONE_HOUR_PLUS" 's/^.*\(..\)$/\1/')

    cd $WORKDIR
    mkdir $VAR_DATE

    cat > namelist.input_inside_ruc_for_bdy_$VAR_DATE <<EOF
&time_control
run_days                            = 0,
run_hours                           = 0,
run_minutes                         = 0,
run_seconds                         = 0,
start_year                          = ${CYCLE_YEAR},
start_month                         = ${CYCLE_MONTH},
start_day                           = ${CYCLE_DAY},
start_hour                          = ${CYCLE_HOUR},
start_minute                        = 00, 00, 00, 00,
start_second                        = 00, 00, 00, 00,
end_year                            = ${CYCLE_YEAR2},
end_month                           = ${CYCLE_MONTH2},
end_day                             = ${CYCLE_DAY2},
end_hour                            = ${CYCLE_HOUR2},
end_minute                          = 00, 00, 00, 00,
end_second                          = 00, 00, 00, 00,
interval_seconds                    = ${INTERVAL_SECONDS},
input_from_file                     = ${INPUT_FROM_FILE}
history_interval                    = ${HISTORY_INTERVAL_AFTER},
frames_per_outfile                  = ${FRAMES_PER_OUTFILE_BEFORE},
restart                             = ${RESTART},
restart_interval                    = ${RESTART_INTERVAL},
io_form_history                     = ${IO_FORM_HISTORY},
io_form_restart                     = ${IO_FORM_RESTART},
io_form_input                       = ${IO_FORM_INPUT},
io_form_boundary                    = ${IO_FORM_BOUNDARY},
io_form_auxinput1                   = ${IO_FORM_AUXINPUT1},
nocolons                            = .true.
/

&dfi_control
dfi_opt                             = ${DFI_OPT_BEFORE},
dfi_nfilter                         = 7,
dfi_cutoff_seconds                  = 1800,
dfi_write_filtered_input            = .true.
dfi_write_dfi_history               = .false.
dfi_bckstop_year                    = ${DFI_START_YEAR},
dfi_bckstop_month                   = ${DFI_START_MONTH},
dfi_bckstop_day                     = ${DFI_START_DAY},
dfi_bckstop_hour                    = ${DFI_START_HOUR},
dfi_bckstop_minute                  = 40,
dfi_bckstop_second                  = 00,
dfi_fwdstop_year                    = ${DFI_STOP_YEAR},
dfi_fwdstop_month                   = ${DFI_STOP_MONTH},
dfi_fwdstop_day                     = ${DFI_STOP_DAY},
dfi_fwdstop_hour                    = ${DFI_STOP_HOUR},
dfi_fwdstop_minute                  = 10,
dfi_fwdstop_second                  = 00,
dfi_savehydmeteors                  = 0,
/

&domains
time_step                           = ${TIME_STEP},
time_step_fract_num                 = 0,
time_step_fract_den                 = 1,
max_dom                             = ${MAX_DOM},
e_we                                = ${E_WE},
e_sn                                = ${E_SN},
e_vert                              = ${E_VERT},
num_metgrid_levels                  = ${NUM_METGRID_LEVELS},
num_metgrid_soil_levels             = 4,
p_top_requested                     = ${P_TOP},
dx                                  = ${DX_WRF},
dy                                  = ${DY_WRF},
grid_id                             = ${GRID_ID},
parent_id                           = ${PARENT_ID},
i_parent_start                      = ${I_PARENT_START},
j_parent_start                      = ${J_PARENT_START},
parent_grid_ratio                   = ${PARENT_GRID_RATIO},
parent_time_step_ratio              = ${PARENT_TIME_STEP_RATIO},
feedback                            = ${FEEDBACK},
smooth_option                       = 0,
/

&physics
mp_physics                          = ${MP_PHYSICS},
ra_lw_physics                       = ${RA_LW_PHYSICS},
ra_sw_physics                       = ${RA_SW_PHYSICS},
radt                                = ${RADT},
sf_sfclay_physics                   = ${SF_SFCLAY_PHYSICS},
sf_surface_physics                  = ${SF_SURFACE_PHYSICS},
bl_pbl_physics                      = ${BL_PBL_PHYSICS},
bldt                                = ${BLDT},
cu_physics                          = ${CU_PHYSICS},
cudt                                = ${CUDT},
isfflx                              = ${ISFFLX},
ifsnow                              = ${IFSNOW},
icloud                              = ${IFCLOUD},
surface_input_source                = 1,
num_soil_layers                     = ${NUM_SOIL_LAYERS},
sf_urban_physics                    = ${UCMCALL},
num_land_cat = 21
/

&fdda
/

&dynamics
w_damping                           = 0,
diff_opt                            = ${DIFF_OPT},
km_opt                              = 4,
diff_6th_opt                        = 2,      0,      0,
diff_6th_factor                     = 0.12,   0.12,   0.12,
base_temp                           = 290.
damp_opt                            = 0,
zdamp                               = 5000.,  5000.,  5000.,
dampcoef                            = 0.2,    0.2,    0.2
khdif                               = 0,      0,      0,
kvdif                               = 0,      0,      0,
non_hydrostatic                     = .true., .true., .true.,
moist_adv_opt                       = 1,      1,      1,
scalar_adv_opt                      = 1,      1,      1,
/

&bdy_control
spec_bdy_width                      = 5,
spec_zone                           = 1,
relax_zone                          = 4,
specified                           = .true., .false.,.false., .false.,
nested                              = .false., .true., .true., .true.,
/

&grib2
/

&namelist_quilt
nio_tasks_per_group = ${NIO_TASKS_PER_GROUP},
nio_groups = 1,
/
EOF

    rm -rf namelist.input
    cp namelist.input_inside_ruc_for_bdy_$VAR_DATE namelist.input
    mv namelist.input_inside_ruc_for_bdy_$VAR_DATE $LOGDIR

    for file in /home/users/hrehman/WRF/WRFV4.5.2/run/*; do
        filename=$(basename "$file")
        if [ "$filename" != "namelist.input" ]; then
            ln -sf "$file" .
        fi
    done

    ln -sf ${MET_EM_FILES}/* .

    ulimit -s 8176
    ulimit -c unlimited

    # Step 1: Run real.exe
    print_sub_border "Step 1: Running real.exe"
    mpiexec -n 1 real.exe
    while true; do
        sleep 30
        grep -i "success" rsl.out.0000 && break
        grep -i "fatal" rsl.out.0000 && break
    done
    sleep 1
    if grep -i "success" rsl.out.0000; then
        print_success "Step 1 completed successfully"
        cp rsl.out.0000 $LOGDIR/ruc_real_run_rsl.out_${VAR_DATE}
        rm -rf rsl.*.????
    else
        print_error "Step 1 failed"
        print_border "Cycle $J Failed: real.exe"
        echo "RUC Real Run failed" > mail_message
        /usr/bin/mail -s "RUC Real Run failed" $EMAIL < mail_message
        exit 1
    fi
    print_sub_border ""

    # Step 2: Run wrf.exe for first guess
    if [ "$SKIP_WRF_RUN" != "true" ]; then
        print_sub_border "Step 2: Running wrf.exe to produce first guess"
        mpirun -n $total_slots --hostfile $hostfile wrf.exe
        while true; do
            sleep 30
            grep -i "success" rsl.out.0000 && break
            grep -i "fatal" rsl.out.0000 && break
        done
        sleep 1
        if grep -i "success" rsl.out.0000; then
            print_success "Step 2 completed successfully"
        else
            print_error "Step 2 failed"
            print_border "Cycle $J Failed: wrf.exe for First Guess"
            echo "WRF Run failed" > mail_message
            /usr/bin/mail -s "WRF Run failed" $EMAIL < mail_message
            exit 1
        fi
    else
        print_sub_border "Step 2: Skipping wrf.exe for First Guess (Testing)"
        print_success "Step 2 completed successfully"
    fi
    print_sub_border ""

    # Step 3: Update namelist and run real.exe for wrfbdy
    NMLINK="$WORKDIR/namelist.input"
    print_sub_border "Step 3: Updating namelist for real.exe"
    print_success "Running real.exe to produce wrfinput and wrfbdy"
    sed -i "/^\s*start_year\s*=/ s/.*/ start_year = ${CYCLE_YEAR2}, ${CYCLE_YEAR2}, ${CYCLE_YEAR2},/" "$NMLINK"
    sed -i "/^\s*start_month\s*=/ s/.*/ start_month = ${CYCLE_MONTH2}, ${CYCLE_MONTH2}, ${CYCLE_MONTH2},/" "$NMLINK"
    sed -i "/^\s*start_day\s*=/ s/.*/ start_day = ${CYCLE_DAY2}, ${CYCLE_DAY2}, ${CYCLE_DAY2},/" "$NMLINK"
    sed -i "/^\s*start_hour\s*=/ s/.*/ start_hour = ${CYCLE_HOUR2}, ${CYCLE_HOUR2}, ${CYCLE_HOUR2},/" "$NMLINK"
    sed -i "/^\s*end_year\s*=/ s/.*/ end_year = ${CYCLE_YEAR3}, ${CYCLE_YEAR3}, ${CYCLE_YEAR3},/" "$NMLINK"
    sed -i "/^\s*end_month\s*=/ s/.*/ end_month = ${CYCLE_MONTH3}, ${CYCLE_MONTH3}, ${CYCLE_MONTH3},/" "$NMLINK"
    sed -i "/^\s*end_day\s*=/ s/.*/ end_day = ${CYCLE_DAY3}, ${CYCLE_DAY3}, ${CYCLE_DAY3},/" "$NMLINK"
    sed -i "/^\s*end_hour\s*=/ s/.*/ end_hour = ${CYCLE_HOUR3}, ${CYCLE_HOUR3}, ${CYCLE_HOUR3},/" "$NMLINK"
    sed -i "/^\s*max_dom\s*=/ s/.*/ max_dom = 1/" "$NMLINK"

    mpiexec -n 1 real.exe
    while true; do
        sleep 30
        grep -i "success" rsl.out.0000 && break
        grep -i "fatal" rsl.out.0000 && break
    done
    sleep 1
    if grep -i "success" rsl.out.0000; then
        print_success "Step 3 completed successfully"
        cp rsl.out.0000 $LOGDIR/ruc_real_run_rsl.out_${VAR_DATE}
        rm -rf rsl.*.????
    else
        print_error "Step 3 failed"
        print_border "Cycle $J Failed: real.exe for wrfbdy_d01"
        echo "RUC Real Run failed for wrfbdy_d01" > mail_message
        /usr/bin/mail -s "RUC Real Run failed" $EMAIL < mail_message
        exit 1
    fi
    print_sub_border ""

    cp -v wrfinput_d01 $VAR_DATE
    cp -v wrfbdy_d01 $VAR_DATE
    cd $VAR_DATE

    cat > namelist.input_3dvar_${VAR_DATE} << EOF
&wrfvar1
WRITE_INCREMENTS=false
PRINT_DETAIL_OBS=true
PRINT_DETAIL_f_OBS=false
print_detail_grad=true
PRINT_DETAIL_MAP=false
PRINT_DETAIL_RADAR=false
check_max_iv_print=true
/
&wrfvar2
CALC_W_INCREMENT=TRUE
/
&wrfvar3
ob_format=2
/
&wrfvar4
USE_GPSPWOBS=false
USE_GPSZTDOBS=true
USE_BUOYOBS=true
USE_SYNOPOBS=true
USE_METAROBS=true
USE_SOUNDOBS=true
USE_AIREPOBS=true
USE_SHIPSOBS=true
USE_PROFILEROBS=true
USE_RADAROBS=false
USE_RADAR_RV=false
USE_RADAR_RF=false
USE_RADAR_RQV=false
USE_RADAR_RHV=false
USE_QSCATOBS=true
USE_GEOAMVOBS=true
USE_AIRSRETOBS=true
USE_SSMITBOBS=false
/
&wrfvar5
max_error_tb=3.0
max_error_uv=3.0
max_error_q=1.5
max_error_t=4.0
max_error_rv=2.5
max_error_rf=3.0
max_error_pw=5.0
/
&wrfvar6
orthonorm_gradient=true
max_ext_its=2
/
&wrfvar7
CV_OPTIONS=5
len_scaling1=1.0
len_scaling2=1.0
len_scaling3=1.0
len_scaling4=1.0
len_scaling5=1.0
/
&wrfvar8
/
&wrfvar9
trace_use=false
WARNINGS_ARE_FATAL=true
/
&wrfvar10
test_transforms=false
test_gradient=false
/
&wrfvar11
calculate_cg_cost_fn=false
/
&wrfvar12
/
&wrfvar13
/
&wrfvar14
RTMINIT_NSENSOR =   14
RTMINIT_PLATFORM =    1,   1,   1,   9,  10,   1,   1,  10,   9, 12, 12,  29, 10, 17
RTMINIT_SATID    =   15,  18,  19,   2,   2,  18,  19,   2,   2, 2 , 3 ,  1 , 2,   0
RTMINIT_SENSOR   =    3,   3,   3,   3,   3,  15,  15,  15,  11, 21, 21 , 63, 16, 19
thinning_mesh    =  50., 50., 50., 50., 50., 35., 35., 35., 40.,15., 15. , 30, 50, 40
thinning = .true.
qc_rad = .true.
write_iv_rad_ascii = .false.
write_oa_rad_ascii = .true.
rtm_option = 1
only_sea_rad = .false.
use_varbc = .true.
rttov_emis_atlas_ir=1
rttov_emis_atlas_mw=1
use_rttov_kmatrix=.true.
varbc_nbgerr=5000,
varbc_nobsmin=50
use_blacklist_rad=.true.
/
&wrfvar15
/
&wrfvar16
/
&wrfvar17
analysis_type="QC-OBS"
/
&wrfvar18
analysis_date='${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}:00:00.0000',
/
&wrfvar19
/
&wrfvar20
/
&wrfvar21
time_window_min='${CYCLE_YEAR_WINDOW_MIN}-${CYCLE_MONTH_WINDOW_MIN}-${CYCLE_DAY_WINDOW_MIN}_${CYCLE_HOUR_WINDOW_MIN}:00:00.0000',
/
&wrfvar22
time_window_max='${CYCLE_YEAR_WINDOW_MAX}-${CYCLE_MONTH_WINDOW_MAX}-${CYCLE_DAY_WINDOW_MAX}_${CYCLE_HOUR_WINDOW_MAX}:00:00.0000',
/
&wrfvar23
/
&time_control
force_use_old_data = T
start_year=${CYCLE_YEAR2}
start_month=${CYCLE_MONTH2},
start_day=${CYCLE_DAY2},
start_hour=${CYCLE_HOUR2},
end_year=${CYCLE_YEAR2},
end_month=${CYCLE_MONTH2},
end_day=${CYCLE_DAY2},
end_hour=${CYCLE_HOUR2},
cycling=.false.
use_netcdf_classic=.true.
nocolons = .true.
/
&dfi_control
/
&domains
e_we=${E_WE},
e_sn=${E_SN},
e_vert=${E_VERT},
dx=${DX_WRF},
dy=${DY_WRF},
max_dom=1
/
&physics
mp_physics=${MP_PHYSICS},
sf_sfclay_physics=${SF_SFCLAY_PHYSICS},
sf_surface_physics=${SF_SURFACE_PHYSICS},
ra_sw_physics=${RA_SW_PHYSICS},
ra_lw_physics=${RA_LW_PHYSICS},
bl_pbl_physics=${BL_PBL_PHYSICS},
radt=${RADT},
cu_physics=${CU_PHYSICS},
cudt=${CUDT},
num_soil_layers=${NUM_SOIL_LAYERS},
num_land_cat=21
/

&fdda
/
&dynamics
/
&bdy_control
/
&grib2
/
&namelist_quilt
/
EOF

    cp namelist.input_3dvar_${VAR_DATE} namelist.input
    cp namelist.input_3dvar_${VAR_DATE} /home/users/hrehman/WRF/WRFDA/WORK_DIR/namelist.input
    mv namelist.input_3dvar_${VAR_DATE} ${LOGDIR}

    WRFOUT_FILENAME="wrfout_d01_${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}_00_00"
    print_success "Copying $WRFOUT_FILENAME to ./fg"
    if [ -f "$WORKDIR/$WRFOUT_FILENAME" ]; then
        rm -f $WORKDIR/fg
        cp -v $WORKDIR/$WRFOUT_FILENAME ./fg
    else
        print_error "Error: $WORKDIR/$WRFOUT_FILENAME does not exist"
        exit 1
    fi

    # Step 4: Update lower boundary conditions
    print_sub_border "Step 4: Updating lower boundary condition"
    cat > parame.in_lbc_$VAR_DATE <<EOF
&control_param
da_file            = './fg'
wrf_input          = './wrfinput_d01'
domain_id          = 1
debug   = .true.
update_lateral_bdy=.false.
update_low_bdy = .true.
update_lsm = .false.
iswater=17
/
EOF

    cp parame.in_lbc_$VAR_DATE parame.in
    mv parame.in_lbc_$VAR_DATE $LOGDIR
    ln -sf /home/users/hrehman/WRF/WRFDA/WORK_DIR/* .
    ulimit -s 8176

    ./da_update_bc.exe > update_low_bdy_${VAR_DATE}.txt
    if grep -i successfully update_low_bdy_${VAR_DATE}.txt; then
        print_success "*** Update_bc completed successfully ***"
        print_success "Step 4 completed successfully"
    else
        print_error "Step 4 failed"
        print_border "Cycle $J Failed: Lower Boundary Conditions"
        exit 1
    fi
    print_sub_border ""

    # Step 5: Run da_wrfvar.exe
    print_sub_border "Step 5: Running da_wrf.exe"
    OBS_FILE="$OBASCIIDIR/concatenated_${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}:00:00.ascii"
    print_success "Checking observation file:"
    ls -l "$OBS_FILE" || {
        print_error "Observation file $OBS_FILE does not exist"
        exit 1
    }
    print_success "Observation file size: $(wc -l < "$OBS_FILE") lines"
    head -n 10 "$OBS_FILE" > $LOGDIR/ob_ascii_head_$VAR_DATE.txt
    cp -v "$OBS_FILE" ./ob.ascii

    print_success "Verifying input files:"
    ls -l fg wrfinput_d01
    ncdump -h fg | grep "num_domains" > $LOGDIR/fg_domains_$VAR_DATE.txt

    mpiexec -n 1 da_wrfvar.exe
    while true; do
        sleep 30
        grep -i "success" rsl.out.0000 && break
        grep -i "fatal" rsl.out.0000 && break
    done
    sleep 1
    if grep -i "success" rsl.out.0000; then
        print_success "*** WRF-Var completed successfully ***"
        print_success "Checking assimilation output:"
        ls -l fg wrfvar_output
        md5sum fg wrfvar_output > checksums.txt
        cat checksums.txt
        ncdump -h wrfvar_output | grep "num_domains" > $LOGDIR/wrfvar_output_domains_$VAR_DATE.txt
        print_success "Copying wrfvar_output to $ANALYSISDIR/wrfvar_output_$VAR_DATE"
        cp -v wrfvar_output $ANALYSISDIR/wrfvar_output_$VAR_DATE
        if [ $? -eq 0 ]; then
            print_success "Copy successful"
            ls -l $ANALYSISDIR/wrfvar_output_$VAR_DATE
        else
            print_error "Copy to $ANALYSISDIR failed"
            exit 1
        fi
        cp rsl.out.0000 $LOGDIR/wrfda_rsl.out.$VAR_DATE
        grep -i "observation" $LOGDIR/wrfda_rsl.out.$VAR_DATE > $LOGDIR/wrfda_obs_summary_$VAR_DATE.txt
        print_success "Step 5 completed successfully"
    else
        print_error "Step 5 failed"
        print_border "Cycle $J Failed: WRF 3DVAR DA"
        echo "WRF 3DVAR DA $VAR_DATE run failed" > mail_message
        /usr/bin/mail -s "WRF 3DVAR DA $VAR_DATE run failed" $EMAIL < mail_message
        exit 1
    fi
    print_sub_border ""

    cp statistics $LOGDIR/statistics_$VAR_DATE

    # Step 6: Update lateral boundary conditions
    print_sub_border "Step 6: Updating lateral boundary condition"
    cat > parame.in_latbc_$VAR_DATE <<EOF
&control_param
da_file            = './wrfvar_output'
wrf_bdy_file       = './wrfbdy_d01'
domain_id          = 1
debug              = .true.
update_lateral_bdy=.true.
update_low_bdy = .false.
update_lsm = .false.
iswater=17
/
EOF

    cp parame.in_latbc_$VAR_DATE parame.in
    mv parame.in_latbc_$VAR_DATE $LOGDIR
    ulimit -s 8176

    print_success "Verifying wrfbdy_d01 before update:"
    ls -l wrfbdy_d01
    md5sum wrfbdy_d01 > $LOGDIR/wrfbdy_pre_update_$VAR_DATE.txt

    ./da_update_bc.exe > update_lat_bdy_${VAR_DATE}.txt
    if grep -i success update_lat_bdy_${VAR_DATE}.txt; then
        print_success "*** Update_bc completed successfully ***"
        print_success "Verifying wrfbdy_d01 after update:"
        ls -l wrfbdy_d01
        md5sum wrfbdy_d01 > $LOGDIR/wrfbdy_post_update_$VAR_DATE.txt
        print_success "Copying updated wrfbdy_d01 and wrfvar_output to $VAR_DATE"
        cp -v wrfbdy_d01 $VAR_DATE/wrfbdy_d01_updated
        cp -v wrfvar_output $VAR_DATE/wrfvar_output_updated
        ls -l $VAR_DATE/wrfbdy_d01_updated $VAR_DATE/wrfvar_output_updated
        print_success "Step 6 completed successfully"
    else
        print_error "Step 6 failed"
        print_border "Cycle $J Failed: Lateral Boundary Conditions"
        echo "Lateral Boundary Update $VAR_DATE run failed" > mail_message
        /usr/bin/mail -s "Lateral Boundary Update $VAR_DATE run failed" $EMAIL < mail_message
        exit 1
    fi
    print_sub_border ""

    # Step 7: Run final WRF forecast
    cd $WORKDIR
    rm -rf rsl.*.????
    rm -f wrfinput_d01 wrfbdy_d01
    print_success "Linking updated wrfvar_output and wrfbdy_d01 for final WRF run"
    ln -sf $VAR_DATE/wrfvar_output ./wrfinput_d01
    ln -sf $VAR_DATE/wrfbdy_d01 ./wrfbdy_d01
    print_success "Verifying links:"
    ls -l wrfinput_d01 wrfbdy_d01
    print_success "Running final WRF forecast"
    mpirun -n $total_slots --hostfile $hostfile wrf.exe
    while true; do
        sleep 30
        grep -i "success" rsl.out.0000 && break
        grep -i "fatal" rsl.out.0000 && break
    done
    sleep 1
    if grep -i "success" rsl.out.0000; then
        print_success "Step 7 completed successfully"
    else
        print_error "Step 7 failed"
        print_border "Cycle $J Failed: Final WRF Forecast"
        echo "WRF RUC $VAR_DATE run failed" > mail_message
        /usr/bin/mail -s "WRF RUC $VAR_DATE run failed" $EMAIL < mail_message
        exit 1
    fi
    print_sub_border ""

    # Copy wrfout files
    WRFOUT_FILENAME_DA="wrfout_d01_${CYCLE_YEAR3}-${CYCLE_MONTH3}-${CYCLE_DAY3}_${CYCLE_HOUR3}_00_00"
    print_success "Copying $WRFOUT_FILENAME_DA to $DAFILES"
    if [ -f "$WORKDIR/$WRFOUT_FILENAME_DA" ]; then
        cp -v "$WORKDIR/$WRFOUT_FILENAME_DA" "$DAFILES"
    else
        print_error "Error: $WORKDIR/$WRFOUT_FILENAME_DA does not exist"
        exit 1
    fi

    # Prepare first guess for next cycle
    NEXT_CYCLE_FG="wrfout_d01_${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}_00_00"
    print_success "Preparing fg for next cycle: $NEXT_CYCLE_FG"
    if [ -f "$WORKDIR/$NEXT_CYCLE_FG" ]; then
        rm -f "$WORKDIR/fg"
        ln -sf "$WORKDIR/$NEXT_CYCLE_FG" "$WORKDIR/fg"
    else
        print_error "Error: $WORKDIR/$NEXT_CYCLE_FG does not exist"
        exit 1
    fi

    print_border "Cycle $J successfully produced wrfout at ${CYCLE_YEAR3}-${CYCLE_MONTH3}-${CYCLE_DAY3}_${CYCLE_HOUR3}"
    I=$((I + 1))
done
fi
