#!/usr/bin/python3

import os
import glob
import sys

dir = sys.argv[1]


def scan_dir(dir):

   print(dir + '/data/*motion.txt')
   for filename in (glob.glob(dir + '/data/*motion.txt')):
      print(filename)
      video_file = filename.replace("-motion.txt", ".mp4")
      video_file = video_file.replace("data/", "")
      cmd = "cp " + video_file + " " + "/mnt/ams2/CAMS/detect_queue/"
      os.system( cmd)


scan_dir(dir)
