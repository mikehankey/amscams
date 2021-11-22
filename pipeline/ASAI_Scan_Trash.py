import os
from lib.PipeDetect import get_contours_in_image, find_object
from lib.PipeUtil import load_json_file, save_json_file, mfd_roi,  convert_filename_to_date_cam 
import cv2
import numpy as np
import glob
import platform
import shutil

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

Tensor = False
if Tensor is True:
   import keras
   from keras.models import *
   import keras
   from keras.models import load_model
   from keras.models import Sequential
   from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img
   from Meteor_Predict import mfd_roi


json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
img_height=150
img_width=150
class_names = [
'bugs','cars','clouds','meteors_bright','meteors_fireballs','meteors_long','meteors_medium','meteors_short','noise','planes','raindrops'
]

OS_SYS = platform.system()
if OS_SYS == "Windows":
   DATA_DIR = "Y:/"
else:
   DATA_DIR = "/mnt/ams2/"

def restore_meteor(meteor_file):
   print("METEOR FILE:", meteor_file)
   if "\\" in meteor_file:
      meteor_file = meteor_file.replace("\\", "/")
   mfn = meteor_file.split("/")[-1]
   mj = load_json_file(meteor_file)
   print("MFN:", mfn)
   meteor_dir = DATA_DIR + "meteors/" + mfn[0:10] + "/"
   print("METEOR_DIR:", mfn)
   if "hd_trim" in mj:
      hd_trim = mj['hd_trim']
   else:
      hd_trim = ""
   sd_wild = meteor_file.replace(".json", "*")
   #shutil.move(sd_wild, meteor_dir)
   print("move", (sd_wild, meteor_dir))
   print("SD WILD:", sd_wild)
   sdfs = glob.glob(sd_wild)
   for fs in sdfs:
      cmd = "move " + fs + " " + meteor_dir
      print(cmd)
      os.system(cmd)

   if hd_trim is not None:
      hd_wild = hd_trim.replace(".json", "*")
      if OS_SYS == "Windows":
         hd_wild = hd_wild.replace("/mnt/ams2/", DATA_DIR)
         hd_wild = hd_wild.replace("meteors", "trash")
         hd_wild = hd_wild.replace(".mp4", "*")
      print("HD WILD:", hd_wild)
      hdfs = glob.glob(hd_wild)
      for fs in hdfs:
         cmd = "move " + fs + " " + meteor_dir
         os.system(cmd)

def get_trash_rois():
   roi_files = []
   trash_dirs = []
   trash_dir = DATA_DIR + "trash/"
   tds = glob.glob(trash_dir + "*")
   for td in tds:
      if os.path.isdir(td) is True:
         trash_dirs.append(td)
   json_files = []
   for td in trash_dirs:
      jss = glob.glob(td + "/*.json")
      for js in jss:
         if "reduced" not in js:
            json_files.append(js)
   #cv2.namedWindow("pepe")
   fc = 0
   for js in json_files:
      print(js)
      fc += 1
      stack_file = js.replace(".json", "-stacked.jpg")
      mj = load_json_file(js)
      roi_file = stack_file.replace("-stacked.jpg", "-ROI_T" + str(0) +".jpg")
      if os.path.exists(roi_file) is False:
         roi_imgs = roi_from_stack(stack_file)
      else:
         roi_imgs = []
      cc = 0
      if roi_imgs is not None:
         for roi_img in roi_imgs:
            roi_file = stack_file.replace("-stacked.jpg", "-ROI_T" + str(cc) +".jpg")
            cv2.imwrite(roi_file, roi_img)
            print("SAVED:", roi_file)
            roi_files.append(roi_file)
            cc += 1

      roi_file = stack_file.replace("-stacked.jpg", "-ROI" + str(0) +".jpg")
      if "confirmed_meteors" in mj and os.path.exists(roi_file) is False:
         cc = 0
         all_non = 0
         for cm in mj['confirmed_meteors']:
            roi_file = stack_file.replace("-stacked.jpg", "-ROI" + str(cc) +".jpg")
            if os.path.exists(roi_file) is True:
               print("ROI ALREADY DONE:", roi_file)
               roi_files.append(roi_file)
               cc += 1
               continue
            x1,y1,x2,y2 = mfd_roi(None, cm['oxs'], cm['oys'])
            print("ROI:", roi_file)

            img = cv2.imread(stack_file)
            roi_img = img[y1:y2,x1:x2]
            cv2.imwrite(roi_file, roi_img)
            roi_files.append(roi_file)

            cc += 1


   return(roi_files)


