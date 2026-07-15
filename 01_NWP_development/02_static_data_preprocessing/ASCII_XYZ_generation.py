# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import os
import subprocess
import tempfile
import json

# Get the absolute path of the folder containing .laz files
folder_path = os.path.expanduser("/Users/haseeb.rehman/Documents/gis4wrf/datasets/geog/Lux_LiDAR2019/extracted")

# Define the output ASCII XYZ file path and name in the same directory
output_xyz_file = os.path.join(folder_path, "lidar.xyz")

# ...

# PDAL pipeline for filtering and exporting to ASCII XYZ
pipeline = [
    {
        "type": "readers.las",
        "filename": folder_path,
        "tag": "input"
    },
    {
        "type": "filters.assign",
        "assignment": "Classification[:]=0"
    },
    {
        "type": "filters.range",
        "limits": "Classification[2:2]"
    },
    {
        "type": "writers.text",
        "filename": output_xyz_file,
        "order": "X,Y,Z"
    }
]

# ...


# Write the pipeline as a JSON string to a temporary file
pipeline_file = tempfile.NamedTemporaryFile(mode='w', delete=False)
pipeline_file.write(json.dumps(pipeline))
pipeline_file.close()


# Run PDAL pipeline
try:
    pdal_output = subprocess.check_output(['pdal', 'pipeline', pipeline_file.name], encoding='utf-8')
    print("ASCII XYZ file generated successfully: %s" % output_xyz_file)
except subprocess.CalledProcessError as e:
    print("Error generating ASCII XYZ file:", e)

# Remove the temporary pipeline file
os.remove(pipeline_file.name)
