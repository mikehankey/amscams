#!/usr/bin/python3
import glob
import os
import sys
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeAutoCal import fn_dir
from lib.FFFuncs import resize_video, best_crop_size, ffprobe, crop_video
import cv2
from lib.PipeImage import stack_frames
from lib.PipeVideo import load_frames_simple, load_frames_fast
from lib.PipeDetect import load_mask_imgs, get_contours_in_image, find_object, analyze_object
import numpy as np


SHOW = 0

def crop_vid(in_file, out_file, x,y,w,h):
   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)
   cmd = "/usr/bin/ffmpeg -i " + in_file + " -filter:v \"" + crop + "\" -y " + out_file + " > /dev/null 2>&1"
   os.system(cmd)

def make_trash_learning_dataset():
   # clip all trash videos and drop into learning dir
   L_DIR = "/mnt/ams2/LEARNING/NON_METEORS/"
   
   learning_db_file = L_DIR + "trash.json"
   if cfe(learning_db_file) == 0:
      ldb = {}
   else:
      ldb = load_json_file(learning_db_file)
   
   mdirs = sorted(glob.glob("/mnt/ams2/trash/*"), reverse=True)

   for md in sorted(mdirs, reverse=True):
      if cfe(md, 1) == 1:
        # get all sd files
        files = glob.glob(md + "/*.mp4")

        for file in files:
            if "HD" not in file and "tracking" not in file:
                # add trash to learning dir    
                ret = add_trash(file,ldb)
                if ret != ():
                    ldb = ret
        

   save_json_file(learning_db_file, ldb)

def add_trash(file, ldb):
    fn, dir = fn_dir(file) 
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
     
    # resize to standard sd
    outfile_lr = outfile.replace(".mp4", "-temp.mp4")
    resize_video(file, outfile_lr, 640, 360, 27) 
    os.system("mv " + outfile_lr + " " + outfile)
    
    # process trash
    objects = process_trash(file)
    ldb[file] = objects
    
    for obj_id in objects:
      objects[obj_id] = analyze_object(objects[obj_id])
      #print(objects[obj_id])
    
    # iterate through all found objects
    for obj_id in objects:
       # only continue if the algorithm thinks this is a meteor
       if objects[obj_id]['report']['meteor'] == 1:
          vw,vh,br,tf = ffprobe(file)
          print("VW:"+str(vw)+" VH:"+str(vh))
          vw,vh = int(vw),int(vh)
          
          hdm_x_360 = 640 / vw
          hdm_y_360 = 360 / vh
          
          ox_360 = []
          oy_360 = []

          for i in range(0,len(objects[obj_id]['oxs'])):
                ox_360.append(int(objects[obj_id]['oxs'][i]*hdm_x_360))
                oy_360.append(int(objects[obj_id]['oys'][i]*hdm_y_360))
          
          # get the corners of the object, scaled with the standard sd size to account for the previous resizing
          min_x = min(ox_360)
          max_x = max(ox_360) 
          min_y = min(oy_360)
          max_y = max(oy_360)  
          
          bw, bh = best_crop_size(objects[obj_id]['oxs'], objects[obj_id]['oys'], vw,vh)

          cx = int((min_x + max_x) / 2)
          cy = int((min_y + max_y) / 2)
          cx = int(cx - (bw/2))
          cy = int(cy - (bh/2))
          
          # crop file and save in CROPS dir
          crop_vid(outfile, crop_file.replace(".mp4", str(obj_id) + ".mp4"), cx,cy,bw,bh)
          
          # make stacked image and save in IMGS dir
          frames = load_frames_simple(crop_file.replace(".mp4", str(obj_id) + ".mp4"))
          stack_img = stack_frames(frames, 1, None, "day")
          print("FRAMES:", len(frames))
          if stack_img is not None: 
             cv2.imwrite(crop_stack.replace(".jpg", str(obj_id) + ".jpg"), stack_img)
          else:
             print("failed to add, stack img bad.")
             return() 

    
    return ldb


def process_trash(video_file):
    # load frames/sub frames and vals
    hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])

    # make dict
    objects = {}

    # set frame # start value
    fn = 0

    # Load masks to block out mask areas
    sd_mask_imgs = load_mask_imgs(json_conf)
    cam = (video_file.split("-trim",1)[0]).split("_")[-1]
    print(cam)
    mask = sd_mask_imgs[0][cam]

    if mask.shape[0] != subframes[0].shape[0]:
       mask = cv2.resize(mask, (subframes[0].shape[1], subframes[0].shape[0]))
    if len(mask.shape) == 3:
        mask = cv2.cvtColor(mask, cv2.COLOR_BGR2GRAY)


    bg_img = hd_frames[0]
    intense = []
    full_bg_avg = np.mean(bg_img)
    for frame in subframes:
       frame = cv2.subtract(frame, mask)
       min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(frame)
       thresh = max_val - 10
       if thresh < 10:
          thresh = 10
       if thresh > 10:
          thresh = 10
       _, threshold = cv2.threshold(frame, thresh, 255, cv2.THRESH_BINARY)
       cnts = get_contours_in_image(threshold)
       for x,y,w,h in cnts:
          if w < 2 or h < 2:
             continue
          cnt_img = hd_frames[fn][y:y+h,x:x+h]
          bg_cnt_img = bg_img[y:y+h,x:x+h]
          int_cnt = cv2.subtract(cnt_img, bg_cnt_img)
          cx = int(x + (w/2))
          cy = int(y + (h/2))
          cval = hd_frames[fn][cy,cx]
          oint = int(np.sum(int_cnt))
          avg_px_int = int(oint / (cnt_img.shape[0] * cnt_img.shape[1]))
          avg_bg_px = int(np.sum(bg_cnt_img) / (cnt_img.shape[0] * cnt_img.shape[1]))
          #print("INTENSITY:", fn, oint, avg_bg_px, cval, avg_px_int)
          # useful to see what is going on sometimes . print rectangles on cnts and show here if desired.
          #cv2.imshow('pepe', int_cnt)
          #cv2.waitKey(30)
          object, objects = find_object(objects, fn,x, y, w, h, oint, 0, 0, None)
       #cv2.imshow('pepe', frame)
       #cv2.waitKey(30)
       fn += 1

    found = 0

    return objects


if len(sys.argv) == 1:
    # load station json_conf
    json_conf = load_json_file("../conf/as6.json")
    
    make_trash_learning_dataset()
