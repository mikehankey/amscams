import os
from datetime import datetime, timedelta
import subprocess
import ephem
import glob
import json
from lib.UtilLib import check_running 
from lib.FileIO import cfe , save_json_file, load_json_file

def fix_days(cmd_mode = 0):
   proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
   if cfe(proc_file) == 0:
      return()
   proc_data = load_json_file(proc_file)
   for day in proc_data:
      if proc_data[day]['video_files'] - proc_data[day]['image_files'] > 10:
         print("Thumbs are missing for these days!")
         if cmd_mode == 0:
            os.system("./scan_stack.py fms " + day + " > /dev/null 2>&1 &")
            return()
         else:
            print("Fixing day:", day)
            print("./scan_stack.py fms " + day )
            os.system("./scan_stack.py fms " + day + " > /dev/null 2>&1 ")

def update_proc_index(day ):
   proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
   if cfe(proc_file) == 1:
      proc_stats = load_json_file(proc_file)
   else:
      return()
   proc_stats[day] = get_proc_stats(day)
   save_json_file(proc_file)


def proc_index():
   proc_stats = {}
   proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
   if cfe(proc_file) == 1:
      proc_stats = load_json_file(proc_file)
      if proc_stats == 0:
         proc_stats = {}
   today = datetime.today()
   num_days = 14
   for i in range (0,int(num_days)):
      past_day = datetime.now() - timedelta(hours=24*i)
      past_day = past_day.strftime("%Y_%m_%d")
      proc_stats[past_day] = get_proc_stats(past_day)
      #print(past_day, proc_stats[past_day])
   for day in proc_stats:
      print(day, proc_stats[day])
   save_json_file(proc_file, proc_stats) 
   print(proc_file)

def get_proc_stats(day):
   proc_dir = "/mnt/ams2/SD/proc2/" + day + "/"
   video_files = get_files(proc_dir, "*.mp4")
   image_files = get_files(proc_dir + "/images/", "*-tn.png")

   data_files = get_files(proc_dir + "/data/", "*.json")
   vals_files = []
   detect_files = []
   mm_files = []
   nm_files = []
   tm_files = []
   m_files = []
   for df in data_files:
      if "-vals.json" in df:
         vals_files.append(df)
      if "-detect.json" in df:
         detect_files.append(df)
      if "-maybe-meteors.json" in df:
         
         mm_files.append(df)
      if "-no-meteor.json" in df:
         nm_files.append(df)
      if "-toomany.json" in df:
         tm_files.append(df)
      if "-meteor.json" in df:
         m_files.append(df)

   proc_stats = {}
   proc_stats['video_files'] = len(video_files)
   proc_stats['image_files'] = len(image_files)
   proc_stats['vals_files'] = len(vals_files)
   proc_stats['detect_files'] = len(detect_files)
   proc_stats['mm_files'] = len(mm_files)
   proc_stats['nm_files'] = len(nm_files)
   proc_stats['tm_files'] = len(tm_files)
   proc_stats['m_files'] = len(m_files)
   return(proc_stats)

def update_latest(cam_info, pending_files):
   print(cam_info)
   print(pending_files)
   cc = {}
   for cd in cam_info:
      cam_id = cd['cam_id']
      if cam_id not in cc:
         cc[cam_id] = 0
      for ff in sorted(pending_files,reverse=True):
         if cam_id in ff:
            if cc[cam_id] > 1:
               outfile = "/mnt/ams2/latest/" + cam_id + ".jpg"
               extract_frames(ff,1,2,outfile)
               print(ff, outfile)
               break 
            cc[cam_id] += 1
         

def extract_frames(video_file,start,end,outfile,w=640,h=360):
   fn = video_file.split("/")[-1] + "-trim" + str(start)
   temp_dir = "/home/ams/tmpvids/" + fn + "/"
   if cfe(temp_dir, 1) == 0:
      os.makedirs(temp_dir)
   cmd = "ffmpeg -y -i " + video_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -vsync 0 " + outfile + ">/dev/null 2>&1" 
   print(cmd)
   os.system(cmd)


