#!/usr/bin/python3

from lib.FFFuncs import slow_stack_video , slow_stack_range, imgs_to_vid, snap_video, splice_video, vid_to_imgs, crop_video, best_crop_size, lower_bitrate, resize_video, list_to_video

import sys
import os

if len(sys.argv) < 2:
   print("""
      useage: ./FFF.py cmd options
      commads:
      slow_stack_video
   """)



cmd = sys.argv[1]

if cmd == "resize_video":
   #resize_video(in_file, out_file, ow, oh, bit_rate=20):

   resize_video(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
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
   if len(sys.argv) >= 5 :
      suffix = sys.argv[4] 
   else:
      suffix = None
   if len(sys.argv) >=6 :
      resz = sys.argv[5] 
      w,h = resz.split("x")
      resize = [w,h]
   else:
      resize = None
   print("v2i: ", file, out_dir)
   vid_to_imgs(file, out_dir, suffix, resize)

if cmd == "lower_bitrate":
   lower_bitrate(sys.argv[2], sys.argv[3])
if cmd == "snap_video":
   snap_video(sys.argv[2])
if cmd == "slow_stack_range":
   date = sys.argv[2]
   start_hour = int(sys.argv[3])
   end_hour = int(sys.argv[4])
   cam = sys.argv[5]
   slow_stack_range(date, start_hour, end_hour, cam)
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
   if len(sys.argv) == 8:
      ftype = sys.argv[7]
   else:
      ftype = "jpg"
   print("IMGS TO VIDEO:", in_dir, out_file, wild, fps, crf, ftype)
   imgs_to_vid (in_dir, out_file, wild, fps, crf)
if cmd == "splice_video":
   #./FFF.py splice_video in_file start end outfile type(blank for sec 'frame' for frame)
   in_file = sys.argv[2]
   start = sys.argv[3]
   end = sys.argv[4]
   outfile = sys.argv[5]
   type = sys.argv[6] 
   print(start, end, type) 
   splice_video(in_file, start, end, outfile, type)
if cmd == "resize":
    in_file = sys.argv[2]
    out_file = sys.argv[3]
    ow = sys.argv[4]
    oh = sys.argv[5]
    br = sys.argv[6]
    # ./FFF.py infile outfile ow oh br
    resize_video(in_file, out_file, ow, oh, br)
if cmd == "list":
    list_file = sys.argv[2]
    out_file = sys.argv[3]
    fps = sys.argv[4]
    ow = sys.argv[5]
    oh = sys.argv[6]
    list_to_video(list_file, out_file, fps, ow, oh)
