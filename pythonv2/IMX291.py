#!/usr/bin/python3
import glob
import numpy as np
import cv2
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

def get_cam_passwd(ip):
   CameraUserName = "admin"
   CameraPassword = ""
   json_conf = load_json_file("../conf/as6.json")
   for cam in json_conf['cameras']:
      cam_ip = json_conf['cameras'][cam]['ip']
      sd_url = json_conf['cameras'][cam]['sd_url']
      if ip == cam_ip:
         el = sd_url.split("&")
         for k in el:
            print("KEY:", k)
            if "password" in k:
               el2 = k.split("=")
               CameraPassword = el2[1]
               print("PASS IS:", CameraPassword)
            #else:
            #   print("Default cam passwd")
            #   CameraPassword=""
   return(CameraPassword)

def sense_up(cam, cam_ip):
   station_id = json_conf['site']['ams_id']
   station_num = int(station_id.replace("AMS", ""))
   if "cal_options" in json_conf:
      cal_options = json_conf['cal_options']
   else:
      cal_options = {}
      cal_options['bw'] = True
      cal_options['cal_median'] = True
      cal_options['sense_up'] = True
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
   if "sense_up" not in cal_options:
      print("No sense up")
      #cam_info[0]['EsShutter'] = '0x00000002'
      #cam.set_info("Camera.Param", cam_info)
      ##print("Slow shutter on.")
   elif cal_options['sense_up'] is True:
<<<<<<< HEAD
      # disable this for now
=======
      # disabled 5/30
>>>>>>> efb768a37cc9210d5f33be0c88fe3dfbde50fe53
      #cam_info[0]['EsShutter'] = '0x00000002'
      print("Slow shutter on.")

   if "bw" in cal_options:

      print("BW FLAG")
      if cal_options['bw'] is True:
<<<<<<< HEAD
         # disable for now
=======
         # disabled 5/30

>>>>>>> efb768a37cc9210d5f33be0c88fe3dfbde50fe53
         #cam_info[0]['DayNightColor'] = '0x00000002'
         #cam.set_info("Camera.Param", cam_info)
         print("SET BW FLAG")
         #time.sleep(3)
      else:
         print("BW FLAG False")
   else:
      print("NO BW FLAG")
<<<<<<< HEAD
         
   #cam.set_info("Camera.Param", cam_info)
   #print("Slow shutter on.")
=======

   # disabled 5/30
   #cam.set_info("Camera.Param", cam_info)
   print("Slow shutter on.")
>>>>>>> efb768a37cc9210d5f33be0c88fe3dfbde50fe53
   #time.sleep(7)


   print("Getting pictures...")
   print(cam_url)

   outdir = "/mnt/ams2/meteor_archive/" + json_conf['site']['ams_id'] + "/CAL/AUTOCAL/" + year + "/" 
   outfile = outdir + dom + "_" + hms + "_000_" + cams_id + ".png"
   if os.path.exists(outdir) is False:
      os.makedirs(outdir)

   # signle frame
   if "cal_median" in cal_options:
      cal_temp = "/mnt/ams2/cal/temp/"
      if os.path.exists(cal_temp) is False :
         os.makedirs(cal_temp) 
      else:
         os.system("rm " + cal_temp + "*.jpg") 

      temp_file = cal_temp + "temp%d.jpg"
      cmd = "/usr/bin/ffmpeg -hide_banner -y -i '" + cam_url + "' -vframes 10 " +temp_file + " >/dev/null 2>&1"
      print(cmd)
      os.system(cmd)

      files = glob.glob(cal_temp + "*.jpg")
      meds = []
      for ff in files:
         img = cv2.imread(ff)
         meds.append(img)
      med_img = cv2.convertScaleAbs(np.median(np.array(meds), axis=0))
      cv2.imwrite(outfile, med_img)
      print("WROTE MEDIAN:", outfile)



   else:
      print("OUT:", outfile)
      if cfe(outdir, 1) == 0:
         os.makedirs(outdir)

      cmd = "/usr/bin/ffmpeg -hide_banner -y -i '" + cam_url + "' -vframes 1 " +outfile + " >/dev/null 2>&1"
      print(cmd)
      os.system(cmd)


   # set slow shutter off
   cam_info[0]['EsShutter'] = '0x00000000'




   # DWDR on / off (turn on for day off for night.)
   #cam_info[0]['BroadTrends']['AutoGain'] = 0
   #cam.set_info("Camera.ParamEx", cam_info)

   cam_info[0]['LowLuxMode'] = 0 

   if "bw" in cal_options:
      if cal_options['bw'] is True:
         if 150 <= station_num <= 165:
            cam_info[0]['DayNightColor'] = '0x00000000'
         else:
            cam_info[0]['DayNightColor'] = '0x00000001'
         print("RESET CAM TO COLOR!", cam_info)

   print("slow shutter is off")
   cam.set_info("Camera.Param", cam_info)
   cam.set_info("Camera.ParamEx", cam_info)
   #print ("\r\n")
   cam.close()

