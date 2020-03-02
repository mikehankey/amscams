#!/usr/bin/python3
import time
import sys
#import fastThresh 
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops

def stack_stack(pic1, pic2):
   stacked_image=ImageChops.lighter(pic1,pic2)
   return(stacked_image)

def scan_stack_fast(file, day = 0):
   stack_file = file.replace(".mp4", "-stacked.png")
   PREVIEW_W = 300
   PREVIEW_H = 169
   start_time = time.time() 

   fc = 0
   print("Loading file:", file)
   cap = cv2.VideoCapture(file)
   frames = []
   gray_frames = []
   sub_frames = []
   fd = []
   stacked_image = None
   while True:
      grabbed , frame = cap.read()
 
      if not grabbed and fc > 5:
         print(fc)
         break
      

      if day == 1:
         small_frame = cv2.resize(frame, (0,0),fx=.5, fy=.5)
      else:
         small_frame = cv2.resize(frame, (0,0),fx=.5, fy=.5)

    
      if day != 1: 
         gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
         if fc > 0:
            sub = cv2.subtract(gray, gray_frames[-1])
         else:
            sub = cv2.subtract(gray, gray)

         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         if max_val < 10:
            data = fc, 0, 0, 0, 0
         else:
            _, thresh_frame = cv2.threshold(sub, 15, 255, cv2.THRESH_BINARY)
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(thresh_frame)
            sum_val =cv2.sumElems(thresh_frame)[0]
            mx = mx * 2
            my = my * 2
            data = fc, sum_val, max_val, mx, my
         gray_frames.append(gray)

      if day == 1:
         if fc % 10 == 1:
            frame_pil = Image.fromarray(small_frame)
            if stacked_image is None:
               stacked_image = stack_stack(frame_pil, frame_pil)
            else:
               stacked_image = stack_stack(stacked_image, frame_pil)
      else:
         if max_val > 10 or fc < 10:
            frame_pil = Image.fromarray(small_frame)
            if stacked_image is None:
               stacked_image = stack_stack(frame_pil, frame_pil)
            else:
               stacked_image = stack_stack(stacked_image, frame_pil)

      frames.append(frame)
      if fc % 100 == 1:
         print(fc)
      fc += 1
   cv_stacked_image = np.asarray(stacked_image)
   cv_stacked_image = cv2.resize(cv_stacked_image, (PREVIEW_W, PREVIEW_H))
   cv2.imwrite(stack_file, cv_stacked_image)

   elapsed_time = time.time() - start_time
   print(stack_file)
   print("Elp:", elapsed_time)


scan_stack_fast(sys.argv[1])

#img = cv2.UMat(cv2.imread("/mnt/ams2/SD/proc2/2020_03_02/images/2020_03_02_16_16_37_000_010005-stacked-tn.png" , cv2.IMREAD_COLOR))
#imgUMat = cv2.UMat(img)
#gray = cv2.GaussianBlur(gray, (7, 7), 1.5)
#gray = cv2.Canny(gray, 0, 50)


