#!/usr/bin/python3

import datetime
import sys
import time
from collections import defaultdict
from as6libs import get_sun_info
import os
import requests
from urllib.request import urlretrieve
import json


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)

def set_camera_time():
   cur_datetime = datetime.datetime.now()
   req_str = "year=" + str(cur_datetime.strftime("%Y")) + "&" + "month=" + str(cur_datetime.strftime("%m")) + "&" + "day=" + str(cur_datetime.strftime("%d")) + "&" + "hour=" + str(cur_datetime.strftime("%H")) + "&" + "minute=" + str(cur_datetime.strftime("%M")) + "&" + "second=" + str(cur_datetime.strftime("%S"))

   print ("Set datetime, timezone and NTP server.")
   url = "http://" + str(cam_ip) + "/cgi-bin/date_cgi?action=set&user=admin&pwd="+ cams_pwd +"&timezone=14&ntpHost=clock.isc.org&" + req_str
   print (url)
   r = requests.get(url)
   print (r.text)



def nighttime_settings( ):
   # set exposure time to 50 
   r = requests.get("http://" + cam_ip + "/webs/btnSettingEx?flag=1000&paramchannel=0&paramcmd=1058&paramctrl=50&paramstep=0&paramreserved=0&")
   time.sleep(3)
   print ("Nighttime settings...")
   print ("turn off wdr")
   WDR(0)
   time.sleep(1)
   print ("fix ir")
   fix_ir()
   set_special("1004", "255")

   ### Set gains to auto ###
   set_special("1084", "0")
   set_special("1087", "0")
   set_special("1085", "0")

   ### BW/COLOR 
   print ("set BW to color=0 BW=2")
   set_special("1036", "0")
   ### BLC
   print ("set BLC")
   set_special("1017", BLC)
   ### SET AGAIN
   set_special("1056", 180)

   ### SET AGAIN
   set_special("1056", 176)

   ### SET DGAIN HIGH to SHOCK SYSTEM 
   set_special("1086", 0)
   time.sleep(1)
   ### SET DGAIN to Value we actually want
   set_special("1086", 41)

   print ("set BRIGHTNESS")
   set_setting("Brightness", brightness)
   print ("set CONTRAST")
   set_setting("Contrast", contrast)
   print ("set GAMA")
   set_setting("Gamma", gamma)
   #set_setting("InfraredLamp", "low")
   #set_setting("TRCutLevel", "low")
   file = open(cams_dir + "/temp/status" + cam_num + ".txt", "w")
   file.write("night")
   file.close()
   #os.system("./allsky6-calibrate.py read_noise " + cam_num)

def daytime_settings():
   ### saturation
   set_special("1004", "128")
   ### Set gains to auto ###
   set_special("1084", "0")
   set_special("1087", "0")
   set_special("1085", "0")
   ### BW/COLOR 
   print ("set BW")
   set_special("1036", "0")
   WDR(1)
   time.sleep(2)
   WDR(0)
   time.sleep(2)
   WDR(1)
   time.sleep(2)
   ### IR mode
   #set_special("1064", "2")
   ### BLC
   set_special("1017", "30")

   set_setting("Brightness", brightness)
   set_setting("Gamma", gamma)
   set_setting("Contrast", contrast)
   #set_setting("InfraredLamp", "low")
   #set_setting("TRCutLevel", "low")
   file = open(cams_dir + "temp/status" + cam_num + ".txt", "w")
   file.write("day")
   file.close()

def set_special(field, value):
   url = "http://" + str(cam_ip) + "/webs/btnSettingEx?flag=1000&paramchannel=0&paramcmd=" + str(field) + "&paramctrl=" + str(value) + "&paramstep=0&paramreserved=0"
   print (url)
   r = requests.get(url)
   print (r.text)

def WDR(on):
   #WDR ON/OFF
   url = "http://" + str(cam_ip) + "/webs/btnSettingEx?flag=1000&paramchannel=0&paramcmd=1037&paramctrl=" + str(on) + "&paramstep=0&paramreserved=0"
   print (url)
   r = requests.get(url)
   print (r.text)

