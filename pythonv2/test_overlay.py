#!/usr/bin/python3

import numpy as np
import cv2


def add_info_to_frame_cv(hd_img, date_text, extra_text, text_position, extra_text_position, watermark, watermark_position, logo, logo_pos, enhancement=0):
   (wH, wW) = watermark.shape[:2]
   (h, w) = hd_img.shape[:2]
 
   (B, G, R, A) = cv2.split(watermark)
   B = cv2.bitwise_and(B, B, mask=A)
   G = cv2.bitwise_and(G, G, mask=A)
   R = cv2.bitwise_and(R, R, mask=A)
   watermark_image = cv2.merge([B, G, R, A])

   print("WI:", watermark_image.shape)

   image = np.dstack([hd_img, np.ones((h, w), dtype="uint8") * 255])

   overlay = np.zeros((h, w, 4), dtype="uint8")
   print("OVERLAY:", h,  wH, wW, w )
   overlay[h - wH - 580:h - 580, w - wW - 10:w - 10] = watermark_image
   overlay[h - wH - 580:h - 580, 10:wW + 10] = watermark_image


   # blend the two images together using transparent overlays
   output = image.copy()
   cv2.addWeighted(overlay, 1, output, 1.0, 0, output)

   hd_img = output

   cv2.putText(hd_img, extra_text,  (10,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
   cv2.putText(hd_img, date_text,  (1100,710), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

   return hd_img


image = cv2.imread("/mnt/ams2/meteors/2019_08_23/2019_08_23_00_03_23_000_010040-trim-1-HD-meteor-stacked.png")
watermark = cv2.imread("/mnt/ams2/logo.png", cv2.IMREAD_UNCHANGED)

print(watermark.shape)

logo  = cv2.imread("/mnt/ams2/CUSTOM_LOGOS/AMS30.png")
date_text = "test"
extra_text = "test"
text_position = 0
watermark_position = 0
extra_text_position = 0
logo_pos = 0



new_frame = add_info_to_frame_cv(image, date_text, extra_text, text_position, extra_text_position, watermark, watermark_position, logo, logo_pos, enhancement=0)

cv2.imwrite("/mnt/ams2/test.png", new_frame)
