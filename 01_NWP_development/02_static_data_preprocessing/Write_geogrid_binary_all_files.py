import numpy as np
import laspy
import os

def write_geogrid(rarray, nx, ny, nz, isigned, endian, scalefactor, wordsize, output_dir, file_index):
    # Determine the number of points and the total size of the array
    narray = nx * ny * nz
    total_points = rarray.shape[0]

    # Calculate the number of chunks
    num_chunks = int(np.ceil(total_points / narray))

    for i in range(num_chunks):
        start_index = int(i * narray)
        end_index = int(min((i + 1) * narray, total_points))
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

        # Construct the output file path with a unique name
        output_filename = f"{file_index:05d}-{i+1:05d}.{file_index:05d}-{i+1:05d}"
        output_path = os.path.join(output_dir, output_filename)

        # Write chunk to file
        with open(output_path, "wb") as bfile:
            bfile.write(barray.tobytes())

def main():
    las_folder = "/Users/haseeb.rehman/Documents/gis4wrf/datasets/geog/Lux_LiDAR2019/extracted/Las_files/"
    output_folder = "/Users/haseeb.rehman/Documents/gis4wrf/datasets/geog/Lux_LiDAR2019/extracted/Binary_files/"
    isigned = 0
    endian = 0  # 0 for big endian, 1 for little endian
    scalefactor = 1.0
    wordsize = 4

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Get the list of LAS files in the folder
    las_files = [file for file in os.listdir(las_folder) if file.endswith(".las")]

    # Variable to track the file index
    file_index = 1

    for las_file in las_files:
        # Construct the full path to the LAS file
        filename = os.path.join(las_folder, las_file)

        # Read LAS file and extract coordinates in chunks
        chunk_size = 1000000  # Adjust this value based on available memory
        in_file = laspy.read(filename)

        total_points = in_file.header.point_count
        nx = in_file.header.max[0] - in_file.header.min[0] + 1
        ny = in_file.header.max[1] - in_file.header.min[1] + 1
        nz = in_file.header.max[2] - in_file.header.min[2] + 1
        num_chunks = int(np.ceil(total_points / chunk_size))

        for i in range(num_chunks):
            start_index = int(i * chunk_size)
            end_index = int(min((i + 1) * chunk_size, total_points))
            points = in_file.points[start_index:end_index]

            X = points['X']
            Y = points['Y']
            Z = points['Z']

            rarray = np.column_stack((X, Y, Z)).flatten()

            # Call the write_geogrid function for each chunk
            write_geogrid(rarray, nx, ny, nz, isigned, endian, scalefactor, wordsize, output_folder, file_index)

        # Increment the file index for the next LAS file
        file_index += 1

        # Close the LAS file
        #in_file.close()


if __name__ == "__main__":
    main()
