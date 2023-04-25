import pickle
import json
import redis
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
      print("\rAllSkyAI is self aware.", end="")
      self.AI_VERSION = 3.2
      self.meteor_dir = "/mnt/ams2/meteors/"
      self.r = redis.Redis("localhost", port=6379, decode_responses=True)
      self.meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/"
      self.ai_data_dir = "/mnt/ams2/datasets/"
      self.img_repo_dir = self.ai_data_dir + "meteor_yn/"
      if os.path.exists(self.img_repo_dir + "meteor/") is False:
         os.makedirs(self.img_repo_dir + "meteor")
      if os.path.exists(self.img_repo_dir + "non_meteor/") is False:
         os.makedirs(self.img_repo_dir + "non_meteor")
      

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

      self.become_aware()

   def become_aware(self):
      # initialization routine for the ALLSKY AI MAIN BRAIN
      # The main brain is the primary task manager for the system
      # and is designed to track all "things", a thing being a task
      # date, data file, status, process, routine, etc. 
    
      # we can start by defining all things
      all_things = {}
      # system related things, client config, disk space, cameras rolling 
      # versions of databases, installed programs and so on

      all_things['system'] = {}
      all_things['ai_version'] = 2
      all_things['disks'] = {}
      all_things['disks']['os'] = {}
      all_things['disks']['data'] = {}
      all_things['disks']['backup'] = {}
      all_things['disks']['cloud'] = {}

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

   def load_my_model(self, model_file = None):
      if model_file is None:
         model_file = "multi_class_model.h5"

      model = Sequential()
      #print("MF:", model_file)
      model =load_model(model_file, compile=False)
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
      img = cv2.resize(img,(224,224))
      img = np.reshape(img,[1,224,224,3])
      img_size = [224,224]

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

   def image_64(self,image):
      # grab the brightest pixel spot and make a crop 64x64 around that

      gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
      ih,iw = image.shape[:2]
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
      x1 = mx - 32
      x2 = mx + 32
      y1 = my - 32
      y2 = my + 32
      if x1 < 0:
         x1 = 0
         x2 = 64
      if y1 < 0:
         y1 = 0
         y2 = 64
      if x2 > iw:
         x2 =iw -1
         x1 = iw - 1 - 64
      if y2 > ih:
         y2 =ih -1
         y1 = ih - 1 - 64
      i64 = image[y1:y2,x1:x2]
      return(i64)
 
   def meteor_prev_yn(self,oimg):
      # just check 1 small img for meteor YN and that is it. 
      # speed is the goal here
      width = 38
      height = 38
      imgfile = "temp.jpg"
      if oimg.shape[0] != 38 or oimg.shape[1] != 38:
         oimg = cv2.resize(oimg, (38,38))
      cv2.imwrite(imgfile, oimg)

      img38 = load_img(imgfile, target_size = (38,38))
      img38 = img_to_array(img38).astype(np.float32) / 255.0 
      img38 = np.expand_dims(img38, axis = 0)
      meteor_prev_yn_class = self.models['meteor_prev_yn'].predict(img38)
      meteor_prev_yn = (1 - meteor_prev_yn_class[0][0]) * 100
 
      if "meteor_or_star" in self.models:
         meteor_or_star_class = self.models['meteor_or_star'].predict(img38)
         meteor_or_star = (1 - meteor_or_star_class[0][0]) * 100
      else:
         meteor_or_star = None



      return(meteor_prev_yn)


   def star_yn(self,oimg=None):
     
      cv2.imwrite("stemp.png", oimg)

      img = load_img("stemp.png", target_size = (32,32))
      img = img_to_array(img).astype(np.float32) / 255.0 
      img = np.expand_dims(img, axis = 0)

      star_yn = self.models['star_yn'].predict(img)
      star_yn_conf = (1 - star_yn[0][0]) * 100
      return(star_yn_conf)


   def meteor_yn(self,root_fn,roi_file=None,oimg=None,roi=None):
      # input - root_fn (orig fn for file ROI)
      # roi_file - direct link to input roi
      # oimg - cv img var - alternative to passing in roi_file
      # roi - [x1,y1,x2,y2] 
      # returns :
      # ai_resp object containing meteor_yn,fireball_yn,mc_class,mc_conf

      print("AI METEOR YN:", root_fn, roi_file)
      if oimg is not None:
         print("OIMG:", oimg.shape)
      if roi is not None:
         print("ROI IMG", roi)
      ai_resp = {}
      ai_resp['ai_version'] = self.AI_VERSION
      ai_resp['root_fn'] = root_fn
      ai_resp['meteor_yn'] = 0
      ai_resp['meteor_prev_yn'] = 0
      ai_resp['fireball_yn'] = 0
      ai_resp['mc_class'] = ""
      ai_resp['mc_class_conf'] = 0
      if roi is not None:
         try:
            x1, y1,x2,y2 = roi
         except:
            x1,y1,x2,y2 = 0,0,0,0
      else:
         x1,y1,x2,y2 = 0,0,0,0
      ai_resp['roi'] = [x1,y1,x2,y2] 

      red_key = "AI:" + root_fn + "_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2)
      if "temp" not in red_key:
         rcache = self.r.get(red_key)
      else:
         rcache = None

      if rcache is not None:
         meteor_yn, fireball_yn, mc_class, mc_class_conf = json.loads(rcache)

         ai_resp['meteor_yn'] = meteor_yn 
         ai_resp['fireball_yn'] = fireball_yn
         ai_resp['mc_class'] = mc_class
         ai_resp['mc_class_conf'] = mc_class_conf 
         print("RED KEY", red_key)
         print("RC:", rcache)
         print("AI", ai_resp)
         return(ai_resp)

      
      if roi_file is not None:
         oimg = cv2.imread(roi_file)
         imgfile = roi_file
      else:
         imgfile = "temp.jpg"

      if roi_file is None:
         imgfile = "temp.jpg"
         cv2.imwrite(imgfile, oimg)
      try:
         img = oimg.copy()
      except:
         return(None)

      img = load_img(imgfile, target_size = (64,64))
      img = img_to_array(img).astype(np.float32) / 255.0 
      img = np.expand_dims(img, axis = 0)

      img38 = load_img(imgfile, target_size = (38,38))
      img38 = img_to_array(img38).astype(np.float32) / 255.0 
      img38 = np.expand_dims(img38, axis = 0)

      if "meteor_prev_yn" in self.models:
         print("Trying Prev:", img38.shape)
         meteor_prev_yn_class = self.models['meteor_prev_yn'].predict(img38)
         meteor_prev_yn = (1 - meteor_prev_yn_class[0][0]) * 100
         ai_resp['meteor_prev_yn'] = meteor_prev_yn
      

      # check meteor yn
      if "meteor_yn_i64" in self.models:
         print("Trying YN:", img.shape)
         meteor_yn_class = self.models['meteor_yn_i64'].predict(img)
         meteor_yn_confidence = (1 - meteor_yn_class[0][0]) * 100
         ai_resp['meteor_yn'] = meteor_yn_confidence

      # check fireball yn
      if "fireball_yn_i64" in self.models:
         meteor_yn_class = self.models['fireball_yn_i64'].predict(img)
         meteor_yn_confidence = (1 - meteor_yn_class[0][0]) * 100
         ai_resp['fireball_yn'] = meteor_yn_confidence

      # check multi class

      if "moving_objects_i64" in self.models:
         pred_result = self.models['moving_objects_i64'].predict(img)

         # Multi class i64
         # extract the class label which has the highest corresponding probability
         i = pred_result.argmax(axis=1)[0]
         label = self.multi_class_labels['moving_objects_i64'].classes_[i]
         predicted_class = label
         confidence = pred_result[0][i] * 100
         ai_resp['mc_class'] = predicted_class 
         ai_resp['mc_class_conf'] = confidence
      print("METEOR YN RESP:", ai_resp)
      payload = [ai_resp['meteor_yn'], ai_resp['fireball_yn'], ai_resp['mc_class'], ai_resp['mc_class_conf']]

      self.r.set(red_key, json.dumps(payload))
      print("SET REDIS!", red_key, payload)
      return(ai_resp)

   def meteor_yn_last(self,root_fn,roi_file=None,oimg=None,roi=None):
      width = 64
      height = 64
      meteor_or_plane = ""
      fireball_or_plane = ""
      # FOR METEOR Y/N PREDICT AND FIREBALL PREDICT!
      if roi is not None:
         try:
            x1, y1,x2,y2 = roi
         except:
            x1,y1,x2,y2 = 0,0,0,0
      else:
         x1,y1,x2,y2 = 0,0,0,0
      
      if roi_file is not None:
         oimg = cv2.imread(roi_file)
         imgfile = roi_file
      else:
         imgfile = "temp.jpg"


      imgfile_224 = imgfile.replace(".jpg", "224.jpg")

      if roi_file is None:
         imgfile = "temp.jpg"
         cv2.imwrite(imgfile, oimg)
      try:
         img = oimg.copy()
      except:
         return(None)
      img = cv2.resize(img,(224,224))
      img_org = img.copy()
      #img = self.image_64(img)

      img = cv2.resize(img,(64,64))
      img38 = cv2.resize(img,(38,38))



      #img = np.reshape(img,[1,width,height,3])
      img_size = [int(width),int(height)]

      img = load_img(imgfile, target_size = img_size)
      img = img_to_array(img).astype(np.float32) / 255.0 
      img = np.expand_dims(img, axis = 0)

      img38 = load_img(imgfile, target_size = (38,38))
      img38 = img_to_array(img38).astype(np.float32) / 255.0 
      img38 = np.expand_dims(img38, axis = 0)


      
      meteor_prev_yn_class = self.model_meteor_prev_yn.predict(img38)
      meteor_prev_yn = (1 - meteor_prev_yn_class[0][0]) * 100
      # check meteor yn
      if self.model_meteor_yn is None:
         print("Models are not fully loaded. can't run.")
         exit()
         return(None)
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

      # check multi class

      pred_result = self.model_multi_class.predict(img)

      # Multi class i64
      # extract the class label which has the highest corresponding probability
      i = pred_result.argmax(axis=1)[0]
      label = self.multi_class_labels['moving_objects_i64'].classes_[i]
      predicted_class = label
      confidence = pred_result[0][i] * 100

      if False:
         # Over-ride the mc_class on some conditions???
         if meteor_yn_confidence >= confidence :
            predicted_class = "meteor"
            confidence = meteor_yn_confidence
         if meteor_fireball_yn_confidence >= confidence :
            predicted_class = "meteor_fireballs"
            confidence = meteor_fireball_yn_confidence
         if meteor_prev_yn >= confidence :
            predicted_class = "meteor"
            confidence = meteor_prev_yn 
 
 
      # meteor or plane
      meteor_or_plane = "" 
      if "meteor" in predicted_class or "plane" in predicted_class or "bird" in predicted_class or "bug" in predicted_class:
         if meteor_or_plane is not None:
            meteor_or_plane_class = self.model_meteor_or_plane.predict(img)
            meteor_or_plane_confidence = (1 - meteor_or_plane_class[0][0]) * 100

            if meteor_or_plane_class[0][0] > .5:
               meteor_or_plane = ["PLANE", meteor_or_plane_confidence]
            else:
               meteor_or_plane = ["METEOR" , meteor_or_plane_confidence]

      if "fireball" in predicted_class or "plane" in predicted_class or "bird" in predicted_class or "bug" in predicted_class:
         if self.model_fireball_or_plane is not None:
            fireball_or_plane_class = self.model_fireball_or_plane.predict(img)
            fireball_or_plane_confidence = (1 - fireball_or_plane_class[0][0]) * 100

            if fireball_or_plane_class[0][0] > .5:
               fireball_or_plane = ["FIREBALL", fireball_or_plane_confidence]
               #if fireball_or_plane_confidence >= .99:
               #   predicted_class = "planes"
            else:
               fireball_or_plane = ["PLANE" , fireball_or_plane_confidence]
               #if fireball_or_plane_confidence <= .01:
               #   predicted_class = "meteor_fireball"
         else:
            fireball_or_plane = "" 

      # determine final confidence for meteors, fireballs and planes!
      final_conf = confidence

      if predicted_class == "meteor" or predicted_class == 'meteor_fireballs':
         # perfect score
         if confidence > 98 and (meteor_yn_confidence  >= 99  or meteor_fireball_yn_confidence >= 99) and (meteor_or_plane[0] == "METEOR" or fireball_or_plane[0] == "FIREBALL"):
            final_conf = 100
      #if predicted_class == "meteor_fireball":
      #if predicted_class == "plane":

      response = {}
      response['roi'] = roi
      response['ai_version'] = 2
      response['meteor_yn'] = meteor_yn
      response['meteor_prev_yn'] = meteor_prev_yn
      response['meteor_yn_confidence'] = float(meteor_yn_confidence)

      if "fireball" in predicted_class or float(meteor_fireball_yn_confidence) > float(meteor_yn_confidence) :
         meteor_fireball_yn = "Y"

      response['meteor_fireball_yn'] = meteor_fireball_yn
      response['meteor_fireball_yn_confidence'] = float(meteor_fireball_yn_confidence)
      response['mc_class'] = predicted_class
      response['mc_class_confidence'] = confidence # int(100 * np.max(score))

      response['meteor_or_plane'] = meteor_or_plane 
      response['fireball_or_plane'] = fireball_or_plane 
      response['final_conf'] = final_conf

      #response['meteor_or_plane_yn'] = meteor_or_plane_yn
      #response['meteor_or_plane_confidence'] = float(meteor_or_plane_confidence)
      #response['meteor_or_bird_yn'] = meteor_or_bird_yn
      #response['meteor_or_bird_confidence'] = float(meteor_or_bird_confidence)
      #response['meteor_or_firefly_yn'] = meteor_or_firefly_yn
      #response['meteor_or_firefly_confidence'] = float(meteor_or_firefly_confidence)


      final_yn_conf = max([meteor_yn_confidence,meteor_fireball_yn_confidence,meteor_prev_yn])
      #if "meteor" in response['mc_class']:
      #   final_yn_conf += response['mc_confidence']
      #else: 
      #   final_yn_conf -= (response['mc_confidence']/2)

      if meteor_yn is True or meteor_fireball_yn is True or "meteor" in response['mc_class'] or meteor_prev_yn > 50:
         final_yn = True
      else:
         final_yn = False 

      response['final_meteor_yn'] = final_yn 
      response['final_meteor_yn_conf'] = final_yn_conf
      if final_yn is True:
         # save sample
         roi_file = self.img_repo_dir + "meteor/" + self.station_id + "_" + root_fn + "-ROI.jpg"
      else:
         roi_file = self.img_repo_dir + "non_meteor/" + self.station_id + "_" + root_fn + "-RX_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2) + ".jpg"

      cv2.imwrite(roi_file, oimg)
      response['roi_fn'] = roi_file.split("/")[-1]
      response['root_fn'] = root_fn
    
      if False:
         show_img = cv2.resize(oimg,(400,400))
         desc = response['mc_class']
         cv2.putText(show_img, desc,  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .3, (255,255,255), 1)
         cv2.imshow('AI', show_img)
         cv2.waitKey(30)

      return(response)




   def meteor_yn_OLD(self,root_fn,roi_file=None,oimg=None,roi=None):
      width = 64
      height = 64
      # FOR METEOR Y/N PREDICT AND FIREBALL PREDICT!
      if roi is not None:
         try:
            x1, y1,x2,y2 = roi
         except:
            x1,y1,x2,y2 = 0,0,0,0
      else:
         x1,y1,x2,y2 = 0,0,0,0
      
      if roi_file is not None:
         oimg = cv2.imread(roi_file)
         imgfile = roi_file
      else:
         imgfile = "temp.jpg"

      #try:
      #   oimg = cv2.resize(oimg,(width,height))
      #except:
      #   print("BAD IMAGE!", roi_file)
      #   return(None)

      if roi_file is None:
         imgfile = "temp.jpg"
         cv2.imwrite(imgfile, oimg)
      try:
         img = oimg.copy()
      except:
         return(None)
      img = cv2.resize(img,(224,224))
      img = self.image_64(img)

      # save/load the i64 image
      if "ROI" in imgfile:
         imgfile = imgfile.replace("ROI", "I64")
      cv2.imwrite(imgfile, img)


      img = np.reshape(img,[1,width,height,3])
      img_size = [width,height]
      #img = keras.preprocessing.image.load_img(imgfile, target_size = img_size)
      #img = keras.preprocessing.image.img_to_array(img).astype(np.float32)
      print("FILE:", imgfile)
      img = load_img(imgfile, target_size = img_size)
      img = img_to_array(img).astype(np.float32) / 255.0 
   #   img = img_to_array(img).astype(np.float32)
     # img /= 255.
      img = np.expand_dims(img, axis = 0)

      # check meteor yn
      meteor_yn_class = self.model_meteor_yn.predict(img)
      meteor_yn_confidence = (1 - meteor_yn_class[0][0]) * 100
      print("DONE METEOR YN", meteor_yn_confidence)
      if meteor_yn_class[0][0] > .5:
         # NON METEOR DETECTED!
         meteor_yn = False 
      else:
         # METEOR DETECTED
         meteor_yn = True 

      # check fireball yn
      fireball_yn_class = self.model_meteor_fireball_yn.predict(img)
      meteor_fireball_yn_confidence = (1 - fireball_yn_class[0][0]) * 100
      print("DONE FIREBALL YN", meteor_fireball_yn_confidence)
      if fireball_yn_class[0][0] > .5:
         # NON METEOR DETECTED!
         meteor_fireball_yn = False 
      else:
         # METEOR DETECTED
         meteor_fireball_yn = True 

      if False:
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
      mc_w = width 
      mc_h = height
      mc_img = load_img(
         imgfile, target_size=(mc_h, mc_w)
      )
      img_array = img_to_array(mc_img)
      img_array = tf.expand_dims(img_array, 0) # Create a batch

      pred_result = self.model_multi_class.predict(img)

      #predictions = self.model_multi_class.predict(img_array)
      #score = tf.nn.softmax(predictions[0])
      #predicted_class = self.class_names[np.argmax(score)]
      #print("MC:", predicted_class, score)


      # Multi class i64
      # extract the class label which has the highest corresponding probability
      i = pred_result.argmax(axis=1)[0]
      label = self.multi_class_labels['moving_objects_i64'].classes_[i]
      predicted_class = label
      confidence = pred_result[0][i] * 100

      print("DONE MULTI :", predicted_class, confidence)

      response = {}
      response['roi'] = roi
      response['ai_version'] = 2
      response['meteor_yn'] = meteor_yn
      response['meteor_yn_confidence'] = float(meteor_yn_confidence)

      if "fireball" in predicted_class and (float(meteor_fireball_yn_confidence) > float(meteor_yn_confidence)) :
         meteor_fireball_yn = True

      response['meteor_fireball_yn'] = meteor_fireball_yn
      response['meteor_fireball_yn_confidence'] = float(meteor_fireball_yn_confidence)
      response['mc_class'] = predicted_class
      response['mc_class_confidence'] = confidence # int(100 * np.max(score))

      #response['meteor_or_plane_yn'] = meteor_or_plane_yn
      #response['meteor_or_plane_confidence'] = float(meteor_or_plane_confidence)
      #response['meteor_or_bird_yn'] = meteor_or_bird_yn
      #response['meteor_or_bird_confidence'] = float(meteor_or_bird_confidence)
      #response['meteor_or_firefly_yn'] = meteor_or_firefly_yn
      #response['meteor_or_firefly_confidence'] = float(meteor_or_firefly_confidence)


      final_yn_conf = max([meteor_yn_confidence,meteor_fireball_yn_confidence])
      #if "meteor" in response['mc_class']:
      #   final_yn_conf += response['mc_confidence']
      #else: 
      #   final_yn_conf -= (response['mc_confidence']/2)

      if meteor_yn is True or meteor_fireball_yn is True or "meteor" in response['mc_class']:
         final_yn = True
      else:
         final_yn = False 

      response['final_meteor_yn'] = final_yn 
      response['final_meteor_yn_conf'] = final_yn_conf
      if final_yn is True:
         # save sample
         roi_file = self.img_repo_dir + "meteor/" + self.station_id + "_" + root_fn + "-ROI.jpg"
      else:
         roi_file = self.img_repo_dir + "non_meteor/" + self.station_id + "_" + root_fn + "-RX_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2) + ".jpg"
      #print("saved", roi_file)
      cv2.imwrite(roi_file, oimg)
      response['roi_fn'] = roi_file.split("/")[-1]
      response['root_fn'] = root_fn
      

      return(response)


   def format_response(self, resp):
      descs = []
      color = [224,224,224]
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
         root_fn = meteor_file.replace(".json", "-ROI.jpg")

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
               resp = self.ASAI.meteor_yn(root_fn, None, img)
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

   def load_all_models(self):


      self.models = {}
      self.multi_class_labels = {}
      if os.path.exists("models/") is False:
         os.makedirs("models/")
      #if os.path.exists("models/moving_objects_i64.labels") is False:
      #   os.system("cp /mnt/archive.allsky.tv/AMS1/ML/moving_objects_i64.labels ./models/moving_objects_i64.labels")


      self.multi_class_labels['moving_objects_i64'] = pickle.loads(open("models/moving_objects_i64.labels", "rb").read())
      bin_model_files = ["meteor_prev_yn","meteor_yn_i64", "fireball_yn_i64", "star_yn"]
      cat_model_files = ["moving_objects_i64", "weather_condition"]
      for mf in bin_model_files:
         if os.path.exists("models/" + mf + ".h5") is False:
            os.system("cp /mnt/archive.allsky.tv/AMS1/ML/" + mf + ".h5 ./models/" + mf)
         if os.path.exists('models/' + mf + '.h5') is True:
            try:
               self.models[mf] = load_model('models/' + mf + '.h5', compile=False)
               self.models[mf].compile(loss='binary_crossentropy',
                  optimizer='rmsprop',
                  metrics=['accuracy'])
               print("loaded models/" + mf)
            except:
               print("loading exception/" + mf)
               exit()
         else:
            print("not found models/" + mf + ".h5")
            self.models[mf] = None

      for mf in cat_model_files:
         if os.path.exists("models/" + mf + ".h5") is True:
         #   os.system("cp /mnt/archive.allsky.tv/AMS1/ML/" + mf + ".h5 ./models/" + mf)
         #if True:
            try:
               self.models[mf] =load_model("models/" + mf + ".h5", compile=False)
               self.models[mf].compile(loss='categorical_crossentropy',
                  optimizer='rmsprop',
                  metrics=['accuracy'])
               self.multi_class_labels[mf] = pickle.loads(open("models/" + mf + ".labels", "rb").read())

               print("loaded models/" + mf)
            except:
               self.models[mf] = None
               print("not found models/" + mf)
               exit()
      print("Loaded models: ", self.models.keys())
         

   def load_all_models_old(self):
      """
         3 Primary Models Currently:
            meteor_yn_model.h5
            meteor_fireball_yn_model.h5
            multi_class_model.h5

            meteor_or_plane_model.h5
            meteor_or_bird_model.h5
            meteor_or_firefly_model.h5
      """
      # binary yn meteor models 
      self.model_meteor_yn = Sequential()
      self.model_meteor_prev_yn = Sequential()

      # binary A or B meteor models 
      # self.model_meteor_or_star = Sequential()
      # self.model_meteor_or_plane = Sequential()
      # self.model_fireball_or_plane = Sequential()

      # Multi class object and weather models 
      self.model_multi_class = Sequential()
      self.model_weather_condition = Sequential()

      model_files = ["meteor_prev_yn.h5","meteor_yn_i64.h5", "meteor_or_plane_i64.h5", "fireball_or_plane_i64.h5", "meteor_or_star.h5", "moving_objects_i64.h5", "weather_condition.h5"]
      # copy model files if they don't exist already!
      #if os.path.exists("models/meteor_prev_yn.h5") is False:
      #   print("Fetch meteor_prev_yn model")
      #   os.system("cp /mnt/archive.allsky.tv/AMS1/ML/meteor_prev_yn.h5 ./models/")

      if False:
         # these models we don't use anymore?
         if os.path.exists("models/fireball_or_plane_i64.h5") is True:
            self.model_meteor_yn =load_model('models/meteor_yn_i64.h5', compile=False)
            self.model_meteor_yn.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])
            print("loaded fireball_or_plane_i64.h5")
         else:
            self.model_meteor_yn = None
            print("Not found: models/meteor_meteor_yn.h5") 

         if os.path.exists("models/meteor_prev_yn.h5") is True:
            self.model_meteor_prev_yn =load_model('models/meteor_prev_yn.h5', compile=False)
            self.model_meteor_prev_yn.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])
            print("loaded meteor_prev_yn.h5")
         else:
            self.model_meteor_prev_yn = None
            print("Not found: models/meteor_prev_yn.h5") 

         if os.path.exists("models/meteor_or_star.h5") is True:
            self.model_meteor_or_star =load_model('models/meteor_or_star.h5', compile=False)
            self.model_meteor_yn.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])
            print("loaded meteor_or_star.h5")
         else:
            self.model_meteor_or_star = None
            print("Not found: models/meteor_or_star.h5") 



         if os.path.exists("models/fireball_or_plane_i64.h5") is True:
            self.model_meteor_fireball_yn =load_model('models/fireball_yn_i64.h5', compile=False)
            self.model_meteor_fireball_yn.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])
            print("loaded fireball_yn_i64.h5")
         else:
            self.model_meteor_fireball_yn = None
            print("Not found: models/meteor_or_fireball_yn.h5") 

         if os.path.exists("models/meteor_or_plane_i64.h5") is True:
            self.model_meteor_or_plane =load_model('models/meteor_or_plane_i64.h5', comile=False)
            self.model_meteor_or_plane.compile(loss='binary_crossentropy',
                 optimizer='rmsprop',
                 metrics=['accuracy'])
         else:
            self.model_meteor_or_plane = None
            print("Not found: models/meteor_or_plane.h5") 
            print("loaded meteor_or_plane.h5")

         if os.path.exists("models/meteor_or_plane_i64.h5") is True:
            self.model_fireball_or_plane =load_model('models/fireball_or_plane_i64.h5', compile=False)
            self.model_fireball_or_plane.compile(loss='binary_crossentropy',
              optimizer='rmsprop',
              metrics=['accuracy'])
         else:
            self.model_fireball_or_plane = None
            print("Not found: models/fireball_or_plane.h5") 
            print("loaded fireball_or_plane.h5")

      mo_lib = "moving_objects_i64"   
      print("models/" + mo_lib + ".h5")
      self.model_multi_class =load_model("models/" + mo_lib + ".h5", compile=False)
      self.model_multi_class.compile(loss='categorical_crossentropy',
         optimizer='rmsprop',
         metrics=['accuracy'])
      self.multi_class_labels[mo_lib] = pickle.loads(open("models/" + mo_lib + ".labels", "rb").read())


      if os.path.exists("models/weather_condition.h5") is True:
         self.model_weather_condition =load_model("models/weather_condition.h5", compile=False)
         self.model_weather_condition.compile(loss='categorical_crossentropy',
            optimizer='rmsprop',
            metrics=['accuracy'])
         self.weather_condition_classes = pickle.loads(open("models/weather_condition.labels", "rb").read())
         print("loaded weather_condition.h5")
      else:
         self.model_weather_condition = None
         print("Not found: models/weather_condition.h5") 


      print("Models loaded")




