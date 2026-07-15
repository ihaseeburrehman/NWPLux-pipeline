# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import os

# List of stations to remove
stations_to_remove = [
    "BAT1", "CT58", "D402", "D596", "D624", "D931", "DBMH", "FFMJ", "KLEV", "LAIG",
    "MABO", "NIKL", "REDU", "SMSP", "TRI2", "VIT2"
]

# Folder containing the concatenate files
input_folder = "/Users/haseeb.rehman/Downloads/concatenate_June_July_2021_event"

# Function to remove specified station entries from a file
def remove_station_entries(file_path, stations_to_remove):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except UnicodeDecodeError:
        # Try a different encoding if UTF-8 fails
        with open(file_path, "r", encoding="latin1") as file:
            lines = file.readlines()

    # List to store the updated file content
    updated_lines = []
    skip_next_line = False

    for line in lines:
        # Skip the next line if it belongs to a station to remove
        if skip_next_line:
            skip_next_line = False
            continue

        # Check if the current line contains a station to remove
        if any(station in line for station in stations_to_remove):
            skip_next_line = True  # Skip the next line as well
            continue

        # Add the current line to the updated content
        updated_lines.append(line)

    # Overwrite the file with the updated content
    with open(file_path, "w", encoding="utf-8") as file:
        file.writelines(updated_lines)

# Iterate through all files in the folder
for file_name in os.listdir(input_folder):
    file_path = os.path.join(input_folder, file_name)
    
    # Skip non-text files like .DS_Store
    if not file_name.endswith(".ascii") and not file_name.endswith(".dat"):
        print(f"Skipping non-text file: {file_name}")
        continue
    
    # Check if it's a file (not a directory) and process it
    if os.path.isfile(file_path):
        print(f"Processing file: {file_name}")
        remove_station_entries(file_path, stations_to_remove)

print("Processing complete. All specified station entries have been removed.")
