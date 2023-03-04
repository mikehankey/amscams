#!/usr/bin/python3
import numpy as np
import cv2
from lib.PipeUtil import load_json_file
import os
import datetime 


def close_all_cams(caps, hd_caps):
   for cam_num in caps:
      print(cam_num)
      caps[cam_num].release()
      hd_caps[cam_num].release()


def connect_cam(con_dict, cam_num, url):
   if cam_num in con_dict:
      con_dict[cam_num].release()
   else:
      con_dict[cam_num] = cv2.VideoCapture(url)
   return(con_dict)



hd_w = 1920
hd_h = 1080 
sd_w = 640
sd_h = 360
max_rows = hd_w / sd_w
max_cols = hd_h / sd_h

#print(max_rows, max_cols)

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

vimg = np.zeros((1080,1920,3),dtype=np.uint8)
blank = np.zeros((1080,1920,3),dtype=np.uint8)



# load up URLs & grid files
urls = {}
hd_urls = {}
grids = {}
rc = 0
cc = 0
img_map = {}
caps = {}
hd_caps = {}
fails = {}
for cam_num in json_conf['cameras']:
   c = int(cam_num.replace("cam", ""))
   x1 = cc * sd_w 
   x2 = x1 + sd_w 
   y1 = rc * sd_h 
   y2 = y1 + sd_h 
   img_map[cam_num] = x1,y1,x2,y2

   print(cam_num, x1, y1, x2, y2, rc, cc)
   cam_ip = json_conf['cameras'][cam_num]['ip']
   sd_url = json_conf['cameras'][cam_num]['sd_url']
   hd_url = json_conf['cameras'][cam_num]['hd_url']
   cam_id = json_conf['cameras'][cam_num]['cams_id']
   grid_file = "/mnt/ams2/cal/plots/" + station_id + "_" + cam_id + "_GRID.jpg"
   if os.path.exists(grid_file) is True:
      gimg = cv2.imread(grid_file)
      grids[cam_num] = {}
      grids[cam_num]['hd'] = gimg
      grids[cam_num]['sd'] = cv2.resize(gimg, (640,360))

   stream_url = "rtsp://" + cam_ip + sd_url
   hd_stream_url = "rtsp://" + cam_ip + hd_url
   urls[cam_num] = stream_url
   hd_urls[cam_num] = hd_stream_url
   cc += 1
   if cc >= max_cols :
      cc = 0
      rc += 1

   caps[cam_num] = cv2.VideoCapture(urls[cam_num])
   hd_caps[cam_num] = cv2.VideoCapture(hd_urls[cam_num])

now = datetime.datetime.now()
primary_cam_num = None
show_grid = False
wc = 0
cv2.namedWindow("ALLSKY")
cv2.resizeWindow("ALLSKY", 1920, 1080)
while True:
   vimg = np.zeros((1080,1920,3),dtype=np.uint8)

   last_now = now
   now = datetime.datetime.now()
   elp = (now - last_now).total_seconds()
   now_dt = now.strftime("%Y_%m_%d %H:%M:%S")
   if primary_cam_num is None:
      for cam_num in urls:
         x1,y1,x2,y2 = img_map[cam_num] 
         grabbed , frame = caps[cam_num].read()
         try:
            frame = cv2.resize(frame, (640,360))
         except:
            frame = np.zeros((360,640,3),dtype=np.uint8)
            print("GET FRAME FAILED FOR CAM!", cam_num)
            if cam_id not in fails:
               fails[cam_id] = 1
            else:
               fails[cam_id] += 1
            if fails[cam_id] == 25:
               print("RECONNECTING CAM!", fails[cam_id], "FAILES FOR", cam_id)
               fails[cam_id] = 0
               caps = connect_cam(caps, cam_num, urls[cam_num])

         if show_grid is True:
            blend = cv2.addWeighted(frame, .8, grids[cam_num]['sd'], .2, .3)
         else:
            blend = frame
         vimg[y1:y2,x1:x2] = blend
   fps = int(1 / elp)
   if primary_cam_num is None:
      # display all cams
      cv2.imshow('ALLSKY', vimg)
   else:
      # display just 1 cam in full HD
      pk = "cam" + str(primary_cam_num)
      hd_grabbed , hd_frame = hd_caps[pk].read()
      if show_grid is True:
         blend = cv2.addWeighted(hd_frame, .8, grids[pk]['hd'], .2, .3)
      else:
         blend = hd_frame
      vimg = blend
      cv2.imshow('ALLSKY', vimg)
   key = cv2.waitKey(20)


   if key > 0 :
      print("KEY", key, "KEY")
   if key == 27 :
      # esc
      close_all_cams(caps, hd_caps)
      print("exit", key)
      cv2.destroyAllWindows()
      exit()
   if 49 <= key <= 57:
      # 1 camera zoom
      primary_cam_num = key - 48
   if key == 97:
      # show all cams
      print(key)
      primary_cam_num = None
   if key == 103:
      #toggle_grid
      if show_grid is False:
         show_grid = True
      else:
         show_grid = False
   if wc % 2 == 0:
      print("FPS:", primary_cam_num, fps)

   wc += 1

