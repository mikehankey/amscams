import cv2
import os
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops



class AllSkyAI():

   def __init__(self):
      print("AllSkyAI is self aware.")

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
      thresh_val = max_val * .8
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
         if x != 0 and y != 0 and w > 1 and h > 1:
            cont.append((x,y,w,h))
      return(cont)

