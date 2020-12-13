#!/usr/bin/python3
import glob
import os
import sys
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir
from lib.FFFuncs import resize_video, best_crop_size, ffprobe, crop_video
import cv2
from lib.PipeImage import stack_frames
from lib.PipeVideo import load_frames_simple 

SHOW = 0

def update_dataset():
   # sync data with deleted meteors etc
   year = "2020"
   L_DIR = "/mnt/ams2/LEARNING/METEORS/" 
   vids = glob.glob(L_DIR + year + "/VIDS/*.mp4")
   for vid in vids:
      fn, dir = fn_dir(vid)
      md = fn[0:10]
      mf = "/mnt/ams2/meteors/" + md + "/" + fn
      if cfe(mf) == 0:
         print("ORIG METEOR NO LONGER FOUND!", fn, mf)
         crop = vid.replace("VIDS", "CROPS")
         crop = crop.replace(".mp4", "-crop-360p.mp4")
         imgs = vid.replace("VIDS", "IMGS")
         imgs = imgs.replace(".mp4", "*")
         cmd = "rm " + vid
         print(cmd)
         os.system(cmd)
         cmd = "rm " + crop
         os.system(cmd)
         print(cmd)
         cmd = "rm " + imgs
         os.system(cmd)
         print(cmd)


def make_meteor_learning_dataset():
   # clip all meteor videos and drop into learning dir
   L_DIR = "/mnt/ams2/LEARNING/METEORS/"
   mdirs = glob.glob("/mnt/ams2/meteors/*")
   learning_db_file = L_DIR + "meteors.json"
   if cfe(learning_db_file) == 0:
      ldb = {}
   else:
      ldb = load_json_file(learning_db_file)
   for md in sorted(mdirs, reverse=True):
      if cfe(md, 1) == 1:
         jss = glob.glob(md + "/*.json")
         for js in jss:
            if "reduced" in js or "star" in js or "manual" in js or "import" in js or "archive" in js or "events" in js:
               continue
            ldb = add_meteor_to_ldb(js, ldb)
   save_json_file(learning_db_file, ldb)

