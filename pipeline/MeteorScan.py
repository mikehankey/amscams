#!/usr/bin/python3

# this script will scan a single meteor dir or all meteor dirs 
# and for each meteor it will run the AI image predict on the stack image.
# it will compile a list of files and results in each dir called AMSXX_YYYY_MM_DD_AI_SCAN.info
#

import numpy as np
import sys
from lib.PipeUtil import load_json_file, save_json_file , mfd_roi, get_file_info, calc_dist
import os
import cv2
from lib.ASAI_Predict import predict_images
import glob
import tensorflow as tf
import os
from tensorflow import keras
from tensorflow.keras.models import *
import tensorflow.keras
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img

from Classes.MLMeteors import MLMeteors
from Classes.ASAI import AllSkyAI 
from Classes.ASAI_Detect import ASAI_Detect 
from lib.FFFuncs import ffprobe
if os.name == "nt":
   windows = True
   root_dir = "Y:/"
else:
   windows = False 
   root_dir = "/mnt/ams2/"

def make_first_frame(video_file):
   cap = cv2.VideoCapture(video_file)
   grabbed , frame = cap.read()
   return(frame)


def save_video_frames(frames, out_file, width,height ):
   #height, width = frames[0].shape[:2]
   fourcc = cv2.VideoWriter_fourcc(*'X264')
   out = cv2.VideoWriter(out_file, fourcc, 25, (width,height))
   for frame in frames:
      frame = cv2.resize(frame,(width,height))
      out.write(frame)
   out.release()
   print("Saved ", out_file)

def save_crop_video(in_file, out_file, x1,y1,x2,y2,width,height ):
   w = x2 - x1
   h = y2 - y1
   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x1) + ":" + str(y1)

   cmd = "/usr/bin/ffmpeg -i " + in_file + " -filter:v \"" + crop + "\" -y " + out_file + " > /dev/null 2>&1"

   os.system(cmd)

   #height, width = frames[0].shape[:2]
   print("Saved ", out_file)



def eval_frame_data(frame_data):
   #frame_data.append(int(fn), int(cm), int(nomo), int(avg), int(np.sum(sub_roi)), float(factor), cnts))
   dists = []
   last_cx = None
   last_cy = None
   fns = []
   cxs = []
   cys = []
   for fd in frame_data:
      cnts = fd[6]
      print("FD", fd)
      fn = fd[0]
      for x,y,w,h,ii,mv in cnts:
         fns.append(fn) 
         cx = x + (w/2)   
         cy = y + (h/2)   
         cxs.append(cx)
         cys.append(cy)
         if last_cx is not None:
            #print("LAST DIST:", cx, cy, last_cx, last_cy) 
            last_dist = calc_dist((cx,cy),(last_cx,last_cy))
         else:
            last_dist = 0
         last_cx = cx
         last_cy = cy
         dists.append(last_dist)


   elp = len(fns)
   if len(fns) >= 3:
      fns_dif = fns[-1] - fns[0]
   else:
      fns_dif = 1
   if elp > 0:
      elp_fns = fns_dif / elp
   else:
      elp_fns = 9999
   if len(cxs) >= 2:
      total_dist = calc_dist((min(cxs), min(cys)), (max(cxs), max(cys)))
   else:
      total_dist = 1

   dists = dists[1:]
   if len(fns) > 0:
      dist_per_fn = total_dist / len(fns)
   else:
      dist_per_fn = 0
   med_dist = np.median(dists)
   print("DISTS:", dists)
   agree = 0
   disagree = 0
   for dd in dists:
      ddd = abs(dd - med_dist)
      print("DDD:", ddd, dd, med_dist)
      if ddd < 3:
         agree += 1
      else:
         disagree += 1

   mscore = 0
   if len(dists) > 0:
      ag_perc = agree / len(dists)
   else:
      ag_perc = 0

   if med_dist <= 0:
      mscore -= 1
   if med_dist > 4:
      mscore += 1


   if ag_perc > .7:
      mscore += 1
   if ag_perc < .5:
      mscore -= 1

   if total_dist < 2:
      mscore -= 1
   else :
      mscore -= 1

   if dist_per_fn < 2:
      mscore -= 1
   else:
      mscore += 1

   if len(fns) < 3:
      mscore -= 1
   else:
      mscore += 1

   if elp_fns > 1.5:
      mscore -= 1
   if elp_fns == 1:
      mscore += 1

   print("MED DISTS:", np.median(dists))
   print("DIST AGREE:", agree, "/", len(dists))
   print("TOTAL DIST:", total_dist)
   print("FNS:", fns)
   print("MSCORE:", mscore)
   resp = {}
   if len(cxs) > 1:
      print("DIST PER FN:", total_dist/ len(cxs))
      print("ELP_FNS:", ((fns[-1] - fns[0])+1) / len(fns))
      resp['med_dist'] = np.median(dists)
      resp['agree_perc'] = agree / len(dists)
      resp['dist_per_fn'] = total_dist / len(cxs)
   else:
      resp['med_dist'] = 0 
      resp['agree_perc'] = 0
      resp['dist_per_fn'] = 0

   resp['total_dist'] = total_dist 
   resp['elp_fns'] = elp_fns
   resp['mscore'] = mscore
   resp['fns'] = fns 
   resp['cxs'] = fns 
   resp['cys'] = fns 
   return(resp)

