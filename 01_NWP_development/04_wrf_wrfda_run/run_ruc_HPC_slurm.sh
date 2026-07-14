#!/bin/bash
#set -x #(for debugging)

# Check if SLURM_JOB_NODELIST is populated
echo "SLURM_JOB_NODELIST: $SLURM_JOB_NODELIST"

# Generate hostfile from SLURM_JOB_NODELIST, assuming each node has the same number of slots (28)
scontrol show hostname $SLURM_JOB_NODELIST | awk '{print $0 " slots=28"}' > /home/users/hrehman/my_hostfile

# Display the generated hostfile to ensure it is correct
echo "Generated hostfile:"
cat /home/users/hrehman/my_hostfile

# Path to the hostfile
hostfile="/home/users/hrehman/my_hostfile"

# Calculate the total number of slots using new field separator
total_slots=$(awk -F 'slots=' '{sum += $2} END {print sum}' $hostfile)

# Print total number of slots
echo "Total slots available: $total_slots"


############################################################
############################################################
#  Forecast Script
#  Author: Haseeb ur Rehman
############################################################
############################################################

HOMEDIR=/home/users/hrehman/WRF #(consist of every wrf elements)

#Parent Work Directory
WORKDIR=$HOMEDIR/WRFV4.5.2/WORKDIR #(wrf out will be produced)
#WRF Directory
WRFDIR=$HOMEDIR/WRFV4.4.2 #(where the WRFv4.5 is located)
WRFDADIR=$HOMEDIR/WRFDA #(WRFDA directory)
ANALYSISDIR=$WORKDIR/analysis_dir #(output from WRFDA ....wrfvar)
DAFILES=$ANALYSISDIR/After_DA #(output from WRFDA ....wrfvar)
#Directory where the met_em files are stored
MET_EM_FILES=$HOMEDIR/WPS-4.5/met_em_files_GFS_000_2021_event  #met_em_files generted by WPS
OBASCIIDIR=$HOMEDIR/WRFDA/DAT_DIR/concatenate_June_July_2021 #(concatenated files directory, which is combination of Synop and GNSS ZTD )
B_MATRIX_DIR=$HOMEDIR/WRFDA/var/run/ #(where is be.DAT)
#Log Directory to be created while start of the code
LOGDIR=${WORKDIR}/log_dir #(where the rsl_out saved)

EMAIL="haseeb.rehman@uni.lu"

RUN_RUC='true'
SKIP_WRF_RUN='false'  # Set to false or remove/comment out this line for an actual run

#Create directories before start
test -d $WORKDIR || mkdir -p $WORKDIR
test -d $LOGDIR || mkdir -p $LOGDIR
test -d $ANALYSISDIR || mkdir -p $ANALYSISDIR
test -d $DAFILES || mkdir -p $DAFILES
############################################################
################### Text Colors########
############################################################
# Define color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

############################################################
################### Time control of the simulations ########
############################################################
START_YEAR=2021
START_MONTH=07
START_DAY=14
START_HOUR=06

CYCLE_LENGTH=6          # Cycling hours interval
CYCLE_LENGTH_BEGIN=00     # Begin of cycling after analysis time
CYCLE_LENGTH_INTERVAL=6  # Same as CYCLE_LENGTH
MULTIPLE=4            # Define number of cycles for a RUC , e.g. if you run for 7 days then at 6 hr interval it should be 7 x 4 (because 4 time in one day)


###########################################################
##########DO NOT CHANGE ANYTHING###########################
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


DFI_OPT_BEFORE=3

############################################################
################### Input data interval settings in seconds
############################################################

INTERVAL_SECONDS=21600

############################################################
################### Domain settings for the simulations ####
############################################################
MAX_DOM=1
PARENT_ID='1,1,2,3,'           # ID of parent domain
PARENT_GRID_RATIO='1,3,3,5'    # grid ratio between domains
I_PARENT_START='1,30,30,380' # X-coordinate of the lower left corner of each domain
J_PARENT_START='1,30,30,310'  # Y-coordinate of the lower left corner of each domain
S_WE='1, 1, 1, 1'              # Set to '1' for each domain
E_WE='120,109,100,1016'        # Number of east-west grid points in each domain
S_SN='1, 1, 1, 1'              # Set to '1' for each domain
E_SN='120,109,100,1016'        # Number of south-north grid points in each domain

