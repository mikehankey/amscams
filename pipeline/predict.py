#!/usr/bin/python3

import numpy as np
import sys
#from lib.PipeUtil import load_json_file, save_json_file , mfd_roi
import cv2
#from lib.ASAI_Predict import predict_images
import glob
import tensorflow as tf
import os
from tensorflow import keras
from tensorflow.keras.models import *
import tensorflow.keras
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img

img_height = 150
img_width = 150
selected_class = "meteors"
data_dir = "/mnt/ams2/datasets/learning/scan_results/" + selected_class + "/"

# LABELS
class_names = [
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
'trees',
        ]
class_names = sorted(class_names)

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