def roi_from_stack(stack_file):
   (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) =  convert_filename_to_date_cam(stack_file)
   mask_file = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/MASKS/" + cam + "_mask.png"
   if os.path.exists(stack_file) is True:
      stack_img = cv2.imread(stack_file)
   if stack_img is None:
      return(None)
   sh,sw = stack_img.shape[:2]
   if os.path.exists(mask_file) is True:
      mask_img = cv2.imread(mask_file)
      mask_img = cv2.resize(mask_img, (sw,sh))
   else:
      mask_img = None
   if mask_img is not None:
      stack_img = cv2.subtract(stack_img, mask_img)
   gray =  cv2.cvtColor(stack_img, cv2.COLOR_BGR2GRAY) 
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
   _, threshold = cv2.threshold(gray.copy(), max_val * .8, 255, cv2.THRESH_BINARY)
   cnts = get_contours_in_image(threshold)
   mfd = []
   cxs = []
   cys = []
   objects = {}
   fn = 1
   for cx,cy,cw,ch in cnts:
      obj, objects = find_object(objects, fn,cx, cy, cw, ch, 0, 0, 0, None)
      fn += 1

   roi_imgs = []
   for obj_id in objects:
      x1,y1,x2,y2 = mfd_roi(None, objects[obj_id]['oxs'], objects[obj_id]['oys'])
      roi_img = stack_img[y1:y2,x1:x2]
      roi_imgs.append(roi_img)


      #cv2.rectangle(threshold, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
   return(roi_imgs)

def load_my_model(model_file = None):
   if model_file is None:
      model_file = "multi_class_model.h5"

   model = Sequential()

   model =load_model(model_file)
   model.compile(loss='categorical_crossentropy',
      optimizer='rmsprop',
      metrics=['accuracy'])
   return(model)

def predict_image(imgfile, model):
   #img = keras.utils.load_img(
   img = load_img(
      imgfile, target_size=(img_height, img_width)
   )
   show_img = cv2.imread(imgfile)
   img_array = img_to_array(img)
   img_array = tf.expand_dims(img_array, 0) # Create a batch

   predictions = model.predict(img_array)

   score = tf.nn.softmax(predictions[0])
   predicted_class = class_names[np.argmax(score)]
   return(predicted_class)

def predict_images(roi_files,model=None):
   data_dir = "/mnt/ams2/datasets/learning/trash/"
   if model is None:
      model = load_my_model()
   
   human_data_file = "/mnt/ams2/datasets/human_data.json"
   machine_data_file = "/mnt/ams2/datasets/" + station_id + "_ML_DATA.json"
   if os.path.exists(human_data_file):
      human_data = load_json_file(human_data_file)
   else:
      human_data = {}
   if os.path.exists(machine_data_file):
      machine_data = load_json_file(machine_data_file)
   else:
      machine_data = {}
   
   
   
   for imgfile in sorted(roi_files, reverse=True):
      img_fn = imgfile.split("/")[-1]
      if "img_fn" in machine_data:
         print("ALREADY DONE:", img_fn)
         continue
      predict_class = predict_image(imgfile, model)
      print(imgfile, predict_class)
      tdir = data_dir + predict_class + "/" 
      if os.path.exists(tdir) is False:
         os.makedirs(tdir)
      machine_data[img_fn] = predict_class
      cmd = "cp " + imgfile + " " + tdir
      print(cmd)
      os.system(cmd)
   
         
   
   #save_json_file(human_data_file, human_data)
   save_json_file(machine_data_file, machine_data)

roi_files = get_trash_rois()
model = load_my_model()
predict_images(roi_files, model)
for roi_file in roi_files:
   print(roi_file)
