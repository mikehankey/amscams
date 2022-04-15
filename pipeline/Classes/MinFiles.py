import sys
import os
import glob
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops



from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs
from Detector import Detector

class MinFiles:
   def __init__(self):
      print("MinFiles Manager
         - Manager Class for handling the min files on the system
      ")

   def redis_index_min_files:      
      night_dir "/mnt/ams/SD/proc2/"
      day_dir = "/mnt/ams/SD/proc2/daytime/"
