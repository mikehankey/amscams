import sys
from Lib.ASAI_Predict import predict_images

import glob
import keras
import os
from keras.models import *
from Lib.Utils import load_json_file, save_json_file
import keras
from keras.models import load_model
from keras.models import Sequential
import cv2
import numpy as np
from keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img
import glob

roi_files = []
machine_data_file = "Y:/datasets/machine_data_meteors.json"
#dataset = "../learning/meteors_short/"
machine_data = load_json_file(machine_data_file)
model_file = "multi_class_model.h5"

model = Sequential()

model =load_model(model_file)
model.compile(loss='categorical_crossentropy',
   optimizer='rmsprop',
   metrics=['accuracy'])


#lfs = glob.glob(dataset + "*")
c = 0
img_height = 150
img_width = 150
batch_size = 32
#print("DATASET DIR:", dataset)
selected_class = "meteors_short"
root_data_dir = "D:/MRH/learning/" 
data_dir = "D:/MRH/learning/" + selected_class + "/"
train_dir = "D:/MRH/learning/WORK/training/"
class_names = sorted(os.listdir(train_dir))
img_height=150
img_width=150

for imgfile in glob.glob(data_dir + "*.jpg"):
   if os.path.exists(imgfile) is False:
      continue
   img = tf.keras.utils.load_img(
      imgfile, target_size=(img_height, img_width)
   )
   show_img = cv2.imread(imgfile)
   img_array = tf.keras.utils.img_to_array(img)
   img_array = tf.expand_dims(img_array, 0) # Create a batch

   predictions = model.predict(img_array)

   score = tf.nn.softmax(predictions[0])
   predicted_class = class_names[np.argmax(score)]
   unsure_dir = root_data_dir + "uncertain/" + selected_class + "/" + "/" + predicted_class + "/" 
   reclass_dir = root_data_dir + "reclass/" + selected_class + "/"  + "/" + predicted_class + "/"
   if os.path.exists(unsure_dir) is False:
      print("MAKE DIR:", unsure_dir)
      os.makedirs(unsure_dir)
   if os.path.exists(reclass_dir) is False:
      print("MAKE DIR:", reclass_dir)
      os.makedirs(reclass_dir)

   print(
    "This image most likely belongs to {} with a {:.2f} percent confidence."
    .format(class_names[np.argmax(score)], 100 * np.max(score))
   )
   desc = class_names[np.argmax(score)] + " " + str(int(100 * np.max(score))) + "%"
   cv2.putText(show_img, desc, (20,20), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 0, 255), 1)
   print(imgfile)
   if "\\" in imgfile:
      print("BACKSLASH")
      fn = imgfile.split("\\")[-1]
   else:
      fn = imgfile.split("/")[-1]
   ih = show_img.shape[0] - 5
   cv2.putText(show_img, fn[0:20], (0,ih), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 0, 255), 1)
   cv2.imshow("pepe", show_img)
   if selected_class not in class_names[np.argmax(score)] :
      print("MOVE TO:", reclass_dir + fn)
      cv2.waitKey(50)
      os.rename(imgfile, reclass_dir + fn)
   else:
      cv2.waitKey(5)
      print("GOOD CLASS:", imgfile)


