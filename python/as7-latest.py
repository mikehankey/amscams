#!/usr/bin/python3 
import ephem 
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import json
import os
from detectlib import cfe
from caliblib import load_json_file 
from datetime import datetime
#import datetime as dt
import datetime as dt
import math, decimal 

try:
    
   from timezonefinder import TimezoneFinder 
   from pytz import timezone, utc
   # TIME ZONE!
   tf = TimezoneFinder()
except:
   print("COULDN'T RUN ZIMEZONE!")
   exit()


dec = decimal.Decimal
jsc = load_json_file("../conf/as6.json")
json_conf = jsc
amsid = jsc['site']['ams_id']

def ephem_info(device_lat, device_lng, capture_date):

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   moon = ephem.Moon()

   sun_rise = obs.previous_rising(sun)
   sun_set = obs.next_setting(moon)
   moon_rise = obs.previous_rising(sun)
   moon_set = obs.next_setting(moon)
   sun.compute(obs)
   moon.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")
   (moon_alt, x,y) = str(moon.alt).split(":")

   saz = str(sun.az)
   moon_az = str(moon.az)
   (sun_az, x,y) = saz.split(":")
   (moon_az, x,y) = moon_az.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"

   print("STATUS:", sun_status)
   print("SUN", sun_az, sun_alt, sun_rise, sun_set)
   print("Moon", moon_az, moon_alt, moon_rise, moon_set)
   return(sun_status, sun_az, sun_alt, sun_rise, sun_set, moon_az, moon_alt, moon_rise, moon_set)

def pil_add_text(cv2img, x,y, text, font, color ):
   image = Image.fromarray(cv2img)
   draw = ImageDraw.Draw(image)

   if font is None:
      #font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", 20, encoding="unic" )
      font = ImageFont.truetype("DejaVuSans.ttf", 12, encoding="unic" )
   draw.text((x, y), str(text), font = font, fill=color)
   return cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)

def get_offset(*, lat, lng):
    """
    returns a location's time zone offset from UTC in minutes.
    local_time = today - dt.timedelta(hours = hour_offset)
    """


    today = datetime.now()
    tz_target = timezone(tf.certain_timezone_at(lng=lng, lat=lat))
    # ATTENTION: tz_target could be None! handle error case
    today_target = tz_target.localize(today)
    today_utc = utc.localize(today)

    offset_min = (today_utc - today_target).total_seconds() / 60
    offset_hour = offset_min / 60
    local_time = today + dt.timedelta(hours = offset_hour)
    return (today_utc - today_target).total_seconds() / 60, today, local_time


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
   return(data)

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

try:
   tz = tf.timezone_at(lng=float(jsc['site']['device_lng']), lat=float(jsc['site']['device_lat']))
   bergamo = {"lat": float(jsc['site']['device_lat']), "lng": float(jsc['site']['device_lng'])}
   #minute_offset, utc_time, local_time = get_offset(**bergamo)
   minute_offset, utc_time, local_time = get_offset(**bergamo)
   print("OFFSET:", minute_offset/60)
   local_time_str = local_time.strftime('%Y-%m-%d %H:%M') + " (UTC " + str(minute_offset/60) + ")"
   print("LOCAL TIME:", local_time_str)
except:
   print("NEED TO INSTALL: sudo python3 -m pip install timezonefinder")
   tz = ""
   local_time_str = None



cameras = jsc['cameras']

