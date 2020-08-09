'''

   functions for enabling various forms of live streaming

'''
import time
import random
import os
import glob
from lib.DEFAULTS import *
from lib.PipeUtil import convert_filename_to_date_cam, cfe, load_json_file, save_json_file, check_running
import datetime
from datetime import datetime as dt

#/usr/bin/ffmpeg -i /mnt/ams2/HD/2020_07_30_23_57_23_000_010003.mp4 -vcodec libx264 -crf 30 -vf 'scale=1280:720' -y test.mp4

def get_random_cam(json_conf):
   cam_ids = []
   for cam in json_conf['cameras']:
      ci = json_conf['cameras'][cam]
      cam_ids.append(ci['cams_id'])
   rand_id = random.randint(0, len(cam_ids) - 1)
   return(cam_ids[rand_id])

def broadcast_minutes(json_conf):


   running = check_running("Process.py bcm")
   if running >= 3:
      print("Already running.")
      return()


   LIVE_CLOUD_MIN_DIR = LIVE_MIN_DIR.replace("ams2/meteor_archive", "archive.allsky.tv")
   if cfe(LIVE_CLOUD_MIN_DIR, 1) == 0:
      os.makedirs(LIVE_CLOUD_MIN_DIR)

   if cfe(LIVE_MIN_DIR, 1) == 0:
      os.makedirs(LIVE_MIN_DIR)

   # copy the broadcast file!
   os.system("git pull")
   #os.system("cp /mnt/archive.allsky.tv/LIVE/BROADCAST/broadcast.json ./broadcast.json") 
   bc = load_json_file("./broadcast.json" )
   for event in bc:
      name = event['name']
      start = event['start']
      end = event['end']
      start_time = dt.strptime(start, "%Y_%m_%d_%H_%M_%S") 
      end_time = dt.strptime(end, "%Y_%m_%d_%H_%M_%S") 
      now = dt.now()
      if start_time <= now <= end_time:
         print("The broadcast is running!")
         this_event = event
      else:
         print("There is no broadcast!")
         return()

   for vp in this_event['video_providers']:
      if vp['ams_id'] == STATION_ID:
         bid = vp['bid']
         operator = vp['operator']
         location = vp['location']
         text = operator + " " + location
         upload_mins = []
         for i in range(0,60):
            match = 0
            for b in bid:
               print(i, b)
               if i < 10:
                  if i == b:
                     upload_mins.append(i)
               else:
                  mm = str(i)[1]
                  if str(b) == str(mm):
                     upload_mins.append(i)


   print("Upload these minutes from the last 2 hours (if not already done)!", upload_mins)
   last_hour_dt = dt.now() - datetime.timedelta(hours=1)
   last_hour_string = last_hour_dt.strftime("%Y_%m_%d_%H_5")
   this_hour_string = now.strftime("%Y_%m_%d_%H")
   print("Last 2 hours: ", this_hour_string, last_hour_string)
   cam_id = None
   cam_id = get_random_cam(json_conf)
   min_files = get_min_files(cam_id, this_hour_string, last_hour_string, upload_mins)
   print(min_files)

   new = 0
   for file in min_files:
      fn = file.split("/")[-1]
      el = fn.split("_") 
      wild = el[0] + "_" + el[1] + "_" + el[2] + "_" + el[3] + "_" + el[4] + "*"
      check = glob.glob(LIVE_MIN_DIR + wild)
      #print(LIVE_MIN_DIR + wild, check)
      if len(check) == 0:
         minify_file(file, LIVE_MIN_DIR, text)
         new = new + 1
      else:
         print("We already made a file for this minute.")
   if new > 0:
      rsync(LIVE_MIN_DIR + "*", LIVE_CLOUD_MIN_DIR )
   

def rsync(src, dest):
   cmd = "/usr/bin/rsync -v --ignore-existing " + src + " " + dest
   print(cmd)
   os.system(cmd)

