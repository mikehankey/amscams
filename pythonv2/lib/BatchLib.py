from urllib import request, parse
import datetime
import os
import subprocess
import numpy as np
import cv2
import glob
import urllib.request
import json
from lib.FileIO import get_day_stats, load_json_file, cfe, get_days, save_json_file,load_json_file, purge_hd_files, purge_sd_daytime_files, purge_sd_nighttime_files, update_meteor_count, purge_hd_cal
from lib.ImageLib import draw_stack, thumb, stack_glob, stack_stack, stack_frames
from PIL import Image
from lib.VideoLib import load_video_frames
from lib.UtilLib import convert_filename_to_date_cam

def batch_reduce(json_conf, day = None):
   meteor_dirs = glob.glob("/mnt/ams2/meteors/*")
   if day is not None:
      meteor_dirs = []
      print("DAY:", day)
      meteor_dirs.append("/mnt/ams2/meteors/" + day + "/")
   for meteor_dir in sorted(meteor_dirs, reverse=True):
      print(meteor_dir)
      print(meteor_dir + "/" + "*.json")
      meteor_files = glob.glob(meteor_dir + "/" + "*.json")
      print("METEOR FILES:", meteor_files)
      for json_file in sorted(meteor_files,reverse=True):
          if "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            reduced_file = json_file.replace(".json", "-reduced.json")
            failed_file = json_file.replace(".json", "-rfailed.txt")
            if cfe(reduced_file) == 1:
               print("Meteor done", reduced_file)
               red_data = load_json_file(reduced_file)
               if "cat_image_stars" not in red_data['cal_params']:
                  sd_video_file = reduced_file.replace("-reduced.json", ".mp4")
                  os.system("./autoCal.py cfit " + sd_video_file)
            elif cfe(failed_file) == 1:
               print("Skip already tried and failed", failed_file)
            else:
               print("Get cal file:", json_file)
               cal_files = get_active_cal_file(json_file)
               if cal_files is not None:
                  cal_params_file = cal_files[0][0]
                  print("Meteor not done", json_file)
                  cmd = "./detectMeteors.py raj " + json_file + " " + cal_params_file
                  print(cmd)
                  os.system(cmd)
                  video_file = json_file.replace(".json", ".mp4")
                  cmd = "./reducer3.py pf " + video_file
                  print(cmd)
                  os.system(cmd)
                  cmd = "./reducer3.py shd " + video_file
                  print(cmd)
                  os.system(cmd)
               else:
                  print("No calfile for : ", json_file)
                  continue
          else:
             print("Skipping already done", json_file)     
             red_data = load_json_file(json_file)
             if "intensity" not in red_data['metconf']: 
                # update the file!
                print("AZS MISSING!")
                vid = json_file.replace("-reduced.json", ".mp4")
                cmd = "./reducer3.py cm " + vid
                os.system(cmd)
             else:
                print("This file is good to go!")
            
                video_file = json_file.replace("-reduced.json", ".mp4")
                sd_archive_file = video_file.replace(".mp4", "-archiveSD.mp4")
                if cfe(sd_archive_file) == 0:
                   cmd = "./reducer3.py shd " + video_file
                   print(cmd)
                   os.system(cmd)
                hd_archive_file = video_file.replace(".mp4", "-archiveHD.mp4")
                if cfe(hd_archive_file) == 0:
                   cmd = "./reducer3.py shd " + video_file
                   print(cmd)
                   os.system(cmd)



def get_kml(kml_file):
   fp = open(kml_file, "r")
   lc = 0
   kml_txt = ""
   lines = fp.readlines()
   for line in lines: 
      if lc >= 3 and lc < len(lines)-2:
         kml_txt = kml_txt + line
      lc = lc + 1 
   fp.close()
   return(kml_txt)
      

def get_kmls(ms_dir):
   kmls = sorted(glob.glob(ms_dir + "/*.kml"))
   return(kmls)
   

def merge_kml_files(json_conf):
   kml_header = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:gx="http://www.google.com/kml/ext/2.2">
    <Document id="1">

   """
   kml_footer = """
    </Document>
