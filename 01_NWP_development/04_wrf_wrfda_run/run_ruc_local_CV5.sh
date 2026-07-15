#!/bin/bash

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

############################################################
############################################################
#  Forecast Script
#  Author: Haseeb ur Rehman
############################################################
############################################################

HOMEDIR=/Users/haseeb.rehman/WRF #(consist of every wrf elements)

# Parent Work Directory
WORKDIR=$HOMEDIR/WORKDIR #(wrf out will be produced)
# WRF Directory
WRFDIR=$HOMEDIR/WRFV4.5 #(where the WRFv4.5 is located)
WRFDADIR=$HOMEDIR/WRFDA #(WRFDA directory)
ANALYSISDIR=$WORKDIR/analysis_dir #(output from WRFDA ....wrfvar)
DAFILES=$ANALYSISDIR/After_DA #(output from WRFDA ....wrfvar)
# Directory where the met_em files are stored
MET_EM_FILES=$HOMEDIR/WPS-4.5/2021_met_em_ERA5_3_domains #met_em_files generted by WPS
OBASCIIDIR=$HOMEDIR/WRFDA/DAT_DIR/data_for_assimilation/concatenate_2021_event #(concatenated files directory, which is combination of Synop and GNSS ZTD )
B_MATRIX_DIR=$HOMEDIR/WRFDA/DAT_DIR/be #(where is be.DAT)
# Log Directory to be created while start of the code
LOGDIR=${WORKDIR}/log_dir #(where the rsl_out saved)
EMAIL="haseeb.rehman@uni.lu"

RUN_RUC='true'
SKIP_WRF_RUN='false'  # Set to false or remove/comment out this line for an actual run

# Create directories before start
test -d $WORKDIR || mkdir -p $WORKDIR
test -d $LOGDIR || mkdir -p $LOGDIR
test -d $ANALYSISDIR || mkdir -p $ANALYSISDIR
test -d $ANALYSISDIR/Before_DA || mkdir -p $ANALYSISDIR/Before_DA
test -d $DAFILES || mkdir -p $DAFILES

