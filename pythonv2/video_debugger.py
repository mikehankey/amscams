import os
import glob
import subprocess 
from lib.VIDEO_VARS import * 
from lib.Video_Tools import * 
from os import listdir, remove
from os.path import isfile, join, exists


#TEST HD_FRAMES
files, path, date, camID = get_hd_frames('010040','2019_07_10')
print("PATH " + str(path))
print("date " + str(date))
print("camID " + str(camID))
print("files " + str(files))


#TEST SD FRAMES
#get_sd_frames('010040','2019_07_07')