def day_night_settings(cam, cam_ip, type):
   if type == 'night':
      cam_info = cam.get_info("Camera.ParamEx")
      cam_info[0]['BroadTrends']['AutoGain'] = 0
      cam.set_info("Camera.ParamEx", cam_info)
      print("Set camera settings for night")

      cam_info = cam.get_info("Camera.Param")
      cam_info[0]['BroadTrends']['AutoGain'] = 0
      cam.set_info("Camera.ParamEx", cam_info)
      print("Set camera settings for night")


   if type == 'day':
      cam_info = cam.get_info("Camera.ParamEx")
      cam_info[0]['BroadTrends']['AutoGain'] = 1
      cam.set_info("Camera.ParamEx", cam_info)
      print("Set camera settings for day")

      cam_info = cam.get_info("Camera.Param")
      cam_info[0]['BroadTrends']['AutoGain'] = 1
      cam.set_info("Camera.Param", cam_info)
      print("Set camera settings for day")

     

def encode(cam, cam_ip):
   enc_info = cam.get_info("Simplify.Encode")
   print(type(enc_info))
   print(enc_info)
   print("SD QUALITY:", enc_info[0]['ExtraFormat']['Video']['Quality'])
   print("HD QUALITY:", enc_info[0]['MainFormat']['Video']['Quality'])
   print("RESOLUTION :", enc_info[0]['MainFormat']['Video']['Resolution'])
   enc_info[0]['ExtraFormat']['Video']['Quality'] = 3
   enc_info[0]['MainFormat']['Video']['Quality'] = 3
   enc_info[0]['MainFormat']['Video']['BitRate'] = 3072
   enc_info[0]['MainFormat']['Video']['Resolution'] = "1080P"
   cam.set_info("Simplify.Encode", enc_info)
   print("SET:", enc_info)
   cam.close()

def test(cam, cam_ip):
   sun, az, alt  = day_or_night(datetime.now(), json_conf)
   print(sun, az,alt)
   #https://github.com/NeiroNx/python-dvr
   enc_info = cam.get_info("Simplify.Encode")
   cam_info2 = cam.get_info("Camera.ParamEx")
   cam_info1 = cam.get_info("Camera.Param")
   net_info = cam.get_info("NetWork.NetCommon")

   # disable cloud
   cloudEnabled = False
   sys_info = cam.set_info("NetWork.Nat", {"NatEnable" : cloudEnabled } )
   sys_info = cam.get_info("NetWork.Nat")

   # set slow shutter to OFF
   #cam_info[0]['EsShutter'] = '0x00000000'
   #cam.set_info("Camera.Param", cam_info)
   print ("ENCODING:\n", enc_info)
   print ("CAM PARAMS1:\n", cam_info1)
   print ("CAM PARAMS2:\n", cam_info2)
   print ("NETWORK:\n", net_info)
   print ("SYS:\n", sys_info)

   print("SLOW SHUTTER:", cam_info1[0]['EsShutter'])
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

