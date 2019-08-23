#!/usr/bin/python3

import numpy as np
import cv2


def add_info_to_frame_cv(hd_img, date_text, extra_text, text_position, extra_text_position, watermark, watermark_position, logo, logo_pos, enhancement=0):
   # Get org img & Watermark dimensions
   (h, w) = hd_img.shape[:2]
   (wH, wW) = watermark.shape[:2]
  
   #Add 4th dimension to image to deal with watermark transparency
   image = np.dstack([hd_img, np.ones((h, w), dtype="uint8") * 255])

   #Construct overlay for watermark
   overlay = np.zeros((h, w, 4), dtype="uint8") 

 
   print("overlay SHAPE")
   print(overlay.shape)

   print("IMAGE SHAPE")
   print(image.shape)
   
   #overlay[0:h,0:w] = watermark
   #overlay[h - wH - 10:h - 10, w - wW - 10:w - 10] = watermark
   #overlay[h - wH - 580:h - 580, w - wW - 10:w - 10] = watermark_image
   #overlay[h - wH - 580:h - 580, 10:wW + 10] = watermark_image
    
   # blend the two images together using transparent overlays
   res = image[:]
   cnd = overlay[:,:,3] > 0
   res[cnd] = overlay[cdn]

   cv2.imwrite("/mnt/ams2/test2.png", res)
   #output = image.copy()
   #cv2.addWeighted(overlay, 1, output, 1.0, 0, output)

   hd_img = output

   cv2.putText(hd_img, extra_text,  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.putText(hd_img, date_text,  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

   return hd_img


image = cv2.imread("/mnt/ams2/meteors/2019_08_23/2019_08_23_00_03_23_000_010040-trim-1-HD-meteor-stacked.png")
watermark = cv2.imread("./dist/img/ams_logo_vid_anim/1920x1080/AMS32.png", cv2.IMREAD_UNCHANGED)


logo  = ""
date_text = "test"
extra_text = "test"
text_position = 0
watermark_position = 0
extra_text_position = 0
logo_pos = 0



new_frame = add_info_to_frame_cv(image, date_text, extra_text, text_position, extra_text_position, watermark, watermark_position, logo, logo_pos, enhancement=0)

cv2.imwrite("/mnt/ams2/test2.png", new_frame)
