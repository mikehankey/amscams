#!/usr/bin/python3
from collections import defaultdict
from PIL import Image, ImageChops
import numpy as np
from pathlib import Path
import requests
import cv2
import os
import time
import datetime
import sys
from collections import deque

import json

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)




sd_video_dir = json_conf['site']['sd_video_dir']
hd_video_dir = json_conf['site']['hd_video_dir']

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
   print(outfile)
   cv2.imwrite(outfile, frame)  

   outfile = sd_video_dir + "../latest/" + str(cams_id) + "-mask.jpg"
   cap = cv2.VideoCapture("rtsp://" + cam_ip + sd_url)
   cv2.setUseOptimized(True)
   _ , frame = cap.read()
   print(outfile)
   cv2.imwrite(outfile, frame)  



cam_num = sys.argv[1]

get_latest_pic(cam_num)
