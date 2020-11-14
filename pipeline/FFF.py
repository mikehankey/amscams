#!/usr/bin/python3

from lib.FFFuncs import slow_stack_video , imgs_to_vid, snap_video

import sys
import os

if len(sys.argv) < 2:
   print("""
      useage: ./FFF.py cmd options
      commads:
      slow_stack_video
   """)



cmd = sys.argv[1]

if cmd == "snap_video":
   snap_video(sys.argv[2])
if cmd == "slow_stack":
   video_file = sys.argv[2]
   out_dir = sys.argv[3]
   stack_rate = sys.argv[4]
   slow_stack_video(video_file, out_dir, stack_rate)
if cmd == "imgs_to_vid":
   in_dir = sys.argv[2]
   wild = sys.argv[3]
   out_file = sys.argv[4]
   fps = sys.argv[5]
   crf = sys.argv[6]
   imgs_to_vid (in_dir, out_file, wild, fps, crf)
if cmd == "splice_video":
   in_file = sys.argv[2]
   start = sys.argv[3]
   end = sys.argv[4]
   if len(sys.argv) > 5:
      outfile = sys.argv[2]
   else: 
      outfile = None
   if len(sys.argv) > 6:
      type = sys.argv[5] 
   else:
      type = "sec" 
 
   splice_video(in_file, start, end, outfile, type)
