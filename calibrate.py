#!/usr/bin/env python3.6

# Applies Radiometric Calibration and Terrain Correction using ESA SNAP python wrapper to a single GRD product

import os
import gc
import shutil
import argparse
import snappy
from snappy import ProductIO
from snappy import HashMap
from snappy import GPF

allowed_polarizations = ['HH', 'HV', 'VH', 'VV']

def main(infolder=False, outfolder=False, polarization=False, basename=False, wktstring=False, db=False, cleanup=False):
    '''main loop for generating calibration products'''

    # determine if we need to walk the dir
    if infolder is False or not os.path.exists(infolder):
        raise Exception('must provide valid input folder.')
    if infolder.endswith('.SAFE'):
        # process the file
        calibrate_file(infolder, outfolder, polarization, basename, wktstring, db, cleanup)
    else:
        #see if we can process any subfolders
        folders = os.listdir(infolder)
        for folder in folders:
            if folder.endswith('.SAFE'):
                new_infolder = os.path.join(infolder, folder)
                calibrate_file(new_infolder, outfolder, polarization, basename, wktstring, db, cleanup)

def calibrate_file(infolder, outfolder, polarization, basename, wktstring, db, cleanup):
    '''calibrate input product'''
    if outfolder is False:
        outfolder = os.path.join(os.getcwd(), 's1_preprocessed')
    if not os.path.exists(outfolder):
        os.mkdirs(outfolder)
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
            timestamp = folder.split("_")[4] 
            date = timestamp[:8]
            print('timestamp: {}, date: {}'.format(timestamp, date))
            calib = os.path.join(outfolder, '{}_calibrate_{}'.format(date, pol)) 
            subset = os.path.join(outfolder, '{}_subset_{}'.format(date, pol))
            terrain = os.path.join(outfolder, '{}_corrected_{}'.format(date, pol))
        else:
            calib = os.path.join(outfolder, '{}_calibrate_{}'.format(basename, pol)) 
            subset = os.path.join(outfolder, '{}_subset_{}'.format(basename, pol))
            terrain = os.path.join(outfolder, '{}_corrected_{}'.format(basename, pol))
           
        #read product
        sentinel_1 = ProductIO.readProduct(os.path.join(infolder, "manifest.safe"))   

        ### CALIBRATION
        parameters = HashMap() 
        parameters.put('outputSigmaBand', True) 
        parameters.put('sourceBands', 'Intensity_' + pol) 
        parameters.put('selectedPolarisations', pol) 
        parameters.put('outputImageScaleInDb', db)  
        print('calibrate file: {}'.format(calib))
        target_0 = GPF.createProduct("Calibration", parameters, sentinel_1) 
        ProductIO.writeProduct(target_0, calib, 'BEAM-DIMAP')
        
        ### SUBSET
        calibration = ProductIO.readProduct(calib + ".dim")    
        WKTReader = snappy.jpy.get_type('com.vividsolutions.jts.io.WKTReader')        
        geom = WKTReader().read(wktstring)
        parameters = HashMap()
        parameters.put('geoRegion', geom)
        parameters.put('outputImageScaleInDb', db)
        print('subset: {}'.format(subset))
        target_1 = GPF.createProduct("Subset", parameters, calibration)
        ProductIO.writeProduct(target_1, subset, 'BEAM-DIMAP')
        
        ### TERRAIN CORRECTION
        parameters = HashMap()     
        parameters.put('demResamplingMethod', 'NEAREST_NEIGHBOUR') 
        parameters.put('imgResamplingMethod', 'NEAREST_NEIGHBOUR') 
        parameters.put('demName', 'GETASSE30') 
        parameters.put('pixelSpacingInMeter', 40.0) 
        parameters.put('sourceBands', 'Sigma0_' + pol)
        print('terrain: {}'.format(terrain)) 
        target_2 = GPF.createProduct("Terrain-Correction", parameters, target_1) 
        ProductIO.writeProduct(target_2, terrain, 'GeoTIFF')

        if cleanup is True:
            os.remove(calib + '.dim')
            os.remove(subset + '.dim')
            shutil.rmtree(subset + '.data')
            shutil.rmtree(calib + '.data')


def safe_file_in(folder):
    '''returns True or False if a .SAFE file is the given directory'''
    infiles = os.listdir(folder)
    if True in [fil.endswith('.SAFE') for fil in infiles]:
        return True
    return False

def parser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    parse = argparse.ArgumentParser(description="Apply radiometric and terrain corrections")
    parse.add_argument("--infolder", required=True, default=False, help="input S1 GRD folder")
    parse.add_argument("--outfolder", required=False, default=False, help="output folder for calibrated products")
    parse.add_argument("--polarization", required=False, default=False, help="polarization to process, HH,VV VH, or HV")
    parse.add_argument("--basename", required=False, default=False, help="base folder/filename to use for output products")
    parse.add_argument("--wkt", required=False, default=False, help="wkt polygon bounds")
    parse.add_argument("-c", "--cleanup", action="store_true", help="cleanup intermediate files")
    parse.add_argument("-db", "--in_decibels", action="store_true", help="output is scaled in decibels" )
    return parse

if __name__ == '__main__':
    args = parser().parse_args()
    main(infolder=args.infolder, outfolder=args.outfolder, polarization=args.polarization, basename=args.basename, wktstring=args.wkt, db=args.db, cleanup=args.cleanup)
