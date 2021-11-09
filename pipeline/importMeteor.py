#!/usr/bin/python3
import cv2
import os
from lib.PipeUtil import save_json_file
from lib.PipeDetect import make_base_meteor_json
def import_meteor(trim_file, hd_trim):

   mj, mjr = make_base_meteor_json(trim_file,hd_trim, None, None)

   os.system("cp " + trim_file + " " + mj['sd_video_file'])
   if hd_trim is not None:
      os.system("cp " + hd_trim + " " + mj['hd_trim'])
   mjf = mj['sd_video_file'].replace(".mp4", ".json")
   save_json_file(mjf, mj)
   print("saved:", mjf)
      # make the stacks
   os.system("./stackVideo.py " + mj['sd_video_file'])
   os.system("./stackVideo.py " + mj['hd_trim'])

   stack_img = cv2.imread(mj['sd_video_file'].replace(".mp4", "-stacked.jpg"))
   tn = cv2.resize(stack_img, (320,180))
   cv2.imwrite(mj['sd_video_file'].replace(".mp4", "-stacked-tn.jpg"), tn)

print("Enter the full path to the SD trim file")
print("make sure trim number is in the file name correctly or time will be off. trim-number = 25 * start second of clip")
trim_file = input("ENTER SD TRIM FILE PATH:")
hd_trim = input("ENTER HD TRIM FILE PATH:")

import_meteor(trim_file, hd_trim)
#make thumb

