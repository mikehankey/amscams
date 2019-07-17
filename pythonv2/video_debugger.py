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
#print("GET SD FRAMES FOR '010037','2019_07_11'")
#path, date, camID
#date = '2019_07_11'
#camID = '010037'
#frames, path = get_hd_frames(camID,date,10)
#if(frames is None):
#    print('NO FRAME FOUND')
#else:
#    where_path = add_info_to_frames(frames, path, date, camID, "Mike Hankey rocks", "1920:1080",  'bl',  'tr',  0)
#   s = create_vid_from_frames(frames, where_path, date, camID, fps="30")
#    print('THE VID SHOULD BE THERE ' + s)




#Test text & logo
text_position, extra_text_position = get_text_pos('br',True)
add_info_to_frame('/mnt/ams2/CUSTOM_VIDEOS/to_test.png','Mike Hankey Rocks',text_position,extra_text_position,"CAM TEXT",get_watermark_pos('bl'),'/mnt/ams2/CUSTOM_VIDEOS/to_test_res','1920:1080','bl','tr',0)