#!/usr/bin/python3
import os
from lib.PipeVideo import ffmpeg_cats

clip1 = "/mnt/ams2/HD/2021_03_21_04_25_00_000_010001.mp4"
clip2 = "/mnt/ams2/HD/2021_03_21_04_26_00_000_010001.mp4"
c2fn = clip2.split("/")[-1]
join_file = clip1.replace(".mp4", "__")
join_file += c2fn 
outfile = clip1.replace(".mp4", "-join.mp4") 
trim_start = 1364
trim_end = 1550
trim_file = clip1.replace(".mp4", "-trim-" + str(trim_start) + "-HD-meteor.mp4")
ffmpeg_cats([clip1,clip2], outfile)
cmd = "./FFF.py splice_video " +join_file +" "  + str(trim_start) + " " + str(trim_end) + " " + trim_file + " frame"
print(cmd)
os.system(cmd)
cmd = "./FFF.py lower_bitrate " + trim_file +" 30"
print(cmd)
os.system(cmd)
cmd = "rm " + join_file
print(cmd)
