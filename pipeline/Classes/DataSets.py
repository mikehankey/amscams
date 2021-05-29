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
         img = cv2.imread(trash_file)
         cv2.imshow('pepe', img)
         cv2.waitKey(10)
