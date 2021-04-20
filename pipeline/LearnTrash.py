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


def remake_learning_index():
   L_DIR = "/mnt/ams2/LEARNING/NON_METEORS/" 
   ldb = load_json_file(L_DIR + "trash.json")
   years = glob.glob(L_DIR + "*")
   for year_dir in years:
      if cfe(year_dir, 1) == 1:
         M_DIR = year_dir + "/VIDS/"
         learning_files = glob.glob(M_DIR + "*.mp4")
         print(year_dir, len(learning_files))
         for lfile in learning_files:
            lfn, ldir = fn_dir(lfile)
            day = lfn[0:10]
            mjv = "/mnt/ams2/trash/" + day + "/" + lfn 
            mjf = mjv.replace(".mp4", ".json")
            if lfn in ldb:
               print("Trash is in the index already.")
            else:
               print("Trash is not in the index.", mjf)
               if cfe(mjf) == 1:
                  mj = load_json_file(mjf)
                  if "best_meteor" in mj:
                     print("BEST METEOR FOUND.")
                     ldb[lfn] = {}
                     ldb[lfn]['ofns'] = mj['best_meteor']['ofns']
                     ldb[lfn]['xs'] = mj['best_meteor']['oxs']
                     ldb[lfn]['ys'] = mj['best_meteor']['oys']
                     ldb[lfn]['ws'] = mj['best_meteor']['ows']
                     ldb[lfn]['hs'] = mj['best_meteor']['ohs']
                     ldb[lfn]['oint'] = mj['best_meteor']['oint']
                     ldb[lfn] = get_crop_info(mjv, ldb[lfn])
                     if SHOW == 1:
                        stack_file = mjv.replace(".mp4", "-stacked.jpg")
                        print("NEW DATA:", ldb[lfn]) 
                        img = cv2.imread(stack_file)
                        img = cv2.resize(img, (640,360))
                        cx1,cy1,cx2,cy2 = ldb[lfn]['crop_360']
                        cv2.rectangle(img, (cx1, cy1), (cx2,cy2), (255, 255, 255), 1)
                        #cv2.imshow('pepe',img)
                        #cv2.waitKey(30)
   save_json_file(L_DIR + "trash.json", ldb)
     
   
def get_crop_info(vid, ldb_row):
   vw,vh,br,tf = ffprobe(vid)
   vw,vh,br,tf = int(vw),int(vh),int(br),int(tf)
   ldb_row['ffprobe'] = [vw,vh,br,tf]
   hdm_x_360 = 640 / vw
   hdm_y_360 = 360 / vh
   ox_360 = []
   oy_360 = []
   ow_360 = []
   oh_360 = []
   for i in range(0,len(ldb_row['xs'])):
      ox_360.append(int(ldb_row['xs'][i]*hdm_x_360))
      oy_360.append(int(ldb_row['ys'][i]*hdm_y_360))
      ow_360.append(int(ldb_row['ws'][i]*hdm_x_360))
      oh_360.append(int(ldb_row['hs'][i]*hdm_y_360))
      ox_360.append(int(ldb_row['xs'][i]*hdm_x_360) + int(ldb_row['ws'][i]*hdm_x_360))
      oy_360.append(int(ldb_row['ys'][i]*hdm_y_360) + int(ldb_row['hs'][i]*hdm_y_360))


   bw, bh = best_crop_size(ldb_row['xs'], ldb_row['ys'], vw,vh)
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

   # fix crop if it is out of bounds
   print("BEFORE CX:", cx1,cy1,cx2,cy2)
   if cx1 <= 0:
      cw = cx2 - cx1
      cx1 = 0 
      cx2 = cx1 + cw
   if cy1 <= 0:
      ch = cy2 - cy1
      cy1 = 0 
      cy2 = cy1 + ch
   if cx2 >= 640:
      cw = cx2 - cx1
      cx1 = 640 - cw
      cx2 = cx1 + cw
   if cy2 >= 360:
      ch = cy2 - cy1
      cy1 = 360 - ch
      cy2 = cy1 + ch

   ldb_row['crop_360'] = [cx1,cy1,cx2,cy2]
   ldb_row['crop_dim'] = [bw,bh]
   return(ldb_row) 


