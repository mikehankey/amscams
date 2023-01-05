#!/usr/bin/python3
import sys
import os
import glob
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.PipeUtil import load_json_file




def stack_stack( pic1, pic2):
      stacked_image=ImageChops.lighter(ipic1,ipic2)
      return(stacked_image)



def stack_video(video_file):
   if "/" not in video_file:
      date = video_file[0:10]
      vmdir = "/mnt/ams2/meteors/" + date + "/" + video_file
      video_file = vmdir
   if os.path.exists(video_file) is False:
      print("Video file not found!", video_file)
      exit()

   red_file = video_file.replace(".mp4", "-reduced.json")
   if os.path.exists(red_file) is True:
      red_data = load_json_file(red_file)
   else:
      red_data = None

   cap = cv2.VideoCapture(video_file)
   stacked_image = None
   frame = True
   while frame is not None:
      # grab each frame in video file
      grabbed , frame = cap.read()
      if frame is None:
         break
      frame_pil = Image.fromarray(frame)

      if stacked_image is None:
         stacked_image = stack_stack(frame_pil, frame_pil)
      else:
         stacked_image = stack_stack(stacked_image, frame_pil)
   image_file = video_file.replace(".mp4", "-stacked.jpg")
   stacked_image = np.asarray(stacked_image)
   cv2.imwrite(image_file, stacked_image)

   # Lets re-save the thumns, half stack too!
   thumb_img = cv2.resize(stacked_image, (320, 180))
   thumb_file = image_file.replace(".jpg", "-tn.jpg")
   obj_file = image_file.replace(".jpg", "-obj-tn.jpg")
   cv2.imwrite(thumb_file, thumb_img)

   # make the obj img if we have red data!
   if red_data is not None:
      hdm_x = 1920 / 320 
      hdm_y = 1080 / 180 
      if "meteor_frame_data" in red_data:
         xs = []
         ys = []
         for row in red_data['meteor_frame_data']:
            xs.append(row[2])
            ys.append(row[3])
         if len(xs) > 0:
            min_x = int(min(xs) / hdm_x)
            max_x = int(max(xs) / hdm_x)
            min_y = int(min(ys) / hdm_y)
            max_y = int(max(ys) / hdm_y)


    
            obj_img = thumb_img
            cv2.rectangle(obj_img, (min_x,min_y), (max_x, max_y) , (255, 255, 255), 1)



            cv2.imwrite(obj_file, obj_img)
   print("Saved", image_file)
   print("Saved", thumb_file)
   print("Saved", obj_file)

stack_video(sys.argv[1])
