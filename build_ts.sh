#!/bin/bash

set -x
set -e

# Uses GDAL to generate brrowse imagery for tiff images in the workdir under vv,vh,hv, or hh subdirectories
projections=("3995", "3031") # first is arctic, second is antarctic
use_projection="${projections[1]}" # which projection to use, will set this to be an input (to project based on loc properly)
allowed_polarizations=("hh" "hv" "vv" "vh")
num_procs=32 # number of parallel processes to run concurrently

folder=$1
shapefile_path=$2
burn_shapefile="/S1GRD_TS/aux/coast.shp"

function get_size () {
    file_path="${1}"
    awk 'Size is{print}' | gdalinfo ${file_path}
}

if [[ -d "${folder}" ]] ; then
    # if there are multiple browse files, we will generate an animated file
    browse_count=$(find $folder -maxdepth 1 -name "*.merged.masked.tiff" -printf '%p\n' | sort -u | wc -l)
    echo "generating animation using ${browse_count} frames..."
    # generate merged shapefile
    #shapefile_path=${folder}/boundary.shp
    #if [ ! -f "${shapefile_path}" ]; then
    #    #gdaltindex -src_srs_format EPSG -src_srs_name src_srs -t_srs EPSG:${use_projection} ${folder}/extent.shp ${folder}/*.merged.tiff
    #    ogrmerge.py -src_layer_field_name location -t_srs EPSG:3031 -o ${shapefile_path} ${kml_path} -single
    #fi

    # cut all images to the shapefile
    iterator=1
    matching_files=$(find $folder -name "*.merged.masked.tiff" -printf '%p\n' | sort -u)
    for file in $matching_files
    do
        filename="$(basename "${file}")"                              # full filename without the path
        filebase="$(echo ${filename} | sed 's/.'"merged.masked.tiff"'//g')"  # filename without extension
        counter=$(printf %03d $iterator)
        warp="${folder}/${filebase}.${counter}.cropped.vrt"
	burned="${folder}/${counter}.burned.tiff"
        mpg="${folder}/${counter}.mpg.png"
        stacked="${folder}/${counter}.stacked.png"
        annotated="${folder}/${counter}.annotated.png"
	base="${folder}/base.png"
	rand=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 6 | head -n 1)
        timeseries="${folder}/timelapse_${rand}.265"
	date=$(echo "${filebase:0:4}-${filebase:4:2}-${filebase:6:2}")

        # crop to the shapefile extent
        gdalwarp -overwrite -cutline ${shapefile_path} -crop_to_cutline -srcalpha -dstalpha "${file}" "${warp}"
        
        #burn shapefile onto raster
        #gdal_rasterize -burn 255 -ts 4000 4000 "${burn_shapefile}" "${burned}"

	# export as png
        gdal_translate -of PNG -r nearest -outsize 4000 4000  "${warp}" "${mpg}"

        # now we generate an overlay of prior images, to avoid flickering black pixels
        if [ ${iterator} -eq 1 ]; then
            cp "${mpg}" "${base}" # copy the image to serve as our initial base
	fi
        # composite background_image overlay_image result_image
        convert -composite "${base}" "${mpg}" "${stacked}"
        rm "${base}"
        cp "${stacked}" "${base}"

	# annotate the date onto the image
        convert "${stacked}" -fill white -stroke '#000C' -strokewidth 2 -gravity Southwest -pointsize 200 -annotate +100+100 "${date}" "${annotated}"
        #convert "${stacked}" -fill white -stroke '#000C' -strokewidth 2 -gravity Southwest -pointsize 200 "${date}" "${annotated}"
        iterator=$((iterator+1))
    done
    #ffmpeg -r 15 -i "${folder}/%03d.finished.png" "${folder}/animation.avi"
    ffmpeg -r 15 -i "${folder}/%03d.annotated.png" -vf scale=3200:-2 -c:v libx265 -crf 3 -preset slow "${timeseries}"

    rm "${folder}"/*.vrt
    rm "${folder}"/*.xml
    #rm "${folder}"/*."${small_ext}"
    #rm "${folder}"/*.mpg.png
fi
