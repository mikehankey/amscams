from Classes.Weather import Weather
import math
import cv2
import glob
from lib.PipeUtil import cfe, convert_filename_to_date_cam
import pickle
import os
import datetime
from datetime import datetime as dt
from lib.FFFuncs import ffprobe
import sys

WW = Weather()

cmd = sys.argv[1]
day = sys.argv[2]
if "_" in day :
   day = day.replace("_", "-")

if cmd == "load_metar":
   start_time = day + "T00:00:00+0000"
   end_time = day + "T23:00:00+0000"
   lat = 39.589
   lon = -76.584
   metar_records = WW.get_metar_records(start_time, end_time, lat, lon, .35)
   exit()


if cmd == "load_weather":
   WW.index_weather_snaps_all()
   WW.load_database()
elif cmd == 'stack_index':
   WW.index_local_stacks()
elif cmd == 'process_snap':
   WW.process_weather_snap(sys.argv[2])
elif cmd == 'process_all':
   WW.process_weather_snap_all()
   