def update_dataset():
   # sync data with deleted meteors etc
   year = "2021"
   L_DIR = "/mnt/ams2/LEARNING/NON_METEORS/" 
   if cfe(L_DIR + year, 1) == 0:
      os.makedirs(L_DIR)
   vids = glob.glob(L_DIR + year + "/VIDS/*.mp4")
   for vid in vids:
      fn, dir = fn_dir(vid)
      md = fn[0:10]
      mf = "/mnt/ams2/trash/" + md + "/" + fn
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


def make_meteor_learning_dataset(day_wild):
   # clip all meteor videos and drop into learning dir
   L_DIR = "/mnt/ams2/LEARNING/NON_METEORS/"
   if day_wild is None:
      mdirs = sorted(glob.glob("/mnt/ams2/trash/*"), reverse=True)
   else:
      mdirs = sorted(glob.glob("/mnt/ams2/trash/" + day_wild + "*"), reverse=True)
   learning_db_file = L_DIR + "trash.json"
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
            ldb = add_trash_to_ldb(js, ldb)
   save_json_file(learning_db_file, ldb)

def add_trash_to_ldb(js, ldb, force=0):
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

               outfile = "/mnt/ams2/LEARNING/NON_METEORS/" + year + "/VIDS/" + fn
               outdir = "/mnt/ams2/LEARNING/NON_METEORS/" + year + "/VIDS/" 
               cdir = "/mnt/ams2/LEARNING/NON_METEORS/" + year + "/CROPS/" 
               idir = "/mnt/ams2/LEARNING/NON_METEORS/" + year + "/IMGS/" 
               if cfe(outdir, 1) == 0:
                  os.makedirs(outdir)
                  os.makedirs(cdir)
                  os.makedirs(idir)

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
               if force == 1:
                  make_vid = 1
                  make_crop = 1
                  make_cs = 1
                  make_lsf = 1

               print("FILE:", learning_vid, crop_file, crop_stack, lsf)
               print("FILE:", make_vid, make_crop, make_cs, make_lsf)

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
                  stack_img = stack_frames(frames, 1, None, "day")
                  print("FRAMES:", len(frames))
                  if stack_img is not None: 
                     cv2.imwrite(crop_stack, stack_img)
                  else:
                     print("failed to add, stack img bad.")
                     return() 
                  print("Saved stack crop:", crop_stack)
                  if SHOW == 1:
                     cv2.imshow('pepe', stack_img)
                     cv2.waitKey(30)
               if make_lsf == 1:
                  print(learning_vid)
                  frames = load_frames_simple(learning_vid)
                  print(len(frames))
                  if len(frames) >= 0:
                     stack_img_full = stack_frames(frames, skip = 1, resize=None, sun_status="day")
                     stack_img_full = cv2.resize(stack_img_full, (640,360))
                     cv2.imwrite(lsf, stack_img_full)

   return(ldb)  

def learning_menu():
   menu = """
      1) Add trash to Learning Data Set
      2) Purge deleted trash from Learning Data Set
      3) Remake trash.json index file 
   """
   print(menu)
   selected = input("Select function #")
   if selected == "1":
      day_wild = input("Select date, or date wildcard (YYYY_MM, YYYY) or blank for all dates")
      if day_wild == "":
         day_wild = None
      make_meteor_learning_dataset(day_wild) 

   if selected == "2":
      update_dataset()
   if selected == "3":
      remake_learning_index()

print(len(sys.argv))


if len(sys.argv) == 1:
   learning_menu()
   #make_meteor_learning_dataset()
else: 
   cmd = sys.argv[1]
   if len(sys.argv) > 2:
      file = sys.argv[2]
   if cmd == "update":
      update_dataset()
   if cmd == "add":
      L_DIR = "/mnt/ams2/LEARNING/NON_METEORS/"
      learning_db_file = L_DIR + "trash.json"
      if cfe(learning_db_file) == 1:
         ldb = load_json_file(learning_db_file)
      else: 
         ldb = {}
      ldb = add_trash_to_ldb(file, ldb, 1)
      save_json_file(learning_db_file, ldb)
