import os
import glob
import subprocess  
import json
from lib.Frame_Tools import *  

meteor_json_file = '/mnt/ams2/meteors/2019_03_06/2019_03_06_06_47_25_000_010038-trim0072.json'
sd_video_file = '/mnt/ams2/meteors/2019_07_31/2019_07_31_06_33_34_000_010038-trim1265.mp4'

#def add_frame(json_conf, sd_video_file, fr_id, hd_x=-1, hd_y=-1): 
#add_frame(meteor_json_file,sd_video_file,str(22),251,123) 
real_add_frame(meteor_json_file,sd_video_file,str(18),251,123) 


Traceback (most recent call last):
  File "./reducer3.py", line 48, in <module>
    make_crop_images(file, json_conf)
  File "/home/ams/amscams/pythonv2/lib/ReducerLib.py", line 1965, in make_crop_images
    metframes = update_intensity(metframes, frames)
  File "/home/ams/amscams/pythonv2/lib/ReducerLib.py", line 30, in update_intensity
    base_cnt_img = base_img[y:y+h,x:x+w]
TypeError: slice indices must be integers or None or have an __index__ method