############################################################
################### Text Colors ########
############################################################
# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to draw borders
draw_border() {
    local message="$1"
    local color="$2"
    local length=${#message}
    local border=$(printf "%-${length}s" "=" | tr ' ' '=')
    echo -e "${color}${border}${NC}"
    echo -e "${color}${message}${NC}"
    echo -e "${color}${border}${NC}"
}

############################################################
################### Time control of the simulations ########
############################################################
START_YEAR=2021
START_MONTH=07
START_DAY=16
START_HOUR=00

CYCLE_LENGTH=6          # Cycling hours interval
CYCLE_LENGTH_BEGIN=00     # Begin of cycling after analysis time
CYCLE_LENGTH_INTERVAL=6  # Same as CYCLE_LENGTH
MULTIPLE=40           # Define number of cycles for a RUC

###########################################################
########## DO NOT CHANGE ANYTHING ##########################
###########################################################

if [ ${START_HOUR} = 00 ]
then
    START_OBS_DAY=$(expr ${START_DAY} - 1)
    START_OBS_HOUR=23
    CYCLE_HOUR_MAX=$(expr ${START_HOUR} + 1)
else
    START_OBS_HOUR=$(expr ${START_HOUR} - 1)
    START_OBS_DAY=${START_DAY}
    CYCLE_HOUR_MAX=$(expr ${START_HOUR} + 1)
fi

if [ ${START_HOUR} = 23 ]
then
    START_HOUR_MAX=00
    START_DAY=`expr ${START_DAY} + 1`
fi

START_DAY=$(printf "%02d\n" ${START_DAY#0})
START_HOUR=$(printf "%02d\n" ${START_HOUR#0})
START_OBS_DAY=$(printf "%02d\n" ${START_OBS_DAY#0})
START_OBS_HOUR=$(printf "%02d\n" ${START_OBS_HOUR#0})
START_OBS_MINUTE=$(printf "%02d\n" ${START_OBS_MINUTE#0})
END_OBS_MINUTE=$(printf "%02d\n" ${END_OBS_MINUTE#0})
START_MONTH=$(printf "%02d\n" ${START_MONTH#0})

# Initial date and initial time
INITIAL_DATE=${START_YEAR}${START_MONTH}${START_DAY}
INITIAL_HOUR=${START_HOUR}

DFI_OPT_BEFORE=0

############################################################
################### Input data interval settings in seconds
############################################################

INTERVAL_SECONDS=21600

############################################################
################### Domain settings for the simulations ####
############################################################
MAX_DOM=1                       #for data assimilation
MAX_DOM_FF=3                     #for final forecast run
PARENT_ID='1,1,2,3,'           # ID of parent domain
PARENT_GRID_RATIO='1,3,3,5'    # grid ratio between domains
I_PARENT_START='1,43,38,380' # X-coordinate of the lower left corner of each domain
J_PARENT_START='1,43,38,310'  # Y-coordinate of the lower left corner of each domain
S_WE='1, 1, 1, 1'              # Set to '1' for each domain
E_WE='120,109,103,1016'        # Number of east-west grid points in each domain
S_SN='1, 1, 1, 1'              # Set to '1' for each domain
E_SN='120,109,103,1016'        # Number of south-north grid points in each domain

DX=12000.0                  # Grid resolution (m) of the outermost domain (ONLY) (lon) (nests calculated)
DY=12000.0                  # Grid resolution (m) of the outermost domain (ONLY) (lat)

############################################################
################### Analysis interval settings in hours ####
############################################################

ANALYSIS_INTERVAL=6

############################################################
# Time Control Options for namelist.input
############################################################

RUN_DAYS=00                                        # Forecast length (days)
RUN_HOURS=00                                       # Forecast length (hours)
INPUT_FROM_FILE='.true., .true., .true., .true.,' # .true. to use high resolution topography
HISTORY_INTERVAL_BEFORE='720, 720, 720, 60'          # Interval of model output (minutes)
HISTORY_INTERVAL_AFTER='360,360,360,60'               # Interval of model output (minutes) after assimilation
FRAMES_PER_OUTFILE_BEFORE='1,1,1,1000'        # Output file is split after <num> output times (0=one file only)
FRAMES_PER_OUTFILE_AFTER='1,1,1,1000'         # Output file is split after <num> output times (0=one file only)
RESTART=.false.                                   # write restart file
RESTART_INTERVAL=7200                              # interval of restart files (minutes)
IO_FORM_HISTORY=11
IO_FORM_RESTART=11                               # Data format (2 = NetCDF) , 11= parallel NetCDF
IO_FORM_INPUT=11                                  #
IO_FORM_BOUNDARY=11
DEBUG_LEVEL=0                                     # Amount of Debug output
INPUT_OUTPUT_INTERVAL=$(expr ${CYCLE_LENGTH_INTERVAL} \* 60) # files written in INPUT_OUTPUT_INTERVAL minutes for assimilation

CYCLING='false'

############################################################
# Domain settings for the simulations
############################################################

TIME_STEP=60                          # Model timestep (seconds) usually use 6x gridbox size
TIME_STEP_FRACT_NUM=0
TIME_STEP_FRACT_DEN=1
S_VERT='1, 1, 1, 1'                   # Uppermost level number
E_VERT='33, 33, 33, 45'            # Lowermost level number
E_VERT_MATRIX="33"                   # same as e_vert but for b-matrix as single number
DX_WRF='12000.0, 4000, 1333.33, 333.333'
DY_WRF='12000.0, 4000, 1333.33, 333.333'
P_TOP=5000
GRID_ID='1, 2, 3, 4'                  # Domain ID
PARENT_TIME_STEP_RATIO='1, 3, 3, 3'   # time step ratio of the domains
FEEDBACK=1                            # 1=2-way nesting

############################################################
################### Physics options settings ###############
############################################################

MP_PHYSICS='8, 8, 8, 1'           # Microphysics scheme: 8 = Thompson, 10 Morrison 2-moment scheme
RA_LW_PHYSICS='1, 1, 1, 1'        # LW radiation scheme: 1 = RRTM , 4=RRTMG
RA_SW_PHYSICS='1, 1, 1, 1'        # SW radiation scheme: 1 = Dudhia 4 = RRTMG
RADT='12, 4, 1, 9'                # Radiation timestep (minutes), dx minutes recommended (NCAR)
SF_SFCLAY_PHYSICS='1, 1, 1, 1'    # Surface layer physics: 1= MM5, 5=MYNN
SF_SURFACE_PHYSICS='2, 2, 2, 2'   # Surface physics: 2 = Noah LSM; 4 = NOAH-MP
BL_PBL_PHYSICS='1, 1, 1, 1'       # Boundary layer scheme: 1 = 1 YSU, 5 = MYNN2
BLDT='0, 0, 0, 0'                 # timestep for boundary layer scheme (model timesteps, 0 = every timestep)
CU_PHYSICS='3, 3, 3, 1'           # Convection scheme: 1 = KF-Eta
CUDT='0, 0, 0, 0'                 # timestep for convection scheme (model timesteps, 0 = every timestep)
ISFFLX=1
IFSNOW=1
IFCLOUD=1
SURFACE_INPUT_SOURCE=1
NUM_SOIL_LAYERS=4                 # Number of soil layers (depending on soil model used)
UCMCALL=0                         # Urban Canopy model
DIFF_OPT=2
P_LEV_DIAG=0

############################################################
################### Metgrid levels settings ################
############################################################

NUM_METGRID_LEVELS=34

############################################################
# for I/O quilting, useful for large domains################
############################################################

NIO_TASKS_PER_GROUP=0 # set at least to 4 for large domains

if [ $RUN_RUC = 'true' ]
then
    cd ${WORKDIR}

    I=0
    while [ ${I} -lt ${MULTIPLE} ]
    do
        CYCLE_NUM=$((I + 1))

        # Date string calculations
        J=`expr $I + 1`
        K=`expr $J + 1`

        CYCLE_LENGTH=`expr $CYCLE_LENGTH_BEGIN + $CYCLE_LENGTH_INTERVAL \* $(expr $J - 1)`
        CYCLE_LENGTH2=`expr $CYCLE_LENGTH_BEGIN + $CYCLE_LENGTH_INTERVAL \* $(expr $K - 1)`
        CYCLE_LENGTH3=`expr $CYCLE_LENGTH_BEGIN + $CYCLE_LENGTH_INTERVAL \* $K`

        [ ${CYCLE_LENGTH3} -lt 10 ] && CYCLE_LENGTH3=0${CYCLE_LENGTH3}
        [ ${CYCLE_LENGTH2} -lt 10 ] && CYCLE_LENGTH2=0${CYCLE_LENGTH2}
        [ ${CYCLE_LENGTH} -lt 10 ] && CYCLE_LENGTH=0${CYCLE_LENGTH}

        CYCLE_YEAR=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH} | sed -e 's/^\(....\).*$/\1/'`
        CYCLE_MONTH=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH} | sed -e 's/^....\(..\).*$/\1/'`
        CYCLE_DAY=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH} | sed -e 's/^.*\(..\)..$/\1/'`
        CYCLE_HOUR=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH} | sed -e 's/^.*\(..\)$/\1/'`

        CYCLE_YEAR2=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH2} | sed -e 's/^\(....\).*$/\1/'`
        CYCLE_MONTH2=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH2} | sed -e 's/^....\(..\).*$/\1/'`
        CYCLE_DAY2=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH2} | sed -e 's/^.*\(..\)..$/\1/'`
        CYCLE_HOUR2=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH2} | sed -e 's/^.*\(..\)$/\1/'`

        CYCLE_YEAR3=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH3} | sed -e 's/^\(....\).*$/\1/'`
        CYCLE_MONTH3=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH3} | sed -e 's/^....\(..\).*$/\1/'`
        CYCLE_DAY3=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH3} | sed -e 's/^.*\(..\)..$/\1/'`
        CYCLE_HOUR3=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH3} | sed -e 's/^.*\(..\)$/\1/'`

        [ ${CYCLE_HOUR} = 00 ] && START_OBS_DAY=$(expr ${CYCLE_DAY} - 1) && START_OBS_HOUR=23 || START_OBS_DAY=${CYCLE_DAY} && START_OBS_HOUR=$(expr ${CYCLE_HOUR} - 1)
        [ ${START_OBS_HOUR} -lt 10 ] && START_OBS_HOUR=0${START_OBS_HOUR}

        VAR_DATE=${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}
        ONE_HOUR='-1'
        ONE_HOUR_PLUS='+1'

        DFI_START_YEAR=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR}${CYCLE_MONTH}${CYCLE_DAY}${CYCLE_HOUR} -i${ONE_HOUR} | sed -e 's/^\(....\).*$/\1/'`
        DFI_STOP_YEAR=${CYCLE_YEAR}
        DFI_START_MONTH=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR}${CYCLE_MONTH}${CYCLE_DAY}${CYCLE_HOUR} -i${ONE_HOUR} | sed -e 's/^....\(..\).*$/\1/'`
        DFI_STOP_MONTH=${CYCLE_MONTH}
        DFI_START_DAY=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR}${CYCLE_MONTH}${CYCLE_DAY}${CYCLE_HOUR} -i${ONE_HOUR} | sed -e 's/^.*\(..\)..$/\1/'`
        DFI_STOP_DAY=${CYCLE_DAY}
        DFI_START_HOUR=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR}${CYCLE_MONTH}${CYCLE_DAY}${CYCLE_HOUR} -i${ONE_HOUR} | sed -e 's/^.*\(..\)$/\1/'`
        DFI_STOP_HOUR=${CYCLE_HOUR}

        CYCLE_YEAR_WINDOW_MIN=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2} -i${ONE_HOUR} | sed -e 's/^\(....\).*$/\1/'`
        CYCLE_YEAR_WINDOW_MAX=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2} -i${ONE_HOUR_PLUS} | sed -e 's/^\(....\).*$/\1/'`
        CYCLE_MONTH_WINDOW_MIN=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2} -i${ONE_HOUR} | sed -e 's/^....\(..\).*$/\1/'`
        CYCLE_MONTH_WINDOW_MAX=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2} -i${ONE_HOUR_PLUS} | sed -e 's/^....\(..\).*$/\1/'`
        CYCLE_DAY_WINDOW_MIN=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2} -i${ONE_HOUR} | sed -e 's/^.*\(..\)..$/\1/'`
        CYCLE_DAY_WINDOW_MAX=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2} -i${ONE_HOUR_PLUS} | sed -e 's/^.*\(..\)..$/\1/'`
        CYCLE_HOUR_WINDOW_MIN=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2} -i${ONE_HOUR} | sed -e 's/^.*\(..\)$/\1/'`
        CYCLE_HOUR_WINDOW_MAX=`$HOMEDIR/date_creator.sh -s${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2} -i${ONE_HOUR_PLUS} | sed -e 's/^.*\(..\)$/\1/'`

        # Cycle header
        draw_border "Cycle ${CYCLE_NUM}: Assimilation at ${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2} ${CYCLE_HOUR2}:00:00" "${GREEN}"

        cd $WORKDIR
        mkdir $VAR_DATE

        # Step 1: Running real.exe
        echo -e "${BLUE}Step 1: Running real.exe${NC}"
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
nocolons                            = .true.
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
&dynamics
hybrid_opt                          = 2
w_damping                           = 0
diff_opt                            = ${DIFF_OPT},
km_opt                              = 4
diff_6th_opt                        = 2
diff_6th_factor                     = 0.12
base_temp                           = 290.0
damp_opt                            = 0
zdamp                               = 5000.0
dampcoef                            = 0.2
khdif                               = 0
kvdif                               = 0
non_hydrostatic                     = .true.
moist_adv_opt                       = 1
scalar_adv_opt                      = 1
gwd_opt                             = 1
/

&bdy_control
spec_bdy_width = 5
specified = .true.
/

&grib2
/

&namelist_quilt
nio_groups = 1,
/
EOF

        rm -rf namelist.input
        cp namelist.input_inside_ruc_for_bdy_$VAR_DATE namelist.input
        mv namelist.input_inside_ruc_for_bdy_$VAR_DATE $LOGDIR

        for file in /Users/haseeb.rehman/WRF/WRFV4.5/run/*; do
            filename=$(basename "$file")
            [ "$filename" != "namelist.input" ] && ln -sf "$file" .
        done

        ln -sf ${MET_EM_FILES}/* .

        ulimit -s 8176
        ulimit -c unlimited

        mpiexec -n 1 real.exe

        while [ 1 = 1 ]
        do
            sleep 30
            grep -i "success" rsl.out.0000 && break 1
            grep -i "fatal"  rsl.out.0000 && break 1
        done
        sleep 1

        if grep -i "success" rsl.out.0000
        then
            draw_border "Step 1 completed successfully" "${GREEN}"
            cp rsl.out.0000 $LOGDIR/ruc_real_run_rsl.out_${VAR_DATE}
            rm -rf rsl.*.????
        else
            draw_border "Step 1 failed" "${RED}"
            echo "RUC Real Run failed" > mail_message
            /usr/bin/mail -s "RUC Real Run failed" $EMAIL < mail_message
            exit 1
        fi

        # Step 2: Running wrf.exe to produce first guess file
        echo -e "${BLUE}Step 2: Running wrf.exe to produce first guess${NC}"
        if [ "$SKIP_WRF_RUN" != "true" ]; then
            mpirun -np 8 ./wrf.exe
            while [ 1 = 1 ]
            do
                sleep 30
                grep -i "success" rsl.out.0000 && break 1
                grep -i "fatal"  rsl.out.0000 && break 1
            done
            sleep 1
            if grep -i "success" rsl.out.0000
            then
                draw_border "Step 2 completed successfully" "${GREEN}"
            else
                draw_border "Step 2 failed" "${RED}"
                echo "WRF Run failed" > mail_message
                /usr/bin/mail -s "WRF Run failed" $EMAIL < mail_message
                exit 1
            fi
        else
            echo -e "${BLUE}Skipping wrf.exe run for testing${NC}"
            draw_border "Step 2 skipped" "${GREEN}"
        fi

        # Step 3: Running real.exe to produce wrfinput and wrfbdy for assimilation
        echo -e "${BLUE}Step 3: Running real.exe to produce wrfinput and wrfbdy${NC}"
        NMLINK="$WORKDIR/namelist.input"
        if [ ! -f "$NMLINK" ]; then
            draw_border "Error: namelist.input not found" "${RED}"
            exit 1
        fi
        sed -i '' "/^[[:space:]]*start_year[[:space:]]*=/ s/.*/ start_year = ${CYCLE_YEAR2}, ${CYCLE_YEAR2}, ${CYCLE_YEAR2},/" "$NMLINK"
        sed -i '' "/^[[:space:]]*start_month[[:space:]]*=/ s/.*/ start_month = ${CYCLE_MONTH2}, ${CYCLE_MONTH2}, ${CYCLE_MONTH2},/" "$NMLINK"
        sed -i '' "/^[[:space:]]*start_day[[:space:]]*=/ s/.*/ start_day = ${CYCLE_DAY2}, ${CYCLE_DAY2}, ${CYCLE_DAY2},/" "$NMLINK"
        sed -i '' "/^[[:space:]]*start_hour[[:space:]]*=/ s/.*/ start_hour = ${CYCLE_HOUR2}, ${CYCLE_HOUR2}, ${CYCLE_HOUR2},/" "$NMLINK"
        sed -i '' "/^[[:space:]]*end_year[[:space:]]*=/ s/.*/ end_year = ${CYCLE_YEAR3}, ${CYCLE_YEAR3}, ${CYCLE_YEAR3},/" "$NMLINK"
        sed -i '' "/^[[:space:]]*end_month[[:space:]]*=/ s/.*/ end_month = ${CYCLE_MONTH3}, ${CYCLE_MONTH3}, ${CYCLE_MONTH3},/" "$NMLINK"
        sed -i '' "/^[[:space:]]*end_day[[:space:]]*=/ s/.*/ end_day = ${CYCLE_DAY3}, ${CYCLE_DAY3}, ${CYCLE_DAY3},/" "$NMLINK"
        sed -i '' "/^[[:space:]]*end_hour[[:space:]]*=/ s/.*/ end_hour = ${CYCLE_HOUR3}, ${CYCLE_HOUR3}, ${CYCLE_HOUR3},/" "$NMLINK"
        sed -i '' "/^[[:space:]]*max_dom[[:space:]]*=/ s/.*/ max_dom = $MAX_DOM_FF/" "$NMLINK"

        mpiexec -n 1 real.exe

        while [ 1 = 1 ]
        do
            sleep 30
            grep -i "success" rsl.out.0000 && break 1
            grep -i "fatal"  rsl.out.0000 && break 1
        done
        sleep 1

        if grep -i "success" rsl.out.0000
        then
            draw_border "Step 3 completed successfully" "${GREEN}"
            cp rsl.out.0000 $LOGDIR/ruc_real_run_rsl.out_${VAR_DATE}
            rm -rf rsl.*.????
            cp wrfinput_d01 $VAR_DATE
            cp wrfbdy_d01 $VAR_DATE
        else
            draw_border "Step 3 failed" "${RED}"
            echo "RUC Real Run failed for wrfbdy_d01" > mail_message
            /usr/bin/mail -s "RUC Real Run failed" $EMAIL < mail_message
            exit 1
        fi
cp wrfinput_d01 $VAR_DATE
cp wrfbdy_d01 $VAR_DATE
        cd $VAR_DATE

        
        cat > namelist.input_3dvar_${VAR_DATE} << EOF
&wrfvar1
WRITE_INCREMENTS=false
PRINT_DETAIL_OBS=false
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
len_scaling1=1.
len_scaling2=1.
len_scaling3=1.
len_scaling4=1.
len_scaling5=1.
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
        cp namelist.input_3dvar_${VAR_DATE} /Users/haseeb.rehman/WRF/WRFDA/WORK_DIR/namelist.input
        mv namelist.input_3dvar_${VAR_DATE} ${LOGDIR}

        WRFOUT_FILENAME="wrfout_d01_${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}_00_00"
        if [ -f "$WORKDIR/$WRFOUT_FILENAME" ]; then
            rm -rf ./fg
            cp "$WORKDIR/$WRFOUT_FILENAME" ./fg || { draw_border "Failed to copy $WRFOUT_FILENAME to ./fg" "${RED}"; exit 1; }
            cp "$WORKDIR/$WRFOUT_FILENAME" "$ANALYSISDIR/Before_DA/" || { draw_border "Failed to copy $WRFOUT_FILENAME to $ANALYSISDIR/Before_DA/" "${RED}"; exit 1; }
        else
            draw_border "Error: $WRFOUT_FILENAME not found in $WORKDIR" "${RED}"
            exit 1
        fi
        # Step 4: Updating lower boundary condition
        echo -e "${BLUE}Step 4: Updating lower boundary condition${NC}"
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

        ln -sf /Users/haseeb.rehman/WRF/WRFDA/WORK_DIR/* .

        ulimit -s 8176

        ./da_update_bc.exe > update_low_bdy_${VAR_DATE}.txt

        if grep -i successfully update_low_bdy_${VAR_DATE}.txt
        then
            draw_border "Step 4 completed successfully" "${GREEN}"
        else
            draw_border "Step 4 failed" "${RED}"
            exit 1
        fi

        # Step 5: Running da_wrfvar.exe
        echo -e "${BLUE}Step 5: Running da_wrfvar.exe${NC}"
        cp $OBASCIIDIR/concatenated_${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}:00:00.ascii ./ob.ascii

        mpiexec -n 1 da_wrfvar.exe

        while [ 1 = 1 ]
        do
            sleep 30
            grep -i "success" rsl.out.0000 && break 1
            grep -i "fatal"  rsl.out.0000 && break 1
        done
        sleep 1

        if grep -i "success" rsl.out.0000
        then
            draw_border "Step 5 completed successfully" "${GREEN}"
            cp rsl.out.0000 $LOGDIR/wrfda_rsl.out.$VAR_DATE
            cp wrfvar_output $ANALYSISDIR/wrfvar_output_$VAR_DATE
            mv $ANALYSISDIR/wrfvar_output_$VAR_DATE $ANALYSISDIR/Before_DA/wrfvar_output_$VAR_DATE
        else
            draw_border "Step 5 failed" "${RED}"
            echo "WRF 3DVAR DA $VAR_DATE run failed" > mail_message
            /usr/bin/mail -s "WRF 3DVAR DA $VAR_DATE run failed" $EMAIL < mail_message
            exit 1
        fi

        # Step 6: Updating lateral boundary condition
        echo -e "${BLUE}Step 6: Updating lateral boundary condition${NC}"
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

        rm -rf parame.in
        cp parame.in_latbc_$VAR_DATE parame.in
        mv parame.in_latbc_$VAR_DATE $LOGDIR

        ulimit -s 8176

        ./da_update_bc.exe > update_lat_bdy_${VAR_DATE}.txt

        if grep -i success update_lat_bdy_${VAR_DATE}.txt
        then
            draw_border "Step 6 completed successfully" "${GREEN}"
        else
            draw_border "Step 6 failed" "${RED}"
            exit 1
        fi

        # Step 7: Producing final forecast running wrf.exe
        echo -e "${BLUE}Step 7: Producing final forecast running wrf.exe${NC}"
        cd $WORKDIR
        rm -rf rsl.*.????
        rm -rf wrfinput_d01
        rm -rf wrfbdy_d01
        ln -sf $VAR_DATE/wrfvar_output ./wrfinput_d01
        ln -sf $VAR_DATE/wrfbdy_d01 ./wrfbdy_d01

        mpirun -np 8 ./wrf.exe

        while [ 1 = 1 ]
        do
            sleep 30
            grep -i "success" rsl.out.0000 && break 1
            grep -i "fatal"  rsl.out.0000 && break 1
        done
        sleep 1

        if grep -i "success" rsl.out.0000
        then
            draw_border "Step 7 completed successfully" "${GREEN}"
        else
            draw_border "Step 7 failed" "${RED}"
            echo "WRF RUC $VAR_DATE run failed" > mail_message
            /usr/bin/mail -s "WRF RUC $VAR_DATE run failed" $EMAIL < mail_message
            exit 1
        fi
        
    
        #copying the final forecast to After_DA Folder
        for ((dom=1; dom<=MAX_DOM_FF; dom++)); do
            WRFOUT_FILENAME_DA="wrfout_d$(printf "%02d" $dom)_${CYCLE_YEAR3}-${CYCLE_MONTH3}-${CYCLE_DAY3}_${CYCLE_HOUR3}_00_00"
            if [ -f "$WORKDIR/$WRFOUT_FILENAME_DA" ]; then
                cp "$WORKDIR/$WRFOUT_FILENAME_DA" "$DAFILES"
                echo -e "${BLUE}Copied $WRFOUT_FILENAME_DA to $DAFILES${NC}"
            else
                echo -e "${RED}Warning: $WRFOUT_FILENAME_DA not found${NC}"
            fi
        done
        cp rsl.out.0000 $LOGDIR/ruc_wrf_run_rsl.out_${CYCLE_YEAR3}-${CYCLE_MONTH3}-${CYCLE_DAY3}_${CYCLE_HOUR3}
        
        # Cycle footer
        draw_border "Cycle ${CYCLE_NUM} successfully produced wrfout at ${CYCLE_YEAR3}-${CYCLE_MONTH3}-${CYCLE_DAY3} ${CYCLE_HOUR3}:00:00" "${GREEN}"

        I=`expr $I + 1`
    done
fi
