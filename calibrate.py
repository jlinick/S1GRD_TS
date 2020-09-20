#!/usr/bin/env python3.6

# Applies Radiometric Calibration and Terrain Correction using ESA SNAP python wrapper to a single GRD product

import os
import re
import gc
import shutil
import argparse
import zipfile
import fiona
import shapely.geometry
import snappy
from snappy import ProductIO
from snappy import HashMap
from snappy import GPF

allowed_polarizations = ['HH', 'HV', 'VH', 'VV']

def main(infolder=False, outfolder=False, polarization=False, basename=False,
         wktstring=False, shapefile=False, pixel_spacing=100, db=False, cleanup=False, unzip=False):
    '''main loop for generating calibration products. infolder can be a folder of .SAF/zip files or a .SAFE/zip file'''
    print('--------------------------------\nRunning Extraction and Calibration over:{}'.format(infolder))
    if shapefile:
        wktstring = get_wkt_from_shapefile(shapefile)
    if db:
        print('output products will be generated in decibels.')
    infolder = unzip_check(infolder, cleanup) # unzip if required
    # determine if we need to walk the dir
    if infolder is False or not os.path.exists(infolder):
        raise Exception('must provide valid input path.')
    if contains_valid_product(infolder, polarization):
        # process the file
        calibrate_file(infolder, outfolder, polarization, basename, wktstring, pixel_spacing, db, cleanup)
    elif os.path.isdir(infolder):
        #see if we can process any subfolders
        for item in os.listdir(infolder):
            folder_path = os.path.join(infolder, item)
            subfolder = unzip_check(folder_path, cleanup)
            if contains_valid_product(subfolder, polarization):
                calibrate_file(subfolder, outfolder, polarization, basename, wktstring, pixel_spacing, db, cleanup)

def unzip_check(path, cleanup):
    '''checks the path to see if it's a valid zip file. If true, will unzip and return path to new folder.
       if False, will return the path.'''
    if path.lower().endswith('zip') and zipfile.is_zipfile(path):
        # extract the file
        filename = os.path.basename(path)
        base = os.path.splitext(filename)[0] + '.SAFE'
        folder = os.path.dirname(path)
        output_path = os.path.join(folder, base)
        if os.path.exists(output_path):
            return output_path # don't extract if the folder already exists
        print('extracting {}...'.format(filename))
        with zipfile.ZipFile(path,"r") as zip_ref:
            zip_ref.extractall(folder)
        if cleanup:
            os.remove(path)
        return output_path
    return path

def contains_valid_product(path, polarization):
    '''checks to see if the given directory contains a valid .tiff GRD file with the optional polarization'''
    if not os.path.isdir(path):
        return False
    meas_dir = os.path.join(path, 'measurement')
    if not 'measurement' in os.listdir(path) or not os.path.isdir(meas_dir):
        return False
    regex = 's1.*-grd-.*.tiff'
    if polarization:
        regex = 's1.*-grd-{}-.*.tiff'.format(polarization.lower())
    for fil in os.listdir(meas_dir):
        print('checking {}'.format(fil))
        if bool(re.search(regex, fil.lower())):
            return True
    return False

def get_wkt_from_shapefile(shapefile_path):
    '''returns the wkt string from the input shapefile'''
    if not os.path.exists(shapefile_path):
        raise Exception("invalid shapefile path: {}".format(shapefile_path))
    c = fiona.open(shapefile_path)
    collection = [ shapely.geometry.shape(item['geometry']) for item in c ]
    return [j.wkt for j in collection][0]

