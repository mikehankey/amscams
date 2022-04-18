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
   def __init__(self,ASAI=None):
      print("Review Network Meteors")
      if ASAI is None:
         self.ASAI = AllSkyAI()
         self.ASAI.load_all_models()
      self.local_event_dir = "/mnt/ams2/EVENTS"
      self.cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS"
      self.cloud_dir = "/mnt/archive.allsky.tv/"
      self.learning_repo = "/mnt/ams2/AI/DATASETS/NETWORK_PREV/"

   def get_stack_img_from_root_fn(self, root_fn):
      
      if "AMS" in root_fn:
         st = root_fn.split("_")[0]
         root_fn = root_fn.replace(st + "_", "")
      date = root_fn[0:10] 
      mdir = "/mnt/ams2/meteors/" + date + "/" 
      stack_file = mdir + root_fn + "-stacked.jpg"
      #json_file = mdir + root_fn + ".json"
      if os.path.exists(stack_file) is True:
         stack_img = cv2.imread(stack_file)
         stack_img = cv2.resize(stack_img,(1920,1080))  
      else:
         #stack_img = np.zeros((1080,1920),dtype=np.uint8) 
         stack_img = None
      print("STACK FILE:", stack_file) 
      return(stack_img)


   def review_meteors(self,date,auto=True):
      if os.path.exists(self.learning_repo + date + "/METEOR/") is False:
         os.makedirs(self.learning_repo + date + "/METEOR/")
      if os.path.exists(self.learning_repo + date + "/NON_METEOR/") is False:
         os.makedirs(self.learning_repo + date + "/NON_METEOR/")
      if os.path.exists(self.learning_repo + date + "/UNSURE/") is False:
         os.makedirs(self.learning_repo + date + "/UNSURE/")

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

      c = 0


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
            else:
               cloud_files[st_id] = []




         sd_vid = obs['sd_video_file']

         if sd_vid in review_data:
            if "objects" in review_data[sd_vid]:
               print("skipping already have objects in the review data.", i)
               i = i + 1
               continue


         print("AI SCANNING", i, sd_vid)
         root_fn = sd_vid.split("/")[-1].replace(".mp4", "")
         if "roi" in obs:
            roi = obs['roi']
         else:
            roi = [0,0,0,0]
         if "meteor_frame_data" in obs:
            mfd = obs['meteor_frame_data']
         else:
            mfd = []

         prev_file = self.obs_img_dir + sd_vid.replace(".mp4", "-prev.jpg")


         cloud_prev_file = self.cloud_dir + st_id + "/METEORS/" + self.year + "/" + self.date + "/" + st_id + "_" + sd_vid.replace(".mp4", "-prev.jpg")
         cloud_prev_fn = st_id + "_" + sd_vid.replace(".mp4", "-prev.jpg")
         fns = [row[1] for row in obs['meteor_frame_data']]

         if cloud_prev_fn not in cloud_files[st_id]:
            review_data[sd_vid] = ["NO_CLOUD_FILE",[0,0,0,0]]
            print("NO CLOUD FILE.")
            i = i + 1
            continue

         cloud_prev_url = cloud_prev_file.replace("/mnt/", "https://")
         if sd_vid not in review_data:
            review_data[sd_vid] = {}

         get_objects = False
         if "objects" not in review_data[sd_vid] and "ai" not in review_data[sd_vid]:
            get_objects = True
         elif review_data[sd_vid]['objects'] is None:
            get_objects = True
         else:
            continue

         if os.path.exists(prev_file) is False:
            try:
               res = requests.get(cloud_prev_url, stream=True)
            except:
               continue
            if res.status_code == 200:
               with open(prev_file,'wb') as f:
                  shutil.copyfileobj(res.raw, f)
               img = cv2.imread(prev_file)
            else:
               print('Image Couldn\'t be retrieved')
               continue
         else:
            img = cv2.imread(prev_file)
         
         #img = cv2.imread(cloud_prev_file)
         try:
            bimg = cv2.resize(img, (1920,1080))
         except:
            print("BAD IMG!", prev_file)
            i += 1
            #os.remove(prev_file)
            #exit()
            continue

         objects = self.detect_objects_in_stack(st_id, root_fn, img.copy())
         print("OBJECTS:", objects)
         print("REVIEW DATA:", review_data[sd_vid])
         if isinstance(review_data[sd_vid],  dict) is not True:
            review_data[sd_vid] = {}

         review_data[sd_vid]['objects'] = objects

         #input("PAUSED. [ENTER] TO CONT")
         try:
            x1,y1,x2,y2 = self.mfd_roi(mfd)
         except:
            # here we should search for top 10 bright spots 
            # until we find a meteor or give up. 
            # right now it is only looking for 1 spot! 
            x1,y1,x2,y2 = 0,0,0,0
            gray = cv2.cvtColor(bimg, cv2.COLOR_BGR2GRAY)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
            x1,x2 = mx,mx
            y1,y2 = my,my
      
         bimg = cv2.resize(img, (1920,1080))

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
         if i % 10 == 0:
            save_json_file(self.obs_review_file, review_data)

         if True:
            sx1 = int(aix1 / 6)
            sy1 = int(aiy1 / 6)
            sx2 = int(aix2 / 6)
            sy2 = int(aiy2 / 6)
            learn_img = img[sy1:sy2,sx1:sx2]

            ai_roi_str = "AI_" + str(aix1) + "_" + str(aiy1) + "_" + str(aix2) + "_" + str(aiy2)

            learn_fn = st_id + "_" + sd_vid.replace(".mp4", ai_roi_str + ".jpg")

            bimg = cv2.rectangle(bimg, (aix1,aiy1), (aix2, aiy2) , (128, 255, 255), 1)
            if sd_vid in review_data:
               if len(review_data[sd_vid]) == 2 and "objects" not in review_data[sd_vid]:
                  label,roi = review_data[sd_vid]
               else:
                  label = review_data[sd_vid]

            cv2.imwrite(prev_file, img)
            #learn_img = cv2.resize(learn_img,(64,64))

            root_fn = prev_file.split("/")[-1]
            roi_file = "tmp.jpg" 

            cv2.imwrite(roi_file, learn_img)

            oimg=None
            roi = [aix1,aiy1,aix2,aiy2]

            obs_id = st_id + "_" + sd_vid.replace(".mp4", "")
            if obs_id in self.ms_obs:
               multi_station = True
               desc = "MULTI STATION EVENT"
               cv2.putText(bimg, desc,  (800,50), cv2.FONT_HERSHEY_SIMPLEX, .8, (0,255,0), 1)
            else:
               multi_station = False


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
            

            show_img = cv2.resize(bimg,(1280,720))

            key = ""
            meteor_confirmed = False 
            non_meteor_confirmed = False 
            if key == 109:
               # meteor Y 
               save_dir = self.learning_repo_yes 
               meteor_confirmed = True
               review_data[sd_vid]['human_label'] = "METEOR"
               cv2.imwrite(save_dir + learn_fn, learn_img)
            if key == 110:
               # meteor N
               non_meteor_confirmed = True
               review_data[sd_vid]['human_label'] = "NON_METEOR"
               save_dir = self.learning_repo_no
               cv2.imwrite(save_dir + learn_fn, learn_img)

            if key == 115:
               # save json!
               save_json_file(self.obs_review_file, review_data)
            i = i + 1
      save_json_file(self.obs_review_file, review_data)
      
   def detect_objects_in_stack(self, station_id, root_fn, img):
      date = root_fn[0:10]
      objects = []
      show_img = img.copy()
      show_img = cv2.resize(img.copy(), (1920,1080))
      tn_img = cv2.resize(img.copy(), (320,180))
      iw = 320
      ih = 180
      if img.shape[0] != 1080:
         img = cv2.resize(img, (1920,1080))
      tries = 0
      if len(img.shape) == 3:
         gray = cv2.cvtColor(tn_img, cv2.COLOR_BGR2GRAY)
      else:
         gray = img
      tn_size = 38
      while tries < 10:
         if True:
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
            pxd = max_val - np.mean(gray)
            if pxd < 10:
               # not enough Pixel Diff between brightest and avg 
               tries += 1
               continue
            x1,x2 = mx,mx
            y1,y2 = my,my
            aix = int((x1 + x2) / 2)
            aiy = int((y1 + y2) / 2)
            aix1 = int(aix - (tn_size/2))
            aix2 = int(aix + (tn_size/2))
            aiy1 = int(aiy - (tn_size/2))
            aiy2 = int(aiy + (tn_size/2))
            if aix1 < 0:
               aix1 = 0
               aix2 =tn_size 
            if aiy1 < 0:
               aiy1 = 0
               aiy2 = tn_size 
            if aix1 >= iw:
               aix1 = iw - 1 - tn_size 
               aix2 = iw 
            if aiy1 >= ih:
               aiy1 = ih - 1 - tn_size
               aiy2 = ih
            gray[aiy1:aiy2,aix1:aix2] = 0
            hdm_x = 1920 / 320
            hdm_y = 1080 / 180
            roi_img = tn_img[aiy1:aiy2,aix1:aix2] 
            if roi_img.shape[0] != roi_img.shape[1]:
               continue 

            roi = [int(aix1*hdm_x),int(aiy1*hdm_y),int(aix2*hdm_x),int(aiy2*hdm_y)]
            roi_file = "test.jpg"
            cv2.imwrite("test.jpg", roi_img)
   
            meteor_prev_yn = self.ASAI.meteor_prev_yn(roi_img)

            aix1,aiy1,aix2,aiy2 = roi
            show_img = cv2.rectangle(show_img, (aix1-2,aiy1-2), (aix2+2, aiy2+2) , (128, 255, 255), 1)
            #result = self.score_met_ai(result)
            save_fn = station_id + "_" + root_fn + str(aix1) + "_" + str(aiy1) + "_" + str(aix2) + "_" + str(aiy2) + ".jpg"
            if meteor_prev_yn >= 80:
               save_file = self.learning_repo + date + "/METEOR/" + save_fn
            elif meteor_prev_yn <= 50:
               save_file = self.learning_repo + date + "/NON_METEOR/" + save_fn 
            else:
               save_file = self.learning_repo + date + "/UNSURE/" + save_fn
            roi_img = cv2.resize(roi_img,(224,244))
            print("SAVING:", save_file)
            cv2.imwrite(save_file, roi_img)
            #cv2.imshow('pepe2', roi_img)
            label_data = [round(meteor_prev_yn,2),roi]
            objects.append(label_data)
            label = str(round(meteor_prev_yn,2)) + "% meteor"
            if aiy2 < ih / 2:
               cv2.putText(show_img, label,  (aix1,aiy2), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
            else:
               cv2.putText(show_img, label,  (aix1,aiy1), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
            tries += 1
      #show_img_show = cv2.resize(show_img, (1280,720))
      #cv2.imshow('final', show_img_show)
      #cv2.waitKey(30)
      return(objects) 

   def score_met_ai(self, ai):
      score = 0
      if ai['meteor_yn_confidence'] > 50:
         score += 1
      if ai['meteor_fireball_yn_confidence'] > 50:
         score += 1
      if ai['meteor_prev_yn'] > 50:
         score += 1
      if ai['meteor_or_plane'] != "":
         if ai['meteor_or_plane'][0] == "METEOR":
            score += 1
      if ai['fireball_or_plane'] != "":
         if ai['fireball_or_plane'][0] == "FIREBALL":
            score += 1
      if "meteor" in ai['mc_class']:
         score += 1
      #input("PAUSE METEOR SCORE " + str(score))
      ai['meteor_score'] = score
      return(ai)

   def mfd_roi(self, mfd):
      xs = [row[2] for row in mfd]
      ys = [row[3] for row in mfd]
      cx = np.mean(xs)
      cy = np.mean(ys)
      min_x = min(xs)
      max_x = max(xs)
      min_y = min(ys)
      max_y = max(ys)
      w = max_x - min_x
      h = max_y - min_y
      if w > h:
         roi_size = int(w * 1.25)
      else:
         roi_size = int(h * 1.25)

      x1 = int(cx - int(roi_size/2))
      x2 = int(cx + int(roi_size/2))
      y1 = int(cy - int(roi_size/2))
      y2 = int(cy + int(roi_size/2))
      roi_w = x2 - x1
      roi_h = y2 - y1
      if roi_w != roi_h:
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

      #print("check_off_frame", x1,y1,x2,y2,w,h)
      if x1 < 0:
         off_frame.append('left')
      if x2 > w - 1:
         off_frame.append('right')
      if y1 < 0:
         off_frame.append('top')
      if y2 > h - 1:
         off_frame.append('bottom')
      return(off_frame)
