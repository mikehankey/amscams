#!/usr/bin/python3

from lib.BatchLib import batch_thumb, make_file_index, move_images, update_file_index, stack_night, purge_data, stack_night_all, batch_meteor_thumb, batch_doHD, sync_multi_station, find_multi_station_meteors, merge_kml_files, batch_reduce, sync_events_to_cloud, hd_stack_meteors
from lib.FileIO import load_json_file 
import sys

json_conf = load_json_file("../conf/as6.json")
if sys.argv[1] == 'stack_hd':
   date = sys.argv[2]
   cam = sys.argv[3]
   hd_stack_meteors(json_conf, date, cam)
if sys.argv[1] == 'msm':
   sync_date = sys.argv[2]
   find_multi_station_meteors(json_conf, sync_date)
if sys.argv[1] == 'sms':
   sync_date = sys.argv[2]
   sync_multi_station(json_conf, sync_date)
if sys.argv[1] == 'cloud':
   sync_date = sys.argv[2]
   sync_events_to_cloud(json_conf, sync_date)
if sys.argv[1] == 'mkml':
   merge_kml_files(json_conf)

if sys.argv[1] == 'br':
   if len(sys.argv) > 3:
      day = sys.argv[2]
   print("BATCH REDUCE", len(sys.argv[2]))
   batch_reduce(json_conf, sys.argv[2])
if sys.argv[1] == 'tn':
   batch_thumb(json_conf)
if sys.argv[1] == 'bmt':
   batch_meteor_thumb(json_conf)
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
if sys.argv[1] == 'batch_doHD':
   batch_doHD(json_conf)