def fix_ir():
   print ("Fixing IR settings.")

   url = "http://" + str(cam_ip) + "/webs/btnSettingEx?flag=1000&paramchannel=0&paramcmd=1063&paramctrl=0&paramstep=0&paramreserved=0"
   r = requests.get(url)
   #print (r.text)

   time.sleep(1)
   url = "http://" + str(cam_ip) + "/webs/btnSettingEx?flag=1000&paramchannel=0&paramcmd=1047&paramctrl=0&paramstep=0&paramreserved=0"
   r = requests.get(url)
   #print (r.text)


   # open or close
   url = "http://" + str(cam_ip) + "/webs/btnSettingEx?flag=1000&paramchannel=0&paramcmd=1081&paramctrl=1&paramstep=0&paramreserved=0"
   r = requests.get(url)
   #print (r.text)

   #ir direction
   url = "http://" + str(cam_ip) + "/webs/btnSettingEx?flag=1000&paramchannel=0&paramcmd=1067&paramctrl=1&paramstep=0&paramreserved=0"
   r = requests.get(url)
   #print (r.text)

   time.sleep(1)
   # high low ICR
   url = "http://" + str(cam_ip) + "/webs/btnSettingEx?flag=1000&paramchannel=0&paramcmd=1066&paramctrl=0&paramstep=0&paramreserved=0"
   r = requests.get(url)
   #print (r.text)

def set_setting(setting, value):
   url = "http://" + str(cam_ip) + "/cgi-bin/videoparameter_cgi?action=set&user=admin&pwd=" + cams_pwd + "&action=get&channel=0&" + setting + "=" + str(value)
   r = requests.get(url)
   print (url)
   return(r.text)


def get_settings():
   url = "http://" + str(cam_ip) + "/cgi-bin/videoparameter_cgi?action=get&user=admin&pwd=" + cams_pwd + "&action=get&channel=0"
   print (url)
   settings = defaultdict()
   r = requests.get(url)
   resp = r.text
   for line in resp.splitlines():
      (set, val) = line.split("=")
      settings[set] = val
   return(settings)

try:
   cam_num = sys.argv[1]
except:
   cam_num = ""
   exit()


cam_key = 'cam' + str(cam_num)
cam_ip = json_conf['cameras'][cam_key]['ip']
cams_pwd = json_conf['site']['cams_pwd']
cams_dir = json_conf['site']['cams_dir']

try:
   file = open(cams_dir + "/temp/status" + cam_num + ".txt", "r")
   cam_status = file.read()
   print ("CAM STATUS: ", cam_status)
except:
   print ("no cam status file exits.")
   cam_status = ""


time_now = datetime.datetime.today().strftime('%Y/%m/%d %H:%M:%S')
print("TIME", time_now)
sun_status,sun_az,sun_alt = get_sun_info(time_now)
print ("SUN:", sun_status); 

set_camera_time()



if sun_status == 'day' or sun_status == 'dusk' or sun_status == 'dawn':
   brightness = json_conf['camera_settingsv1']['day']['brightness']
   contrast = json_conf['camera_settingsv1']['day']['contrast']
   gamma = json_conf['camera_settingsv1']['day']['gamma']
   BLC = json_conf['camera_settingsv1']['day']['BLC']
   if cam_status != sun_status:
      print ("Daytime settings are not set but it is daytime!", cam_status, sun_status)
      daytime_settings()
   else:
      print ("nothing to do...")
else:
   brightness = json_conf['camera_settingsv1']['night']['brightness']
   contrast = json_conf['camera_settingsv1']['night']['contrast']
   gamma = json_conf['camera_settingsv1']['night']['gamma']
   BLC = json_conf['camera_settingsv1']['night']['BLC']
   nighttime_settings()
   if cam_status != sun_status:
      print ("Nighttime settings are not set but it is nighttime!", cam_status, sun_status)
      nighttime_settings()