cur_day = datetime.now().strftime("%Y_%m_%d")
cur_day_hm = datetime.now().strftime("%Y_%m_%d_%H_%M")
cur_hour = datetime.now().strftime("%H")
cur_min = datetime.now().strftime("%M")
cloud_dir = "/mnt/archive.allsky.tv/" + amsid + "/LATEST/" 
cloud_arc_dir = cloud_dir + cur_day + "/" 
wdata = log_weather(cur_day_hm)



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

   naked_file = "/mnt/ams2/latest/" + cur_day + "/" + amsid + "_" + cams_id + "_" + cur_day_hm + ".jpg"
   naked_img = cv2.imread(naked_file)
   marked_file = "/mnt/ams2/latest/" + amsid + "_" + cams_id + ".jpg"

   # add txt to image

   yy, mm, dd, h,m = wdata['datetime'].split("_")
   datestr = yy + "/" + mm + "/" + dd + " " + h + ":" + m + " UTC"
   datestr2 = yy + "/" + mm + "/" + dd + " " + h + ":" + m 

   # 
   (sun_status, saz, sun_alt, sun_rise, sun_set, moon_az, moon_alt, moon_rise, moon_set) = ephem_info(json_conf['site']['device_lat'], json_conf['site']['device_lng'], datestr2)


   desc1 = json_conf['site']['ams_id'] + " - " + json_conf['site']['operator_name'] + " " + wdata['location'] + " " + datestr + " - ALLSKY7.NET "
   
   temp = wdata['temp'].split(" ")[0] + "\u00B0"
   temp = wdata['temp'].replace("  ", "")
   #.split(" ")[0] + "\u00B0"
   moond = wdata['moon_phase'].split("(")
   moon = moond[0]
   moon_perc = moond[1]
   moon_perc = moon_perc.replace(")", "")
   moon_perc = str(int(float(moon_perc) * 100)) + "% full"

   new_moon = moon + "Moon " + moon_perc

   if False:
      logo = cv2.imread("allsky_logo.png")
      #print(logo.shape)
      logo = cv2.cvtColor(logo, cv2.COLOR_RGBA2BGRA)
      h,w = logo.shape[:2]
      #434 107
      w = 217
      h = 54
      logo = cv2.resize(logo, (w,h))
   


   if local_time_str is not None:
      datestr = local_time_str


#{'station_id': 'AMS1', 'location': 'Monkton, MD US', 'conditions': 'Sunny', 'temp': '30(26) °F      ', 'wind': '↘ 3 mph        ', 'mi': '6 mi           ', 'moon_phase': 'Waxing Gibbous (0.325)', 'datetime': '2022_01_12_12_10'}

   #(sun_status, saz, sun_alt, sun_rise, sun_set, moon_az, moon_alt, moon_rise, moon_set)
   if sun_status == "day":
      sun_status == "Daytime"
      if int(saz) < 180 and 0 <= int(sun_alt) < 5:
         sun_status = "Morning"
      if int(saz) < 180 and -10 <= int(sun_alt) < 0:
         sun_status = "Dawn"
   else:
      sun_status == "Nightime"
      if int(saz) < 180 and -10 <= int(sun_alt) < 5:
         sun_status = "Dusk"

   desc2 = sun_status + " " + wdata['conditions'] + " " + temp + " " + "Solar elv: " + str(sun_alt) + " " + new_moon + " " + str(moon_alt) + " elv"


   #cv2.putText(naked_img, desc1,   (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255), 1)
   #cv2.putText(naked_img, desc2,   (10,30), cv2.FONT_HERSHEY_SIMPLEX, .4, (255), 1)
   naked_img = pil_add_text(naked_img, 10,10, desc1, None, "white")
   naked_img = pil_add_text(naked_img, 10,30, desc2, None, "white")

   print("D1", desc1)
   print("D2", desc2)
   print("T:", temp)
   #434 107
   if False:
      y1 = naked_img.shape[0] - logo.shape[0]
      y2 = naked_img.shape[0] 
      x1 = 0
      x2 = logo.shape[1]
      print("X1:", x1,x2,y1,y2)

      #naked_img = cv2.cvtColor(naked_img, cv2.COLOR_RGBA2BGRA)

      naked_img[y1:y2,x1:x2] = logo
   cv2.imwrite(marked_file, naked_img)
   print("MARKED:", marked_file)

   exit()

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
