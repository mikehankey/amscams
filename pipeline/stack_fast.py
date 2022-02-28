import sys
import time
import os
import glob
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops
import cython


def stack_only(sd_filename, mask_img):
   stack_file = sd_filename.replace(".mp4", "-stacked.jpg") 

   fc = 0
   thresh_adj = 0
   stack_file = sd_filename.replace(".mp4", "-stacked.jpg")
   cap = cv2.VideoCapture(sd_filename)

   while True:
      grabbed , color_frame = cap.read()
      if not grabbed and fc > 5:
         break
      if fc > 1:
         frame_sub = cv2.subtract(color_frame, last_frame)
         if np.max(frame_sub) > 15:
            # stacked_image = cv2.addWeighted(stacked_image, .5, color_frame, .5, .5)

            stacked_image=ImageChops.lighter(stacked_image,Image.fromarray(color_frame))
      else:
         print(fc) 
         print(color_frame.shape)
         stacked_image = Image.fromarray(color_frame)
 
      last_frame = color_frame
      fc += 1
   #stacked_image = stacked_image.astype(np.unit8)
  
   stacked_image = cv2.resize(np.asarray(stacked_image), (640,360))
   cv2.imwrite(stack_file, stacked_image)
   return(stacked_image)
 
def get_objects_in_stack(image_file, ASAI=None):
   objs = []
   image = cv2.imread(image_file)
   sub = image.copy()
   detect_file = image_file.replace("-stacked.jpg", "-objs.jpg") 
 
   print("IM:", image.shape)
   bw = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   hd_img = cv2.resize(image,(1920,1080))
   for i in range(0,11):
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw)
      x1,y1,x2,y2,roi_img= get_roi(image,mx,my,224,224) 
      max_val = np.max(roi_img)
      avg_val = np.mean(roi_img)
      px_diff = max_val - avg_val
      if px_diff < 10:
         continue
      root_fn = image_file.split("/")[-1] + "_" + str(i) + ".jpg"
      resp = ASAI.meteor_yn(root_fn, None, roi_img)   
      print(resp)
      mx1 = mx - 50
      mx2 = mx + 50
      my1 = my - 50
      my2 = my + 50
      if mx1 < 0:
         mx1 = 0
      if mx2 > image.shape[1]:
         mx2 = image.shape[1]-1
      if my1 < 0:
         my1 = 0
      if my2 > image.shape[0]:
         my2 = image.shape[0]-1

      bw[my1:my2,mx1:mx2] = 0
      print(i, x1,y1,x2,y2)
      desc = resp['mc_class'] + " " + str(resp['mc_class_confidence'])[:4] + "%"
      if resp['meteor_yn_confidence'] > resp['meteor_fireball_yn_confidence']:
         mconf = resp['meteor_yn_confidence']
      else:
         mconf = resp['meteor_fireball_yn_confidence']
      desc2 = str(mconf)[0:4] + "% meteor"

      cv2.putText(hd_img, desc,  (x1,y2 ), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
      cv2.putText(hd_img, desc2,  (x1,y2-20 ), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
      cv2.rectangle(hd_img, (x1,y1), (x2, y2) , (255, 255, 255), 1)
      # do detect here!
   cv2.imwrite(detect_file, hd_img)
   print("Saved !", detect_file)
   

def get_roi(image,mx,my,rw,rh):
   oih,oiw = image.shape[0:2]
   hd_img = cv2.resize(image,(1920,1080))
   hdm_x = 1920 / oiw
   hdm_y = 1080 / oih
   x1 = int(mx*hdm_x) - int(rw / 2)
   y1 = int(my*hdm_y) - int(rh / 2)
   x2 = int(mx*hdm_x) + int(rw / 2)
   y2 = int(my*hdm_y) + int(rh / 2)
   if x1 < 0:
      x1 = 0 
      x2 = x1 + rw
   if y1 < 0:
      y1 = 0 
      y2 = y1 + rh

   if x2 > 1920:
      x2 = 1919 
      x1 = x2 - rw
   if y2 > 1080:
      y2 = 1080 
      y1 = y2 - rh
   roi_img = hd_img[y1:y2,x1:x2]
   return(x1,y1,x2,y2,roi_img)


# MAIN SCRIPT

if __name__ == "__main__":
   vfile = sys.argv[1]
   cam_id = vfile.split("_")[-1].replace(".mp4", "")
   station_id = "AMS1"
   #mask_img = get_mask(station_id, cam_id)
   mask_img = blank_image = np.zeros((1080,1920,3),dtype=np.uint8)
   t = time.time()
   stack_only(vfile, mask_img )
   e = time.time() - t
   print(e)
