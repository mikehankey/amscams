#!/usr/bin/python3.6
import cv2
import os
import glob
from lib.PipeUtil import convert_filename_to_date_cam, get_trim_num, load_json_file, save_json_file, day_or_night

"""
make_weather_repo.py
this script will scan files in /mnt/ams2/latest and crop/sort them into the weather learning repo

"""

def extract_images(img_file, this_repo_dir, repo_label):
   print("EXTRACT", img_file) #, this_repo_dir, repo_label)
  
   station_id, cam, year, month, day, hour, minute = img_file.split("_")

   latest_dir = "/mnt/ams2/latest/" + year + "_" + month + "_" + day + "/"
   img_file = latest_dir + img_file
   img = cv2.imread(img_file)
   lcc = 0
   if img is not None:
      print(img.shape)
      for row in range(0,2):
         for col in range(0,4):
            learning_file = this_repo_dir + "/" + img_file.split("/")[-1].replace(".jpg", "-" + str(lcc) + ".jpg")
            if os.path.exists(learning_file):
               continue


            x1 = 180 * col
            x2 = x1 + 180 
            y1 = row * 180
            y2 = y1 + 180 
            learning_img = img[y1:y2,x1:x2] 
            cv2.imwrite(learning_file, learning_img)
            print("Saved learning file:", x1,y1,x2,y2, row, col, learning_file)
            lcc += 1
      
   else:
      print("FAIL:", img_file)
def do_weather_day(day, day_dir, cam_ids,json_conf):
   day_dict = {}
   json_files = glob.glob(day_dir + "*.json") 
   img_files = glob.glob(day_dir + "*.jpg") 
   for jf in json_files:
      img_fn = jf.split("/")[-1]
      try:
         year, month, day, hour, minute = img_fn.split("_")
      except:
         continue
      minute = minute.replace(".json", "")
      f_date_str = str(year) + "-" + str(month) + "-" + str(day) + " " + str(hour) + ":" + str(minute)
      hkey = hour + "_" + minute

      if hkey not in day_dict:
         day_dict[hkey] = {}
         for cam_id in cam_ids:
            day_dict[hkey][cam_id] = ""

      sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
      day_dict[hkey]['sun_status'] = sun_status


      try:
         day_dict[hkey]['weather'] = load_json_file(jf)
      except:
         day_dict[hkey]['weather'] = ""

   for img_file in sorted(img_files, reverse=True):
      img_fn = img_file.split("/")[-1]
      station_id, cam, year, month, day, hour, minute = img_fn.split("_")
      minute = minute.replace(".jpg", "")
      hkey = hour + "_" + minute
      if hkey not in day_dict:
         day_dict[hkey] = {}
         for cam_id in cam_ids:
            day_dict[hkey][cam_id] = ""
      day_dict[hkey][cam] = img_fn

   for hkey in sorted(day_dict.keys()):
      if "sun_status" in day_dict[hkey]:
         row = hkey + "\t" + str(day_dict[hkey]['sun_status'])
         sun_status = str(day_dict[hkey]['sun_status'])
      else:
         row = hkey + "\t" + ""
         sun_status = None

      if "weather" in day_dict[hkey]:
         if "conditions" in day_dict[hkey]['weather']:
            row += "\t" + str(day_dict[hkey]['weather']['conditions']) 
            weather_label = str(day_dict[hkey]['weather']['conditions'])
         else:
            row += "\t"
      else:
         row += "\t"

      if sun_status is not None and weather_label is not None:
         repo_label = sun_status + "_" + weather_label.replace(" ", "_")
      else:
         repo_label = ""
         continue
      repo_label = repo_label.lower()
      repo_label = repo_label.replace(",","")
      repo_label = repo_label.replace(">","")
      repo_label = repo_label.replace("'","")
      repo_label = repo_label.replace("\"","")
      row += "\t" + repo_label 
      this_repo_dir = repo_dir + repo_label
      if os.path.exists(this_repo_dir) is False:
         os.makedirs(this_repo_dir)

      for cam_id in sorted(day_dict[hkey].keys()):
          
         if cam_id != "weather" and cam_id != 'sun_status':
            row += "\t" + day_dict[hkey][cam_id]
            img_file = day_dict[hkey][cam_id]
            if img_file != "":
               print("IMG FILE:", img_file)
               extract_images(img_file, this_repo_dir, repo_label)
      row += "\n"
      print(row)

json_conf = load_json_file("../conf/as6.json")
cam_ids = []
for cam_num in json_conf['cameras']:
   cams_id = json_conf['cameras'][cam_num]['cams_id']
   cam_ids.append(cams_id)

latest_dir = "/mnt/ams2/latest/"
repo_dir = "/mnt/ams2/datasets/weather/"
if os.path.exists(repo_dir) is False:
   os.makedirs(repo_dir)

temp = os.listdir(latest_dir)
for day in sorted(temp,reverse=True):
   if os.path.isdir(latest_dir + day ) is True:
      do_weather_day(day, latest_dir + day + "/", cam_ids, json_conf)