def auto_settings(cam, cam_ip):
   # check the day or night sun elevation 
   # check settings for default overrides
   # if it is daytime make sure DWDR = 1 , color = 1  
   # if it is nighttime make sure DWDR = 0 , color = 0  (optional)

   sun, az, alt  = day_or_night(datetime.now(), json_conf)
   if int(alt) < -10:
      # it is nighttime
      set_daytime_settings(cam)
   else:
      set_nighttime_settings(cam)
      # it is daytime


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

#if cmd == "sense_up" or cmd == "sense_all":
      #exit()

if len(sys.argv) > 1:
    CameraIP = str(sys.argv[2])

    CameraPassword = get_cam_passwd(CameraIP)

if cmd == "day_night_settings":
   # switch camera settings back and forth from day to night (just WDR for now)  
   new = 0
   update = 0
   sun, az, alt  = day_or_night(datetime.now(), json_conf)
   if cfe("../conf/settings.json") == 0:
      settings = {}
      new = 1
      update = 1
      settings['current'] = sun
   else:
      settings = load_json_file("../conf/settings.json")
      if settings['current'] != sun:
         settings['current'] = sun
         update = 1
   if update == 1 or new == 1:
      for camera in json_conf['cameras']:
         CameraIP = json_conf['cameras'][camera]['ip']
         CameraIP = json_conf['cameras'][camera]['ip']
         CameraPassword = get_cam_passwd(CameraIP)
         cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
         if cam.login():
            print ("Success! Connected to " + CameraIP)
         else:
            print ("Failure. Could not connect to camera!")

         day_night_settings(cam, CameraIP, sun)
         cam.close()
         save_json_file("../conf/settings.json", settings)
   else:
      print("Settings are already set for ", sun)

      



if cmd == "sense_all":
   for camera in json_conf['cameras']:
      CameraIP = json_conf['cameras'][camera]['ip']
      CameraPassword = get_cam_passwd(CameraIP)
      cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
      try:
         cam.login()
         print ("Success! Connected to " + CameraIP)
      except:
         print ("Failure. Could not connect to camera!")
         exit()


      # make sure remote cloud is disabled 
      cloudEnabled = False
      sys_info = cam.set_info("NetWork.Nat", {"NatEnable" : cloudEnabled } )


      #sense_up(cam, CameraIP)

      sun, az, alt  = day_or_night(datetime.now(), json_conf)
      if int(alt) >= -10 and cam is not None:
         print("SUN:", sun, az, alt, "abort")
         print(cam)
         if cam is not None:
            try:
               cam.close()
            except:
               print("Cam already closed")
         continue

      print("Sense up ", CameraIP)
      try:
         sense_up(cam, CameraIP)
      except:
         print("Could not acquire images for camera:", cam)

if cmd == "test":
   cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
   if cam.login():
      print ("Success! Connected to " + CameraIP)
   else:
      print ("Failure. Could not connect to camera!")
   test(cam, CameraIP)

if cmd == "sense_up":
   cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
   if cam.login():
      print ("Success! Connected to " + CameraIP)
   else:
      print ("Failure. Could not connect to camera!")


   sense_up(cam, CameraIP)

if cmd == "auto_settings":
   cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
   auto_settings(cam, CameraIP)
if cmd == "reboot":
   cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
   if cam.login():
      print ("Success! Connected to " + CameraIP)
   else:
      print ("Failure. Could not connect to camera!")
   print("REBOOTING CAM", CameraIP)
   cam.reboot()
  
 
if cmd == "encode":
   cam = DVRIPCam(CameraIP,CameraUserName,CameraPassword)
   if cam.login():
      print ("Success! Connected to " + CameraIP)
   else:
      print ("Failure. Could not connect to camera!")
   encode(cam, CameraIP)
