#!/usr/bin/python3
import sys
import os
import glob
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops




def stack_stack( pic1, pic2):
      stacked_image=ImageChops.lighter(pic1,pic2)
      return(stacked_image)



def stack_video(video_file):
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
   print("Saved", image_file)


stack_video(sys.argv[1])
