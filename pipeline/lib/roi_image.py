import cv2
import numpy as np



def make_roi_image(x,y,w,h,roi_size,image,thresh_img, roi_src_image_size):
   docs = """
      x,y,w,h -- (int) values /scaling pertain to the original source image passed into the fucntion
      roi_size -- (int) final roi size
      roi_src_image_size (list) - w,h of the scaled image to pull the ROI from (should be 1920x1080 most of the time!)
      notes : if you pass in 1080p x,y values then image source should also be 1080p! x,y needs to match 
              original image not final val as this function will auto-scale.
   """

   cx = int(x + (w/2))
   cy = int(y + (h/2))
   new_w, new_h = roi_src_image_size
   org_h, org_w = image.shape[:2]
   hdm_x = new_w / org_w
   hdm_y = new_h / org_h
   new_img = cv2.resize(image,(new_w,new_h))

   blank_image = np.zeros((new_h,new_w),dtype=np.uint8)
   blank_image[:] = 255
   gray = cv2.cvtColor(new_img, cv2.COLOR_BGR2GRAY)
   if thresh_img is not None:
      if len(thresh_img.shape) == 3:
         thresh_gray = cv2.cvtColor(thresh_img, cv2.COLOR_BGR2GRAY)
      else:
         thresh_gray = thresh_img
   else:
      thresh_gray = blank_image
      thresh_gray[:] = 0
   hd_x = (cx * hdm_x)
   hd_y = (cy * hdm_y)


   x1 = int(hd_x - (roi_size / 2))
   y1 = int(hd_y - (roi_size / 2))
   x2 = int(hd_x + (roi_size / 2))
   y2 = int(hd_y + (roi_size / 2))

   if x1 < 0:
      x1 = 0
      x2 = roi_size
   if y1 < 0:
      y1 = 0
      y2 = roi_size
   if x2 >= new_w:
      x2 = new_w - 1
      x1 = new_w - 1 - roi_size
   if y2 > new_h:
      y2 = new_h - 1
      y1 = new_h - 1 - roi_size

   blank_image[y1:y2,x1:x2] = 0
   temp_img = cv2.subtract(gray, blank_image)
   thresh_gray = cv2.resize(thresh_gray,(gray.shape[1], gray.shape[0]))
   temp_img = cv2.subtract(gray, thresh_gray)

   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(temp_img)

   if x1 < 0:
      x1 = 0
      x2 = roi_size
   if y1 < 0:
      y1 = 0
      y2 = roi_size
   if x2 >= new_w:
      x2 = new_w - 1
      x1 = new_w - 1 - roi_size
   if y2 > new_h:
      y2 = new_h - 1
      y1 = new_h - 1 - roi_size

   #cv2.rectangle(new_img, (x1,y1), (x2, y2) , (0, 0, 0), 1)
   #cv2.imshow('main', new_img)
   #cv2.waitKey(30)

   roi_img = new_img[y1:y2,x1:x2]

   return(x1,y1,x2,y2,roi_img)
