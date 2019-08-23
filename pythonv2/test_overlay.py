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
   #overlay = np.zeros((h, w, 4), dtype="uint8") 

   #watermark_4 = np.dstack([watermark, np.ones((h, w), dtype="uint8") * 255])

   #print("overlay SHAPE")
   #print(overlay.shape)

   #print("IMAGE SHAPE")
   #print(image.shape)
   
   #overlay[0:h,0:w] = watermark 
   #overlay[h - wH - 10:h - 10, w - wW - 10:w - 10] = watermark
   #overlay[h - wH - 580:h - 580, w - wW - 10:w - 10] = watermark_image
   #overlay[h - wH - 580:h - 580, 10:wW + 10] = watermark_image
    
   # blend the two images together using transparent overlay 
   output = image[:]
   cnd = watermark[:,:,3] > 0
   output[cnd] = watermark[cnd]

   #cv2.imwrite("/mnt/ams2/test2.png", res)
   #output = image.copy()
   #cv2.addWeighted(overlay, 1, output, 1.0, 0, output)

   hd_img = output

   cv2.putText(hd_img, extra_text,  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.putText(hd_img, date_text,  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

   return hd_img


def add_info_to_frame_cv_test_full_transparent(hd_img, date_text, extra_text, text_position, extra_text_position, watermark, watermark_position, logo, logo_pos, enhancement=0):
   
   #Watermark position (temporarily hardcoded)
   x = 0
   y = 0

   #TODO: rezise watermark if necessary
   #if overlay_size is not None:
   #     img_to_overlay_t = cv2.resize(img_to_overlay_t.copy(), overlay_size) 

   bg_img = hd_img.copy()

   # Extract the alpha mask of the RGBA image, convert to RGB 
   b,g,r,a = cv2.split(watermark)
   overlay_color = cv2.merge((b,g,r))

   # Apply some simple filtering to remove edge noise
   mask = cv2.medianBlur(a,5)

   h, w, _ = overlay_color.shape
   roi = bg_img[y:y+h, x:x+w]

   # Black-out the area behind the watermark in our original ROI
   img1_bg = cv2.bitwise_and(roi.copy(),roi.copy(),mask = cv2.bitwise_not(mask))

   # Mask out the logo from the logo image.
   img2_fg = cv2.bitwise_and(overlay_color,overlay_color,mask = mask)


   # Update the original image with our new ROI
   bg_img[y:y+h, x:x+w] = cv2.add(img1_bg, img2_fg)

   hd_img = bg_img

   cv2.putText(hd_img, extra_text,  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.putText(hd_img, date_text,  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

   return hd_img


image = cv2.imread("/mnt/ams2/meteors/2019_08_23/2019_08_23_00_03_23_000_010040-trim-1-HD-meteor-stacked.png")
watermark = cv2.imread("./dist/img/ams_logo_vid_anim/1920x1080/AMS30.png", -1)


logo  = ""
date_text = "test"
extra_text = "test"
text_position = 0
watermark_position = 0
extra_text_position = 0
logo_pos = 0



new_frame = add_info_to_frame_cv_test_full_transparent(image, date_text, extra_text, text_position, extra_text_position, watermark, watermark_position, logo, logo_pos, enhancement=0)

cv2.imwrite("/mnt/ams2/test3.png", new_frame)
