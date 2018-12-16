#!/usr/bin/python
import time
import os
import glob
import sys
#ffmpeg -i "concat:/mnt/ams2/HD/2018-03-23_02-21-02-cam2-trim-466.mp4|/mnt/ams2/HD/2018-03-23_02-21-02-cam2-stacked.mp4" -c copy /mnt/ams2/HD/2018-03-23_02-21-02-cam2-final.mp4

glob_dir = sys.argv[1]
cat_out = glob_dir + "meteors.mp4"
cat_tmp1 = glob_dir + "tmp1.mp4"
cat_tmp2 = glob_dir + "tmp2.mp4"
cat_line = ""
count = 0
meteor_files = sorted(glob.glob(glob_dir + "*meteor.mp4"))

data = ""
for i in range(0,len(meteor_files)):
   data = data + "file '" + meteor_files[i] + "'\n"

fp = open("catdata.txt", "w")
fp.write(data)
fp.close()
cmd = "/usr/bin/ffmpeg -f concat -safe 0 -i catdata.txt -c copy " + cat_out
print(cmd)
os.system(cmd)
