import os
import glob
import subprocess 
from lib.VIDEO_VARS import * 
from lib.Video_Tools import * 
from os import listdir, remove
from os.path import isfile, join, exists


#TEST HD_FRAMES
#print("GET HD FRAMES FOR '010040','2019_07_10'")
#files, path, date, camID = get_hd_frames('010040','2019_07_10')
#print("PATH " + str(path))
#print("date " + str(date))
#print("camID " + str(camID))
#print("files " + str(files))
#/mnt/ams2/HD/tmp/2019_07_10_08_53_53_000_010040.mp4.png


#TEST SD FRAMES
print("GET HD FRAMES FOR '010040','2019_07_08'")
files, path, date, camID = get_sd_frames('010040','2019_07_07')
print("PATH " + str(path))
print("date " + str(date))
print("camID " + str(camID))
print("files " + str(files))