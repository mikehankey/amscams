import cv2
import os
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops
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
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
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
      self.class_names = [
         'birds',
         'bugs',
         'cars',
         'clouds',
         'meteors_bright',
         'meteors_faint',
         'meteors_fireballs',
         'meteors_long',
         'meteors_medium',
         'meteors_short',
         'moon',
         'noise',
         'planes',
         'raindrops',
         'stars',
         'trees'
      ]
      self.class_names = sorted(self.class_names)

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
      print("MF:", model_file)
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
      print("CLASS:", np.argmax(score), predicted_class)
      return(predicted_class)


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
            print("found", mif)
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
