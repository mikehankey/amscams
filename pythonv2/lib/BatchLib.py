import cv2
import glob
from lib.FileIO import get_day_stats, load_json_file, cfe, get_days, save_json_file,load_json_file
from lib.ImageLib import draw_stack, thumb

def make_file_index(json_conf):
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
