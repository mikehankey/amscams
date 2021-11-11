import os
from lib.PipeUtil import load_json_file, save_json_file
from tensorflow import keras
from tensorflow.keras.models import *
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
import cv2
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img
import glob
SHOW = 0

def predict_images(imgs, model_file, label):
   print("MODEL:", model_file)
   #repo_dir = "Y:/datasets/images/repo/" 
   repo_dir = "/mnt/ams2/datasets/images/repo/" 
   model = Sequential()
   
   #model =load_model('first_try_model.h5')
   model =load_model(model_file)
   model.compile(loss='binary_crossentropy',
                 optimizer='rmsprop',
                 metrics=['accuracy'])
   
   human_data_file = "/mnt/ams2/datasets/human_data.json"
   machine_data_file = "/mnt/ams2/datasets/machine_data_" + label + ".json"
   if os.path.exists(human_data_file):
      human_data = load_json_file(human_data_file)
   else:
      human_data = {}
   if os.path.exists(machine_data_file):
      machine_data = load_json_file(machine_data_file)
   else:
      machine_data = {}
   
   if SHOW == 1: 
      cv2.namedWindow("pepe")
      cv2.moveWindow("pepe", 2000,100)
   
   for imgfile in imgs:
      img_fn = imgfile.split("/")[-1]
      if img_fn in machine_data:
         label, score = machine_data[img_fn]
         if score < .5 or label == "METEOR":
            continue

      
      oimg = cv2.imread(imgfile)
      orig_img = oimg.copy()
      oimg = cv2.resize(oimg,(150,150))
   
      img = np.reshape(oimg,[1,150,150,3])
      img_size = [150,150]
      img = keras.preprocessing.image.load_img(imgfile, target_size = img_size)
      img = keras.preprocessing.image.img_to_array(img).astype(np.float32)
      img /= 255.
      img = np.expand_dims(img, axis = 0)
      classes = model.predict(img)
      
      if classes[0][0] > .5:
         #cv2.putText(oimg, "NONMETEOR", (20,20), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 255), 1)
         print ("NON METEOR:", classes)
         #cv2.imshow('pepe', oimg)
         #key = cv2.waitKey(5)
         predict = "NONMETEOR"
         repo_file = repo_dir + "nonmeteors/" + img_fn
         #if os.path.exists(repo_file) is False:
         #if False:
         #   cv2.imwrite(repo_file, orig_img)
            #print("SAVED:", repo_file)

      else:
         #cv2.putText(oimg, "METEOR", (20,20), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 255, 0), 1)
         print("METEOR:", classes)
         #cv2.imshow('pepe', oimg)
         #key = cv2.waitKey(5)
         predict = "METEOR"
         repo_file = repo_dir + "meteors/" + img_fn
         #if os.path.exists(repo_file) is False:
         #if False:
         #   cv2.imwrite(repo_file, orig_img)
            #print("SAVED:", repo_file)
   
      machine_data[img_fn] = [predict, float(classes[0][0])]
   
         
   
   save_json_file(human_data_file, human_data)
   save_json_file(machine_data_file, machine_data)
