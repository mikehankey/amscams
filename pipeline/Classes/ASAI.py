import cv2
import os
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops

#from lib.PipeUtil import load_json_file, save_json_file , get_file_info
from lib.PipeUtil import load_json_file, save_json_file , get_file_info
import tensorflow as tf
import os
from tensorflow import keras
from tensorflow.keras.models import *
import tensorflow.keras
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img


class AllSkyAI():

   def __init__(self):
      print("AllSkyAI is self aware.")
      self.meteor_dir = "/mnt/ams2/meteors/"
      self.meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/"
      self.ai_data_dir = "/mnt/ams2/datasets/"
      if os.path.exists("../conf/as6.json") is True:
         self.json_conf = load_json_file("../conf/as6.json")
      else:
         self.json_conf = None
      if self.json_conf is not None:
         self.station_id = self.json_conf['site']['ams_id']
      else:
         self.station_id = "AMSX"
      self.meteor_delete_file = self.ai_data_dir + self.station_id + "_METEOR_DELETE.json"
      self.machine_data_file = self.ai_data_dir + self.station_id + "_ML_DATA.json"
      self.human_data_file = self.ai_data_dir + self.station_id + "_human_data.json"
      self.ai_meteor_index_file = self.ai_data_dir + self.station_id + "_AI_METEOR_INDEX.json"
      self.ai_summary_file = self.ai_data_dir + self.station_id + "_AI_SUMMARY.json"
      self.no_longer_exists_file = self.ai_data_dir + self.station_id + "_no_longer_exists.json"
      self.corrupt_json_file = self.ai_data_dir + self.station_id + "_corrupt_json.json"
      self.ai_missing_file = self.ai_data_dir + self.station_id + "_ai_missing.json"


      if os.path.exists(self.machine_data_file) is True:
         self.machine_data = load_json_file(self.machine_data_file)
      else:
         self.machine_data = {}
      if os.path.exists(self.human_data_file) is True:
         self.human_data = load_json_file(self.human_data_file)
      else:
         self.human_data = {}

      if os.path.exists(self.meteor_delete_file) is True:
         self.meteor_deletes = load_json_file(self.meteor_delete_file)
      else:
         self.meteor_deletes = {}

      if os.path.exists(self.ai_meteor_index_file) is True:
         self.ai_meteor_index = load_json_file(self.ai_meteor_index_file)
      else:
         self.ai_meteor_index = {}
      temp = load_json_file("labels.json")
      self.class_names = temp['labels']
      self.class_names = sorted(self.class_names)

   def check_update_install(self):
      # does the AI File exist? If not then we are not at the v1.0 update yet! Do what is needed.
      ai_conf_file = "../conf/ai_conf.json"
      update_needed = False
      if os.path.exists(ai_conf_file) is False:
         ai_conf = {}
      else:
         ai_conf = load_json_file(ai_conf_file)
      if "version" not in ai_conf:
         update_needed = True

      if update_needed is True:
         # make sure we have the latest model versions
         ai_conf['version'] = 1
         cmd = "cp /mnt/archive.allsky.tv/AMS1/ML/*.h5 ./"
         print(cmd)
         os.system(cmd)


      # make python3.6 and tensor flow is installed!  
      if 'tf_installed' not in ai_conf:
         cmd = "echo 'INSTALL TENSOR FLOW & PYTHON 3.6!'"
         print(cmd)
         os.system(cmd)
         try:
            import tensorflow
            ai_conf['tf_installed'] = 1
         except:
            ai_conf['tf_installed'] = 0
      else:
         if ai_conf['tf_installed'] == 1:
            print("Tensor flow is installed.")
         else:
            print("PROBLEM: Tensor flow is NOT installed.")
      save_json_file(ai_conf_file, ai_conf)


   def load_config(self):
      print("Loading AllSkyAI config...")

   def load_history(self):
      print("Loading AllSkyAI history...")

   def load_ai_model(self):
      print("Loading AllSkyAI AI model...")

   def load_masks(self):
      print("AllSkyAI loading masks...")

   def start_server_process(self):
      print("Starting AllSkyAI server...")

   def stop_server_process(self):
      print("Stopping AllSkyAI server...")

   def load_all_models(self):
      """
         3 Primary Models Currently:
            meteor_yn_model.h5
            meteor_fireball_yn_model.h5
            multi_class_model.h5

            meteor_or_plane_model.h5
            meteor_or_bird_model.h5
            meteor_or_firefly_model.h5
      """
      self.model_meteor_yn = Sequential()
      self.model_meteor_fireball_yn = Sequential()
      self.model_multi_class = Sequential()
      self.model_meteor_or_plane = Sequential()
      self.model_meteor_or_bird = Sequential()
      self.model_meteor_or_firefly = Sequential()

      self.model_meteor_yn =load_model('meteor_yn_model.h5')
      self.model_meteor_yn.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

      self.model_meteor_fireball_yn =load_model('meteor_fireball_yn_model.h5')
      self.model_meteor_fireball_yn.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

      self.model_meteor_or_plane =load_model('meteor_or_plane_model.h5')
      self.model_meteor_or_plane.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

      self.model_meteor_or_bird =load_model('meteor_or_bird_model.h5')
      self.model_meteor_or_bird.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])

      self.model_meteor_or_firefly =load_model('meteor_or_firefly_model.h5')
      self.model_meteor_or_firefly.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])


      self.model_multi_class =load_model("multi_class_model.h5")
      self.model_multi_class.compile(loss='categorical_crossentropy',
         optimizer='rmsprop',
         metrics=['accuracy'])

   def load_my_model(self, model_file = None):
      if model_file is None:
         model_file = "multi_class_model.h5"

      model = Sequential()
      #print("MF:", model_file)
      model =load_model(model_file)
      model.compile(loss='categorical_crossentropy',
         optimizer='rmsprop',
         metrics=['accuracy'])
      return(model)

   def predict_image(self, imgfile, model):
      img_height = 150
      img_width = 150
      #img = keras.utils.load_img(
      img = load_img(
         imgfile, target_size=(img_height, img_width)
      )
      show_img = cv2.imread(imgfile)
      img_array = img_to_array(img)
      img_array = tf.expand_dims(img_array, 0) # Create a batch

      predictions = model.predict(img_array)

      score = tf.nn.softmax(predictions[0])
      predicted_class = self.class_names[np.argmax(score)]
      return(predicted_class)


   def predict_yn(self,oimg,model,size):
      imgfile = "temp.jpg"
      oimg = cv2.resize(oimg,(150,150))
      cv2.imwrite(imgfile, oimg)
      img = oimg.copy()
      img = cv2.resize(img,(128,128))
      img = np.reshape(img,[1,128,128,3])
      img_size = [128,128]

      img = load_img(imgfile, target_size = img_size)
      img = img_to_array(img).astype(np.float32)
      img /= 255.
      img = np.expand_dims(img, axis = 0)

      # check meteor yn
      pred_yn_class = model.predict(img)
      if pred_yn_class[0][0] > .5:
         # NON METEOR DETECTED!
         pred_yn = False 
      else:
         # METEOR DETECTED
         pred_yn = True 
      return(pred_yn)


   def meteor_yn(self,roi_file=None,oimg=None):
      # FOR METEOR Y/N PREDICT AND FIREBALL PREDICT!
      if roi_file is not None:
         oimg = cv2.imread(roi_file)
         imgfile = roi_file
      else:
         imgfile = "temp.jpg"


      try:
         oimg = cv2.resize(oimg,(150,150))
      except:
         print("BAD IMAGE!", roi_file)
         return(None)
      if roi_file is None:
         imgfile = "temp.jpg"
         cv2.imwrite(imgfile, oimg)
      img = oimg.copy()
      img = cv2.resize(img,(128,128))
      img = np.reshape(img,[1,128,128,3])
      img_size = [128,128]
      #img = keras.preprocessing.image.load_img(imgfile, target_size = img_size)
      #img = keras.preprocessing.image.img_to_array(img).astype(np.float32)

      img = load_img(imgfile, target_size = img_size)
      img = img_to_array(img).astype(np.float32)
      img /= 255.
      img = np.expand_dims(img, axis = 0)

      # check meteor yn
      meteor_yn_class = self.model_meteor_yn.predict(img)
      meteor_yn_confidence = (1 - meteor_yn_class[0][0]) * 100
      if meteor_yn_class[0][0] > .5:
         # NON METEOR DETECTED!
         meteor_yn = False 
      else:
         # METEOR DETECTED
         meteor_yn = True 

      # check fireball yn
      fireball_yn_class = self.model_meteor_fireball_yn.predict(img)
      meteor_fireball_yn_confidence = (1 - fireball_yn_class[0][0]) * 100
      if fireball_yn_class[0][0] > .5:
         # NON METEOR DETECTED!
         meteor_fireball_yn = False 
      else:
         # METEOR DETECTED
         meteor_fireball_yn = True 

      # check meteor_or_plane 
      meteor_or_plane_class = self.model_meteor_or_plane.predict(img)
      meteor_or_plane_confidence = (1 - meteor_or_plane_class[0][0]) * 100
      if meteor_or_plane_class[0][0] > .5:
         # NON METEOR DETECTED!
         meteor_or_plane_yn = False 
      else:
         # METEOR DETECTED
         meteor_or_plane_yn = True 

      # check meteor_or_bird
      meteor_or_bird_class = self.model_meteor_or_bird.predict(img)
      meteor_or_bird_confidence = (1 - meteor_or_bird_class[0][0]) * 100
      if meteor_or_bird_class[0][0] > .5:
         # NON METEOR DETECTED!
         meteor_or_bird_yn = False 
      else:
         # METEOR DETECTED
         meteor_or_bird_yn = True 

      # check meteor_or_firefly
      meteor_or_firefly_class = self.model_meteor_or_firefly.predict(img)
      meteor_or_firefly_confidence = (1 - meteor_or_firefly_class[0][0]) * 100
      if meteor_or_firefly_class[0][0] > .5:
         # NON METEOR DETECTED!
         meteor_or_firefly_yn = False 
      else:
         # METEOR DETECTED
         meteor_or_firefly_yn = True 




      # check multi class
      mc_w = 150
      mc_h = 150
      mc_img = load_img(
         imgfile, target_size=(mc_h, mc_w)
      )
      img_array = img_to_array(mc_img)
      img_array = tf.expand_dims(img_array, 0) # Create a batch

      predictions = self.model_multi_class.predict(img_array)

      score = tf.nn.softmax(predictions[0])
      predicted_class = self.class_names[np.argmax(score)]

      response = {}
      response['meteor_yn'] = meteor_yn
      response['meteor_yn_confidence'] = float(meteor_yn_confidence)
      response['meteor_fireball_yn'] = meteor_fireball_yn
      response['meteor_fireball_yn_confidence'] = float(meteor_fireball_yn_confidence)
      response['meteor_or_plane_yn'] = meteor_or_plane_yn
      response['meteor_or_plane_confidence'] = float(meteor_or_plane_confidence)
      response['meteor_or_bird_yn'] = meteor_or_bird_yn
      response['meteor_or_bird_confidence'] = float(meteor_or_bird_confidence)
      response['meteor_or_firefly_yn'] = meteor_or_firefly_yn
      response['meteor_or_firefly_confidence'] = float(meteor_or_firefly_confidence)
      response['mc_class'] = predicted_class
      response['mc_confidence'] = int(100 * np.max(score))

      final_yn_conf = max([meteor_yn,meteor_fireball_yn])
      if "meteor" in response['mc_class']:
         final_yn_conf += response['mc_confidence']
      else: 
         final_yn_conf -= (response['mc_confidence']/2)

      if meteor_yn is True or meteor_fireball_yn is True or "meteor" in response['mc_class']:
         final_yn = True
      else:
         final_yn = False 

      response['final_meteor_yn'] = final_yn 
      response['final_meteor_yn_conf'] = final_yn_conf

      return(response)

   def format_response(self, resp):
      descs = []
      color = [128,128,128]
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
      return((desc,desc2),color)

      

   def detect_objects_in_stack(self, stack_file):
      # open image, find max val, set thresh val, dilate, 
      # find_cnts, group into objects, make bound ROIs for each, 
      # create data dict for each object
      # return array for each object with roi_img and roi xys 
      print("AllSkyAI detect objects in stack...")
      img, img_gray, img_thresh, img_dilate, avg_val, max_val, thresh_val = self.ai_open_image(stack_file)

   def ai_open_image(self, img_file):
      # open image, find max val, set thresh val, dilate, 
      img = cv2.imread(img_file)
      img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(img_gray)
      avg_val = np.mean(img_gray)
      px_diff = max_val - avg_val
      thresh_val = max_val * .5
      if max_val < avg_val * 1.4:
         thresh_val = avg_val * 1.4
      _, img_thresh = cv2.threshold(img_gray, thresh_val, 255, cv2.THRESH_BINARY)
      img_dilate = cv2.dilate(img_thresh.copy(), None , iterations=4)
      return(img, img_gray, img_thresh, img_dilate, avg_val, max_val, thresh_val)
    

   def stack_stack(self, pic1, pic2):
         stacked_image=ImageChops.lighter(pic1,pic2)
         return(stacked_image)

   def stack_video(self, video_file):
      print("AllSkyAI stack video...")
      cap = cv2.VideoCapture(video_file)
      stacked_image = None
      frame = True
      while frame is not None:
         # grab each frame in video file
         grabbed , frame = cap.read()
         if frame is None:
            break
         frame_pil = Image.fromarray(frame)
         if stacked_image is not None:
            frame_sub = cv2.subtract(frame, stacked_image)
            frame_sub = cv2.cvtColor(frame_sub, cv2.COLOR_BGR2GRAY)

         if stacked_image is None:
            stacked_image = stack_stack(frame_pil, frame_pil)
         else:
            stacked_image = stack_stack(stacked_image, frame_pil)

      stacked_image = np.asarray(stacked_image)
      return(stacked_image)


   def get_contours(self,sub):
      print("AllSkyAI get contours...")
      cont = []
      cnt_res = cv2.findContours(sub.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      noise = 0
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         if w > 1 and h > 1:
            cont.append((x,y,w,h))
      return(cont)

   def make_ai_summary(self):
      summary = {}
      summary['total_meteor_obs'] = 0
      summary['total_reduced'] = 0
      summary['total_not_reduced'] = 0
      summary['total_ai_checked'] = 0
      summary['total_human_checked'] = 0
      summary['totals_by_class'] = {}
      summary['roi_missing'] = 0
      summary['roi_bad'] = 0
      summary['roi_found'] = 0
      ai_missing = {}

      for row in self.ai_meteor_index:
         (meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm,mlabel,hlabel) = row
         roi_file = self.meteor_scan_dir + meteor_file[0:10] + "/" +  self.station_id + "_" + meteor_file.replace(".json", "-ROI.jpg")
         if os.path.exists(roi_file) is False:
            summary['roi_missing'] += 1
         else:
            summary['roi_found'] += 1
            size, tdiff = get_file_info(roi_file)
            if size == 0:
               summary['roi_bad'] += 1
            if mlabel == "NONE":
               ai_missing[roi_file] = []

         summary['total_meteor_obs'] += 1
          
         if reduced == 1 or reduced == "1":
            summary['total_reduced'] += 1
         else:
            summary['total_not_reduced'] += 1
         if mlabel != "NONE":
            summary['total_ai_checked'] += 1
         if hlabel != "NONE":
            summary['total_human_checked'] += 1

         if mlabel not in summary['totals_by_class']:
            summary['totals_by_class'][mlabel] = 1
         else: 
            summary['totals_by_class'][mlabel] += 1
      save_json_file(self.ai_summary_file,summary)     
      save_json_file(self.ai_missing_file,ai_missing)     
      print("Saved:", self.ai_summary_file)
      print("Saved:", self.ai_missing_file)
         

   def reindex_meteors(self):
      meteor_days = sorted(os.listdir(self.meteor_dir), reverse=True)
      summary = {}
      summary['total_meteor_obs'] = 0
      summary['total_reduced'] = 0
      summary['total_not_reduced'] = 0
      summary['total_ai_checked'] = 0
      summary['total_human_checked'] = 0
      summary['totals_by_class'] = {}
 
      temp = []
      for mday in meteor_days:
          
         mdir = self.meteor_dir + mday + "/" 
         if os.path.isdir(mdir) is False:
            continue
         mif = self.meteor_dir + mday + "/" + mday + "-" + self.station_id + ".meteors"
         if os.path.exists(mif):
            #print("found", mif)
            data = load_json_file(mif)
            temp.extend(data)
         else:
            print("not found", mif)
      print("ALL:", len(temp))
      all_index = []
      for dd in temp:
         meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm = dd
         meteor_file = meteor_file.split("/")[-1]
         roi_file = self.station_id + "_" + meteor_file.replace(".json", "-ROI.jpg")

         if roi_file in self.machine_data:
            mlabel = self.machine_data[roi_file]
            summary['total_ai_checked'] += 1
         else:
            mlabel = "NONE" 
            print("MISSING FROM AI", roi_file, meteor_file, reduced)
            date = meteor_file[0:10]
            ms_dir = "/mnt/ams2/METEOR_SCAN/" + date + "/"
            if os.path.exists(ms_dir + roi_file) is True:
               print("ROI FILE FOUND:", ms_dir + roi_file)
               img = cv2.imread(roi_file)
               resp = self.ASAI.meteor_yn(None, img)
               print("FINAL:", resp['final_meteor_yn']) 
               print("FINAL:", resp['final_meteor_yn_conf']) 
      
               print(resp)
            else:
               print("ROI FILE NOT FOUND:", self.station_id, ms_dir + roi_file)

         if roi_file in self.human_data:
            hlabel = self.human_data[roi_file]
            summary['total_human_checked'] += 1
         else:
            hlabel = "NONE" 
         if mlabel not in summary['totals_by_class']:
            summary['totals_by_class'][mlabel] = 1
         else:
            summary['totals_by_class'][mlabel] += 1

         #print("DD:", meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm, mlabel, hlabel)
         if reduced == 1:
            summary['total_reduced'] += 1
         else:
            summary['total_not_reduced'] += 1
         summary['total_meteor_obs'] += 1
        
         all_index.append((meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm,mlabel,hlabel))

      no_longer_exists = []
      corrupt_json = []
      mc = 0
      for data in all_index:
         (meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm,mlabel,hlabel) = data
         mdate = meteor_file[0:10]
         mfile = "/mnt/ams2/meteors/" + mdate + "/" + meteor_file 
         if os.path.exists(mfile) is False:
            print("NOT found.", mc, mfile)
            no_longer_exists.append(mfile)
         else:
            size, td = get_file_info(mfile)
            print("File found.", mc, mfile, size)
            if size == 0:
               print("CORRUPT JSON FILE!!!.", mc, mfile, size)
               corrupt_json.append(meteor_file)
            
         mc += 1
 
      save_json_file(self.no_longer_exists_file,no_longer_exists)     

      save_json_file(self.ai_meteor_index_file,all_index)     
      #save_json_file(self.ai_summary_file,summary)     
      save_json_file(self.corrupt_json_file,corrupt_json)     
      print("saved", self.ai_meteor_index_file)
      #print("saved", self.ai_summary_file)
      print("saved", self.no_longer_exists_file)
      print("saved", self.corrupt_json_file)

   def save_files(self):
      save_json_file(self.machine_data_file, self.machine_data)

   def predict_meteor_yn(self,img_file, model=None):
      if model is None:
         model = "meteor_yn_model.h5"

   def bound_cnt(self, x1,y1,x2,y2,img, margin=.5):
      ih,iw = img.shape[:2]
      rw = x2 - x1
      rh = y2 - y1
      if rw > rh:
         rh = rw
      else:
         rw = rh
      rw += int(rw*margin )
      rh += int(rh*margin )
      if rw >= ih or rh >= ih:
         rw = int(ih*.95)
         rh = int(ih*.95)
      if rw < 180 or rh < 180:
         rw = 180
         rh = 180

      cx = int((x1 + x2)/2)
      cy = int((y1 + y2)/2)
      nx1 = cx - int(rw / 2)
      nx2 = cx + int(rw / 2)
      ny1 = cy - int(rh / 2)
      ny2 = cy + int(rh / 2)
      if nx1 <= 0:
         nx1 = 0
         nx2 = rw
      if ny1 <= 0:
         ny1 = 0
         ny2 = rh
      if nx2 >= iw:
         nx1 = iw-rw-1
         nx2 = iw-1
      if ny2 >= ih:
         ny2 = ih-1
         ny1 = ih-rh-1
      if ny1 <= 0:
         ny1 = 0
      if nx1 <= 0:
         nx1 = 0
      #print("NX", nx1,ny1,nx2,ny2)
      return(nx1,ny1,nx2,ny2)
