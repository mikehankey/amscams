#!/usr/bin/python3

from lib.PipeVideo import ffmpeg_cats

clip1 = "2021_03_21_04_25_00_000_010037.mp4"
clip2 = "2021_03_21_04_26_00_000_010037.mp4"
outfile = clip1.replace(".mp4", "-join.mp4") 
trim_start = 1364
trim_end = 1500
trim_file = clip1.replace(".mp4", "-trim-" + trim_start + "-HD-meteor.mp4"
ffmpeg_cats([clip1,clip2], outfile)
cmd = "./FFF.mp4 splice_video " + str(trim_start) + " " + str(trim_end) + " " + trim_file
print(cmd)
os.system(cmd)
