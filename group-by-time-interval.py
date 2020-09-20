#!/usr/bin/env python3

# Groups geotiff files, given by an input regex, by acquisition time.

import os
import re
import sys
import shutil
import fnmatch
import argparse
import datetime
from osgeo import gdal

DT_FIELD='TIFFTAG_DATETIME' # datetime metadata field

class granule():
    '''simple class to hold granule objects with associated info'''
    def __init__(self):
        self.path = None
        self.datetime = None
        self.subdir = None

def main(folder, interval, regex):
    '''main loop. moves files into proper subdirectories'''
    # get a list of files that match the regex in the input folder
    matching_files = get_matching_files(folder, regex)
    # get the datetime info for each granule
    gran_list = get_info(folder, matching_files)
    # determine which subdirectory each granule belongs in
    gran_list = group_granules(gran_list, interval)
    # move the granules into their proper subdirectory
    move_files(gran_list, folder)
    #print_subdir_count(gran_list)

def move_files(gran_list, folder):
    '''moves the files into their given subdir'''
    for gran in gran_list:
        filename = os.path.basename(gran.path)
        to_folder = os.path.join(folder, gran.subdir)
        to = os.path.join(to_folder, filename)
        if not os.path.exists(to_folder):
            os.makedirs(to_folder)
        print('moving {} to {}/'.format(filename, to_folder))
        shutil.move(gran.path, to)

def print_subdir_count(gran_list):
    '''simple print to see how many files each subdir contains'''
    subdirs = sorted(list(set([g.subdir for g in gran_list])))
    for subdir in subdirs:
        count = 0
        for g in gran_list:
            if g.subdir == subdir:
                count=count+1
        print('{} : {}'.format(subdir, count))

def group_granules(gran_list, interval):
    '''determines which granules go into which subdirs, placing the info in the gran_list objects'''
    dt_interval = datetime.timedelta(days=interval)
    # if the interval is zero we group by the date
    if interval == 0:
        print('INTERVAL IS ZERO')
        for gran in gran_list:
            gran.subdir = gran.datetime.strftime('%Y%m%d')
        return gran_list
    # group by time interval
    while not get_min_unfilled_granule(gran_list) is None:
        min_g = get_min_unfilled_granule(gran_list)
        start_time = min_g.datetime
        i_time = start_time + dt_interval
        for gran in gran_list:
            if gran.subdir == None and gran.datetime < i_time:
                gran.subdir = start_time.strftime('%Y%m%d')
    return gran_list


def get_min_unfilled_granule(gran_list):
    '''returns the granule from gran_list with the minimum time that hasn't been assigned a subdir'''
    min_g = None # granule w /min time
    for gran in gran_list:
        if min_g == None and gran.subdir == None:
            min_g = gran
        elif gran.subdir == None and gran.datetime < min_g.datetime:
            min_g = gran
    return min_g


def get_info(folder, matching_file_list):
    '''gets the granule path & datetime information'''
    gran_list = []
    # determine datetimes for each file
    for fil in matching_file_list:
        gran = granule()
        gran.path = os.path.join(folder, fil)
        gran.datetime = get_datetime(gran.path)
        gran_list.append(gran)
    return gran_list

def get_datetime(file_path):
    '''returns the datetime object for the given file'''
    rds = gdal.Open(file_path)
    dt_string = rds.GetMetadata().get(DT_FIELD, None)
    if dt_string is None:
        raise Exception("could not parse metadata field: {} , for datetime.".format(DT_FIELD))
    return datetime.datetime.strptime(dt_string, '%Y:%m:%d %H:%M:%S')

def get_matching_files(folder, regex):
    '''returns files matching regex'''
    match_list = []
    for fil in os.listdir(folder):
        if fnmatch.fnmatch(fil, regex):
            match_list.append(fil)
    return list(set(match_list))

def parser():
    '''
    Construct a parser to parse arguments, returns the parser
    '''
    parse = argparse.ArgumentParser(description="Groups geotiff files by date in separate subfolders")
    parse.add_argument("--folder", required=True, default=None, help="folder to search & group files")
    parse.add_argument("--interval", required=False, type=float, default=0, help="n day time interval to group files. 0 will be same day.")
    parse.add_argument("--regex", required=False, default="*.tiff", help="regex to use for matching files") 
    return parse

if __name__ == '__main__':
    args = parser().parse_args()
    main(args.folder, args.interval, args.regex)

