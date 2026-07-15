#!/bin/bash

# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773


# Define the base output directory
BASE_DIR=/Users/haseeb.rehman/Documents/gis4wrf/datasets/met/GFS/2016

# Define start and end dates in YYYYMMDD format
start_date=20160713
end_date=20160810

# Initialize current date to start date
current_date=$start_date

# Number of retries for failed downloads
max_retries=3

# Delay between retries in seconds
retry_delay=5

# Delay between downloads in seconds
download_delay=1

# Loop through each date from start to end inclusive
while [ $current_date -le $end_date ]; do
    # Create output directory for the current date
    output_dir=$BASE_DIR/$current_date
    mkdir -p $output_dir

    # Loop through each hour: 00, 06, 12, 18
    for hour in 00 06 12 18; do
        # Construct the URL
        url=https://noaa-gfs-bdp-pds.s3.amazonaws.com/gdas.$current_date/$hour/gdas1.t${hour}z.pgrb2.0p25.f000
        
        # Define the output file path
        output_file=$output_dir/gdas1.t${hour}z.pgrb2.0p25.f000
        
        # Provide feedback
        echo "Downloading $url to $output_file"
        
        # Attempt to download with retries
        attempt=1
        while [ $attempt -le $max_retries ]; do
            curl -o $output_file $url
            if [ $? -eq 0 ]; then
                echo "Download successful"
                break
            else
                echo "Attempt $attempt failed. Retrying in $retry_delay seconds..."
                sleep $retry_delay
                attempt=$((attempt + 1))
            fi
        done
        
        if [ $attempt -gt $max_retries ]; then
            echo "Failed to download $url after $max_retries attempts."
        fi
        
        # Delay before the next download
        sleep $download_delay
    done

    # Increment the current date by one day
    current_date=$(date -j -f "%Y%m%d" -v+1d $current_date +%Y%m%d)
done