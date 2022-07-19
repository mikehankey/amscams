
#import acapture
import cv2

import sys
import time
import os
import glob
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops
import cython

def stack_only(sd_filename, mask_img):
   if os.path.exists(sd_filename) is False:
      print("not found", sd_filename)
      exit()

   if "\\" in sd_filename:
      sd_filename = sd_filename.replace("\\", "/")
   stack_file = sd_filename.replace(".mp4", "-stacked.jpg") 

   fc = 0
   thresh_adj = 0
   stack_file = sd_filename.replace(".mp4", "-stacked.jpg")
   cap = cv2.VideoCapture(sd_filename)
   #cap = acapture.open(sd_filename)
   max_pxs = []
   fns = []
   saved_frames = {}
   frames = []
   while True:
      grabbed,color_frame = cap.read() # non-blocking
      print("FC:", fc)
      if not grabbed :
         fc += 1
         if fc > 5:
            break 
         continue

      small_frame = cv2.resize(color_frame, (0,0),fx=.5, fy=.5)
      if fc > 1:

         frame_sub = cv2.subtract(small_frame, last_small_frame)
         max_px = int(np.max(frame_sub))
         max_pxs.append(max_px)
         if max_px > 15:
            # stacked_image = cv2.addWeighted(stacked_image, .5, color_frame, .5, .5)

            stacked_image=ImageChops.lighter(stacked_image,Image.fromarray(color_frame))
            saved_frames[fc] = color_frame
      else:
         first_image = color_frame
         stacked_image = Image.fromarray(color_frame)
 
      last_small_frame = small_frame
      fc += 1
 

   stacked_image = np.asarray(stacked_image)

   first_file = stack_file.replace("-stacked", "-first")

   cv2.imwrite(stack_file, stacked_image, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
   #print("SAVE STACK FILE", stack_file)
   cv2.imwrite(first_file, first_image, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
   return(stacked_image, first_image, max_pxs, saved_frames, fc)


def get_stars_in_stack(image_file, stacked_image=None, first_image=None, ASAI=None ):
   objs = []
   if stacked_image is None:
      image = cv2.imread(image_file)
   else:
      image = stacked_image
   if False:
      # for blacking out the BG -- not a good result...
      norm = np.zeros((image.shape[0],image.shape[1],3),dtype=np.uint8)
      img = cv2.normalize(image,norm,0,255,cv2.NORM_MINMAX)
      gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
      max_val = np.max(gray)
      thresh = int(max_val / 3)
      if thresh > 80:
         thresh = 80
         _, img = cv2.threshold(img, thresh, 0, cv2.THRESH_TOZERO)
         image = img

   resp_img = image.copy()
   sh, sw = resp_img.shape[:2]
   obj_img =  np.zeros((sw,sh,3),dtype=np.uint8)
   bw = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   sbw = cv2.resize(bw, (1920,1080))
   stars = []
   non_stars = []
   star_rois = []
   non_star_rois = []

   for i in range(0,15):
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw)
      x1,y1,x2,y2,roi_img= get_roi(image,mx,my,224,224) 
      max_val = np.max(roi_img)
      avg_val = np.mean(roi_img)
      px_diff = max_val - avg_val
      if px_diff < 25:
         #print("Skip low px diff!", px_diff, max_val)
         break
         #continue
      if "\\" in image_file:
         image_file = image_file.replace("\\", "/")
      if "/" in image_file:
         root_fn = image_file.split("/")[-1] #+ "_" + str(i) + ".jpg"
      else:
         root_fn = image_file
      #print("METEOR YN:", roi_img.shape)
      resp = ASAI.meteor_yn(root_fn, None, roi_img)   
      if "meteor" in resp['mc_class'] : #or "plane" in resp['mc_class'] or "bug" in resp['mc_class'] or "bird" in resp['mc_class']:
         print("RESP:", resp)
      #print(resp['mc_class'])
      if resp['mc_class'] == "meteor" and resp['meteor_yn_confidence'] < 50:
         resp['mc_class'] = "planes"
      if resp['mc_class'] == 'meteor_fireball' and resp['meteor_fireball_yn_confidence'] < 50:
         resp['mc_class'] = "planes"

      if resp['mc_class'] == "stars":
         star_rois.append(roi_img)
         mx1 = mx - 50
         mx2 = mx + 50
         my1 = my - 50
         my2 = my + 50
         smx1 = mx - 10
         smx2 = mx + 10
         smy1 = my - 10
         smy2 = my + 10
         if smx1 < 0:
            smx1 = 0
            smx2 = 10
         if smx2 > image.shape[1] :
            smx2 = image.shape[1] - 1
            smx1 = image.shape[1] - 11
         if smy1 < 0:
            smy1 = 0
            smy2 = 10
         if smy2 > image.shape[0]:
            smy2 = image.shape[0] - 1
            smy1 = image.shape[0] - 11

         bw[smy1:smy2,smx1:smx2] = 0
         resp_img[smy1:smy2,smx1:smx2] = 0
         stars.append((mx,my,resp['mc_class_confidence']))
      else:
         non_star_rois.append(roi_img)
         mx1 = mx - 50
         mx2 = mx + 50
         my1 = my - 50
         my2 = my + 50
         if mx1 < 0:
            mx1 = 0
            mx2 = 50
         if my1 < 0:
            my1 = 0
            my2 = 50
         if mx2 > bw.shape[1]:
            mx2 = bw.shape[1] - 1
            mx1 = bw.shape[1] - 1 - 50
         if my2 > bw.shape[0]:
            my2 = bw.shape[0] - 1
            my1 = bw.shape[0] - 1 - 50

         bw[my1:my2,mx1:mx2] = 0
         cv2.rectangle(bw, (mx1,my1), (mx2, my2) , (0, 0, 0), 1)
         non_stars.append((mx1,my1,mx2,my2,resp['mc_class'],float(round(resp['mc_class_confidence'],2)),int(resp['meteor_yn_confidence']),int(resp['meteor_fireball_yn_confidence'])))

   return(stars, non_stars, resp_img, star_rois, non_star_rois)
   # 

def get_patch_objects_in_stack(image_file, stacked_image=None, first_image=None, ASAI=None ):
   if "\\" in image_file:
      image_file = image_file.replace("\\", "/")
   Min_Datasets = "F:/AI/DATASETS/MinFiles/"
   objs = []
   if stacked_image is None:
      image = cv2.imread(image_file)
   else:
      image = stacked_image

   sub = image.copy()
   detect_file = image_file.replace("-stacked.jpg", "-objs.jpg") 
 
   img_diff = cv2.subtract(image,first_image)

   _, threshold = cv2.threshold(first_image.copy(), 60, 255, cv2.THRESH_BINARY)
   #thresh_img = cv2.dilate(threshold.copy(), None , iterations=4)

   # img_diff = cv2.subtract(img_diff,thresh_img)


   bw = cv2.cvtColor(img_diff, cv2.COLOR_BGR2GRAY)
   sbw = cv2.resize(bw, (1920,1080))
   #cv2.imshow('pepe', sbw)
   #cv2.waitKey(30)
   hd_img = cv2.resize(image,(1920,1080))
   cv2.putText(hd_img, image_file,  (5,1070 ), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)

   for i in range(0,11):
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(bw)
      x1,y1,x2,y2,roi_img= get_roi(image,mx,my,224,224) 
      max_val = np.max(roi_img)
      avg_val = np.mean(roi_img)
      px_diff = max_val - avg_val
      if px_diff < 15:
         #cv2.imshow('pepe', hd_img)
         #cv2.waitKey(30)
         continue
      root_fn = image_file.split("/")[-1] #+ "_" + str(i) + ".jpg"
      resp = ASAI.meteor_yn(root_fn, None, roi_img)   
      cat = resp['mc_class']
      ldir = Min_Datasets  + cat + "/"
      lfile = ldir + root_fn + "_" + str(x1) + "_" + str(y1) + "_" + str(x2) + "_" + str(y2) + ".jpg"
      lfile = lfile.replace("-stacked.jpg", "")

      if os.path.exists(ldir) is False:
         os.makedirs(ldir)
      cv2.imwrite(lfile, roi_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
      mx1 = mx - 50
      mx2 = mx + 50
      my1 = my - 50
      my2 = my + 50
      if mx1 < 0:
         mx1 = 0
      if mx2 > image.shape[1]:
         mx2 = image.shape[1]
      if my1 < 0:
         my1 = 0
      if my2 > image.shape[0]:
         my2 = image.shape[0]

      bw[my1:my2,mx1:mx2] = 0
      desc = resp['mc_class'] + " " + str(resp['mc_class_confidence'])[:4] + "%"
      if resp['meteor_yn_confidence'] > resp['meteor_fireball_yn_confidence']:
         mconf = resp['meteor_yn_confidence']
      else:
         mconf = resp['meteor_fireball_yn_confidence']
      #desc2 = str(mconf)[0:4] + "% meteor"
      desc2 = ""

       
      if resp['mc_class'] != 'stars' and resp['mc_class'] != 'cloud':
         cv2.putText(hd_img, desc,  (x1,y2 ), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
         cv2.putText(hd_img, desc2,  (x1,y2-20 ), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
         cv2.rectangle(hd_img, (x1,y1), (x2, y2) , (255, 255, 255), 1)
         #cv2.imshow('pepe', hd_img)
         #cv2.waitKey(30)
      elif resp['mc_class'] == 'cloud':
         if y2 < 1080 / 2:
            cv2.putText(hd_img, desc,  (x1,y2-20 ), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
         else:
            cv2.putText(hd_img, desc,  (x1,y1-20 ), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
      elif resp['mc_class'] == 'stars' :
         sx = int((x1+x2)/2)
         sy = int((y1+y2)/2)
         if float(resp['mc_class_confidence']) > 96:
            cv2.circle(hd_img, (sx,sy), 10, (128,128,128),1)
            cv2.putText(hd_img, "Star " + str(round(resp['mc_class_confidence'],1)) + "%",  (sx,sy-20 ), cv2.FONT_HERSHEY_SIMPLEX, .8, (128,128,128), 1)
   #cv2.imshow('pepe', hd_img)
   #cv2.waitKey(30)
   cv2.imwrite(detect_file, hd_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
   

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