def add_meteor_to_ldb(js, ldb, force=0):
   if True:
      if True:
         if True:
            mj = load_json_file(js)
            if mj == 0:
               return(ldb) 
            vid = js.replace(".json", ".mp4")
            if "best_meteor" in mj:
               bm = mj['best_meteor']
               min_x = min(bm['oxs'])
               max_x = max(bm['oxs'])
               min_y = min(bm['oys'])
               max_y = max(bm['oys'])
               ff = min(bm['ofns']) - 1
               lf = max(bm['ofns']) + 3
               fn, dir = fn_dir(vid) 
               year = fn[0:4] 

               outfile = "/mnt/ams2/LEARNING/METEORS/" + year + "/VIDS/" + fn
               learning_vid = outfile
               lsf = outfile.replace("VIDS", "IMGS")
               lsf = lsf.replace(".mp4", "-stacked.jpg")
               crop_file = outfile.replace("VIDS", "CROPS")
               crop_file = crop_file.replace(".mp4", "-crop-360p.mp4")
               crop_stack = crop_file.replace(".mp4", "-stacked.jpg")
               crop_stack = crop_stack.replace("CROPS", "IMGS")
               make_vid = 0
               make_crop = 0
               make_lsf = 0
               make_cs = 0
               lfn , dx = fn_dir(learning_vid)
               if lfn not in ldb:
                  ldb[lfn] = {}
               if "vw" not in ldb[lfn]:
                  vw,vh,br,tf = ffprobe(vid)
                  vw,vh,br,tf = int(vw),int(vh),int(br),int(tf)
                  ldb['ffprobe'] = [vw,vh,br,tf]
               else:
                  vw,vh,br,tf = ldb['ffprobe']
                  vw,vh,br,tf = int(vw),int(vh),int(br),int(tf)

               if vw == 0 or vh == 0:
                  lbd[lfn]['error'] = "video is bad."
                  return(ldb) 

               if cfe(learning_vid) == 0:
                  make_vid = 1
               if cfe(crop_file) == 0:
                  make_crop = 1
               if cfe(crop_stack) == 0:
                  make_cs = 1
               if cfe(lsf) == 0:
                  make_lsf = 1
                  make_lsf = 0
               if force == 1:
                  make_vid = 1
                  make_crop = 1
                  make_cs = 1
                  #make_lsf = 1

               if make_vid == 1:
                  trim_cmd = "./FFF.py splice_video " + vid + " " + str(ff) + " " + str(lf) + " " + outfile + " frame"  
                  os.system(trim_cmd)
                  print(trim_cmd)

                  outfile_lr = outfile.replace(".mp4", "-temp.mp4")
                  resize_video(outfile, outfile_lr, 640, 360, 27) 
                  os.system("mv " + outfile_lr + " " + outfile)
               if "crop_360" not in ldb[lfn] or "oxs" not in ldb[fn]:
                  hdm_x_360 = 640 / vw
                  hdm_y_360 = 360 / vh
                  ox_360 = []
                  oy_360 = []
                  ow_360 = []
                  oh_360 = []
                  for i in range(0,len(bm['oxs'])):
                     ox_360.append(int(bm['oxs'][i]*hdm_x_360))
                     oy_360.append(int(bm['oys'][i]*hdm_y_360))
                     ow_360.append(int(bm['ows'][i]*hdm_x_360))
                     oh_360.append(int(bm['ohs'][i]*hdm_y_360))
                     ox_360.append(int(bm['oxs'][i]*hdm_x_360) + int(bm['ows'][i]*hdm_x_360))
                     oy_360.append(int(bm['oys'][i]*hdm_y_360) + int(bm['ohs'][i]*hdm_y_360))

                  if "oxs" not in ldb[lfn]:
                     ldb[lfn]['ofns'] = bm['ofns']
                     ldb[lfn]['xs'] = ox_360
                     ldb[lfn]['ys'] = oy_360
                     ldb[lfn]['ws'] = ow_360
                     ldb[lfn]['hs'] = oh_360
                     ldb[lfn]['oint'] = bm['oint']

                  bw, bh = best_crop_size(bm['oxs'], bm['oys'], vw,vh) 
                  min_x = min(ox_360)
                  min_y = min(oy_360)
                  max_x = max(ox_360)
                  max_y = max(oy_360)
                  cx = int((min_x + max_x) / 2)
                  cy = int((min_y + max_y) / 2)
                  #bw, bh = bc_size
                  cx1 = int(cx - (bw/2))
                  cx2 = int(cx + (bw/2))
                  cy1 = int(cy - (bh/2))
                  cy2 = int(cy + (bh/2))
                  ldb[lfn]['crop_360'] = [cx1,cy1,cx2,cy2]
                  ldb[lfn]['crop_dim'] = [bw,bh]

               if make_crop == 1:
                  sf = vid.replace(".mp4", "-stacked.jpg") 
                  img = cv2.imread(sf)
                  img = cv2.resize(img, (640,360))
                  cv2.rectangle(img, (min_x, min_y), (max_x,max_y), (255, 255, 255), 1)
                  cv2.rectangle(img, (cx1, cy1), (cx2,cy2), (255, 255, 255), 1)
                  crop_video(outfile, crop_file, [cx1,cy1,bw,bh])
                  cv2.imwrite("/mnt/ams2/test123.jpg", img)
                  if SHOW == 1:
                     cv2.imshow('pepe', img)
                     cv2.waitKey(30)
               if make_cs == 1:
                  frames = load_frames_simple(crop_file)
                  stack_img = stack_frames(frames, skip = 1, resize=None, sun_status="day")
                  cv2.imwrite(crop_stack, stack_img)
                  print("Saved stack crop:", crop_stack)
                  if SHOW == 1:
                     cv2.imshow('pepe', stack_img)
                     cv2.waitKey(30)
               if make_lsf == 1:
                  frames = load_frames_simple(learning_vid)
                  stack_img_full = stack_frames(frames, skip = 1, resize=None, sun_status="day")
                  stack_img_full = cv2.resize(stack_img_full, (640,360))
                  cv2.imwrite(lsf, stack_img_full)
            
   return(ldb)  
# PER METEOR LOOP HERE

print(len(sys.argv))
if len(sys.argv) == 1:
   make_meteor_learning_dataset()
else: 
   cmd = sys.argv[1]
   if len(sys.argv) > 2:
      file = sys.argv[2]
   if cmd == "update":
      update_dataset()
   if cmd == "add":
      L_DIR = "/mnt/ams2/LEARNING/METEORS/"
      learning_db_file = L_DIR + "meteors.json"
      if cfe(learning_db_file) == 1:
         ldb = load_json_file(learning_db_file)
      else: 
         ldb = {}
      ldb = add_meteor_to_ldb(file, ldb, 1)
      save_json_file(learning_db_file, ldb)
