#!/usr/bin/python3

from lib.BatchLib import batch_thumb, make_file_index, move_images, update_file_index, stack_night, purge_data, stack_night_all
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
   limit = 0
   if len(sys.argv) == 3:
      limit = int(sys.argv[2])
      stack_night(json_conf, limit)
   elif len(sys.argv) >= 4:
      tday = int(sys.argv[3])
      stack_night(json_conf, limit, tday)
   else:
      stack_night(json_conf)

if sys.argv[1] == 'sna':
   limit = 0
   if len(sys.argv) == 3:
      limit = int(sys.argv[2])
      stack_night_all(json_conf, limit )
   if len(sys.argv) == 4:
      tday = sys.argv[3]
      print("MIKE", tday)
      stack_night_all(json_conf, 0, tday)

if sys.argv[1] == 'pd':
   purge_data(json_conf)