def minify_file(file, outdir, text):
   start_time = time.time()
   fn = file.split("/")[-1]
   outfile = outdir + fn
   if cfe(outfile) == 0:

         #/usr/bin/ffmpeg -i """ + file + """ -vcodec libx264 -crf 35 -vf 'scale=1280:720', drawtext="fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf: text='""" + text + """': fontcolor=white: fontsize=24: box=1: boxcolor=black@0.5: boxborderw=5: x=(10): y=(h-text_h)-10" -vf "drawtext=expansion=strftime: basetime=$(date +%s -d'2013-12-01 12:00:00')000000: text='%H\\:%S\\:%S'" """ + outfile 
      #03\:05\:00\:00
      fn = file.split("/")[-1]
      el = fn.split("_")
      y = el[0] 
      mo = el[1] 
      d = el[2] 
      h = el[3] 
      m = el[4] 
      s = el[5] 
      date_txt = "UTC " + y + "/" + mo + "/" + d
      text += " " + date_txt + "_" 
      timecode = h + "\\:" + m + "\\:" + s + "\\:00"
      #timecode = h + "\\:" + m + "\\:" + s 
      cmd = """
         /usr/bin/ffmpeg -i """ + file + """ -vcodec libx264 -crf 35 -vf "scale='1280:720', drawtext=fontfile='fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf':text='""" + text + """ ':box=1: boxcolor=black@0.5: boxborderw=5:x=20:y=h-lh-1:fontsize=16:fontcolor=white:shadowcolor=black:shadowx=1:shadowy=1:timecode='""" + timecode + """':timecode_rate=25" """ + outfile  
#+ " >/dev/null 2>&1"


      print(cmd)
      os.system(cmd)
   elapsed_time = time.time() - start_time 
   print("TIME TO MINIFY FILE:", elapsed_time)

        

