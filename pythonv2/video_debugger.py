import os
import glob
import subprocess 
from lib.VIDEO_VARS import * 
from lib.Video_Tools import * 
from os import listdir, remove
from os.path import isfile, join, exists

 


#TEST SD FRAMES
#print("GET SD FRAMES FOR '010042','2019_06_20'")
#path, date, camID
#date = '2019_06_02'
#camID = '010042'
#frames, path = get_sd_frames(camID,date)
#if(frames is None):
 #   print('NO FRAME FOUND')
#else:
#    where_path = add_info_to_frames(frames, path, date, camID,  "1920:1080",  'bl',  'tr',  0)
#    s = create_vid_from_frames(frames, where_path, date, camID, fps="60")
#    print('THE VID SHOULD BE THERE ' + s)

 
 #TEST HD FRAMES
print("GET SD FRAMES FOR '010038','2019_07_09'")
#path, date, camID
date = '2019_06_02'
camID = '010042'
frames, path = get_hd_frames(camID,date)
if(frames is None):
    print('NO FRAME FOUND')
else:
    where_path = add_info_to_frames(frames, path, date, camID,  "1920:1080",  'bl',  'tr',  0)
    s = create_vid_from_frames(frames, where_path, date, camID, fps="120")
    print('THE VID SHOULD BE THERE ' + s)
