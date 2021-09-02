import time
import json
import os
import glob
from pathlib import Path
from lib.UtilLib import convert_filename_to_date_cam, get_sun_info

def purge_hd_cal(json_conf):
   days = glob.glob("/mnt/ams2/cal/hd_images/*")
   for day in days:
      if cfe( day, 1) == 1:
         files = glob.glob(day + "/*-stacked.png" )
         for file in files:
            bad = 0
            stars = 0
            json_file = file.replace("-stacked.png", "-calparams.json")
            if cfe(json_file) == 1:
               try:
                  json_data = load_json_file(json_file)
               except:
                  bad = 1
               try:
                  stars = len(json_data['cat_image_stars'])
                  if len(json_data['cat_image_stars']) < 15:
                     bad = 1
               except:
                  bad = 1
      
            else:
               bad = 1
            if bad == 1:
               cmd = "rm " + file + ";" + "rm " + json_file
               os.system(cmd)
               print(cmd)
            #print(file, json_file, bad, stars)

         files = glob.glob(day + "/*-calparams.json" )
         for file in files:
            bad = 0
            stars = 0
            img_file = file.replace("-calparams.json", "-stacked.png")
            if cfe(file) == 1:
               json_data = load_json_file(file)
               stars = len(json_data['cat_image_stars'])
               if len(json_data['cat_image_stars']) < 15:
                  bad = 1
            else:
               bad = 1
            if cfe(img_file) == 0:
               bad = 1
            if cfe(img_file) == 0 or cfe(json_file):
               bad = 1

            if bad == 1:
               cmd = "rm " + img_file + ";" + "rm " + file
               os.system(cmd)
               print(cmd)
            print(file, img_file, bad, stars)

def purge_sd_nighttime_files(sd_dir,json_conf):
   days = sorted(get_days(json_conf), reverse=True)
   dc = 0 
   for day in days:
      if dc > 30:
         #print(day)
         files = glob.glob(sd_dir + day + "/*.mp4")
         for file in files:
            el = file.split("/")
            #print(file, len(el))
            #if len(el) != 9:
            #   continue
            (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
            sun_status,sun_az,sun_el = get_sun_info(f_date_str,json_conf)
            st = os.stat(file)
            cur_time = int(time.time())
            mtime = st.st_mtime
            tdiff = cur_time - mtime
            tdiff = tdiff / 60 / 60 / 24
            if tdiff > 30:
               if dc % 100 == 0:
                  print ("Deleted 100 files from ", day)
               cmd = "rm " + file
               if "trim" not in file:
                  #print ("Deleted ", file)
                  print("rm " + file)
                  os.system("rm " + file)
      dc = dc + 1

def purge_sd_daytime_files(proc_dir,json_conf):
   files = glob.glob(proc_dir + "daytime/*")
   for file in files:
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      sun_status,sun_az,sun_el = get_sun_info(f_date_str,json_conf)
      st = os.stat(file)
      cur_time = int(time.time())
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60 / 60 / 24
      if sun_status == 'day' and tdiff > 1:
         print ("File is daytime and this many days old", tdiff, file)
         os.system("rm " + file)


def purge_hd_files(hd_video_dir,json_conf):
   files = glob.glob(hd_video_dir + "*")
   for file in files:
      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      sun_status,sun_az,sun_el = get_sun_info(f_date_str, json_conf)
      st = os.stat(file)
      cur_time = int(time.time())
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60 / 60 / 24
      if sun_status == 'day' and tdiff > 1:
         print ("File is daytime and this many days old", tdiff, file)
         print("rm " + file)
         os.system("rm " + file)
      elif tdiff > 2:
         print ("File is nighttime and this many days old will be purged.", tdiff, file)
         print("rm " + file)
         os.system("rm " + file)



def archive_meteor (sd_video_file,hd_file,hd_trim,hd_crop_file,hd_box,hd_objects,sd_objects,json_conf,trim_time_offset, trim_dur):
   el = sd_video_file.split("/")
   fn_base = el[-1] 
   fn_base = fn_base.replace(".mp4", "")

   print("ARCHIVE METEOR:", sd_video_file)
   # make / determine archive dir and then
   # copy SD trim, SD stack
   # HD trim, HD crop, HD trim stack & HD crop stack
   # to meteor dir (make stacks if needed)
   meteor_dir = make_meteor_dir(sd_video_file, json_conf) 

   meteor_json_file =  meteor_dir + fn_base + ".json"
   sd_wild = sd_video_file.replace(".mp4", ".*")   
   os.system("cp " + sd_wild + " " + meteor_dir)
   if hd_trim is not None and hd_trim != 0: 
      os.system("cp " + hd_trim + " " + meteor_dir)
      os.system("cp " + hd_crop_file+ " " + meteor_dir)
   meteor_json = {}
   meteor_json['sd_video_file'] = sd_video_file
   meteor_json['hd_file'] = hd_file
   meteor_json['hd_trim'] = hd_trim
   meteor_json['hd_crop_file'] = hd_crop_file
   meteor_json['hd_box'] = hd_box 
   meteor_json['hd_objects'] = hd_objects
   meteor_json['sd_objects'] = sd_objects
   meteor_json['hd_trim_time_offset'] = trim_time_offset
   meteor_json['hd_trim_dur'] = trim_dur 
   print("saving", meteor_json_file)
   save_json_file(meteor_json_file, meteor_json )
   


def make_meteor_dir(sd_video_file, json_conf):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_video_file)
   meteor_dir = "/mnt/ams2/meteors/" + fy + "_" + fm + "_" + fd + "/" 
   if cfe(meteor_dir, 1) == 0:
      os.system("mkdir " + meteor_dir)
   return(meteor_dir)

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
   pending_dir = base_dir + "/" + base_fn + "-trim*.mp4"

   fail_files = glob.glob(fail_dir)
   meteor_files = glob.glob(meteor_dir)  
   pending_files = glob.glob(pending_dir)  
   return(fail_files, meteor_files, pending_files)