def run_vals_detect(day=None, cmd_mode=0):
   running = check_running("flex-detect.py bv")
   if running == 0:

      proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
      if cfe(proc_file) == 0:
         return()
      proc_data = load_json_file(proc_file)
      for day in sorted(proc_data, reverse=True):
         if True:
            print("Need to detect vals on this day!", day)
            if cmd_mode == 0:
               os.system("./flex-detect.py bv " + day + " > /dev/null 2>&1 &")
               return()
            else:
               os.system("./flex-detect.py bv " + day )
   else:
      print("Vals detect is already running.")


def run_verify_meteors(day=None, cmd_mode=0):
   proc_file = "/mnt/ams2/SD/proc2/json/proc_stats.json";
   running = check_running("flex-detect.py vms")
   if running == 0:
      if cmd_mode == 0:
         cmd = "./flex-detect.py vms " + day + " > /dev/null 2>&1 &"
         print(cmd)
         os.system(cmd)
      else:
         proc_data = load_json_file(proc_file)
         for day in sorted(proc_data, reverse=True):
            if proc_data[day]['mm_files'] >= 1:
               print("detect vals on this day: ", day)
               os.system("./flex-detect.py vms " + day + "  ")
               #os.system("./flex-detect.py vms " + day + " > /dev/null 2>&1 ")
   else:
      print("Verify Meteor is already running.")



def get_files(dir, match = None):
   if match is None:
      files = glob.glob(dir + "*")
   else:
      files = glob.glob(dir + match)
   return(files)

def exec_cmd(cmd):
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      return(1, output)
   except:
      output = "Command failed." 
      return(0, output)

def get_old_meteors(day):
   meteor_files = []
   mf = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")
   for f in mf:
      if "trim" in f and ("HD-meteor" not in f and "reduced" not in f and "manual" not in f):
         meteor_files.append(f)
         print(f)
   return(meteor_files)

def build_meteor_file_index(year=None):
   all_meteors = {}
   meteor_dirs = glob.glob("/mnt/ams2/meteors/*")
   for md in meteor_dirs:
      if year is not None:
         if year in md:
            mday = md.split("/")[-1]
            mfs = get_old_meteors(mday) 
            for mf in mfs:
               all_meteors[mf] = {} 
      else:
         mday = md.split("/")[-1]
         mfs = get_old_meteors(mday) 
         for mf in mfs:
            all_meteors[mf] = {} 
   if year == None:
      jf = "/mnt/ams2/SD/proc2/json/all_meteors.json"
   else:
      jf = "/mnt/ams2/SD/proc2/json/all_meteors-" + year + ".json"
   save_json_file(jf, all_meteors)
   return(all_meteors)
 
def arc_check(year=None, cmd_mode=0) :
   refits = []
   bad_frames = []
   if year == None:
      jf = "/mnt/ams2/SD/proc2/json/all_meteors.json"
   else:
      jf = "/mnt/ams2/SD/proc2/json/all_meteors-" + year + ".json"
   #if cfe(jf) == 1 :
   if False:
      print("Load:", jf)
      all_meteors = load_json_file(jf)
   else:
      print("Build MI:", year)
      all_meteors = build_meteor_file_index(year)
   print("done")

   for m in all_meteors:
      arc_file,ad = get_arc(m) 
      if arc_file is not None:
         all_meteors[m]['arc_file'] = arc_file
         if ad is not None :
            if "frames" in ad:
               if len(ad['frames']) < 3:
                  bad_frames.append(arc_file)
            else:
               bad_frames.append(arc_file)
            if "calib" in ad:
               if "total_res_px" in ad['calib']['device']:
                  print(m, arc_file,ad['calib']['device']['total_res_px'])
               else:
                  print("REFIT NEEDED:")
                  refits.append(arc_file)
            else:
               print("NO calib!", arc_file)
               exit()
         else:
            print("BAD ARC JSON!?", arc_file)
            exit()
   print("REFITS:", refits)
   for fi in refits:
      os.system("./flex-detect.py faf " + fi)
   print("BAD FRAMES:", bad_frames)
   for fi in bad_frames:
      os.system("./flex-detect.py fam " + fi)
   save_json_file(jf, all_meteors)

def get_arc(m):
   js = load_json_file(m)
   if js == 0:
      print("BAD JS:", m)
      exit()
   if "archive_file" in js:
      if js['archive_file'] != "":
         if cfe(js['archive_file']) == 1:
            ad = load_json_file(js['archive_file'])
            return(js['archive_file'],ad)
   return(None,None)
 
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
   return(sun_status)