</kml>
   """
   solutions = {}
   ms_dirs = sorted(glob.glob("/mnt/ams2/multi_station/*"))
   for ms_dir in ms_dirs:
      if cfe(ms_dir, 1) == 1:
         solutions[ms_dir] = get_kmls(ms_dir)
   master_kml = kml_header
   for ms_dir in solutions:
      el = ms_dir.split("/")
      day_folder_name = el[-1]
      master_kml = master_kml + "\n<Folder>\n\t<name>" + day_folder_name + "</name>"
      print(ms_dir, len(solutions[ms_dir]))
      for kml_file in solutions[ms_dir]:
         el = kml_file.split("/")
         ef = el[-1]
         event_folder_name = ef[0:20] 
         master_kml = master_kml + "\n<Folder>\n\t<name>" + event_folder_name + "</name>"
         kml_text = get_kml(kml_file) 
         master_kml = master_kml + kml_text + "\n</Folder>\n"
      master_kml = master_kml + "</Folder>\n"
   master_kml = master_kml + kml_footer
   out = open("/mnt/ams2/master_meteor_kml.kml", "w")
   out.write(master_kml)
   out.close()

def solve_event(event_id, meteor_events):
   meteor = meteor_events[event_id]
   obs = []
   for station_name in meteor['observations']:
      if len(meteor['observations'][station_name]) > 1:
         # pick the best video from this station since there is more than one
         for device_name in meteor['observations'][station_name]:
            video_file = meteor['observations'][station_name][device_name]
      else:
         for device_name in meteor['observations'][station_name]:
            video_file = meteor['observations'][station_name][device_name]
      reduced_file = video_file.replace(".mp4", "-reduced.json")
      if cfe(reduced_file) == 0:
         reduced_file = reduced_file.replace("/meteors/", "/multi_station/")
      obs.append(reduced_file)

   print("OBS:", obs)
   arglist = ""
   for ob in obs:
      arglist = arglist + ob + " " 

   #cmd = "./mikeSolve.py " + arglist
   cmd = "cd /home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory; python mikeTrajectory.py " + arglist
   os.system(cmd)
   print(cmd)
         

def get_meteor_files(mdir):
   files = glob.glob(mdir + "/*-reduced.json")
   return(files)

def id_event(meteor_events, meteor_file, meteor_json, event_start_time) :
   
   total_events = len(meteor_events)
   station_name = meteor_json['station_name']
   device_name = meteor_json['device_name']
   sd_video_file = meteor_json['sd_video_file']
   if total_events == 0:
      event_id = 1
      meteor_events[event_id] = {}
      meteor_events[event_id]['start_time'] = event_start_time
      meteor_events[event_id]['observations'] = {}
      meteor_events[event_id]['observations'][station_name]  = {}
      meteor_events[event_id]['observations'][station_name][device_name] = sd_video_file
      return(meteor_events) 

   for ekey in meteor_events:
      this_start_time = meteor_events[ekey]['start_time']
      evst_datetime = datetime.datetime.strptime(event_start_time, "%Y-%m-%d %H:%M:%S.%f")
      this_datetime = datetime.datetime.strptime(this_start_time, "%Y-%m-%d %H:%M:%S.%f")
      tdiff = (evst_datetime-this_datetime).total_seconds() 
      print(ekey, this_start_time, tdiff)
      if abs(tdiff) < 5:
         print("second capture of same event")
         meteor_events[ekey]['observations'][station_name][device_name] = sd_video_file
         return(meteor_events)

   # no matches found so make new event
   event_id = total_events + 1
   print("new event:", event_id)
   meteor_events[event_id] = {}
   meteor_events[event_id]['start_time'] = event_start_time
   meteor_events[event_id]['observations'] = {}
   meteor_events[event_id]['observations'][station_name]  = {}
   meteor_events[event_id]['observations'][station_name][device_name] = sd_video_file

   return(meteor_events)

def find_multi_station_meteors(json_conf, meteor_date="2019_03_20"):
   meteor_events = {}
   meteor_dir = "/mnt/ams2/meteors/" + meteor_date
   multi_station_dir = "/mnt/ams2/multi_station/" + meteor_date
   meteor_files = get_meteor_files(meteor_dir)
   ms_files = get_meteor_files(multi_station_dir)
   multi_station_meteors = {}
   for meteor_file in meteor_files:
      meteor_json = load_json_file(meteor_file)
      event_start_time = meteor_json['event_start_time']
      print(meteor_file) 
      meteor_events = id_event(meteor_events, meteor_file, meteor_json, event_start_time)

   event_file = "/mnt/ams2/multi_station/" + meteor_date + "/" + "events_" + meteor_date + ".json"

   for event_id in meteor_events:
      event_start_time = meteor_events[event_id]['start_time']
      evst_datetime = datetime.datetime.strptime(event_start_time, "%Y-%m-%d %H:%M:%S.%f")
      for ms_file in ms_files:
         ms_json = load_json_file(ms_file)
         ms_start_time = ms_json['event_start_time'] 
         ms_datetime = datetime.datetime.strptime(ms_start_time, "%Y-%m-%d %H:%M:%S.%f")
         ms_station_name = ms_json['station_name']
         ms_device_name = ms_json['device_name']
         ms_sd_video_file = ms_json['sd_video_file']
         time_diff = abs((evst_datetime-ms_datetime).total_seconds())
          
         if time_diff < 5:
            print("MULTI-STATION DETECTION:", event_id, ms_file)
            if ms_device_name in meteor_events:
               meteor_events[event_id]['observations'][ms_station_name][ms_device_name] = ms_sd_video_file
            else:
               meteor_events[event_id]['observations'][ms_station_name]  = {}
               meteor_events[event_id]['observations'][ms_station_name][ms_device_name] = ms_sd_video_file

   save_json_file(event_file, meteor_events)
   for event_id in meteor_events:
      total_obs = len(meteor_events[event_id]['observations'])
      if total_obs > 1:
         print(event_id, " TOTAL OBS " , total_obs)
         solve_event(event_id, meteor_events)
   
   exit()
   for meteor_file in meteor_files:
      multi_station_matches = []
      meteor_datetime, cam_id, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(meteor_file)
      print(meteor_datetime)
      for ms_file in ms_files:
         ms_datetime, ms_cam_id, ms_date, ms_y, ms_m, ms_d, ms_h, ms_M, ms_s = convert_filename_to_date_cam(ms_file)
         time_diff = abs((meteor_datetime-ms_datetime).total_seconds())
         if time_diff < 120:
            print("\t", ms_datetime, time_diff)
            #multi_station_matches
            cmd = "./mikeSolve.py " + meteor_file  + " " + ms_file
            os.system(cmd)
            print(cmd)


def sync_event(meteor_json_url, meteor_date):
   xl = meteor_json_url.split("/")
   host = xl[2]
   meteor_data = urllib.request.urlopen(meteor_json_url).read()
   meteor_data_json = json.loads(meteor_data.decode("utf-8"))
   el = meteor_json_url.split("/")
   event_file = el[-1]
   data_file = "/mnt/ams2/multi_station/" + meteor_date + "/" + event_file
   print("Syncing...", data_file)
   save_json_file(data_file, meteor_data_json)
   sync_video =  meteor_data_json['sd_video_file'] 
   sync_pic =  sync_video.replace(".mp4", "-stacked.png")
   video_file = data_file.replace("json", "mp4")
   video_url = "http://" + host + sync_video
   stack_url = "http://" + host + sync_pic
   stack_file = data_file.replace(".json", "-stacked.png")
   video_url = "http://" + host + sync_video
   if cfe(video_file) == 0:
      cmd = "wget \"" + video_url + "\" -O " + video_file
      os.system(cmd)
      print(cmd)
   if cfe(stack_file) == 0:
      cmd = "wget \"" + stack_url + "\" -O " + stack_file
      os.system(cmd)

def get_event_start_frame(sd_objects):
   st = 0
   for object in sd_objects:
      if object['meteor'] == 1:
         st = object['history'][0][0]
   return(st)

def sync_events_to_cloud(json_conf, meteor_date):
   meteors = glob.glob("/mnt/ams2/meteors/" + meteor_date + "/*.json")
   station_name = json_conf['site']['ams_id'].upper()
   json_data = {}
   json_data['station_name'] = json_conf['site']['ams_id'].upper()
   json_data['meteor_date'] = meteor_date
   json_data['capture_files'] = []
   json_data['start_times'] = []
   for meteor in meteors:
      if "reduced" in meteor and "calparams" not in meteor and "manual" not in meteor:
         meteor_json = load_json_file(meteor)

         mf = meteor.split("/")[-1] 
         event_start_time = meteor_json['event_start_time'] 
 
         json_data['capture_files'].append(mf)
         json_data['start_times'].append(str(event_start_time))

   req_json = json.dumps(json_data)
   json_data['cmd'] = "upload_caps"
   url = "http://54.214.104.131/pycgi/api-captures.py"
   mydata = parse.urlencode(json_data).encode()
   post = request.Request(url, data=mydata)
   resp = request.urlopen(post).read()

   # capture list syncd
   print("capture list syncd")

   # check if there are any multi-station files that need syncing...
   url = "http://54.214.104.131/json_data/" + meteor_date + "/events_by_station-" + meteor_date + ".json"
   print(url)

   try:
      resp = request.urlopen(url).read()
      json_data = json.loads(resp.decode('utf-8'))
   except:
      print("No events to sync with yet.", url)
      exit()

   print(json_data[station_name])

   for file in json_data[station_name]:
      print(station_name, file)
      event_id = int(json_data[station_name][file]['event_id'])
      reduction_file_syncd = int(json_data[station_name][file]['reduction_file_syncd'])
      sd_video_file_syncd = int(json_data[station_name][file]['sd_video_file_syncd'])
      sd_stack_file_syncd = int(json_data[station_name][file]['sd_stack_file_syncd'])
      device_name = json_data[station_name][file]['device_name']
    
      if reduction_file_syncd == 0:
         cmd = "./upload_file.py " + str(meteor_date) + " " + str(station_name) + " " + str(device_name) + " " + str(event_id) + " reduced.json " + "/mnt/ams2/meteors/" + str(meteor_date) + "/" + file
         print(cmd)
         os.system(cmd)
      if sd_video_file_syncd == 0:
         vid_file = file.replace("-reduced.json", ".mp4")
         cmd = "./upload_file.py " + str(meteor_date) + " " + str(station_name) + " " + str(device_name) + " " + str(event_id) + " sd.mp4 " + "/mnt/ams2/meteors/" + str(meteor_date) + "/" + vid_file
         print(cmd)
         os.system(cmd)
      if sd_stack_file_syncd == 0:
         stack_file = file.replace("-reduced.json", "-stacked.png")
         cmd = "./upload_file.py " + str(meteor_date) + " " + str(station_name) + " " + str(device_name) + " " + str(event_id) + " stacked.png " + "/mnt/ams2/meteors/" + str(meteor_date) + "/" + stack_file
         print(cmd)
         os.system(cmd)

def sync_multi_station(json_conf, meteor_date='2019_03_20'):
   sync_urls = load_json_file("/home/ams/amscams/conf/sync_urls.json")
   stations = json_conf['site']['multi_station_sync']
   for station in stations:
      url = sync_urls['sync_urls'][station]
      url = url + "pycgi/webUI.py?cmd=list_meteors&meteor_date=" + meteor_date 
      multi_dir = "/mnt/ams2/multi_station/" + meteor_date
      if cfe(multi_dir, 1) == 0:
         os.system("mkdir " + multi_dir)
      station_data = urllib.request.urlopen(url).read()
      dc_station_data = json.loads(station_data.decode("utf-8"))
      print(dc_station_data)
      multi_file = multi_dir + "/" + station + "_" + meteor_date + ".txt"
      save_json_file(multi_file, dc_station_data)
      data = load_json_file(multi_file)
      for file in data:
         print(station, file)
         file_url = sync_urls['sync_urls'][station] + file
         sync_event(file_url, meteor_date)
      

def purge_trash(json_conf):
   os.system("rm -rf /mnt/ams2/trash")
   os.system("mkdir /mnt/ams2/trash")
   


def batch_doHD(json_conf):
   from lib.UtilLib import check_running
   running = check_running("batch_doHD")
   if running > 2:
      print("Already running.")
      exit()
   proc_dir = json_conf['site']['proc_dir']
   all_days = get_days(json_conf)
   meteors = []
   for day_dir in all_days:
      meteor_glob = proc_dir + day_dir + "/passed/*.mp4"
      print(meteor_glob)
      meteor_files = glob.glob(meteor_glob)
      for mf in meteor_files:
         if "meteor" not in mf:
            meteors.append(mf) 

   for meteor in meteors:
      base_meteor = meteor.replace(proc_dir, "")
      base_meteor = base_meteor.replace("/passed", "")
      arc_meteor = "/mnt/ams2/meteors/" + base_meteor
      if cfe(arc_meteor) == 1:
         print("DONE:", arc_meteor)
         done = 1
      else:
         cmd = "./detectMeteors.py doHD " + meteor
         print(cmd)
         os.system(cmd)

def purge_data(json_conf):
   proc_dir = json_conf['site']['proc_dir']
   hd_video_dir = json_conf['site']['hd_video_dir']
   disk_thresh = 80   

   print("PURGE HD CAL")
   purge_hd_cal(json_conf)
   print("PURGE TRASH")
   purge_trash(json_conf)
   
   try:
      cmd = "df -h | grep ams2"
      #output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      #stuff = output.split(" ")
      stuff = []
      print(stuff)
      for st in stuff:
         if "%" in st:
            disk_perc = int(st.replace("%", ""))
   except:
      disk_perc = 81
   disk_perc = 81
   if disk_perc > disk_thresh:
      print("DELETE some stuff...")
      # delete HD Daytime Files older than 1 day
      # delete HD Nighttime Files older than 3 days
      # delete SD Daytime Files older than 3 days
      # delete NON Trim SD Nighttime Files (and stacks) older than 15 days
      # delete NON Meteor SD Nighttime Files older than 30 days
      # Keep all dirs in the proc2 dir (for archive browsing), but after time delete everything
      # except the passed dir and its contents. *?refine maybe?*
   print(disk_perc)
   purge_hd_files(hd_video_dir,json_conf)
   purge_sd_daytime_files(proc_dir,json_conf)
   purge_sd_nighttime_files(proc_dir,json_conf)


def hd_stack_meteors(json_conf, day, cam):
   hd_glob = "/mnt/ams2/meteors/" + day + "/*" + cam + "*HD-meteor-stacked.png"
   out_file = "/mnt/ams2/meteors/" + day + "/hd_stack-" + cam + ".png"
   stack_glob(hd_glob, out_file)

def stack_night_all(json_conf, limit=0, tday = None):
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
         stack_day_cam_all(json_conf, glob_dir, cams_id)
   else:
      for day in sorted(days,reverse=True):
         for cam in json_conf['cameras']:
            cams_id = json_conf['cameras'][cam]['cams_id']
            glob_dir = proc_dir + day + "/" 
            print(glob_dir,cams_id)
            stack_day_cam_all(json_conf, glob_dir, cams_id)

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

   
def stack_day_cam_all(json_conf, glob_dir, cams_id ):
   print ("stacking failures")
   # stack failed captures
   img_dir = glob_dir + "/images/"
   f_glob_dir = glob_dir + "/images/*" + cams_id + "*-stacked-tn.png"
   out_file = img_dir + cams_id + "-night-stack.png"


   stack_glob(f_glob_dir, out_file)


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
   new_stats = {}
   days = days[0:3]

   for day in days:
      (failed_files, meteor_files,pending_files,min_files) = get_day_stats(proc_dir + day + "/", json_conf)

      new_stats[day] = {}
      new_stats[day]['failed_files'] = len(failed_files)
      new_stats[day]['meteor_files'] = len(meteor_files)
      new_stats[day]['pending_files'] = len(pending_files)
      new_min_files, cam_counts = count_min_files(min_files,json_conf)
      new_stats[day]['min_files'] = len(new_min_files)
      for key in cam_counts:
         new_stats[day][key] = cam_counts[key]


   new_stats_copy = new_stats.copy()
   for day in stats:
      new_stats[day] = stats[day]
   for day in new_stats_copy:
      new_stats[day] = new_stats_copy[day]
 
   save_json_file(json_file, sorted(new_stats,reverse=True))
   print(json_file)

def count_min_files(min_files,json_conf):
   new_min_files = []
   cam_counts = {}
   for camera in json_conf['cameras']:
      cams_id = json_conf['cameras'][camera]['cams_id']
      cam_counts[cams_id] = 0
   
   for file in min_files:
      el = file.split("_")
      if "trim" in file or len(el) <=9:
         skip = 1
      else:
         cams_id = el[9].replace(".mp4","")
         try:
            cam_counts[cams_id] = cam_counts[cams_id] + 1
            new_min_files.append(file)
         except:
            print("bad file")
   return(new_min_files, cam_counts)



def make_file_index(json_conf ):
   print("FILE INDEX")
   proc_dir = json_conf['site']['proc_dir']
   data_dir = proc_dir + "/json/"
   days = get_days(json_conf)
   
   d = 0
   html = ""
   stats = {}

   json_file = data_dir + "main-index.json"
   if cfe(json_file) == 1:
      main_index = load_json_file(json_file)
      if main_index == 0:
         main_index = {}
   else:
      main_index = {}

   for day in days:
      stats[day] = {}
      if day in main_index:
         (failed_files, meteor_files,pending_files,min_files) = get_day_stats(day, proc_dir + day + "/", json_conf)
         stats[day]['failed_files'] = len(failed_files)
         stats[day]['meteor_files'] = len(meteor_files)
         stats[day]['pending_files'] = len(pending_files)

         new_min_files, cam_counts = count_min_files(min_files,json_conf)
         stats[day]['min_files'] = len(new_min_files)
         for key in cam_counts:
            stats[day][key] = cam_counts[key]

      else:  
         main_index[day] = {}
         (failed_files, meteor_files,pending_files,min_files) = get_day_stats(day, proc_dir + day + "/", json_conf)
         stats[day]['failed_files'] = len(failed_files)
         stats[day]['meteor_files'] = len(meteor_files)
         stats[day]['pending_files'] = len(pending_files)
         meteors = update_meteor_count(day)
         print("meteors:", day, len(meteors))
         main_index[day]['meteor_files'] = len(meteors)
         #pending_files = main_index[day]['pending_files'] 
         #min_files = main_index[day]['min_files'] 

         #stats[day] = main_index[day]

      
      print(day)
   json_file = data_dir + "main-index.json"
   save_json_file(json_file, stats)
   print(json_file)


def thumb_mp4s(mp4_files,json_conf):
   stack_image = None
   objects = []
   # there should be 3 types of MP4 files (sd, hd, crop)
   # for each of these there should be a : stack & stack_tn
   # the sd file should also have an obj and obj_tn

   for file in mp4_files:
      print("WORKING ON FILE:", file)

      stack_file = file.replace(".mp4", "-stacked.png") 
      draw_file = file.replace(".mp4", "-stacked-obj.png") 
      stack_thumb = stack_file.replace(".png", "-tn.png") 
      meteor_json_file = file.replace(".mp4", ".json") 

      if "crop" in meteor_json_file:
         if cfe(stack_file) == 0 :
            frames = load_video_frames(file,json_conf)
            stack_file, stack_image = stack_frames(frames, file)
         if cfe(stack_thumb) == 0 :
            thumb(stack_file)

      elif "HD" in meteor_json_file and "crop" not in meteor_json_file and "archive" not in meteor_json_file:
         if cfe(stack_file) == 0 :
            frames = load_video_frames(file,json_conf)
            stack_file, stack_image = stack_frames(frames, file)
         if cfe(stack_thumb) == 0 :
            thumb(stack_file)
      elif "archive" in meteor_json_file or "allmeteors" in meteor_json_file:
         print("skip archive files.")
       

      else:  
         if cfe(meteor_json_file) == 1:
            meteor_json = load_json_file(meteor_json_file)
         else:
            meteor_json = {}
         try:
            objects = meteor_json['sd_objects']
         except:
            objects = []
         if cfe(stack_file) == 0 :
            frames = load_video_frames(file,json_conf)
            stack_file, stack_image = stack_frames(frames, file)
         if cfe(stack_thumb) == 0 :
            thumb(stack_file)

      draw_file_tn = draw_file.replace(".png", "-tn.png")
      if cfe(draw_file) == 0:
         print("DRAW:", draw_file)
         stack_image = cv2.imread(stack_file, 0)
         if len(objects) > 0:
            print(objects)
            draw_stack(objects,stack_image,stack_file)
         else:
            cmd = "cp " + stack_file + " " + draw_file
            os.system(cmd)
            draw_file_tn = draw_file.replace(".png", "-tn.png")
      if cfe(draw_file_tn) == 0  :
         thumb(draw_file)

def batch_meteor_thumb(json_conf):
   meteor_base_dir = "/mnt/ams2/meteors/"
   meteor_dirs = sorted(glob.glob(meteor_base_dir + "/*"), reverse=True)
   for meteor_dir in meteor_dirs[:15]:
      mp4_files = glob.glob(meteor_dir + "/*.mp4")
      thumb_mp4s(mp4_files,json_conf)

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

def get_active_cal_file(input_file):
   print("INPUT FILE", input_file)
   if "png" in input_file:
      input_file = input_file.replace(".png", ".mp4")
   
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)

   # find all cal files from his cam for the same night
   print("FIND MATCH:", cam_id, f_datetime)
   matches = find_matching_cal_files(cam_id, f_datetime)
   #print("MATCHED:", matches)
   if len(matches) > 0:
      return(matches)
   else:
      return(None)


def better_parse_file_date(input_file):
   el = input_file.split("/")
   fn = el[-1]
   ddd = fn.split("_")
   Y = ddd[0]
   M = ddd[1]
   D = ddd[2]
   H = ddd[3]
   MM = ddd[4]
   S = ddd[5]
   MS = ddd[6]
   CAM = ddd[7]
   extra = CAM.split("-")
   cam_id = extra[0]
   cam_id = cam_id.replace(".mp4", "")
   f_date_str = Y + "-" + M + "-" + D + " " + H + ":" + MM + ":" + S
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S)

def find_matching_cal_files(cam_id, capture_date):
   matches = []
   all_files = glob.glob("/mnt/ams2/cal/freecal/*")
   for file in all_files:
      if cam_id in file and cfe(file, 1) == 1:
         print("cal FILE FOUND:", file)
         el = file.split("/")
         fn = el[-1]
         cal_p_file = file  + "/" + fn + "-stacked-calparams.json"
         if cfe(cal_p_file) == 1:
            matches.append(cal_p_file)
         else:
            cal_p_file = file  + "/" + fn + "-calparams.json"
         #   print("CAL P FILE PROBS:", cal_p_file)
         if cfe(cal_p_file) == 1:
            matches.append(cal_p_file)
 
   td_sorted_matches = []

   for match in matches:
      (t_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(match)
      tdiff = (capture_date-t_datetime).total_seconds()
      td_sorted_matches.append((match,f_date_str,tdiff))

   temp = sorted(td_sorted_matches, key=lambda x: x[2], reverse=False)
   return(temp)

