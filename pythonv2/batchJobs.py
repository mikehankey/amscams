#!/usr/bin/python3

from lib.BatchLib import batch_thumb, make_file_index, move_images, update_file_index, stack_night, purge_data
from lib.FileIO import load_json_file 
import sys

json_conf = load_json_file("../conf/as6.json")

if sys.argv[1] == 'tn':
   batch_thumb(json_conf)
if sys.argv[1] == 'fi':
   make_file_index(json_conf)
if sys.argv[1] == 'ufi':
   update_file_index(json_conf)
if sys.argv[1] == 'mi':
   move_images(json_conf)
if sys.argv[1] == 'sn':
   stack_night(json_conf)
if sys.argv[1] == 'pd':
   purge_data(json_conf)
