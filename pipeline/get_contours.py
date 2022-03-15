import cv2
import numpy as np

def get_contours(image):
   conts = []
   if len(image.shape) == 3:
      image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(image)

   thresh_val = int(max_val * .70)
   avg_px = np.mean(image)
   if avg_px < 100:
      if thresh_val < avg_px * 1.2 :
         thresh_val = avg_px * 1.2
   else:
      if thresh_val < avg_px * 1.3 :
         thresh_val = avg_px * 1.3
   _, thresh_img = cv2.threshold(image.copy(), thresh_val, 255, cv2.THRESH_BINARY)

   cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      intensity = int(np.sum(image[y:y+h,x:x+w]))
      conts.append((int(x),int(y),int(w),int(h),int(intensity)))
   return(conts)