def scan_meteors_for_day(station_id, date):
   make_movie = False
   if os.name == "nt":
      windows = True
      root_dir = "Y:/"
   else:
      windows = False 
      root_dir = "/mnt/ams2/"

   ASAI = AllSkyAI()
   AID = ASAI_Detect()
   mc_model = AID.load_my_model("multi_class_model.h5")

   ASAI.load_all_models()
   MLM = MLMeteors()
   msdir = root_dir + "METEOR_SCAN/" + date + "/" 
   mfiles, roi_files, non_reduced_files, ai_data, ai_data_file = MLM.load_meteors_for_day(date, station_id)
   ms_data_file = ai_data_file.replace("AI_SCAN", "MS_DATA")

   learning_meteor_dir = root_dir + "datasets/meteor_yn/" 
   if os.path.exists(learning_meteor_dir) is False:
      os.makedirs(learning_meteor_dir)

   print("ROI FILES:", len(roi_files))
   print("NON REDUCED METEORS:", len(non_reduced_files))
   print("AI DATA:", len(ai_data.keys()))
   print("AI DATA KEYS:", ai_data.keys())


   for mfile in mfiles:
      show_frames = []
      if mfile not in ai_data:
         print("MFILE NOT IN METEOR SCAN DATA YET!", mfile)
         ai_data[mfile] = {}
         ai_data[mfile]['rois'] = []
      else:
         if "meteor_found" in ai_data[mfile]:
            print("SKIP DONE THIS ALREADY", mfile, "Meteor:", ai_data[mfile]['meteor_found'])
            continue
      mdir = root_dir + "meteors/" + mfile[0:10] + "/"
      sd_video_file = mdir + station_id + "_" + mfile
      stack_file = mdir + mfile.replace(".mp4", "-stacked.jpg")

      #img = cv2.imread(stack_file)
      detect_img, roi_imgs, roi_vals = AID.detect_in_stack(stack_file, mc_model)

      ai_resp = []
      cc = 0
      show_stack = cv2.imread(stack_file)
      show_stack = cv2.resize(show_stack,(1920,1080))
      frames = None
      meteor_found = False
      ric = 0
      for rimg in roi_imgs:
         resp = ASAI.meteor_yn(None, rimg)
         x1, y1, x2, y2 = roi_vals[cc]
         roi_fn = mfile.replace(".mp4", "-RX_")
         roi_fn = roi_fn + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2) + ".jpg"
         x1,y1,x2,y2 = ASAI.bound_cnt(x1,y1,x2,y2,show_stack, margin=.5)
         if frames is None:
            frames, roi_frames, roi_sub_frames, frame_data = AID.make_roi_video(mdir + mfile, x1,y1,x2,y2, frames=None)
         else:
            frames, roi_frames, roi_sub_frames, frame_data = AID.make_roi_video(mdir + mfile, x1,y1,x2,y2, frames)
         # Now what do we do with this ROI INFO???
         eval_report = eval_frame_data(frame_data)

         resp['frame_data'] = frame_data
         resp['roi'] = [x1,y1,x2,y2]
         resp['motion_eval'] = eval_report
         cv2.rectangle(show_stack, (x1,y1), (x2, y2) , (255, 255, 255), 1)
         descs,color = ASAI.format_response(resp)

         ai_data[mfile]['rois'].append(resp)
         ai_data[mfile]['rois'].append((x1,y1,x2,y2,resp))
         print("RESP:", resp)

         if len(eval_report['fns']) < 10 and eval_report['mscore'] >= 3 :
            looper = 3
            detect_color = (0,255,0)
         else:
            looper = 1
            detect_color = (128,128,255)
         if resp['meteor_yn'] is True or resp['meteor_fireball_yn'] is True or "meteor" in resp['mc_class']: 
            looper = 3
            detect_color = (0,255,0)
         if eval_report['mscore'] < 2 :
            looper = 1
            detect_color = (128,128,255)

         #final_confidence
         #final_meteor_yn
         final_confidence = "med"
         final_meteor_yn = "non_meteor"
         if resp['mc_class'] == 'fireflies':
            # reassign unless the month is 6 - 8 and the station is a Firefly station (1,7,9,15,41,42,48)
            resp['mc_class'] = 'meteor_bright'

         # Decide final meteor_yn status and confidence
         # Case 1 for meteor yes
         if (resp['meteor_yn'] is True or resp['meteor_fireball_yn'] is True) and "meteor" in resp['mc_class'] and eval_report['mscore'] >= 2: 
            # highest possible confidence this is a meteor!
            final_confidence = "high" 
            final_meteor_yn = "meteor" 
         if (resp['meteor_yn'] is True or resp['meteor_fireball_yn'] is True) and "meteor" in resp['mc_class'] and eval_report['mscore'] < 2: 
            # medium possible confidence this is a meteor!
            final_confidence = "med"
            final_meteor_yn = "meteor" 
         if (resp['meteor_yn'] is False and resp['meteor_fireball_yn'] is False) and "meteor" not in resp['mc_class'] and eval_report['mscore'] >= 3: 
            # highest possible confidence this is Not  meteor!
            final_confidence = "med"
            final_meteor_yn = "meteor" 
         if (resp['meteor_yn'] is True or resp['meteor_fireball_yn'] is True) and "meteor" not in resp['mc_class'] and eval_report['mscore'] >= 3: 
            # highest possible confidence this is Not  meteor!
            final_confidence = "med"
            final_meteor_yn = "meteor" 
         if (resp['meteor_yn'] is True or resp['meteor_fireball_yn'] is True ) and "meteor" in resp['mc_class'] and eval_report['mscore'] <= 2: 
            # highest possible confidence this is Not  meteor!
            final_confidence = "med"
            final_meteor_yn = "meteor" 

         # Case 2 for meteor no 

         if (resp['meteor_yn'] is False and resp['meteor_fireball_yn'] is False) and "meteor" not in resp['mc_class'] and eval_report['mscore'] < 2: 
            # highest possible confidence this is Not  meteor!
            final_confidence = "high"
            final_meteor_yn = "non_meteor" 


         if (resp['meteor_yn'] is False and resp['meteor_fireball_yn'] is False) and "meteor" not in resp['mc_class'] and eval_report['mscore'] == 2: 
            # highest possible confidence this is Not  meteor!
            final_confidence = "med"
            final_meteor_yn = "non_meteor" 
         if (resp['meteor_yn'] is True or resp['meteor_fireball_yn'] is True ) and "meteor" not in resp['mc_class'] and eval_report['mscore'] <= 1: 
            # highest possible confidence this is Not  meteor!
            final_confidence = "high"
            final_meteor_yn = "non_meteor" 
         if (resp['meteor_yn'] is False and resp['meteor_fireball_yn'] is False ) and "meteor" not in resp['mc_class'] and eval_report['mscore'] == 2: 
            # highest possible confidence this is Not  meteor!
            final_confidence = "med"
            final_meteor_yn = "non_meteor" 
         if (resp['meteor_yn'] is False and resp['meteor_fireball_yn'] is False) and "meteor" in resp['mc_class'] and eval_report['mscore'] <= 2: 
            # med possible confidence this is Not  meteor!
            final_confidence = "med"
            final_meteor_yn = "non_meteor" 

         if final_meteor_yn == "meteor":
            meteor_found = True
            detect_color = (0,255,0)
         else:
            detect_color = (128,128,255)
         cv2.rectangle(show_stack, (x1,y1), (x2, y2) , (detect_color), 4)


         ai_data[mfile]['meteor_yn_final'] = final_meteor_yn
         ai_data[mfile]['meteor_yn_confidence'] = final_confidence
         print("FINAL METEOR YN:", final_meteor_yn)
         if final_meteor_yn == "meteor": 
            learn_dir = root_dir + "datasets/meteor_yn/" + final_confidence + "/meteor/"
            roi_video_dir = root_dir + "datasets/meteor_yn/roi_vids/" + "/meteor/"
         else:
            learn_dir = root_dir + "datasets/meteor_yn/" + final_confidence + "/non_meteor/"
            roi_video_dir = root_dir + "datasets/meteor_yn/roi_vids/" + "/non_meteor/"

         if os.path.exists(roi_video_dir) is False:
            os.makedirs(roi_video_dir)

         learn_file = learn_dir + station_id + "_" + roi_fn
         roi_video_file = roi_video_dir + station_id + "_" + roi_fn.replace(".jpg", ".mp4")
         save_video_frames(roi_frames, roi_video_file, 180,180)
         #save_crop_video(sd_video_file, roi_video_file, x1,y1,x2,y2,180,180)
         print("Saved.", roi_video_file)
         
         if os.path.exists(learn_dir) is False:
            os.makedirs(learn_dir)
         print("Saving:", learn_file)
         rimg = cv2.resize(rimg,(180,180))
         cv2.imwrite(learn_file, rimg)
         
         desc4 = final_meteor_yn + " - " + final_confidence
         if y2 < 1080/2:
            cv2.putText(show_stack, descs[0],  (x1, y2+20 ), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.putText(show_stack, descs[1],  (x1, y2+40), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.putText(show_stack, "MScore:"+ str(eval_report['mscore']),  (x1, y2+60), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.putText(show_stack, desc4,  (x1, y2+80), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
         else:
            cv2.putText(show_stack, descs[0],  (x1, y1-80 ), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.putText(show_stack, descs[1],  (x1, y1-60), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.putText(show_stack, "MScore:"+ str(eval_report['mscore']),  (x1, y1-40), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)
            cv2.putText(show_stack, desc4,  (x1, y1-20), cv2.FONT_HERSHEY_SIMPLEX, .6, detect_color, 1)

         if ric < 2 and make_movie is True:
            for ll in range(0,looper):
               for fn in eval_report['fns']:
                  show_frame = show_stack.copy()

                  cv2.rectangle(show_frame, (x1,y1), (x2, y2) , (detect_color), 3)
                  show_frame[y1:y2,x1:x2] = roi_frames[fn]
                  show_frame = cv2.resize(show_frame,(640,360))

                  cv2.imshow('pepe', show_frame)
                  cv2.waitKey(30)
         ric += 1
         cc += 1
      show_stack = cv2.resize(show_stack,(1280,720))

      if os.path.exists(root_dir + "datasets/meteor_yn/marked_stacks/meteor/") is False:
         try:
            os.makedirs(root_dir + "datasets/meteor_yn/marked_stacks/meteor/")
         except:  
            print("???")
      if os.path.exists(root_dir + "datasets/meteor_yn/marked_stacks/non_meteor/") is False:
         try:
            os.makedirs(root_dir + "datasets/meteor_yn/marked_stacks/non_meteor/")
         except:  
            print("???")

      if meteor_found is True:
         marked_stack_file = root_dir + "datasets/meteor_yn/marked_stacks/meteor/" + station_id + "_" + mfile.replace(".mp4", "-marked.jpg")
      else:
         marked_stack_file = root_dir + "datasets/meteor_yn/marked_stacks/non_meteor/" + station_id + "_" + mfile.replace(".mp4", "-marked.jpg")
      cv2.imwrite(marked_stack_file, show_stack)

      ai_data[mfile]['meteor_found'] = meteor_found
      cv2.imshow('pepe', show_stack)
      cv2.waitKey(60)

   #save_json_file(ms_data_file, ai_data)
   save_json_file(ai_data_file, ai_data)
   #print("MSDATA:", ms_data_file)
   print("AIDATA:", ai_data_file)

   return(ai_data)

   for mfile in non_reduced_files:
      print(mfile)
      mdir = root_dir + "meteors/" + mfile[0:10] + "/"
      stack_file = mdir + mfile.replace(".json", "-stacked.jpg")
      img = cv2.imread(stack_file)
      detect_img, detect_cnts = AID.detect_in_stack(stack_file, mc_model)
      print("DETECT INFO:", detect_cnts)
      cv2.imshow('pepe', img)
      cv2.waitKey(0)

      ai_data[mfile] = {} 

   for roi_f in roi_files:
      roi_fn = roi_f.split("/")[-1]
      #print(key, ai_data[key])
      roi_file = msdir + roi_fn 
      img = cv2.imread(roi_file)
      resp = ASAI.meteor_yn(None, img)
      if roi_fn not in ai_data:
         ai_data[roi_fn] = {}
      ai_data[roi_fn]['classes'] = resp
      print(roi_f, resp)
      print(ai_data[roi_fn])
      if resp is not None: 
         if resp['meteor_yn'] is True:
            desc = "Meteor "  + str((1 - resp['meteor_yn_confidence']) * 100)[0:4] + "%"
            color = (0,255,0)
         else:
            desc = "Non Meteor "  + str((1 - resp['meteor_yn_confidence']) * 100)[0:4] + "%"
            color = (0,0,255)
         if resp['meteor_fireball_yn'] is True:
            desc = "Fireball Meteor "  + str((1 - resp['meteor_fireball_yn_confidence']) * 100)[0:4] + "%"
            color = (0,255,0)
         desc2 = resp['mc_class']
         desc2 += " " + str(resp['mc_confidence']) + "%"
         cv2.putText(img, desc,  (0, img.shape[0]-30), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
         cv2.putText(img, desc2,  (0, img.shape[0]-20), cv2.FONT_HERSHEY_SIMPLEX, .3, color, 1)

      if "human_label" in  ai_data[roi_fn]:
         desc3 = "Human: " + ai_data[roi_fn]['human_label']
      else:
         desc3 = "not reviewed."
      cv2.putText(img, desc3,  (0, img.shape[0]-10), cv2.FONT_HERSHEY_SIMPLEX, .3, (128,255,255), 1)

      try:
         cv2.imshow('pepe', img)
         cv2.waitKey(0)
      except:
         print("Problem with image:", roi_file)
   
   print("saved:", ai_data_file)
   save_json_file(ai_data_file, ai_data)
json_conf = load_json_file("../conf/as6.json")
meteor_dir = root_dir + "meteors/"

station_id = json_conf['site']['ams_id']
date = sys.argv[1]
if date != "ALL":
   scan_meteors_for_day(station_id, date)
else:
   all_dirs = os.listdir(meteor_dir)
   for date in sorted(all_dirs, reverse=True):
      print(date)
      if os.path.isdir(meteor_dir + date) is True:
         scan_meteors_for_day(station_id, date)
