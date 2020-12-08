#!/usr/bin/python3 

import os
from detectlib import cfe
from caliblib import load_json_file 
from datetime import datetime
jsc = load_json_file("../conf/as6.json")
amsid = jsc['site']['ams_id']


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
   cloud_on = 1
else: 
   cloud_on = 1 

#cloud_on = 1 

cameras = jsc['cameras']
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
   cur_day = datetime.now().strftime("%Y_%m_%d")
   cur_day_hm = datetime.now().strftime("%Y_%m_%d_%H_%M")
   cloud_dir = "/mnt/archive.allsky.tv/" + amsid + "/LATEST/" 
   cloud_arc_dir = cloud_dir + cur_day + "/" 
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