def get_day_files(day, cams_id, json_conf, sun=None,in_hour=None,detect=None):
   file_info = {} 
   proc_dir = json_conf['site']['proc_dir']
   if sun is None:
      sun = "0"

   
   #Get all the JSON Files of the day
   [failed_files, meteor_files,pending_files,min_files] = get_day_stats(day, proc_dir + day + "/", json_conf)
   day_dir = proc_dir + day + "/" + "*" + cams_id + "*.mp4"
   #temp_files = glob.glob(day_dir)
   temp_files = min_files
 
   for file in sorted(temp_files, reverse=True):
      if "trim" not in file and file != "/" and cams_id in file:
         fn = file.split("/")[-1]
         rt = fn.replace(".mp4", "")
         if rt in meteor_files:
            base_info = "meteor"
         else:
            base_info = ""
     
         base_file = file.replace(".mp4", "")
         (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
         sun_status,sun_az,sun_el = get_sun_info(f_date_str,json_conf)
         if in_hour is not None:
            if int(in_hour) == int(fh):
               file_info[base_file] = base_info

         else:
            
            if sun is None or sun == "0":
               if int(sun_el) < 0:
                  file_info[base_file] = base_info
            else:
               if int(sun_el) > 0:
                  file_info[base_file] = base_info
         
   if detect is not None:
      file_info = {}
      day_dir = proc_dir + day + "/" + "*.mp4"
      temp_files = glob.glob(day_dir)
      # pos vals: meteor, nonmeteor, toomany
      tm = 0
      mm = 0
      met = 0
      det = 0
      nm = 0
      for file in temp_files:
         fn = file.split("/")[-1]
         rt = fn.replace(".mp4", "")
         if rt in meteor_files:
            base_info = "meteor"
         else:
            base_info = ""

         base_file = file.replace(".mp4", "")

         fn = file.split("/")[-1]
         dir = file.replace(fn, "")
         fn = fn.replace(".mp4", "")
         data_dir = dir + "data/"
         tm_file = data_dir + fn + "-toomany.json" 
         mm_file = data_dir + fn + "-maybe-meteors.json" 
         m_file = data_dir + fn + "-meteor.json" 
         nm_file = data_dir + fn + "-nometeor.json" 
         d_file = data_dir + fn + "-detect.json" 
         if cfe(tm_file) == 1: 
            tm += 1
            file_info[base_file] = ""
         if cfe(mm_file) == 1: 
            mm += 1
            file_info[base_file] = ""
         if cfe(nm_file) == 1: 
            mm += 1
            file_info[base_file] = ""
         if cfe(m_file) == 1: 
            met += 1
            file_info[base_file] = ""
         if cfe(d_file) == 1: 
            det += 1
            #file_info[base_file] = ""
   return(file_info)

def get_day_stats(day, day_dir, json_conf):
   proc_dir = json_conf['site']['proc_dir']
   data_dir = day_dir + "/data/*.json"
   meteor_dir = "/mnt/ams2/meteors/" + day + "/*.json"
   pending_dir = "/mnt/ams2/SD/proc2/" + day + "/*trim*.mp4"
   data_dir = "/mnt/ams2/SD/proc2/" + day + "/data/*-meteor.json"
   min_file_dir = "/mnt/ams2/SD/proc2/" + day + "/*.mp4"
   min_file_day_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/*.mp4"
   trash_dir = "/mnt/ams2/trash/" + day + "/"

   if cfe(trash_dir, 1) == 1:
      failed_files = glob.glob(trash_dir + "*.json")
   else:
      failed_files = []

   print("TRASH:", trash_dir, len(failed_files))
   tmp_meteor_files = glob.glob(meteor_dir)
   tmp_meteor_files2 = glob.glob(data_dir)
   tmp_meteor_files2 = []
   meteor_files = []
   umeteor_files = {}
   temp = []
   for f in failed_files:
      if "reduced" not in f:
         temp.append(f)
   failed_files = temp
   for tmp in tmp_meteor_files2 :
      mf = tmp.split("/")[-1]
      el = mf.split("-trim")
      mfr = el[0] 
      mfr = mfr.replace("-meteor.json", "")
      #if "reduced" not in tmp and "manual" not in tmp and "star" not in tmp:
         #meteor_files.append(mfr)
      #   umeteor_files[mfr] = 1
   for tmp in tmp_meteor_files :
      mf = tmp.split("/")[-1]
      el = mf.split("-trim")
      mfr = el[0] 
      mfr = mfr.replace("-meteor.json", "")
      if "reduced" not in tmp and "manual" not in tmp and "star" not in tmp:
         #meteor_files.append(mfr)
         umeteor_files[mfr] = 1
   for key in umeteor_files:
      meteor_files.append(key)
   pending_files = glob.glob(pending_dir)
   min_files = glob.glob(min_file_dir)
   min_day_files = glob.glob(min_file_day_dir)
   for mf in min_day_files:
      min_files.append(mf)
   detect_files = [failed_files, meteor_files,pending_files,min_files]

   return(detect_files)

def update_meteor_count(day):
   meteor_dir = "/mnt/ams2/meteors/" + day + "/*.json"
   tmp_meteor_files = glob.glob(meteor_dir)
   meteor_files = []
   for tmp in tmp_meteor_files :
      if "reduced" not in tmp and "manual" not in tmp and "star" not in tmp:
         meteor_files.append(tmp)
   return(meteor_files)

def get_proc_days(json_conf):
   proc_dir = json_conf['site']['proc_dir']
   files = glob.glob(proc_dir + "*")
   return(files)


def save_meteor(video_file, objects, json_conf = None):
   print("SAVE METEOR", objects)
   (base_fn, base_dir, image_dir, data_dir,failed_dir,passed_dir) = setup_dirs(video_file)
   if "trash" in passed_dir:
      proc_dir = json_conf['site']['proc_dir']
      el = video_file.split("/")
      day_dir = el[-1][0:10]
      passed_dir = proc_dir + day_dir + "/passed/"
   if "failed" not in video_file and "passed" not in video_file:
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
   print("Video JSON ", video_json_file)
   save_json_file(video_json_file, objects)




def save_failed_detection(video_file, objects):
   print("MIKE: SAVE FAILED DETECTION")
   (base_fn, base_dir, image_dir, data_dir,failed_dir,passed_dir) = setup_dirs(video_file)


   if "failed" not in video_file and "passed" not in video_file:
      cmd = "mv " + base_dir + base_fn + ".mp4 "  + failed_dir
      print(cmd) 
      os.system(cmd)

      cmd = "mv " + base_dir + base_fn + "-stacked.png "  + failed_dir
      print(cmd) 
      os.system(cmd)
      cmd = "mv " + base_dir + base_fn + "-stacked-obj.png "  + failed_dir 
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
   json_str = json_file.read()
   json_conf = json.loads(json_str)
   return(json_conf)

def save_json_file(json_file, json_data, compress=False):
   with open(json_file, 'w') as outfile:
      if(compress==False):
         json.dump(json_data, outfile, indent=4, allow_nan=True)
      else:
         json.dump(json_data, outfile, allow_nan=True)
   outfile.close()

def load_json_file_MIKESVERSION(json_file):
   with open(json_file, 'r' ) as infile:
      json_data = json.load(infile)
   return(json_data)


def load_json_file(json_file):  
   try:
      with open(json_file, 'r' ) as infile:
         json_data = json.load(infile)
   except:
      json_data = False
   return json_data 

