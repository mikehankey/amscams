import keras
import os
from keras.models import *
from Lib.Utils import load_json_file, save_json_file
import cv2
import numpy as np
import glob
import platform
import shutil

Tensor = False
if Tensor is True:
   import keras
   from keras.models import load_model
   from keras.models import Sequential
   from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img
   from Meteor_Predict import mfd_roi

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
   if Tensor is True:
      model = Sequential()
   
      model =load_model('first_try_model.h5')
      model.compile(loss='binary_crossentropy',
                 optimizer='rmsprop',
                 metrics=['accuracy'])

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
   for js in json_files:
      print(js)
      stack_file = js.replace(".json", "-stacked.jpg")
      mj = load_json_file(js)
      if "confirmed" in mj:
         print("OBJS:", mj['confirmed'])
      if "confirmed_meteors" in mj:
         cc = 0
         all_non = 0
         for cm in mj['confirmed_meteors']:
            print("ALL_NON:", all_non)
            print("xs", cm['oxs'] )
            print("ys", cm['oys'] )
            x1,y1,x2,y2 = mfd_roi(None, cm['oxs'], cm['oys'])
            print("STACK:", stack_file)
            print("ROI:", x1,y1,x2,y2)
            img = cv2.imread(stack_file)
            try:
               show_img = img.copy()
            except:
               continue
            roi_img = img[y1:y2,x1:x2]
            roi_file = stack_file.replace("-stacked.jpg", "-ROI" + str(cc) +".jpg")
            cv2.imwrite(roi_file, roi_img)

            img = cv2.resize(img,(150,150))
   
            img = np.reshape(img,[1,150,150,3])
            img_size = [150,150]
            if Tensor is True:
               img = keras.preprocessing.image.load_img(roi_file, target_size = img_size)
               img = keras.preprocessing.image.img_to_array(img).astype(np.float32)
               img /= 255.
               img = np.expand_dims(img, axis = 0)
               classes = model.predict(img)
            if "\\" in stack_file:
               stack_file = stack_file.replace("\\", "/")
            stack_fn = stack_file.split("/")[-1]
            roi_file = DATA_DIR + "datasets/images/repo/nonmeteors/" + stack_fn.replace("-stacked.jpg", "-ROI" + str(cc) + ".jpg")
            if Tensor is True:
               if classes[0][0] < .5:
                  label = "meteors"
                  color = [0,255,0]
                  roi_file = DATA_DIR + "datasets/images/repo/" + label + "/" + stack_fn.replace("-stacked.jpg", "-ROI" + str(cc) + ".jpg")
               else:
                  label = "nonmeteors"
                  color = [0,0,255]
                  roi_file = DATA_DIR + "datasets/images/repo/" + label + "/" + stack_fn.replace("-stacked.jpg", "-ROI" + str(cc) + ".jpg")

            if Tensor is True:
               cv2.putText(show_img, str(classes[0][0]), (20,20), cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1)
               cv2.rectangle(show_img, (x1, y1), (x2,y2), (255, 255, 255), 1)
               cv2.imshow('pepe', show_img)
               if all_non == 0:
                  key = cv2.waitKey(0)
               else:
                  cv2.waitKey(30)
                  key = ""
               print("KEY:", key)
               print("ALL NON:", all_non)
               if str(key) == "27":
                  exit()
               if str(key) == "109":
                  # Meteor
                  label = "meteors"
                  roi_file = DATA_DIR + "datasets/images/repo/" + label + "/" + stack_fn.replace("-stacked.jpg", "-ROI" + str(cc) + ".jpg")
                  cv2.imwrite(roi_file,roi_img)
                  print("SAVED :", roi_file)
                  restore_meteor(js)
               if str(key) == "97":
                  all_non = 1
                  label = "nonmeteors"
                  roi_file = DATA_DIR + "datasets/images/repo/" + label + "/" + stack_fn.replace("-stacked.jpg", "-ROI" + str(cc) + ".jpg")
                  print("************************************************** A key hit ALL NON", all_non)
               if str(key) == "110" or all_non == 1:
                  # Non Meteor
                  print("NON METEOR!")
                  print("SAVED :", roi_file)
                  cv2.imwrite(roi_file,roi_img)
            else:
               roi_file = DATA_DIR + "datasets/images/repo/nonmeteors/" + stack_fn.replace("-stacked.jpg", "-ROI" + str(cc) + ".jpg")
               cv2.imwrite(roi_file,roi_img)
            cc += 1

def predict_images(roi_files):
   model = Sequential()
   
   model =load_model('first_try_model.h5')
   model.compile(loss='binary_crossentropy',
                 optimizer='rmsprop',
                 metrics=['accuracy'])
   
   label = "meteors"
   
   human_data_file = "Y:/datasets/human_data.json"
   machine_data_file = "Y:/datasets/machine_data_" + label + ".json"
   if os.path.exists(human_data_file):
      human_data = load_json_file(human_data_file)
   else:
      human_data = {}
   if os.path.exists(machine_data_file):
      machine_data = load_json_file(machine_data_file)
   else:
      machine_data = {}
   
   
   
   data_dir = "Y:/datasets/images/training/" + label + "/" 
   if "meteors" in data_dir:
      meteor_data = 1
   else:
      meteor_data = 0
   
   imgs = glob.glob("Y:/datasets/images/training/" + label + "/*")
   cv2.namedWindow("pepe")
   cv2.moveWindow("pepe", 2000,100)
   nonmeteor = ""
   
   
   
   meteor = ""
   for imgfile in imgs:
      img_fn = imgfile.split("/")[-1]
      
      print(imgfile)
      oimg = cv2.imread(imgfile)
      oimg = cv2.resize(oimg,(150,150))
   
      img = np.reshape(oimg,[1,150,150,3])
      img_size = [150,150]
      img = keras.preprocessing.image.load_img(imgfile, target_size = img_size)
      img = keras.preprocessing.image.img_to_array(img).astype(np.float32)
      img /= 255.
      img = np.expand_dims(img, axis = 0)
      classes = model.predict(img)
      #if img_fn in human_data: 
         #cv2.imshow('pepe', oimg)
         #key = cv2.waitKey(30)
         #continue
      
      if classes[0][0] > .5:
         cv2.putText(oimg, "NONMETEOR", (20,20), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 1)
         print ("NON METEOR:", classes)
         cv2.imshow('pepe', oimg)
         key = cv2.waitKey(0)
         predict = "NONMETEOR"
      else:
         cv2.putText(oimg, "METEOR", (20,20), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 1)
         print("METEOR:", classes)
         cv2.imshow('pepe', oimg)
         key = cv2.waitKey(30)
         predict = "METEOR"
   
      machine_data[img_fn] = predict
   
      print("KEY:", key)
      if str(key) == "32":
         # SPACE - ACCEPT WHAT THE RESULT OF THE AI PREDICTOR 
         human_data[img_fn] = predict
   
      if str(key) == "110":
         # NON_METEOR - IF IMAGE IS CURRENTLY LABELED AS METEOR MOVE IT TO TO NON_METEOR DIR
         human_data[img_fn] = "NONMETEOR"
      if str(key) == "109":
         # METEOR - IF IMAGE IS CLASSED AS NONMETEOR MOVE IT TO METEOR DIR
         human_data[img_fn] = "METEOR"
      if str(key) == "115":
         # save file
         save_json_file(human_data_file, human_data)
      if str(key) == "27":
         # save file
         save_json_file(human_data_file, human_data)
         exit()
         
   
   save_json_file(human_data_file, human_data)
   save_json_file(machine_data_file, machine_data)

get_trash_rois()
