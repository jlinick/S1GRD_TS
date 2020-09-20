#!/usr/bin/env python3

'''
Wrapper for generating Sentinel GRD Timeseries
'''

import os
import getpass
import html
import json
import shutil
import argparse
import subprocess
import requests
import fiona
import shapely.geometry


def main(shapefile=False, workdir=False, pol=False, res='MR', max_results=False, cleanup=False, dry_run=False):
    '''main wrapper script for generating time series'''
    script_dir = os.path.dirname(os.path.realpath(__file__))
    if workdir is False:
        workdir = os.getcwd()
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    #validate auth keyfile
    authkey_file = os.path.join(script_dir, 'auth.key')
    if not os.path.exists(authkey_file):
        authkey_file = os.path.join(workdir, 'auth.key')
        if not os.path.exists(authkey_file):
            gen_authkey(authkey_file)
    if shapefile is False:
        shapefile = os.path.join(script_dir, 'aux', 'poly.shp') #use default polygon if not specified
    if not os.path.exists(shapefile):
        raise Exception('shapefile: {} does not exist.'.format(shapefile))
    if shapefile.endswith('kml'):
        shapefile = convert_kml_to_shapefile(shapefile)

    # get a polygon string from the shapefile
    wkt_string = get_wkt_from_shapefile(shapefile)
    asf_string = convert_wkt_to_asf(wkt_string)
    print('parsed shapefile.\nQuerying ASF for granules...')
    query_asf(pol, res, max_results, asf_string)
    drystr = ' (dry-run only)' if dry_run else ''
    print('--------------------------------\nDownloading files from ASF...{}'.format(drystr))
    download_asf(pol, res, max_results, asf_string, authkey_file, dry_run, workdir)

    #per zip file:
        #unzip file
        #calibrate each file & compress the result

    #merge files into folders by date
    #merge each folder into a composite
    #generate the time series

def convert_kml_to_shapefile(kml_path):
    '''converts the input kml into a shapefile'''
    kmlfile_basename = os.path.basename(kml_path)
    kmlfile_folder = os.path.dirname(kml_path)
    shapefile_filename = '{}.shp'.format(kmlfile_basename)
    shapefile_path = os.path.join(kmlfile_folder, shapefile_filename)
    cmd = ['ogr2ogr', shapefile_path, kml_path]
    os.system(cmd)
    if not os.path.exist(shapefile_path):
        raise Exception('unable to generate shapefile from {}'.format(kml_path))
    return shapefile_path

def get_wkt_from_shapefile(shapefile_path):
    '''returns the wkt string from the input shapefile'''
    c = fiona.open(shapefile_path)
    collection = [ shapely.geometry.shape(item['geometry']) for item in c ]
    return [j.wkt for j in collection][0]

def convert_wkt_to_asf(wkt_string):
    '''converts a wkt string to the string format required for querying asf'''
    return wkt_string.replace('POLYGON ','polygon=').replace(' ',',').replace(',,',',').replace('(', '').replace(')','')

def gen_authkey(authkey_file):
    '''prompts the user to create the proper auth.key file in their workdir'''
    username = input("Earthdata username:")
    pw = getpass.getpass(prompt="Earthdata password:")
    print('saving user/pass to: {}'.format(authkey_file))
    outstr = 'EARTHDATA_USER={}\nEARTHDATA_PASSWORD={}'.format(username, pw)
    fout = open(authkey_file, 'w')
    fout.write(outstr)
    fout.close()

def query_asf(pol, res, max_results, poly_str):
    query = gen_asf_query(pol, res, max_results, poly_str, retrieve=False)
    response = requests.get(query)
    maxstr = ''
    if max_results:
        maxstr = ', only retrieving {} products'.format(max_results)
    print('ASF has {} results matching input parameters{}...'.format(response.text.strip(), maxstr))

def gen_asf_query(pol, res, max_results, poly_str, retrieve=False):
    # polarization
    polstr = ''
    if not pol is None:
        polstr = '&polarization={}'.format(pol).replace('+', '%2B').replace(' ', '+')
    # resolution
    resdct = {'FR':'GRD_FS,GRD_FD', 'HR':'GRD_HS,GRD_HD', 'MR':'GRD_MS,GRD_MD'}
    resstr = '&processingLevel={}'.format(resdct.get(str(res)))
    # number of results
    maxstr = ''
    if max_results and retrieve is True:
        maxstr = '&maxResults={}'.format(max_results)
    retstr = '&output=count'
    if retrieve:
        retstr = '&output=metalink'
    query="https://api.daac.asf.alaska.edu/services/search/param?platform=S1{}{}{}{}{}".format(resstr, polstr, maxstr, '&' + poly_str, retstr)
    qstr = html.escape(query).replace('&amp;', '&')
    return qstr

def download_asf(pol, res, max_results, poly_str, authkey_file, dry_run, workdir):
    query = gen_asf_query(pol, res, max_results, poly_str, retrieve=True)
    dry_run_str = ''
    if dry_run:
        dry_run_str = '--dry-run '
    cmd = '. {} && aria2c --continue {}--dir="{}"--http-auth-challenge=true --http-user="$EARTHDATA_USER" --http-passwd="$EARTHDATA_PASSWORD" "{}"'.format(authkey_file, dry_run_str, workdir, query)
    #print('system command: {}'.format(cmd))
    subprocess.Popen(cmd, shell=True)

def parser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    parse = argparse.ArgumentParser(description="Generate time-series animation from input location/polygon")
    parse.add_argument("--shapefile", required=False, default=False, help="input shapefile or kml file")
    parse.add_argument("--path", required=False, default=False, help="output folder for products. Defaults to current directory.")
    parse.add_argument("--polarization", required=False, default='HH', choices=['VV','VV+VH','Dual VV','VV+VH','Dual HV','HH','HH+HV','VV','Dual VH', None], help="polarization to process.")
    parse.add_argument("--resolution", required=False, default="MR", choices=["FR", "HR", "MR"], help="GRD resolution: FR, HR, or MR (Full, High, or Medium)")
    parse.add_argument("--max_results", required=False, default=False, type=int, help="max number of input files to download")
    parse.add_argument("--dry_run", action="store_true", help="checks file availability but does not download files")
    parse.add_argument("-c", "--cleanup", action="store_true", help="cleanup intermediate files")    
    return parse


if __name__ == '__main__':
    args = parser().parse_args()
    main(shapefile=args.shapefile, workdir=args.path, pol=args.polarization, res=args.resolution, max_results=args.max_results, cleanup=args.cleanup, dry_run=args.dry_run)