DX=12000.0                  # Grid resolution (m) of the outermost domain (ONLY) (lon) (nests calculated)
DY=12000.0                  # Grid resolution (m) of the outermost domain (ONLY) (lat)

############################################################
################### Analysis interval settings in hours ####
############################################################

ANALYSIS_INTERVAL=6

############################################################
# Time Control Options for namelist.input (which wasn't defined above)
############################################################

RUN_DAYS=00                                        # Forecast length (days)
RUN_HOURS=00                                       # Forecast length (hours)
INPUT_FROM_FILE='.true., .true., .true., .true.,' # .true. to use high resolution topography
HISTORY_INTERVAL_BEFORE='720, 720, 720, 60'          # Interval of model output (minutes)
HISTORY_INTERVAL_AFTER='360,360,360,60'               # Interval of model output (minutes) afetr assimilation
FRAMES_PER_OUTFILE_BEFORE='1,1000,24,1000'        # Output file is splitted after <num> output times (0=one file only)
FRAMES_PER_OUTFILE_AFTER='1,1000,24,1000'         # Output file is splitted after <num> output times (0=one file only)
RESTART=.false.                                   # write restart file
RESTART_INTERVAL=7200                              # interval of restart files (minutes)
IO_FORM_HISTORY=2
IO_FORM_RESTART=2                                # Data format (2 = NetCDF) , 11= parallel NetCDF
IO_FORM_INPUT=2                                  #
IO_FORM_BOUNDARY=2
DEBUG_LEVEL=0                                     # Amount of Debug output
INPUT_OUTPUT_INTERVAL=$(expr ${CYCLE_LENGTH_INTERVAL} \* 60) # files written in INPUT_OUTPUT_INTERVAL minutes for assimilation

CYCLING='false'

############################################################
# Domain settings for the simulations (which wasn't defined above)
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
PARENT_TIME_STEP_RATIO='1, 3, 3, 3'   # time step ration of the domains
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
CU_PHYSICS='3, 3, 1, 1'           # Convection scheme: 1 = KF-Eta
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
###########################################################
#######Change to working directory##########################
############################################################

cd ${WORKDIR}

I=00
while [ ${I} -lt ${MULTIPLE} ]
do

# some counters
J=`expr $I + 1`
K=`expr $J + 1`

############################################################
#calculation of datestring for RUC ## DO NOT CHANGE ########
############################################################

CYCLE_LENGTH=`expr $CYCLE_LENGTH_BEGIN + $CYCLE_LENGTH_INTERVAL \* $(expr $J - 1) `

CYCLE_LENGTH2=`expr $CYCLE_LENGTH_BEGIN + $CYCLE_LENGTH_INTERVAL \* $(expr $K - 1)`
# Assuming K is the interval index for CYCLE_LENGTH2, calculate CYCLE_LENGTH3 for the next interval
CYCLE_LENGTH3=`expr $CYCLE_LENGTH_BEGIN + $CYCLE_LENGTH_INTERVAL \* $K`

if [ ${CYCLE_LENGTH3} -lt 10 ];
then
CYCLE_LENGTH3=0${CYCLE_LENGTH3}
fi

if [ ${CYCLE_LENGTH2} -lt 10 ]
then
CYCLE_LENGTH2=0${CYCLE_LENGTH2}
fi

if [ ${CYCLE_LENGTH} -lt 10 ]
then
CYCLE_LENGTH=0${CYCLE_LENGTH}
fi



# calculate the date string for cycling
CYCLE_YEAR=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH} | sed -e 's/^\(....\).*$/\1/'`
CYCLE_MONTH=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH} | sed -e 's/^....\(..\).*$/\1/'`
CYCLE_DAY=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH} | sed -e 's/^.*\(..\)..$/\1/'`
CYCLE_HOUR=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH} | sed -e 's/^.*\(..\)$/\1/'`

# After calculating the first cycle
echo "First Cycle: YEAR=${CYCLE_YEAR}, MONTH=${CYCLE_MONTH}, DAY=${CYCLE_DAY}, HOUR=${CYCLE_HOUR}"

CYCLE_YEAR2=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH2} | sed -e 's/^\(....\).*$/\1/'`
CYCLE_MONTH2=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH2} | sed -e 's/^....\(..\).*$/\1/'`
CYCLE_DAY2=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH2} | sed -e 's/^.*\(..\)..$/\1/'`
CYCLE_HOUR2=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH2} | sed -e 's/^.*\(..\)$/\1/'`

