"""

script to export trash for learning purposes

"""
import os
import cv2


st_id = "AMS1"
trash_learn = "/mnt/ams2/AI/DATASETS/TRASH/"
if os.path.exists(trash_learn) is False:
   os.makedirs(trash_learn)


tfolders = []
trash_folder = "/mnt/ams2/trash/"
temp = os.listdir(trash_folder)
for t in temp:
   if os.path.isdir(trash_folder + t) :
      tfolders.append(trash_folder + t + "/")


jpgs = []
for tf in tfolders:
   files = os.listdir(tf)
   for f in files:
      if "stacked.jpg" in f and "HD" not in f:
         jpgs.append(tf + f)


for jpg in jpgs:
   fn = jpg.split("/")[-1]
   if os.path.exists(trash_learn + fn) is False:
      img = cv2.imread(jpg)
      img = cv2.resize(img, (640,360))
      cv2.imwrite(trash_learn + fn, img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
      print("Learning from trash:", fn)

print("Export / check ROIs Objects")

from Classes.ReviewNetwork import ReviewNetwork
import sys

date = sys.argv[1]
RN = ReviewNetwork(date)

for jpg in jpgs:
   fn = jpg.split("/")[-1]
   if os.path.exists(trash_learn + fn) is True:
      img = cv2.imread(jpg)
      img = cv2.resize(img, (1920,1080))
      objects = RN.detect_objects_in_stack(st_id, fn, img.copy())
      print(objects)

      #resp = ASAI.meteor_yn("temp.jpg", None, roi_img_1080p_224)
