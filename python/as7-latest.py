#!/usr/bin/python3 
import json
import os
from detectlib import cfe
from caliblib import load_json_file 
from datetime import datetime
#import datetime as dt
import datetime as dt
import math, decimal 
dec = decimal.Decimal
jsc = load_json_file("../conf/as6.json")
amsid = jsc['site']['ams_id']


def save_json_file(json_file, json_data):
   with open(json_file, 'w') as outfile:
      json.dump(json_data, outfile)
   outfile.close()

def position(now=None):
   if now is None:
      now = dt.datetime.now()

   diff = now - dt.datetime(2001, 1, 1)
   days = dec(diff.days) + (dec(diff.seconds) / dec(86400))
   lunations = dec("0.20439731") + (days * dec("0.03386319269"))

   return lunations % dec(1)

def phase(pos):
   index = (pos * dec(8)) + dec("0.5")
   index = math.floor(index)
   return {
      0: "New Moon",
      1: "Waxing Crescent",
      2: "First Quarter",
      3: "Waxing Gibbous",
      4: "Full Moon",
      5: "Waning Gibbous",
      6: "Last Quarter",
      7: "Waning Crescent"
   }[int(index) & 7]

def get_moon_phase():
   pos = position()
   phasename = phase(pos)

   roundedpos = round(float(pos), 3)
   return ("%s (%s)" % (phasename, roundedpos))

def log_weather(datetime_str):
   date_str = datetime_str[0:10]
   lat = str(jsc['site']['device_lat'])[0:4]
   lng = str(jsc['site']['device_lng'])[0:4]
   cloud_dir = "/mnt/archive.allsky.tv/" + jsc['site']['ams_id'] + "/LATEST/" 
   cloud_day_dir = cloud_dir + date_str + "/" 
   try:
      city = str(jsc['site']['operator_city'])
   except:
      city = ""
   try:
      state = str(jsc['site']['operator_state'])
   except:
      state = ""
   try:
      country = str(jsc['site']['operator_country'])
   except:
      country = ""

   if "US" in country or "United States" in country :
      country = "US"
      location = city + ", " + state + " " + country
   else:
      location = city + ", " + country
   outdir = "/mnt/ams2/latest/" + date_str + "/" 
   if cfe(outdir,1) == 0:
      os.makedirs(outdir)
   if cfe(cloud_dir,1) == 0:
      os.makedirs(cloud_dir)
   outfile = "/mnt/ams2/latest/" + date_str + "/" + datetime_str + ".txt"

   url = "wttr.in/" + str(lat) + "," + str(lng) + "?0T --output " + outfile
   print(url)
   os.system("curl " + url)
   fp = open(outfile)
   lc = 0
   for line in fp:
      line = line.replace("\n", "")
      if lc == 2:
         status = line[16:]
      if lc == 3:
         temp = line[16:]
      if lc == 4:
         wind = line[16:]
      if lc == 5:
         wind_speed = line[16:]
      lc += 1
   #print(lc, line, wind, wind_speed)

   fp.close()
   moon_phase = get_moon_phase()
   data = {}
   data['station_id'] = jsc['site']['ams_id']
   data['location'] = location 
   data['conditions'] = status
   data['temp'] = temp 
   data['wind'] = wind 
   data['mi'] = wind_speed
   data['moon_phase'] = moon_phase
   data['datetime'] = datetime_str
   wjs = outfile.replace(".txt", ".json") 
   save_json_file(wjs, data)
   #print(location, status, temp, wind, wind_speed, moon_phase) 
   cmd = "cp " + wjs + " /mnt/ams2/latest/current_weather.json"
   print(cmd)
   os.system(cmd)

   cmd = "cp " + wjs + " " + cloud_dir + "current_weather.json"
   print(cmd)
   os.system(cmd)

   cmd = "cp " + wjs + " " + cloud_day_dir + datetime_str + ".json"
   print(cmd)
   os.system(cmd)

def ping_cam(cam_num, config=None):
   #config = read_config("conf/config-" + str(cam_num) + ".txt")
   if config is None:
      config = load_json_file("../conf/as6.json")

   key = "cam" + str(cam_num)
   cmd = "ping -c 1 " + config['cameras'][key]['ip']

   response = os.system(cmd)
   if response == 0:
      print ("Cam is up!")
      return(1)
   else:
      print ("Cam is down!")
      return(0)



if "cloud_latest" in jsc:
   cloud_on = jsc['cloud_latest']
else: 
   cloud_on = 0 


cameras = jsc['cameras']

cur_day = datetime.now().strftime("%Y_%m_%d")
cur_day_hm = datetime.now().strftime("%Y_%m_%d_%H_%M")
cur_hour = datetime.now().strftime("%H")
cur_min = datetime.now().strftime("%M")
cloud_dir = "/mnt/archive.allsky.tv/" + amsid + "/LATEST/" 
cloud_arc_dir = cloud_dir + cur_day + "/" 
log_weather(cur_day_hm)



for cam in cameras:
   cam_num = cam.replace("cam", "")
   ping_ok = ping_cam(cam_num, jsc)
   if ping_ok == 0:
      print("Cam ping down.")
      continue
   cams_id = cameras[cam]['cams_id']

   cmd = "./get_latest.py " + cam_num
   print(cmd)
   os.system(cmd)
   if cfe("/mnt/ams2/latest/" + cur_day, 1) == 0:
      os.makedirs("/mnt/ams2/latest/" + cur_day) 

   # downsample the image and save to latest archive (for year long timelapses later)
   latest = "latest"
   cmd = "convert /mnt/ams2/latest/" + cams_id + ".jpg -resize 640x360 -quality 80 /mnt/ams2/latest/" + cur_day + "/" + amsid + "_" + cams_id + "_" + cur_day_hm + ".jpg"
   print("1", cmd)
   os.system(cmd)

   if cloud_on == 1:
      cmd = "cp /mnt/ams2/latest/" + cur_day + "/" + amsid + "_" + cams_id + "_" + cur_day_hm + ".jpg " + cloud_dir + cams_id + ".jpg"
      print("2", cmd)
      os.system(cmd)

      if cfe(cloud_arc_dir, 1) == 0:
         os.makedirs(cloud_arc_dir)

      cmd = "cp " + cloud_dir + cams_id + ".jpg " + cloud_arc_dir + amsid + "_" + cams_id + "_" + cur_day_hm + ".jpg"
      print("3", cmd)
      os.system(cmd)

      # copy to cloud
   #exit()
      
if True:
   print("HOUR/MIN", cur_hour, cur_min)
   if int(cur_hour) % 4 == 0:
      if int(cur_min) <= 10:
         # run system health 1x per 3 hours
         cmd = "cd /home/ams/amscams/pipeline; ./system_health.py"
         print(cmd)
         os.system(cmd)

         cmd = "cd /home/ams/amscams/; git pull"
         print(cmd)
         os.system(cmd)
