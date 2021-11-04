#!/usr/bin/python3

import os
from lib.PipeUtil import save_json_file

def import_meteor(trim_file, hd_trim):

   mj, mjr = make_base_meteor_json(trim_file,hd_trim, None, None)
   out += str(mj)

   os.system("cp " + trim_file + " " + mj['sd_video_file'])
   if hd_trim is not None:
      os.system("cp " + hd_trim + " " + mj['hd_trim'])
   mjf = mj['sd_video_file'].replace(".mp4", ".json")
   save_json_file(mjf, mj)
      # make the stacks
   os.system("./stackVideo.py " + mj['sd_video_file'])
   os.system("./stackVideo.py " + mj['hd_trim'])


print("Enter the full path to the SD trim file")
print("make sure trim number is in the file name correctly or time will be off. trim-number = 25 * start second of clip"
trim_file = input("ENTER SD TRIM FILE PATH")
hd_trim = input("ENTER HD TRIM FILE PATH")

import_meteor(trim_file, hd_trim)
