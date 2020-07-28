#!/usr/bin/python3

import sys
from dvrip import DVRIPCam
from time import sleep
import json
import time
from datetime import datetime
import os
import ephem

from lib.FileIO import load_json_file, save_json_file, cfe

#FILL IN YOUR DETAILS HERE:
CameraUserName = "admin"
CameraPassword = ""
CameraIP = '192.168.76.71'
BitrateRequired = 7000
#END OF USER DETAILS


json_conf = load_json_file("../conf/as6.json")


def get_cam_url(cam_ip):
   for as_cam in json_conf['cameras']:
      if json_conf['cameras'][as_cam]['ip'] == cam_ip:
         url = "rtsp://" + cam_ip + json_conf['cameras'][as_cam]['hd_url'] 
         cams_id = json_conf['cameras'][as_cam]['cams_id'] 
   return(url, cams_id)


def sense_up(cam, cam_ip):
   print("Sense up for : ", cam_ip)
   # put cam into slow shutter. 
   # sleep 3 seconds
   # grab and save one picture
   # put cam back to normal 

   now = datetime.now()
   day = now.strftime("%m_%d")
   dom = now.strftime("%Y_%m_%d")
   year = now.strftime("%Y")
   hms = now.strftime("%H_%M_%S")
   #f_date_str = dom + "_" 

   cam_url, cams_id = get_cam_url(cam_ip)

   cam_info = cam.get_info("Camera.ParamEx")
   print (cam_info)
   cam_info2 = cam.get_info("Camera.Param")
   print (cam_info2)


   # set slow shutter on 
   cam_info[0]['EsShutter'] = '0x00000002'
   cam.set_info("Camera.Param", cam_info)
   print("Slow shutter on.")
   time.sleep(3)

   print("Getting picture.")
   print(cam_url)


   outdir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/CAL/AUTOCAL/" + year + "/" 
   outfile = outdir + dom + "_" + hms + "_000_" + cams_id + ".png"
   print("OUT:", outfile)
   if cfe(outdir, 1) == 0:
      os.makedirs(outdir)

   cmd = "/usr/bin/ffmpeg -y -i '" + cam_url + "' -vframes 1 " +outfile + " >/dev/null 2>&1"
   os.system(cmd)


   # set slow shutter off
   cam_info[0]['EsShutter'] = '0x00000000'
   cam.set_info("Camera.Param", cam_info)
   print("slow shutter is off")




   # DWDR on / off (turn on for day off for night.)
   #cam_info[0]['BroadTrends']['AutoGain'] = 0
   #cam.set_info("Camera.ParamEx", cam_info)

   cam_info[0]['LowLuxMode'] = 0 
   cam.set_info("Camera.ParamEx", cam_info)


   #print ("\r\n")
   cam.close()

def camera_settings():
   sleep(2)
   print ("Current encoding settings:")
   #enc_info = cam.get_info("Simplify.Encode")
   cam_info = cam.get_info("Camera.ParamEx")
   print (cam_info)
   cam_info[0]['BroadTrends']['AutoGain'] = 1
   cam.set_info("Camera.ParamEx", cam_info)
   print ("\r\n")
   cam.close()

def encoding_settings():
   sleep(2)
   enc_info[0]['MainFormat']['Video']['BitRate'] = BitrateRequired
   cam.set_info("Simplify.Encode", enc_info)
   print ("Sent new bitrate settings\r\n")
   sleep(5)
   print ("New encoding settings:")
   print(cam.get_info("Simplify.Encode"))
   print(cam.get_info("Simplify.Encode"))
   sleep(5)

def day_or_night(capture_date, json_conf):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < -1:
      sun_status = "night"
   else:
      sun_status = "day"
   return(sun_status, sun_az, sun_alt)


if len(sys.argv) > 2:
    cmd = str(sys.argv[1])
else:
   print("Usage: ./IMX291 [command] [IP ADDRESS of CAM]")
   exit()

if cmd == "sense_up" or cmd == "sense_all":
   sun, az, alt  = day_or_night(datetime.now(), json_conf)
   if int(alt) >= -10:
      print("SUN:", sun, az, alt, "abort")
      exit()

if len(sys.argv) > 1:
    CameraIP = str(sys.argv[2])




if cmd == "sense_all":
   for camera in json_conf['cameras']:
      CameraIP = json_conf['cameras'][camera]['ip']
      cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
      if cam.login():
         print ("Success! Connected to " + CameraIP)
      else:
         print ("Failure. Could not connect to camera!")


      print("Sense up ", CameraIP)
      sense_up(cam, CameraIP)

if cmd == "sense_up":
   cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
   sense_up(cam, CameraIP)
