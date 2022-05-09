import math
import cv2
import glob
from lib.PipeUtil import cfe, convert_filename_to_date_cam, check_running, load_json_file
import pickle
import os
import datetime
from datetime import datetime as dt
from lib.FFFuncs import ffprobe
import sys


from Classes.Weather import Weather
json_conf = load_json_file("../conf/as6.json")

station_id = json_conf['site']['ams_id']
lat = json_conf['site']['device_lat']
lon = json_conf['site']['device_lng']

# make sure it is not already running
running = check_running("Weather.py")
if running > 2:
   print("Weather program is already running...")
   #cmd = "/bin/echo 'ABORT WEATHER RUNNING:" + str(running) + "'>run.txt"
   #os.system(cmd)
   exit()


WW = Weather()
if len(sys.argv) <= 1:
   WW.help()
   exit()     
   exit()     
elif len(sys.argv) == 2:
   cmd = sys.argv[1]
   day = datetime.datetime.now().strftime("%Y_%m_%d")

elif len(sys.argv) == 3:
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


if cmd == "load_weather" or cmd == "":
   os.system("/usr/bin/python3.6 Weather.py load_metar")
   WW.index_weather_snaps_all()
   WW.load_database()
elif cmd == 'stack_index':
   WW.index_local_stacks()
elif cmd == 'process_snap':
   WW.process_weather_snap(sys.argv[2])
elif cmd == 'process_all':
   os.system("clear")
   print("please wait...")
   WW.process_weather_snap_all()
   
