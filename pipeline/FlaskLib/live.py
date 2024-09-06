from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template
import cv2
import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir
import random
import json

random_number = random.random()
json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)

sd_video_dir = json_conf['site']['sd_video_dir']
hd_video_dir = json_conf['site']['hd_video_dir']

def live_view(amsid ):
  
   json_conf = load_json_file("../conf/as6.json")
   template = make_default_template(amsid, "live.html", json_conf)
   out = "Images updates once per 15-minutes, <a id='loadLink' href=?update=1>Click to update now</a>.<br>"
   for cam in json_conf['cameras']:
      cam_id = json_conf['cameras'][cam]['cams_id']
      late_url = "/mnt/ams2/latest/" + cam_id + ".jpg"
      vlate_url = late_url.replace("/mnt/ams2", "")
      out += "<img width=640 height=360 src=" + vlate_url + "?" + str(random_number) + ">"
   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def live_view_update(amsid):
   for cam_num in json_conf['cameras']:
      num = cam_num.replace("cam", "")
      print(num)
      get_latest_pic(num)
   template = live_view(amsid)
   return(template)

def get_latest_pic(cam_num):
   cam_key = 'cam' + str(cam_num)
   cam_ip = json_conf['cameras'][cam_key]['ip']
   sd_url = json_conf['cameras'][cam_key]['sd_url']
   hd_url = json_conf['cameras'][cam_key]['hd_url']
   cams_id = json_conf['cameras'][cam_key]['cams_id']


   outfile = sd_video_dir + "../latest/" + str(cams_id) + ".jpg"

   print("rtsp://" + cam_ip + hd_url)
   cap = cv2.VideoCapture("rtsp://" + cam_ip + hd_url)
   cv2.setUseOptimized(True)
   _ , frame = cap.read()
   cv2.imwrite(outfile, frame)

   outfile = sd_video_dir + "../latest/" + str(cams_id) + "-mask.jpg"
   cap = cv2.VideoCapture("rtsp://" + cam_ip + sd_url)
   cv2.setUseOptimized(True)
   _ , frame = cap.read()
   cv2.imwrite(outfile, frame)
