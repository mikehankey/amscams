from Classes.ASAI import AllSkyAI 
import cv2

ASAI = AllSkyAI()
(img, img_gray, img_thresh, img_dilate, avg_val, max_val, thresh_val) = ASAI.ai_open_image("/mnt/ams2/meteors/2020_11_19/2020_11_19_00_09_00_000_010001-trim-0300-stacked.jpg")
img_dilate = cv2.resize(img_dilate,(1920,1080))
cnts = ASAI.get_contours(img_dilate)
for x,y,w,h in cnts:
   cv2.rectangle(img_dilate, (x,y), (x+w, y+h) , (255, 255, 255), 1)
cv2.imwrite("/mnt/ams2/test.jpg", img_dilate)

