# NWPLux
# Haseeb ur Rehman
# Funded by the Fonds National de la Recherche Luxembourg (FNR),
# Industrial Fellowship, Project No. 17130773

import numpy as np
import laspy
import os

def write_geogrid(rarray, nx, ny, nz, isigned, endian, scalefactor, wordsize, output_dir):
    # Determine the number of points and the total size of the array
    narray = nx * ny * nz
    total_points = rarray.shape[0]

    # Calculate the number of chunks
    num_chunks = int(np.ceil(total_points / narray))

    for i in range(num_chunks):
        start_index = i * narray
        end_index = min((i + 1) * narray, total_points)
        chunk = rarray[start_index:end_index]

        # Convert and store values in barray based on wordsize
        iarray = np.asarray(chunk / scalefactor, dtype=np.uint32)
        barray = np.zeros(chunk.size * wordsize, dtype=np.uint8)

        if wordsize == 1:
            barray[::wordsize] = iarray & 0xff
        elif wordsize == 2:
            barray[1::2] = (iarray >> 8) & 0xff
            barray[0::2] = iarray & 0xff
        elif wordsize == 3:
            barray[2::3] = (iarray >> 16) & 0xff
            barray[1::3] = (iarray >> 8) & 0xff
            barray[0::3] = iarray & 0xff
        elif wordsize == 4:
            barray[3::4] = (iarray >> 24) & 0xff
            barray[2::4] = (iarray >> 16) & 0xff
            barray[1::4] = (iarray >> 8) & 0xff
            barray[0::4] = iarray & 0xff

        # Construct the output file path
        output_filename = f"{i+1:05d}-{nx:05d}.{i+1:05d}-{ny:05d}"
        output_path = os.path.join(output_dir, output_filename)

        # Write chunk to file
        with open(output_path, "wb") as bfile:
            bfile.write(barray.tobytes())

def main():
    filename = "/Users/haseeb.rehman/Documents/gis4wrf/datasets/geog/Lux_LiDAR2019/extracted/Las_files/LIDAR2019_NdP_85500_79000_EPSG2169.las"
    nx = 8188383
    ny = 8188383
    nz = 8188383
    isigned = 0
    endian = 0  # 0 for big endian, 1 for little endian
    scalefactor = 1.0
    wordsize = 4

    # Read LAS file and extract coordinates in chunks
    chunk_size = 1000000  # Adjust this value based on available memory
    in_file = laspy.read(filename)

    total_points = in_file.header.point_count
    num_chunks = int(np.ceil(total_points / chunk_size))


    for i in range(num_chunks):
        start_index = i * chunk_size
        end_index = min((i + 1) * chunk_size, total_points)
        points = in_file.points[start_index:end_index]

        X = points['X']
        Y = points['Y']
        Z = points['Z']

        rarray = np.column_stack((X, Y, Z)).flatten()
        # Extract the directory path from the input filename
        output_dir = os.path.dirname(filename)
        
        # Call the write_geogrid function for each chunk
        write_geogrid(rarray, nx, ny, nz, isigned, endian, scalefactor, wordsize, output_dir)


if __name__ == "__main__":
    main()