def get_min_files(cam_id, this_hour_string, last_hour_string, upload_mins):
   now = dt.now()
   bc_clips = []
   files = glob.glob("/mnt/ams2/HD/" + this_hour_string + "*" + cam_id + "*.mp4")
   for file in sorted(files):

      (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(file)
      elp = now - f_datetime
      sec = elp.total_seconds()
   
      if "trim" not in file and sec > 120:
         el = file.split("_")
         min = el[4]
         print(min, file)
         if int(min) in upload_mins:
            bc_clips.append(file)
   if True:
      files = glob.glob("/mnt/ams2/HD/" + last_hour_string + "*" + cam_id + "*.mp4")
      for file in sorted(files):
       
         if "trim" not in file:
            el = file.split("_")
            min = el[4]
            print(min, file)
            if int(min) in upload_mins:
               bc_clips.append(file)
   return(bc_clips)

def cat_videos(in_wild, outfile):

   files = glob.glob(in_wild)
   list_file = outfile.replace(".mp4", "-ALL.txt")
   list = ""
   for file in sorted(files):
      if "ALL" not in file:
         list += "file '" + file + "'\n"
   fp = open(list_file, "w")
   fp.write(list)
   fp.close()
   cmd = "/usr/bin/ffmpeg -f concat -safe 0 -i " +list_file + " -c copy -y " + outfile
   print(cmd)
   os.system(cmd)

def purge_deleted_live_files (live_dir, live_cloud_dir, day):

   cloud_files = glob.glob(live_cloud_dir + "*.mp4")
   live_meteors = glob.glob(live_dir + day + "*.mp4")
   meteor_dir = "/mnt/ams2/meteors/" + day + "/" 
   print("METEOR DIR:", meteor_dir)
   detected_meteors = glob.glob(meteor_dir + day + "*.mp4")
   for lm in live_meteors:
      fn = lm.split("/")[-1]
      dmf = meteor_dir + fn
      if dmf not in detected_meteors:
         print("DELETE LIVE FILE (it doesn't exist in meteor dir:\n" )
         print("LIVE FILE:", lm)
         print("DETECT FILE:", dmf)
         cloud_file = live_cloud_dir + fn
         print("CLOUD FILE:", cloud_file)
         cmd = "rm " + lm 
         print(cmd)
         os.system(cmd)
         if cloud_file in cloud_files:
            print("NEED TO DELETE THE CLOUD FILE!")
            cmd = "rm " + cloud_file 
            print(cmd)
            os.system(cmd)
         else:
            print("FILE IS NOT ON CLOUD!")
      else:
         print("\nSTILL GOOD:", lm, "\n")

def meteors_last_night(json_conf, day=None):
   # sync best meteors within the last 48 hours to the LIVE meteor dir
   station_id = json_conf['site']['ams_id']
   if "extra_text" in json_conf['site']:
      text = "AMSMeteors.org / " + json_conf['site']['extra_text']
   else: 
      text = "AMSmeters.org " 
   best_meteors = []
   LAST_NIGHT_DIR = ARC_DIR + "LIVE/METEORS_LAST_NIGHT/"
   LIVE_METEOR_DIR = ARC_DIR + "LIVE/METEORS/"

   LAST_NIGHT_CLOUD_DIR = LIVE_METEOR_DIR.replace("ams2/meteor_archive", "archive.allsky.tv")
   LIVE_CLOUD_METEOR_DIR = LIVE_METEOR_DIR.replace("ams2/meteor_archive", "archive.allsky.tv")

   if cfe(LAST_NIGHT_CLOUD_DIR,1) == 0:
      os.makedirs(LAST_NIGHT_CLOUD_DIR)
   if cfe(LIVE_CLOUD_METEOR_DIR,1) == 0:
      os.makedirs(LIVE_CLOUD_METEOR_DIR)
   

   if cfe(LIVE_METEOR_DIR,1) == 0:
      os.makedirs(LIVE_METEOR_DIR)
   if cfe(LAST_NIGHT_DIR,1) == 0:
      os.makedirs(LAST_NIGHT_DIR)
   if day is None:
      now = dt.now()
      day = now.strftime("%Y_%m_%d")
   else:   
      now = datetime.strptime(day, "%Y_%m_%d")

   yesterday = now - datetime.timedelta(days = 1) 
   yest = yesterday.strftime("%Y_%m_%d")

   mdir = "/mnt/ams2/meteors/" + day + "/"

   purge_deleted_live_files (LIVE_METEOR_DIR, LIVE_CLOUD_METEOR_DIR, day)
   purge_deleted_live_files (LIVE_METEOR_DIR, LIVE_CLOUD_METEOR_DIR, yest)

   files = glob.glob(mdir + "*.json")
   for file in sorted(files):
      js = load_json_file(file)
      if len(js['sd_objects'][0]['history']) > 5:
         print(file)
         best_meteors.append(js['hd_trim'])

   mdir = "/mnt/ams2/meteors/" + yest + "/"
   files = glob.glob(mdir + "*.json")
   for file in sorted(files):
      js = load_json_file(file)
      if len(js['sd_objects'][0]['history']) > 5:
         print(file)
         best_meteors.append(js['hd_trim'])
   for bm in best_meteors:
      print(bm)
      minify_file(bm, LIVE_METEOR_DIR, text)
   cat_videos(LIVE_METEOR_DIR + day + "*", LAST_NIGHT_DIR + day + "-" + station_id  + ".mp4")
   cat_videos(LIVE_METEOR_DIR + yest + "*", LAST_NIGHT_DIR + yest + "-" + station_id + ".mp4")

   rsync(LIVE_METEOR_DIR + "*", LIVE_CLOUD_METEOR_DIR )

   rsync(LAST_NIGHT_DIR + "*", LAST_NIGHT_CLOUD_DIR)

def meteor_min_files(day, json_conf):
   year, month, dom = day.split("_")
   meteor_dir = METEOR_ARC_DIR + year + "/" + month + "/" + dom + "/"  
   hd_files = glob.glob("/mnt/ams2/HD/" + year + "_" + month + "_" + dom + "*")

   live_dir = ARC_DIR + "LIVE/" 
   if cfe(live_dir, 1) == 0:
      os.makedirs(live_dir)
   #print(meteor_dir)
   meteor_files = glob.glob(meteor_dir + "*.json")
   for meteor_file in meteor_files:
      print(meteor_file)
      cp = load_json_file(meteor_file)
      print(cp)
      print("ANG:", cp['report']['classify']['ang_sep_px'], cp['report']['classify']['ang_sep_deg'])
      if cp['report']['classify']['ang_sep_px'] < 7:
         continue
      hd_file = get_hd_min_file(meteor_file, hd_files)
      if hd_file == 0:
         print("HD FILE NOT FOUND.", hd_file)
         return()

      mf =meteor_file.split("/")[-1] 
      el = mf.split("-trim")
      mf_root = el[0]
      hdf = hd_file.split("/")[-1]
      min_out_file = live_dir + hdf
      
      if cfe(min_out_file) == 0: 
         cmd = "/usr/bin/ffmpeg -i " + hd_file + " -vcodec libx264 -crf 35 -vf 'scale=1280:720' -y " + min_out_file
         os.system(cmd)
         print(cmd)

def get_hd_min_file(meteor_file, hd_files):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_file)
   search_str = fy + "_" + fm + "_" + fd + "_" + fh + "_" + fmin 
   for file in hd_files:
      if search_str in file and cam in file and "trim" not in file:
         return(file)


   print(search_str)
   if len(hd_files) == 1: 
      return(hd_files[0])
   if len(hd_files) > 1:
      for hdf in hd_files:
         if "trim" not in hdf:
            return(hdf)
   return(0)

