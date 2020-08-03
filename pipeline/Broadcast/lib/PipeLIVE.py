'''

   functions for enabling various forms of live streaming

'''

import os
import glob
from lib.DEFAULTS import *
from lib.PipeUtil import convert_filename_to_date_cam, cfe, load_json_file, save_json_file

#/usr/bin/ffmpeg -i /mnt/ams2/HD/2020_07_30_23_57_23_000_010003.mp4 -vcodec libx264 -crf 30 -vf 'scale=1280:720' -y test.mp4


def meteor_min_files(day, json_conf):
   year, month, dom = day.split("_")
   meteor_dir = METEOR_ARC_DIR + year + "/" + month + "/" + dom + "/"  
   hd_files = glob.glob("/mnt/ams2/HD/" + year + "_" + month + "_" + dom + "*")

   live_dir = ARC_DIR + "LIVE/" 
   #print(meteor_dir)
   meteor_files = glob.glob(meteor_dir + "*.json")
   print(meteor_files)
   for meteor_file in meteor_files:
      print(meteor_file)
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
