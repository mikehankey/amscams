from decimal import Decimal
import glob
import json
import math
import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

from PIL import ImageFont, ImageDraw, Image, ImageChops

from Classes.DisplayFrame import DisplayFrame
from Classes.Detector import Detector
from Classes.Camera import Camera
from Classes.Event import Event
from Classes.Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.FFFuncs import best_crop_size, ffprobe
import boto3
import socket

class DataSets():
   def __init__(self):
      self.labels = ["Meteors", "Non-Meteors"]
      self.label = ""

   def build_dataset(self,label):
      self.trashfiles = []
      if label == "Non-Meteors":
         cmd = "ls /mnt/ams2/trash/2021*/* |grep stacked.jpg |grep -v HD > /mnt/ams2/trash/trash_files.txt"
         os.system(cmd)
         fp = open("/mnt/ams2/trash/trash_files.txt")
         for line in fp:
            self.trashfiles.append(line.replace("\n", ""))
      for trash_file in self.trashfiles:
         print(trash_file)
         jsf = trash_file.replace("-stacked.jpg", ".json")
         mj = load_json_file(jsf)
         if "best_meteor" in mj:
            print(mj['best_meteor']['oxs'])
         img = cv2.imread(trash_file)
         ih,iw = img.shape[:2]
         hdm_x = 1920/iw
         hdm_y = 1920/ih
         bw_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
         thresh_val = np.mean(bw_img) + 50
         _, threshold = cv2.threshold(bw_img.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         threshold = cv2.dilate(threshold.copy(), None , iterations=4)
         #img = threshold 
         cnts = self.get_contours_simple(threshold, bw_img)

         if len(cnts) > 3:
            cnts = cnts[0:5]
         cntc = 0
         for cnt in cnts:
            x,y,w,h,intensity = cnt
            cx = int(x + (w/2))
            cy = int(y + (h/2))
            if w > h:
               h = w
            else:
               w = h
            if w > 10 and h > 10:
               x1 = cx - w
               y1 = cy - h 
               x2 = cx + w
               y2 = cy + h 
               if x1 <= 0:
                  x1 = 0 
                  x2 = x1 + w
               if y1 <= 0:
                  y1 = 0 
                  y2 = y1 + h
               if x2 >= iw:
                  x1 = iw - w 
                  x2 = iw
               if y2 >= ih:
                  y1 = ih - h
                  y2 = h

               sane = ((x2 - x1) / (y2 - y1))
               if sane == 1:
                  cv2.rectangle(img, (x1,y1), (x2,y2), (255, 255, 255), 1) 
                  crop = img[y1:y2,x1:x2]
                  img_fn = trash_file.split("/")[-1]

                  img_fn = "/mnt/ams2/datasets/training/nonmeteors/" + img_fn
                  img_fn = img_fn.replace(".jpg", "-" + str(cntc) + ".jpg")
                  cntc + 1
                  cv2.imwrite(img_fn, crop)
                  print("    " + img_fn)
         cv2.imshow('pepe', img)
         cv2.waitKey(30)

   def get_contours_simple(self,image,sub):
      cnt_res = cv2.findContours(image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

      conts = []
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(sub[y:y+h,x:x+w]))
         conts.append((x,y,w,h,intensity))
      conts = sorted(conts, key=lambda x: ((x[2]+x[3])), reverse=True)
      return(conts)