# After calculating the second cycle (make sure these calculations are done before this echo)
echo "Second Cycle: YEAR=${CYCLE_YEAR2}, MONTH=${CYCLE_MONTH2}, DAY=${CYCLE_DAY2}, HOUR=${CYCLE_HOUR2}"

# Calculate the date string for the third cycle using CYCLE_LENGTH3
CYCLE_YEAR3=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH3} | sed -e 's/^\(....\).*$/\1/'`
CYCLE_MONTH3=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH3} | sed -e 's/^....\(..\).*$/\1/'`
CYCLE_DAY3=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH3} | sed -e 's/^.*\(..\)..$/\1/'`
CYCLE_HOUR3=`$HOMEDIR/date_creator.sh -s${INITIAL_DATE}${INITIAL_HOUR} -i${CYCLE_LENGTH3} | sed -e 's/^.*\(..\)$/\1/'`

# After calculating the third cycle
echo "Third Cycle: YEAR=${CYCLE_YEAR3}, MONTH=${CYCLE_MONTH3}, DAY=${CYCLE_DAY3}, HOUR=${CYCLE_HOUR3}"


if [ ${CYCLE_HOUR} = 00 ]
then
START_OBS_DAY=$(expr ${CYCLE_DAY} - 1)
START_OBS_HOUR=23
else
START_OBS_HOUR=$(expr ${CYCLE_HOUR} - 1)
START_OBS_DAY=${CYCLE_DAY}
fi


if [ ${START_OBS_HOUR} -lt 10 ]
then
START_OBS_HOUR=0${START_OBS_HOUR}
fi

VAR_DATE=${CYCLE_YEAR2}${CYCLE_MONTH2}${CYCLE_DAY2}${CYCLE_HOUR2}
echo $VAR_DATE
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


############################################################
#need a new wrfbdy file for real and forecast afterwards
############################################################
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

ln -sf /home/users/hrehman/WRF/WRFV4.5.2/run/* .


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
echo -e "${GREEN}RUC Real Run successfully completed${NC}"
sleep 1
echo "Preparing for RUC DA Run"
cp rsl.out.0000 $LOGDIR/ruc_real_run_rsl.out_${VAR_DATE}
rm -rf rsl.*.????
else
echo "RUC Real Run failed" > mail_message
/usr/bin/mail -s "RUC Real Run failed" $EMAIL < mail_message
exit 1
fi

# WRF Run:
if [ "$SKIP_WRF_RUN" != "true" ]; then
    echo "Starting WRF run..."
    # Running WRF
   mpirun -n $total_slots --hostfile $hostfile wrf.exe

    # Check for success or failure
    while [ 1 = 1 ]
    do
        sleep 30
        grep -i "success" rsl.out.0000 && break 1
        grep -i "fatal"  rsl.out.0000 && break 1
    done
    sleep 1

    if grep -i "success" rsl.out.0000
    then
        echo -e "${GREEN}WRF Run successfully completed${NC}"
        # Additional actions if needed
    else
        echo -e "${RED}WRF Run failed${NC}" > mail_message
        /usr/bin/mail -s "WRF Run failed" $EMAIL < mail_message
        exit 1
    fi
else
    echo "Skipping WRF run for testing purposes."
    # Simulate a successful WRF run for the rest of the script, if necessary
    # For example, touch dummy output files expected by the rest of the script
fi

###Here you need to update the namelist for real.exe to produce wrfbdy based on new start and end time

update_namelist_alternative() {
    local pattern="$1"
    local replacement="$2"
    local symlink="$3"
    local target_file=$(readlink "$symlink" || echo "$symlink")
    local temp_file="temp_namelist.input"

    echo "Target file: $target_file"  # Debug: print resolved target file path

    if [ ! -f "$target_file" ]; then
        echo "Target file does not exist: $target_file"
        return 1
    fi

    echo "Performing update..."  # Debug: indicate update attempt

    # Use awk to perform the update, ensuring exact pattern matching
    awk -v pat="^${pattern}" -v rep="${replacement}" '{
        if ($0 ~ pat) print rep; else print $0;
    }' "$target_file" > "$temp_file" && mv "$temp_file" "$target_file"

    if [ $? -eq 0 ]; then
        echo "Update successful for pattern: $pattern"
    else
        echo "Update failed for pattern: $pattern"
        [ -f "$temp_file" ] && rm "$temp_file"  # Cleanup temp file on failure
    fi
}

# Path to the symlink of namelist.input
# Path to namelist.input
NMLINK="/home/users/hrehman/WRF/WRFV4.5.2/WORKDIR/namelist.input"
echo "Updating to: start_year = ${CYCLE_YEAR2}, start_month = ${CYCLE_MONTH2}, start_day = ${CYCLE_DAY2}, start_hour = ${CYCLE_HOUR2} for all domains"
echo "Updating to: end_year = ${CYCLE_YEAR3}, end_month = ${CYCLE_MONTH3}, end_day = ${CYCLE_DAY3}, end_hour = ${CYCLE_HOUR3} for all domains"

# Update process for three domains
sed -i "/^\s*start_year\s*=/ s/.*/ start_year = ${CYCLE_YEAR2}, ${CYCLE_YEAR2}, ${CYCLE_YEAR2},/" "$NMLINK"
sed -i "/^\s*start_month\s*=/ s/.*/ start_month = ${CYCLE_MONTH2}, ${CYCLE_MONTH2}, ${CYCLE_MONTH2},/" "$NMLINK"
sed -i "/^\s*start_day\s*=/ s/.*/ start_day = ${CYCLE_DAY2}, ${CYCLE_DAY2}, ${CYCLE_DAY2},/" "$NMLINK"
sed -i "/^\s*start_hour\s*=/ s/.*/ start_hour = ${CYCLE_HOUR2}, ${CYCLE_HOUR2}, ${CYCLE_HOUR2},/" "$NMLINK"

# Update end time parameters for all three domains
sed -i "/^\s*end_year\s*=/ s/.*/ end_year = ${CYCLE_YEAR3}, ${CYCLE_YEAR3}, ${CYCLE_YEAR3},/" "$NMLINK"
sed -i "/^\s*end_month\s*=/ s/.*/ end_month = ${CYCLE_MONTH3}, ${CYCLE_MONTH3}, ${CYCLE_MONTH3},/" "$NMLINK"
sed -i "/^\s*end_day\s*=/ s/.*/ end_day = ${CYCLE_DAY3}, ${CYCLE_DAY3}, ${CYCLE_DAY3},/" "$NMLINK"
sed -i "/^\s*end_hour\s*=/ s/.*/ end_hour = ${CYCLE_HOUR3}, ${CYCLE_HOUR3}, ${CYCLE_HOUR3},/" "$NMLINK"

echo "Running Real.exe based on new date and time to produce wrfbdy_d01 (which is needed for lateral boundry condition)"

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
echo -e "${GREEN}Real Run successfully completed for generation of wrfbdy_d01${NC}"
sleep 1
echo "Preparing for RUC DA Run"
cp rsl.out.0000 $LOGDIR/ruc_real_run_rsl.out_${VAR_DATE}
rm -rf rsl.*.????
else
echo -e "${RED}RUC Real Run failed for the generation of wrfbdy_d01${NC}" > mail_message
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
!CALC_STD=false
USE_SSMITBOBS=false
/
&wrfvar5
max_error_tb=3.0
max_error_uv=3.0
max_error_q=1.5 ! was 3
max_error_t=4.0
max_error_rv=2.5 ! was 3.
max_error_rf=3.0 ! was 4.
max_error_pw=5.0 ! please adjust
/
&wrfvar6
orthonorm_gradient=true
max_ext_its=2
/
&wrfvar7
CV_OPTIONS=5
var_scaling1=1.5
var_scaling2=1.5
var_scaling3=1.5
var_scaling4=2.0  ! Increase for RHs due to sparse humidity data
var_scaling5=1.5
len_scaling1=1.5
len_scaling2=1.5
len_scaling3=1.5
len_scaling4=2.0  ! Broaden moisture influence
len_scaling5=1.5
je_factor=1.5
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
!num_pseudo=1
!pseudo_x=260.
!pseudo_y=260.
!pseudo_z=10.
!pseudo_val=10.
!pseudo_err=1.
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
!pseudo_var="t"
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
!use_baseparam_fr_nml=.true.
! iso_temp = 0.,
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

# Construct the wrfout filename
WRFOUT_FILENAME="wrfout_d01_${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}_00_00"

# Echo the filename for confirmation
echo -e "${BLUE}Copying $WRFOUT_FILENAME to ./fg${NC}"

# Copy the WRF output file for the next 6th hour
rm $WORKDIR/fg
cp $WORKDIR/$WRFOUT_FILENAME ./fg

############################################################
# create parame.in for updating boundary conditions before 3DVAR
############################################################

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

if grep -i successfully update_low_bdy_${VAR_DATE}.txt
then
echo -e "${GREEN}Lower boundary conditions successfully completed${NC}"
else
echo -e "${RED}Lower boundary conditions failed${NC}"
exit 1
fi
# end of update low BC

cp $OBASCIIDIR/concatenated_${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}:00:00.ascii ./ob.ascii

# Echo the filename for confirmation
echo -e "${BLUE}Copying concatenated_${CYCLE_YEAR2}-${CYCLE_MONTH2}-${CYCLE_DAY2}_${CYCLE_HOUR2}:00:00.ascii to ./ob.ascii${NC}"

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
echo -e "${GREEN}WRF 3DVAR DA run successfully completed${NC}"
cp rsl.out.0000 $LOGDIR/wrfda_rsl.out.$VAR_DATE
cp wrfvar_output $ANALYSISDIR/wrfvar_output_$VAR_DATE
else
echo -e "${RED}WRF 3DVAR DA $VAR_DATE run failed${NC}"
echo "WRF 3DVAR DA $VAR_DATE run failed, please check the code immediately" > mail_message
/usr/bin/mail -s "WRF 3DVAR DA $VAR_DATE run failed, please check the code immediately" $EMAIL < mail_message
exit 1
fi

cp statistics $LOGDIR/statistics_$VAR_DATE
############################################################
# update boundary conditions after Hybrid
############################################################

### create parame.in for updating lateral boundary conditions

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
echo -e "${GREEN}Lateral boundary conditions updated successfully${NC}"
else
echo -e "${RED}Lateral boundary conditions update failed${NC}"
exit 1
fi
## fi update

cd  $WORKDIR

rm -rf rsl.*.????
rm -rf wrfinput_d01
rm -rf wrfbdy_d01
echo "removing wrfinput-d01, wrfbdy-d01 from directory and Linking newly generated these files for WRF RUN after DA"
ln -sf $VAR_DATE/wrfvar_output ./wrfinput_d01
ln -sf $VAR_DATE/wrfbdy_d01 ./wrfbdy_d01


# Commenting out the SKIP_WRF_RUN condition, always run the block
#echo "Checking if WRF run should be skipped..."
#if [ "$SKIP_WRF_RUN" != "true" ]; then
    echo "Starting WRF run..."
    # Running WRF
    mpirun -n $total_slots --hostfile $hostfile wrf.exe

    # Check for success or failure
    while [ 1 = 1 ]
    do
        sleep 30
        grep -i "success" rsl.out.0000 && break 1
        grep -i "fatal"  rsl.out.0000 && break 1
    done
    sleep 1

    if grep -i "success" rsl.out.0000
    then
        echo -e "${GREEN}WRF Run successfully completed${NC}"
        # Additional actions if needed
    else
        echo -e "${RED}WRF RUC $VAR_DATE run failed${NC}"
        echo "WRF RUC $VAR_DATE run failed, please check the code immediately" > mail_message
        /usr/bin/mail -s "WRF RUC $VAR_DATE run failed, please check the code immediately" $EMAIL < mail_message
        exit 1
    fi
#else
#    echo "Skipping WRF run for testing purposes."
    # Simulate a successful WRF run for the rest of the script, if necessary
    # For example, touch dummy output files expected by the rest of the script
#fi



cd $WORKDIR
#Copying the wrfout files after DA to analysis_dir
# Construct the wrfout filename
WRFOUT_FILENAME_DA="wrfout_d01_${CYCLE_YEAR3}-${CYCLE_MONTH3}-${CYCLE_DAY3}_${CYCLE_HOUR3}_00_00"

# Echo the filename for confirmation
echo -e "${BLUE}Copying $WRFOUT_FILENAME_DA to ./fg${NC}"

# Copy the WRF output file for the next 6th hour
rm $WORKDIR/fg
cp $WORKDIR/$WRFOUT_FILENAME_DA $DAFILES
###########################################################
###########################################################
I=`expr $I + 1`
done
#End RUC if condition
fi