def broadcast_live_meteors():
   LIVE_URL = "rtmp://a.rtmp.youtube.com/live2/"
   LIVE_KEY = "mg2f-1ub9-yehd-8h32-a3dh"
   live_files = {}
   live_dir = ARC_DIR + "LIVE/"
   live_files = update_live_files(live_dir, live_files)
   run = True
   lc = 0
   qc = 0
   tc = len(live_files.keys())
   while run == True:
      if qc == 0 or lc % 5 == 0:
         queue = build_queue(live_files) 
         save_json_file(live_dir + "livefiles.json", live_files)
         if len(queue) == 0:
            print("Oh no we have no files left in the queue :(")
            return()
      play_file = queue[0]
      broadcast_clip(play_file, LIVE_URL, LIVE_KEY)
      print("Play first movie in the queue:", play_file)
      live_files[play_file]['played'] = 1
      lc += 1 
   print(live_dir + "livefiles.json")

def build_queue(live_files):
   queue = []
   for lf in sorted(live_files.keys()):
      if live_files[lf]['played'] == 0:
         queue.append(lf)
   return(queue)

def update_live_files(live_dir, live_files):
   lfs = glob.glob(live_dir + "*.mp4")
   for lf in lfs:
      if lf not in live_files:
         live_files[lf] =  {"played": 0}
   return(live_files)

def broadcast_clip(SOURCE, URL, KEY):
   
   #YOUTUBE_URL="rtmp://a.rtmp.youtube.com/live2/cvep-ehuy-9tg5-737j"  # URL de base RTMP youtube
   #FB_URL="rtmps://live-api-s.facebook.com:443/rtmp/10157538776313530?s_bl=1&s_ps=1&s_sml=3&s_sw=0&s_vt=api-s&a=AbxBjTySKHROyaX9"
   #SOURCE="rtsp://192.168.76.74/user=admin&password=&channel=1&stream=0.sdp"              # Source UDP (voir les annonces SAP)
   LIVE_URL = URL + KEY
   FPS = "25"
   VBR = "256k"
   QUAL= "fast"
   ffmpeg = """
    /usr/bin/ffmpeg -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero  \
    -i """ + SOURCE + """ -deinterlace -vf scale=1280:720 \
    -vcodec libx264 -pix_fmt yuv420p -preset fast -r 25 -g $((25 * 2)) -b:v """ + VBR  + """ \
    -acodec libmp3lame -ar 44100 -threads 6 -qscale 3 -b:a 712000 -bufsize 512k \
    -f flv """ +  LIVE_URL
   print(ffmpeg)
   os.system(ffmpeg)
