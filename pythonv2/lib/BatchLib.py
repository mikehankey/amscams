import os
import numpy as np
import cv2
import glob
from lib.FileIO import get_day_stats, load_json_file, cfe, get_days, save_json_file,load_json_file
from lib.ImageLib import draw_stack, thumb, stack_glob, stack_stack
from PIL import Image

def stack_night(json_conf, limit=0, tday = None):
   proc_dir = json_conf['site']['proc_dir']
   all_days = get_days(json_conf)
   if limit > 0:
      days = all_days[0:limit]
   else:
      days = all_days

   if tday is not None:
      for cam in json_conf['cameras']:
         cams_id = json_conf['cameras'][cam]['cams_id']
         glob_dir = proc_dir + tday + "/" 
         print(glob_dir,cams_id)
         stack_day_cam(json_conf, glob_dir, cams_id)
   else:
      for day in sorted(days,reverse=True):
         for cam in json_conf['cameras']:
            cams_id = json_conf['cameras'][cam]['cams_id']
            glob_dir = proc_dir + day + "/" 
            print(glob_dir,cams_id)
            stack_day_cam(json_conf, glob_dir, cams_id)

   

def stack_day_cam(json_conf, glob_dir, cams_id ):
   print ("stacking failures")
   # stack failed captures
   img_dir = glob_dir + "/images/"
   f_glob_dir = glob_dir + "/failed/*" + cams_id + "*-stacked.png"
   out_file = img_dir + cams_id + "-failed-stack.png"
   stack_glob(f_glob_dir, out_file)

   print ("stacking meteors")
   # then stack meteors, then join together
   glob_dir = f_glob_dir.replace("failed", "passed")
   print("GLOB:", glob_dir)
   meteor_out_file = img_dir + cams_id + "-meteors-stack.png"
   stack_glob(glob_dir, meteor_out_file)

   # now join the two together (if both exist)
   if cfe(out_file) == 1 and cfe(meteor_out_file) == 1:
      print ("Both files exist")
      im1 = cv2.imread(out_file, 0)
      im2 = cv2.imread(meteor_out_file, 0)
      im1p = Image.fromarray(im1)
      im2p = Image.fromarray(im2)

      print(out_file, meteor_out_file)
      final_stack = stack_stack(im1p,im2p)
      night_out_file = img_dir + cams_id + "-night-stack.png"
      final_stack_np = np.asarray(final_stack)
      cv2.imwrite(night_out_file, final_stack_np)
      print(night_out_file)
   elif cfe(out_file) == 1 and cfe(meteor_out_file) == 0:
      im1 = cv2.imread(out_file, 0)
      ih,iw = im1.shape
      empty = np.zeros((ih,iw),dtype=np.uint8)
      cv2.imwrite(meteor_out_file, empty)
      night_out_file = img_dir + cams_id + "-night-stack.png"
      print ("Only fails and no meteors exist")
      os.system("cp " + out_file + " " + night_out_file)
      print(night_out_file)
   elif cfe(out_file) == 0 and cfe(meteor_out_file) == 0:
      ih,iw = 576,704
      empty = np.zeros((ih,iw),dtype=np.uint8)
      night_out_file = img_dir + cams_id + "-night-stack.png"
      cv2.imwrite(meteor_out_file, empty)
      cv2.imwrite(out_file, empty)
      cv2.imwrite(night_out_file, empty)
      print(meteor_out_file)
      print(out_file)
      print(night_out_file)


def move_images(json_conf):
 
   proc_dir = json_conf['site']['proc_dir']
   days = get_days(json_conf)
   for day in days:
      cmd = "mv " + proc_dir + day + "/*.png " + proc_dir + day + "/images/"
      print(cmd)
      os.system(cmd)
      cmd = "mv " + proc_dir + day + "/*.txt " + proc_dir + day + "/data/"
      print(cmd)
      os.system(cmd)
  
