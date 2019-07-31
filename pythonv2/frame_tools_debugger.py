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