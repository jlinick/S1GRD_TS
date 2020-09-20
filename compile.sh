#!/bin/bash

allowed_polarizations=("hh" "hv" "vv" "vh")
current_workdir=$(pwd)   # folder we are extracting tiffs onto
folder=$1                # the folder we are extracting zipfiles from
#unzip the folders and extract their contents
zip_files=$(find $folder -name "*.zip" -printf '%p\n' | sort -u)
for zip_file in ${zip_files}
do
    # unzip the folder
    echo "extracting ${zip_file}..."
    #unzip -d ${current_workdir} ${zip_file} > /dev/null 2>&1
    unzip -d ${current_workdir} ${zip_file} 2> /dev/null
    zip_filename=$(basename ${zip_file})
    zip_folder="${zip_filename/.zip/.SAFE}"
    # find all the tiff files in the extracted folder
    tiff_folders=$(find ${zip_folder} -name '*.tiff' -printf '%h\n' -path './S1[AB]*' | sort -u)

    # find all folders containing tiff files
    for folder in ${tiff_folders}
    do
        # for each folder split by polarization and place in proper directory
        for pol in "${allowed_polarizations[@]}"
        do
            matching_files=$(find . -name "*${pol}*.tiff" -printf '%p\n' | sort -u)
            for file in $matching_files
	    do
		if [ "$(basename $folder)" != "$pol" ]; then 
                    fil=$(basename "$file")
                    mkdir -m 755 -p $pol
		    cp -n $folder/$fil ./$pol/$fil 2> /dev/null
	        fi
            done
        done
    # finished extracting and copying the zip folder, remove the original file and folder
    rm -rf ${zip_folder}
    rm ${zip_file}
    done
done