def update_file_index(json_conf):
   proc_dir = json_conf['site']['proc_dir']
   data_dir = proc_dir + "/json/"
 
   stats = {}

   json_file = data_dir + "main-index.json"
   stats = load_json_file(json_file) 
   days = get_days(json_conf)
   days = sorted(days, reverse=True)
   days = days[0:1]

   for day in days:
      (failed_files, meteor_files,pending_files) = get_day_stats(proc_dir + day + "/", json_conf)

      stats[day] = {}
      stats[day]['failed_files'] = len(failed_files)
      stats[day]['meteor_files'] = len(meteor_files)
      stats[day]['pending_files'] = len(pending_files)
      print(day)
   save_json_file(json_file, stats)
   print(json_file)

def make_file_index(json_conf ):
   proc_dir = json_conf['site']['proc_dir']
   data_dir = proc_dir + "/json/"
   days = get_days(json_conf)
   
   d = 0
   html = ""
   stats = {}

   json_file = data_dir + "main-index.json"

   for day in days:

      (failed_files, meteor_files,pending_files) = get_day_stats(proc_dir + day + "/", json_conf)

      stats[day] = {}
      stats[day]['failed_files'] = len(failed_files)
      stats[day]['meteor_files'] = len(meteor_files)
      stats[day]['pending_files'] = len(pending_files)
      print(day)
   json_file = data_dir + "main-index.json"
   save_json_file(json_file, stats)
   print(json_file)


def batch_thumb(json_conf):
   print("BATCH THUMB")
   proc_dir = json_conf['site']['proc_dir']
   temp_dirs = glob.glob(proc_dir + "/*")
   proc_days = []
   for proc_day in temp_dirs :
      if "daytime" not in proc_day and "json" not in proc_day and "meteors" not in proc_day and cfe(proc_day, 1) == 1:
         proc_days.append(proc_day+"/")

   for proc_day in sorted(proc_days,reverse=True):
      folder = proc_day + "/images/"
      print("FOLDER", folder)
      glob_dir = folder + "*-stacked.png"
      image_files = glob.glob(glob_dir) 
      for file in image_files:
         tn_file = file.replace(".png", "-tn.png")
         if cfe(tn_file) == 0:
            print(file)
            thumb(file)

def batch_obj_stacks(json_conf):
   proc_dir = json_conf['site']['proc_dir']

   temp_dirs = glob.glob(proc_dir + "/*")
   proc_days = []
   for proc_day in temp_dirs :
      if "daytime" not in proc_day and "json" not in proc_day and "meteors" not in proc_day and cfe(proc_day, 1) == 1:
         proc_days.append(proc_day+"/")
   for proc_day in sorted(proc_days,reverse=True):
      folder = proc_day + "/"
      stack_folder(folder,json_conf)

def stack_folder(folder,json_conf):
   print("GOLD:", folder)
   [failed_files, meteor_files,pending_files] = get_day_stats(folder, json_conf)
   for file in meteor_files:
      stack_file = file.replace(".mp4", "-stacked.png")
      stack_img = cv2.imread(stack_file,0)
      stack_obj_file = file.replace(".mp4", "-stacked-obj.png")
      obj_json_file = file.replace(".mp4", ".json")
      objects = load_json_file(obj_json_file)
      if cfe(stack_obj_file) == 0: 
         try:
            draw_stack(objects,stack_img,stack_file)
         except:
            print("draw failed")
   for file in failed_files:
      stack_file = file.replace(".mp4", "-stacked.png")
      stack_img = cv2.imread(stack_file,0)
      stack_obj_file = file.replace(".mp4", "-stacked-obj.png")
      obj_json_file = file.replace(".mp4", ".json")
      objects = load_json_file(obj_json_file)
      if cfe(stack_obj_file) == 0:
         try:
            draw_stack(objects,stack_img,stack_file)
         except:
            print("draw failed")
