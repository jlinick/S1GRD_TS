#!/bin/bash

#set -x
# merges files by subdir under the input directory

DIR=$1
for subdir in $(find ${DIR} -maxdepth 1 -name '[0-9]*' -type d); do
    if [ -d "${subdir}" ]; then
        # merge all the corrected files
        subdir=$(basename ${subdir})
	echo "In subdirectory: ${subdir}"
        files=$(find "${DIR}/${subdir}" -name "S1*.corrected.tif" -printf '%p ' | sort -u)
        for file in ${files}
	do
	    echo "warping file: ${filename}"
	    filename="$(basename "${file}")"    # full filename without the path
	    filebase="$(echo ${filename} | sed 's/.corrected.tif//g')"  # filename without extension
	    warped_file="${filebase}.warped.tiff"
            
	    gdalwarp -of GTiff -s_srs EPSG:4326 -novshiftgrid -srcnodata 0 -t_srs EPSG:3031 -r near -dstalpha -multi -of GTiff ${file} ${DIR}/${subdir}/${warped_file}
	    gdal_translate -of GTiff -scale 0 0.85 0 255 -ot Byte ${DIR}/${subdir}/${warped_file} ${DIR}/${subdir}/${filebase}.translate.tiff
	    nearblack -of VRT -nb 1 -near 0 -setalpha ${DIR}/${subdir}/${filebase}.translate.tiff
        done
        gdal_merge.py -ot Byte -of GTiff -n 0 -o ${DIR}/${subdir}.merged.tiff ${DIR}/${subdir}/*.translate.tiff
        #set band 2 as alpha
        gdal_translate ${DIR}/${subdir}.merged.tiff ${DIR}/${subdir}.merged.masked.tiff -b 1 -mask 2 -co COMPRESS=LZW --config GDAL_TIFF_INTERNAL_MASK YES
        



        #rm -rf ${DIR}/${subdir}
        rm ${DIR}/${subdir}.merged.tiff
        #gdal_translate -of PNG ${DIR}/${subdir}.scaled.tiff ${DIR}/${subdir}.png
        #gdalwarp -of GTiff -t_srs EPSG:3031 ${DIR}/${subdir}.scaled.tiff ${DIR}/${subdir}.warped.tiff
    fi
done

