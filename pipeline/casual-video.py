import cv2
import sys
from lib.PipeVideo import ffmpeg_cats, load_frames_simple
import numpy as np


vid = sys.argv[1]

sd_frames = load_frames_simple(vid)
last = None
c = 0
med_frame = cv2.convertScaleAbs(np.median(np.array(sd_frames[0:7]), axis=0))
med_frame = cv2.resize(med_frame, (640,360))
#for fr in sd_frames[0:7]:
#      cv2.imshow('Original', fr)
#      cv2.waitKey(0)

oy, ox, cx =  sd_frames[0].shape


nx = 640 * 2 
ny = 360 * 5
img = np.zeros((ny,nx,3),dtype=np.uint8)
rx = 0

for fr in sd_frames:
   fr = cv2.resize(fr, (640,360))
   print(fr.shape)
   if c > 216 and c < 222:
      sub = cv2.subtract(fr, med_frame)
      val = np.sum(sub)
      print(c, val)

      ny1 = rx * 360
      ny2 = ny1 + 360 
      img[ny1:ny2,0:640] = fr
      img[ny1:ny2,640:1280] = sub  
      cv2.imshow('img', img)
      cv2.waitKey(0)
      rx += 1
   last = med_frame
   c += 1
cv2.imwrite("/mnt/f/meteorite_falls/SaltLakeCity.jpg", img)
