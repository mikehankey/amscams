
import json
import os
import glob
from pathlib import Path

def get_days(json_conf):
   proc_dir = json_conf['site']['proc_dir']
   days = []
   files = os.listdir(proc_dir)
   for file in files:
      if file[0] == "2":
         # the above line will stop working in 980 years i.e. y3k
         days.append(file)
   return(sorted(days, reverse=True))


def get_trims_for_file(video_file):
   el = video_file.split("/")
   base_dir = video_file.replace(el[-1], "")
   fn = el[-1]
   base_fn = fn.replace(".mp4","")
   fail_dir = base_dir + "/failed/" + base_fn + "*.mp4"
   meteor_dir = base_dir + "/passed/" + base_fn + "*.mp4"
   fail_files = glob.glob(fail_dir)
   meteor_files = glob.glob(meteor_dir)  
   return(fail_files, meteor_files)

def get_day_files(day, cams_id, json_conf):
  
   file_info = {} 
   proc_dir = json_conf['site']['proc_dir']
   [failed_files, meteor_files,pending_files] = get_day_stats(proc_dir + day + "/", json_conf)
   day_dir = proc_dir + day + "/" + "*" + cams_id + "*.mp4"
   temp_files = glob.glob(day_dir)
   for file in sorted(temp_files, reverse=True):
      if "trim" not in file and file != "/" and cams_id in file:
         base_file = file.replace(".mp4", "")
         file_info[base_file] = ""
   for file in failed_files : 
      if cams_id in file:
         junk = file.split("-trim")
         base_file = junk[0]
         base_file = base_file.replace("/failed/", "")
         if base_file != '/':
            file_info[base_file] = "failed"
   for file in meteor_files : 
      if cams_id in file:
         junk = file.split("-trim")
         base_file = junk[0]
         base_file = base_file.replace("/passed/", "")
         if base_file != '/':
            file_info[base_file] = "meteor"
   for file in pending_files: 
      if cams_id in file:
         junk = file.replace("-trim", "")
         base_file = junk[0]
         if base_file != '/':
            file_info[base_file] = "pending"
     

   return(file_info)

def get_day_stats(day, json_conf):
   proc_dir = json_conf['site']['proc_dir']
   failed_dir = day + "/failed/*trim*.mp4"
   meteor_dir = day + "/passed/*trim*.mp4"
   pending_dir = day + "/*trim*.mp4"
   failed_files = glob.glob(failed_dir)
   meteor_files = glob.glob(meteor_dir)
   pending_files = glob.glob(pending_dir)
   detect_files = [failed_files, meteor_files,pending_files]

   return(detect_files)


def get_proc_days(json_conf):
   proc_dir = json_conf['site']['proc_dir']
   files = glob.glob(proc_dir + "*")
   return(files)


def save_meteor(video_file, objects):
   (base_fn, base_dir, image_dir, data_dir,failed_dir,passed_dir) = setup_dirs(video_file)
   cmd = "mv " + base_dir + base_fn + ".mp4 "  + passed_dir
   print(cmd) 
   os.system(cmd)
   cmd = "mv " + base_dir + base_fn + "-stacked.png "  + passed_dir
   print(cmd) 
   os.system(cmd)
   cmd = "mv " + base_dir + base_fn + "-stacked-obj.png "  + passed_dir
   print(cmd) 
   os.system(cmd)

   video_json_file = passed_dir + base_fn + ".json"
   save_json_file(video_json_file, objects)




def save_failed_detection(video_file, objects):
   (base_fn, base_dir, image_dir, data_dir,failed_dir,passed_dir) = setup_dirs(video_file)
   cmd = "mv " + base_dir + base_fn + ".mp4 "  + failed_dir
   print(cmd) 
   os.system(cmd)
   cmd = "mv " + base_dir + base_fn + "-stacked.png "  + failed_dir
   print(cmd) 
   os.system(cmd)

   cmd = "mv " + base_dir + base_fn + "-stacked-obj.png "  + passed_dir
   print(cmd) 
   os.system(cmd)

   video_json_file = failed_dir + base_fn + ".json"
   save_json_file(video_json_file, objects)






def save_failed_detection(video_file, objects):
   (base_fn, base_dir, image_dir, data_dir,failed_dir,passed_dir) = setup_dirs(video_file)
   cmd = "mv " + base_dir + base_fn + ".mp4 "  + failed_dir
   print(cmd) 
   os.system(cmd)
   cmd = "mv " + base_dir + base_fn + "-stacked.png "  + failed_dir
   print(cmd) 
   os.system(cmd)
   video_json_file = failed_dir + base_fn + ".json"
   save_json_file(video_json_file, objects)


def cfe(file,dir = 0):
   if dir == 0:
      file_exists = Path(file)
      if file_exists.is_file() is True:
         return(1)
      else:
         return(0)
   if dir == 1:
      file_exists = Path(file)
      if file_exists.is_dir() is True:
         return(1)
      else:
         return(0)

def setup_dirs(filename):
   el = filename.split("/")
   fn = el[-1]
   working_dir = filename.replace(fn, "")
   data_dir = working_dir + "/data/"
   images_dir = working_dir + "/images/"
   failed_dir = working_dir + "/failed/"
   passed_dir = working_dir + "/passed/"

   file_exists = Path(failed_dir)
   if file_exists.is_dir() == False:
      os.system("mkdir " + failed_dir)
   file_exists = Path(passed_dir)
   if file_exists.is_dir() == False:
      os.system("mkdir " + passed_dir)
   file_exists = Path(data_dir)
   if file_exists.is_dir() == False:
      os.system("mkdir " + data_dir)

   file_exists = Path(images_dir)
   if file_exists.is_dir() == False:
      os.system("mkdir " + images_dir)
   base_fn = fn.replace(".mp4","")
   return(base_fn, working_dir, data_dir, images_dir, failed_dir,passed_dir)

def load_config(json_file):
   print("JSON FILE:", json_file)
   json_str = json_file.read()
   json_conf = json.loads(json_str)
   return(json_conf)

def save_json_file(json_file, json_data):
   with open(json_file, 'w') as outfile:
      json.dump(json_data, outfile)
   outfile.close()

def load_json_file(json_file):
   with open(json_file, 'r') as infile:
      json_data = json.load(infile)
   return(json_data)

