#!/bin/bash

set -x
set -e

# Uses GDAL to generate brrowse imagery for tiff images in the workdir under vv,vh,hv, or hh subdirectories
projections=("3995", "3031") # first is arctic, second is antarctic
use_projection="${projections[1]}" # which projection to use, will set this to be an input (to project based on loc properly)
allowed_polarizations=("hh" "hv" "vv" "vh")
num_procs=32 # number of parallel processes to run concurrently
kml_path=$1

function get_size () {
    file_path="${1}"
    awk 'Size is{print}' | gdalinfo ${file_path}
}

gdal_time() {
    if [[ -z "$1" ]]; then
        echo "Missing arguments. Syntax:"
        echo "  gdal_pixelsize_gdalwarp_tr <input_raster>"
        return
    fi;
    DATETIME=$(gdalinfo "$1" |\
        grep "TIFFTAG_DATETIME=" |\
	sed "s/TIFFTAG_DATETIME=//g" |\
	    tr -cd '0-9' );
	#tr -c " " "T" |\
        #tr -d "[(,])-");
    echo -n "$DATETIME"
}

for folder in ${allowed_polarizations[*]}; do
    if [[ -d "${folder}" ]] ; then
        # if there are multiple browse files, we will generate an animated file
	browse_count=$(find $folder -maxdepth 1 -name "*.merged.tiff" -printf '%p\n' | sort -u | wc -l)
	if [ "${browse_count}" -gt "1" ] ; then

	    echo "generating animation using ${browse_count} frames..."
            # generate merged shapefile
	    shapefile_path=${folder}/boundary.shp
            if [ ! -f "${shapefile_path}" ]; then
                #gdaltindex -src_srs_format EPSG -src_srs_name src_srs -t_srs EPSG:${use_projection} ${folder}/extent.shp ${folder}/*.merged.tiff
                ogrmerge.py -src_layer_field_name location -t_srs EPSG:3031 -o ${shapefile_path} ${kml_path} -single
            fi

            # cut all images to the shapefile
            iterator=1
	    matching_files=$(find $folder -name "*.merged.tiff" -printf '%p\n' | sort -u)
	    for file in $matching_files
            do
		filename="$(basename "${file}")"                              # full filename without the path
	        filebase="$(echo ${filename} | sed 's/.'"merged.tiff"'//g')"  # filename without extension
		counter=$(printf %03d $iterator)
		warp="${folder}/${filebase}.${counter}.cropped.vrt"
		mpg="${folder}/${counter}.mpg.png"

                # crop to the shapefile extent

		#gdalwarp -overwrite -cutline ${shapefile_path} -crop_to_cutline -srcalpha -dstalpha "${file}" "${warp}"
		gdalwarp -overwrite -cutline ${shapefile_path} -crop_to_cutline -srcalpha -dstalpha "${file}" "${warp}"
		# export as png

                #gdal_translate -outsize 4096 0 -of PNG -r nearest "${warp}" "${mpg}" # THIS IS EXTREMELY SLOW. NEED TO MAKE FASTER
                gdal_translate -of PNG -r nearest -outsize 7424 6521 "${warp}" "${mpg}" # THIS IS EXTREMELY SLOW. NEED TO MAKE FASTER

                # now we generate an overlay of prior images, to avoid flickering black pixels
		if [ ${iterator} -eq 1 ]; then
                    cp "${mpg}" "${folder}/base.png" # just copy the image
	        else
		    # composite background_image overlay_image result_image
		    convert -composite "${folder}/base.png" "${mpg}" "${folder}/${counter}.finished.png"
		    rm "${folder}/base.png"
		    cp "${folder}/${counter}.finished.png" "${folder}/base.png"
		fi
		iterator=$((iterator+1))
            done
            ffmpeg -r 15 -i "${folder}/%03d.finished.png" "${folder}/animation.avi"
            #rm "${folder}"/*.vrt
	    #rm "${folder}"/*.xml
	    #rm "${folder}"/*."${small_ext}"
	    #rm "${folder}"/*.mpg.png
	fi
    fi
done

