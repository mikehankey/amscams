import cv2
import random
import numpy as np
from detectlib import eval_cnt
from scipy import signal
from scipy.interpolate import splrep, sproot, splev


def bound_cnt(x,y,img_w,img_h):
   sz = 10 

   if x - sz < 0:
      mnx = 0
   else:
      mnx = x - sz 

   if y - sz < 0:
      mny = 0
   else:
      mny = y - sz 

   if x + sz > img_w - 1:
      mxx = img_w - 1 
   else: 
      mxx = x + sz

   if y + sz > img_h -1:
      mxy = img_h - 1
   else:
      mxy = y + sz
   return(mnx,mny,mxx,mxy)


def clean_star_bg(cnt_img, bg_avg):
   for x in range(0,cnt_img.shape[1]):
      for y in range(0,cnt_img.shape[0]):
         px_val = cnt_img[y,x]
         if px_val < bg_avg:
            cnt_img[y,x] = random.randint(int(bg_avg - 3),int(bg_avg+3))
   return(cnt_img)
  

def find_bright_pixels(med_stack_all):
   img_height,img_width = med_stack_all.shape
   med_cpy = med_stack_all.copy()
   star_pixels = []
   max_px = np.max(med_stack_all)
   avg_px = np.mean(med_stack_all)
   pdif = max_px - avg_px
   pdif = int(pdif / 15) + avg_px
   #star_bg = 255 - cv2.adaptiveThreshold(med_stack_all, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 3)
  
   _, star_bg = cv2.threshold(med_stack_all, pdif, 255, cv2.THRESH_BINARY)

   #cv2.imshow('pepe', star_bg)
   #cv2.waitKey(0)

   #star_bg = cv2.GaussianBlur(star_bg, (7, 7), 0)
   #thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   thresh_obj= cv2.convertScaleAbs(star_bg)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   masked_pixels = []

   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cv2.rectangle(star_bg, (x, y), (x + w+5, y + h+5), (255, 0, 0), 1)
   #cv2.imshow('pepe', star_bg)
   #cv2.waitKey(1)

   bg_avg = 0

   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if True:
         cnt_img = med_stack_all[y:y+h,x:x+w]
         (max_px, avg_px,px_diff,max_loc) = eval_cnt(cnt_img)

         mx,my = max_loc
         cx = x + mx
         cy = y + my
         mnx,mny,mxx,mxy = bound_cnt(cx,cy,img_width,img_height) 
         cnt_img = med_stack_all[mny:mxy,mnx:mxx]
         cnt_w,cnt_h = cnt_img.shape
         if cnt_w > 0 and cnt_h > 0:
            is_star = star_test(cnt_img)
            if is_star == 1:
               bg_avg = bg_avg + np.mean(cnt_img)
               star_pixels.append((cx,cy))
               cv2.circle(med_cpy, (int(cx),int(cy)), 5, (255,255,255), 1)
               #cv2.imshow('pepe', cnt_img)
               #cv2.waitKey(0)
            else:
               cv2.rectangle(med_cpy, (cx-5, cy-5), (cx + 5, cy + 5), (255, 0, 0), 1)
         else:
               cv2.rectangle(med_cpy, (cx-15, cy-15), (cx + 15, cy + 15), (255, 0, 0), 1)

   if len(star_pixels) > 0:
      bg_avg = bg_avg / len(star_pixels) 
   else:
      bg_avg = 35

   plate_image = med_stack_all.copy()
   for x in range(0,plate_image.shape[1]):
      for y in range(0,plate_image.shape[0]):
         plate_image[y,x] = random.randint(int(bg_avg - 3),int(bg_avg+3))

   #cv2.imshow('pepe', plate_image)
   #cv2.waitKey(0)


   #plate_image[0:-1,0:-1] = bg_avg
 
   star_sz = 10
   for star in star_pixels:
      sx,sy = star
      mnx,mny,mxx,mxy = bound_cnt(sx,sy,img_width,img_height) 
      star_cnt = med_stack_all[mny:mxy,mnx:mxx]
      star_cnt = clean_star_bg(star_cnt, bg_avg)
      plate_image[mny:mxy,mnx:mxx] = star_cnt
      #cv2.imshow('pepe', star_cnt)
      #cv2.waitKey(0)

   #cv2.imshow('pepe', plate_image)
   #cv2.waitKey(0)


   return(star_pixels, plate_image)

def star_test(cnt_img):
   PX = []
   PY = []
   ch,cw = cnt_img.shape
   my = int(ch / 2)
   mx = int(cw / 2)
   max_px = np.max(cnt_img)
   avg_px = np.mean(cnt_img)
   px_diff = max_px - avg_px 

   for x in range(0,cw-1):
      px_val = cnt_img[my,x]
      PX.append(px_val)
      #cnt_img[my,x] = 255
   for y in range(0,ch-1):
      py_val = cnt_img[y,mx]
      PY.append(py_val)
      #cnt_img[y,mx] = 255

   ys_peaks = signal.find_peaks(PY)
   y_peaks = len(ys_peaks[0])
   xs_peaks = signal.find_peaks(PX)
   x_peaks = len(xs_peaks[0])

   print("STAR TEST:", x_peaks, y_peaks, px_diff)

   #cv2.imshow('pepe', cnt_img)
   #cv2.waitKey(0)
   if px_diff > 10:
      is_star = 1 
   else:
      is_star = 0

   return(is_star)
