import requests
import shutil
import json
from lib.PipeUtil import load_json_file, save_json_file
import numpy as np
import sys
import os
import cv2
from Classes.ASAI import AllSkyAI

class ReviewNetwork():
   def __init__(self):
      print("Review Network Meteors")
      self.ASAI = AllSkyAI()
      self.ASAI.load_all_models()
      self.local_event_dir = "/mnt/f/EVENTS"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS"
      self.cloud_dir = "/mnt/archive.allsky.tv/"
      self.learning_repo = "/mnt/f/AI/DATASETS/NETWORK_PREV/"


   def review_meteors(self,date,auto=True):
      self.year, self.month, self.day = date.split("_")
      self.date = date
      self.local_evdir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day  + "/"
      self.cloud_evdir = self.cloud_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/"
      self.all_obs_file = self.local_evdir + date + "_ALL_OBS.json"
      self.obs_review_file = self.local_evdir + date + "_OBS_REVIEWS.json"
      self.min_events = self.local_evdir + date + "_MIN_EVENTS.json"
      self.obs_img_dir = self.local_event_dir + "/" + self.year + "/" + self.month + "/" + self.day   + "/OBS/"

      #self.learning_repo_yes = self.obs_img_dir + "/METEOR/"
      #self.learning_repo_no = self.obs_img_dir + "/NON_METEOR/"

      self.learning_repo_yes = self.learning_repo + "/METEOR/"
      self.learning_repo_no = self.learning_repo + "/NON_METEOR/"

      if os.path.exists(self.learning_repo_yes) is False:
         os.makedirs(self.learning_repo_yes)
      if os.path.exists(self.learning_repo_no) is False:
         os.makedirs(self.learning_repo_no)


      if os.path.exists(self.obs_img_dir) is False:
         os.makedirs(self.obs_img_dir) 

      if os.path.exists(self.obs_review_file) is True:
         review_data = load_json_file(self.obs_review_file)
      else:
         review_data = {}

      if os.path.exists(self.min_events) is True:
         min_events = load_json_file(self.min_events)
      else:
         min_events = {}
      self.ms_obs = {}
      for minute in min_events:
         for ev_id in min_events[minute]:
            if len(set(min_events[minute][ev_id]['stations'])) > 1:
               for i in range(0,len(min_events[minute][ev_id]['stations'])):
                  st_id = min_events[minute][ev_id]['stations'][i]
                  fn = min_events[minute][ev_id]['files'][i]
                  self.ms_obs[fn] = min_events[minute][ev_id]

      for k in self.ms_obs:
         print(k)

      try:
         all_obs = load_json_file(self.all_obs_file)
      except:
         return()
      all_obs = sorted(all_obs, key=lambda x: x['station_id'] + "_" + x['sd_video_file'])
      #for i in range(0, len(all_obs)):
      i = 0
      go = True
      cloud_files = {}
      while go is True:
         if i >= len(all_obs):
            go = False
            break
         obs = all_obs[i]
         st_id = obs['station_id']
         if st_id not in cloud_files:
            if os.path.exists(self.cloud_dir + st_id + "/METEORS/" + self.year + "/" + self.date + "/"):
               cloud_files[st_id] = os.listdir(self.cloud_dir + st_id + "/METEORS/" + self.year + "/" + self.date + "/")
               print( cloud_files[st_id])
            else:
               cloud_files[st_id] = []




         sd_vid = obs['sd_video_file']
         if "roi" in obs:
            roi = obs['roi']
         else:
            roi = [0,0,0,0]
         if "meteor_frame_data" in obs:
            mfd = obs['meteor_frame_data']
         else:
            mfd = []

         prev_file = self.obs_img_dir + sd_vid.replace(".mp4", "-prev.jpg")

         if sd_vid in review_data:
            print("skipping", i)
            i = i + 1
            continue

         cloud_prev_file = self.cloud_dir + st_id + "/METEORS/" + self.year + "/" + self.date + "/" + st_id + "_" + sd_vid.replace(".mp4", "-prev.jpg")
         cloud_prev_fn = st_id + "_" + sd_vid.replace(".mp4", "-prev.jpg")
         print("GO:", go, i, sd_vid, cloud_prev_file)
         fns = [row[1] for row in obs['meteor_frame_data']]
         print("FNS:", fns)


         #if os.path.exists(cloud_prev_file) is False:

         if cloud_prev_fn not in cloud_files[st_id]:
            review_data[sd_vid] = ["NO_CLOUD_FILE",[0,0,0,0]]
            print("NO CLOUD FILE", cloud_prev_file)
            i = i + 1
            continue

         cloud_prev_url = cloud_prev_file.replace("/mnt/", "https://")

         if os.path.exists(prev_file) is False:
            try:
               res = requests.get(cloud_prev_url, stream=True)
            except:
               continue
            if res.status_code == 200:
               with open(prev_file,'wb') as f:
                  shutil.copyfileobj(res.raw, f)
                  print('Image sucessfully Downloaded: ',prev_file, cloud_prev_url)
               img = cv2.imread(prev_file)
               print(img.shape)
            else:
               print('Image Couldn\'t be retrieved')
               continue
         else:
            print("READ EXISTING PREV FILE?")
            img = cv2.imread(prev_file)

         #img = cv2.imread(cloud_prev_file)
         bimg = cv2.resize(img, (1920,1080))

         try:
            x1,y1,x2,y2 = self.mfd_roi(mfd)
         except:
            x1,y1,x2,y2 = 0,0,0,0
            gray = cv2.cvtColor(bimg, cv2.COLOR_BGR2GRAY)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
            x1,x2 = mx,mx
            y1,y2 = my,my
      

         aix = int((x1 + x2) / 2)
         aiy = int((y1 + y2) / 2)
         aix1 = int(aix - (224/2))
         aix2 = int(aix + (224/2))
         aiy1 = int(aiy - (224/2))
         aiy2 = int(aiy + (224/2))
         if aix1 < 0:
            aix1 = 0
            aix2 = 224
         if aiy1 < 0:
            aiy1 = 0
            aiy2 = 224
         if aix1 >= 1920:
            aix1 = 1919 - 224 
            aix2 = 1919 
         if aiy1 >= 1080:
            aiy1 = 1079 - 224 
            aiy2 = 1079 
         print(st_id, sd_vid, roi, obs.keys())
         if i % 10 == 0:
            save_json_file(self.obs_review_file, review_data)

         if True:
            print(cloud_prev_file)
            sx1 = int(aix1 / 6)
            sy1 = int(aiy1 / 6)
            sx2 = int(aix2 / 6)
            sy2 = int(aiy2 / 6)
            learn_img = img[sy1:sy2,sx1:sx2]

            ai_roi_str = "AI_" + str(aix1) + "_" + str(aiy1) + "_" + str(aix2) + "_" + str(aiy2)

            learn_fn = st_id + "_" + sd_vid.replace(".mp4", ai_roi_str + ".jpg")

            bimg = cv2.rectangle(bimg, (aix1,aiy1), (aix2, aiy2) , (128, 255, 255), 1)
            if sd_vid in review_data:
               if len(review_data[sd_vid]) == 2:
                  label,roi = review_data[sd_vid]
               else:
                  label = review_data[sd_vid]
               if label == "NON_METEOR":
                  cv2.putText(bimg, label,  (aix1,aiy2), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,0,255), 1)
               else:
                  cv2.putText(bimg, label,  (aix1,aiy2), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)


            print("SAVE PREV:", prev_file)
            cv2.imwrite(prev_file, img)
            #learn_img = cv2.resize(learn_img,(64,64))

            root_fn = prev_file.split("/")[-1]
            roi_file = "tmp.jpg" 

            print("SAVE ROI:", roi_file)
            cv2.imwrite(roi_file, learn_img)

            oimg=None
            roi = [aix1,aiy1,aix2,aiy2]

            obs_id = st_id + "_" + sd_vid.replace(".mp4", "")
            if obs_id in self.ms_obs:
               multi_station = True
            else:
               multi_station = False

            if sd_vid not in review_data:
               review_data[sd_vid] = {}
            if "ai" not in review_data[sd_vid]:
               result = self.ASAI.meteor_yn(root_fn,roi_file,oimg,roi)
               result['learn_fn'] = learn_fn
               review_data[sd_vid]['ai'] = result
               review_data[sd_vid]['roi'] = [aix1,aiy1,aix2,aiy2]

            result['multi_station'] = multi_station

            if "meteor" in result['mc_class'] or (result['meteor_yn_confidence'] > 80 or result['meteor_fireball_yn_confidence'] > 80) or multi_station is True:
               label = "METEOR:" + result['mc_class'] + " / " + str(round(result['meteor_yn_confidence'],1)) + "% Meteor " + str(round(result['meteor_fireball_yn_confidence'],1)) + "% Fireball"
               cv2.putText(bimg, label,  (aix1,aiy2), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)
               save_dir = self.learning_repo_yes
            else:
               label = "NON_METEOR:" + result['mc_class'] + " / " + str(round(result['meteor_yn_confidence'],1)) + "% Meteor " + str(round(result['meteor_fireball_yn_confidence'],1)) + "% Fireball"
               cv2.putText(bimg, label,  (aix1,aiy2), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,0,255), 1)
               save_dir = self.learning_repo_no

            print(result)
            cv2.imshow('pepe', bimg)
            cv2.imshow('pepe2', learn_img)
            print("SM IMG:", learn_img.shape)
            if "human_label" not in review_data[sd_vid]:
               auto = True
            else:
               auto = False
            
            if auto is False:
               key = cv2.waitKeyEx(0)
               print("KEY:", key)
               if key == 65363:
                  # Right  
                  i = i + 1
               if key == 65361:
                  # Left
                  i = i - 1
               if key == 65364:
                  # Down 
                  review_data[sd_vid]['human_label'] = "NON_METEOR"
                  #,[aix1,aiy1,aix2,aiy2]]
                  save_dir = self.learning_repo_no
                  cv2.imwrite(save_dir + learn_fn, learn_img)
                  i = i + 1
                  print(save_dir + learn_fn)
               if key == 65362:
                  # Down 
                  save_dir = self.learning_repo_yes
                  review_data[sd_vid]['human_label'] = "METEOR"
                  #review_data[sd_vid] = ["METEOR",[aix1,aiy1,aix2,aiy2]]
                  i = i + 1
                  cv2.imwrite(save_dir + learn_fn, learn_img)
                  print(save_dir + learn_fn)
               if key == 115:
                  save_json_file(self.obs_review_file, review_data)
            else:
               i = i + 1
               print("**** SAVING: ****", save_dir + learn_fn)
               cv2.imwrite(save_dir + learn_fn, learn_img)

               if multi_station is False:
                  key = cv2.waitKey(30)

               else:
                  print("MULTI_STATION!")
                  print(self.ms_obs[obs_id])
                  key = cv2.waitKeyEx(30)
                  print("\n\n\n ******************* KEY:",key, "\n\n\n")
                  if key == 110:
                     review_data[sd_vid]['human_label'] = "NON_METEOR"
                  if key == 109:
                     review_data[sd_vid]['human_label'] = "METEOR"



   def mfd_roi(self, mfd):
      xs = [row[2] for row in mfd]
      ys = [row[3] for row in mfd]
      cx = np.mean(xs)
      cy = np.mean(ys)
      min_x = min(xs)
      max_x = max(xs)
      min_y = min(ys)
      max_y = max(ys)
      print("MFD AREA:", min_x, min_y, max_x, max_y)
      print("xs", xs)
      print("ys", ys)
      w = max_x - min_x
      h = max_y - min_y
      print("DIM:", w,h)
      if w > h:
         roi_size = int(w * 1.25)
      else:
         roi_size = int(h * 1.25)
      print(roi_size)

      x1 = int(cx - int(roi_size/2))
      x2 = int(cx + int(roi_size/2))
      y1 = int(cy - int(roi_size/2))
      y2 = int(cy + int(roi_size/2))
      print("HD ROI:", x1,y1,x2,y2)
      roi_w = x2 - x1
      roi_h = y2 - y1
      print("HD ROI W/H:", roi_w, roi_h)
      if roi_w != roi_h:
         print("HD ROI PROBLEM? W/H SHOULD BE THE SAME?")
         if roi_w < roi_h:
            roi_size = roi_w
         else:
            roi_size = roi_h
      else:
         roi_size = roi_w
      if roi_size > 1070:
         print("METEOR IS TOO BIG TO MAKE AN ROI!")
         hd_roi = [0,0,1920,1080]
         return(hd_roi)
      # check if the ROI BOX extends offframe
      off_frame = self.check_off_frame(x1,y1,x2,y2,1920,1080)
      if len(off_frame) > 0:
         x1,y1,x2,y2 = self.fix_off_frame(x1,y1,x2,y2,1920,1080, off_frame)
      return(x1,y1,x2,y2)
      
      
      
   def check_off_frame(self,x1,y1,x2,y2,w,h):
      off_frame = []

      print("check_off_frame", x1,y1,x2,y2,w,h)
      if x1 < 0:
         print("X1 < 0")
         off_frame.append('left')
      if x2 > w - 1:
         print("X2 > W", x2, w)
         off_frame.append('right')
      if y1 < 0:
         print("Y1 < 0")
         off_frame.append('top')
      if y2 > h - 1:
         print("Y2 > H", y2, h)
         off_frame.append('bottom')
      print("OFF FRAME:", off_frame)
      return(off_frame)
