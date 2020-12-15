#!/usr/bin/python3

from lib.FFFuncs import slow_stack_video , imgs_to_vid, snap_video, splice_video, vid_to_imgs, crop_video, best_crop_size, lower_bitrate

import sys
import os

if len(sys.argv) < 2:
   print("""
      useage: ./FFF.py cmd options
      commads:
      slow_stack_video
   """)



cmd = sys.argv[1]

if cmd == "crop_video":
   in_file = sys.argv[2]
   out_file = sys.argv[3]
   cb = sys.argv[4]
   x,y,w,h = cb.split(",")
   crop_box = [x,y,w,h]
   crop_video(in_file, out_file, crop_box)

if cmd == "vid_to_imgs":
   file = sys.argv[2]
   out_dir = sys.argv[3]
   if len(sys.argv) >= 4 :
      suffix = sys.argv[4] 
   else:
      suffix = None
   if len(sys.argv) >=5 :
      resz = sys.argv[5] 
      w,h = resz.split("x")
      resize = [w,h]
   else:
      resize = None

   vid_to_imgs(file, out_dir, suffix, resize)

if cmd == "lower_bitrate":
   lower_bitrate(sys.argv[2], sys.argv[3])
if cmd == "snap_video":
   snap_video(sys.argv[2])
if cmd == "slow_stack":
   video_file = sys.argv[2]
   out_dir = sys.argv[3]
   stack_rate = sys.argv[4]
   slow_stack_video(video_file, out_dir, stack_rate)
if cmd == "imgs_to_vid":
   #./FFF.py imgs_to_vid IN_DIR WILD_STR OUT_FILE FPS CRF 
   #./FFF.py ims_to_vid /images/ mystring /vids/out.mp4 25 28
   in_dir = sys.argv[2]
   wild = sys.argv[3]
   out_file = sys.argv[4]
   fps = sys.argv[5]
   crf = sys.argv[6]
   print("IMGS TO VIDEO:", in_dir, out_file, wild, fps, crf)
   imgs_to_vid (in_dir, out_file, wild, fps, crf)
if cmd == "splice_video":
   #./FFF.py splice_video in_file start end outfile type(blank for sec 'frame' for frames)
   in_file = sys.argv[2]
   start = sys.argv[3]
   end = sys.argv[4]
   outfile = sys.argv[5]
   type = sys.argv[6] 
   print(start, end, type) 
   splice_video(in_file, start, end, outfile, type)