def calibrate_file(infolder, outfolder, polarization, basename, wktstring, pixel_spacing, db, cleanup):
    '''calibrate input product'''
    print('--------------------------\nCalibrating product: {}'.format(infolder))
    if outfolder is False:
        outfolder = os.path.join(os.getcwd(), 's1_preprocessed')
    if not os.path.exists(outfolder):
        os.makedirs(outfolder)
    assert polarization in allowed_polarizations
    if polarization is False:
        polarization = ['HH', 'HV', 'VH', 'VV']
    else:
        polarization = [polarization]
    if wktstring is False:
        wktstring = 'POLYGON ((-94.3242680177268 -68.1554115901846,-94.4799907148995 -78.0386897518533,-133.488922458484 -75.1093782424761,-116.988045118527 -66.0302485803105,-94.3242680177268 -68.1554115901846))'

    GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
    HashMap = snappy.jpy.get_type('java.util.HashMap')
    gc.enable()

    # build folder paths
    folder = os.path.basename(infolder)
    for pol in polarization:

        if basename is False:
            print("folder: {}".format(folder))
            basename = os.path.basename(folder).rstrip('.SAFE')
        calib = os.path.join(outfolder, '{}.{}.{}.calibrated'.format(basename, pol, pixel_spacing)) 
        subset = os.path.join(outfolder, '{}.{}.{}.subset'.format(basename, pol, pixel_spacing))
        terrain = os.path.join(outfolder, '{}.{}.{}.corrected'.format(basename, pol, pixel_spacing))
 
        # read product
        sentinel_1 = ProductIO.readProduct(os.path.join(infolder, "manifest.safe"))   

        ### CALIBRATION
        parameters = HashMap() 
        parameters.put('outputSigmaBand', True) 
        parameters.put('sourceBands', 'Intensity_' + pol) 
        parameters.put('selectedPolarisations', pol) 
        parameters.put('outputImageScaleInDb', db)  
        print('Applying radiometric correction: {}'.format(calib))
        target_0 = GPF.createProduct("Calibration", parameters, sentinel_1) 
        ProductIO.writeProduct(target_0, calib, 'BEAM-DIMAP')
        
        ### SUBSET
        calibration = ProductIO.readProduct(calib + ".dim")    
        WKTReader = snappy.jpy.get_type('com.vividsolutions.jts.io.WKTReader')        
        geom = WKTReader().read(wktstring)
        parameters = HashMap()
        parameters.put('geoRegion', geom)
        parameters.put('outputImageScaleInDb', db)
        print('Generating subset file: {}'.format(subset))
        target_1 = GPF.createProduct("Subset", parameters, calibration)
        ProductIO.writeProduct(target_1, subset, 'BEAM-DIMAP')
        
        ### TERRAIN CORRECTION
        parameters = HashMap()     
        parameters.put('demResamplingMethod', 'NEAREST_NEIGHBOUR') 
        parameters.put('imgResamplingMethod', 'NEAREST_NEIGHBOUR') 
        parameters.put('demName', 'GETASSE30') 
        parameters.put('pixelSpacingInMeter', pixel_spacing) 
        parameters.put('sourceBands', 'Sigma0_' + pol)
        print('Applying terrain correction: {}'.format(terrain)) 
        target_2 = GPF.createProduct("Terrain-Correction", parameters, target_1) 
        ProductIO.writeProduct(target_2, terrain, 'GeoTIFF')

        if cleanup is True:
            os.remove(calib + '.dim')
            os.remove(subset + '.dim')
            shutil.rmtree(subset + '.data')
            shutil.rmtree(calib + '.data')
    if cleanup:
        shutil.rmtree(infolder)

def parser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    parse = argparse.ArgumentParser(description="Apply radiometric and terrain corrections")
    parse.add_argument("--infolder", required=True, default=False, help="input S1 GRD folder")
    parse.add_argument("--outfolder", required=False, default=False, help="output folder for calibrated products")
    parse.add_argument("--polarization", required=False, default='HH', choices=['HH','VV','VH','HV'], help="polarization to process.")
    parse.add_argument("--basename", required=False, default=False, help="base folder/filename to use for output products")
    parse.add_argument("--wkt", required=False, default=False, help="wkt polygon bounds")
    parse.add_argument("--shapefile", required=False, default=False, help="shapefile for bounds")
    parse.add_argument("--pixel_spacing", required=False, default=100, type=float, help="Pixel spacing in meters")
    parse.add_argument("--in_decibels", action="store_true", help="output is scaled in decibels")
    parse.add_argument("--unzip", action="store_true", help="will extract zipped files")
    parse.add_argument("--cleanup", action="store_true", help="cleanup intermediate files")
    return parse

if __name__ == '__main__':
    args = parser().parse_args()
    main(infolder=args.infolder, outfolder=args.outfolder, polarization=args.polarization,
          basename=args.basename, wktstring=args.wkt, shapefile=args.shapefile,
          pixel_spacing=args.pixel_spacing, db=args.in_decibels, cleanup=args.cleanup, unzip=args.unzip)
