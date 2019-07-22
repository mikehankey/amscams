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
#text_position, extra_text_position = get_text_pos('br',True)
#watermark_position = get_watermark_pos('tr')
#logo_pos  = logo_position = get_watermark_pos('br') 
#add_info_to_frame('/mnt/ams2/CUSTOM_VIDEOS/2019_07_19_010037.png',\
 #                 "CAM TEXT",'EXTRA TEXT',text_position,extra_text_position,AMS_WATERMARK,watermark_position,'','X','/mnt/ams2/CUSTOM_VIDEOS/to_test_BR','1920:1080', 0)

#text_position, extra_text_position = get_text_pos('bl',True)
#watermark_position = get_watermark_pos('tl')
#add_info_to_frame('/mnt/ams2/CUSTOM_VIDEOS/to_test.png',"BL",'Mike Hankey Rocks',text_position,extra_text_position,watermark_position,'/mnt/ams2/CUSTOM_VIDEOS/to_test_BL','1920:1080', 0)

#text_position, extra_text_position = get_text_pos('tl',True)
#watermark_position = get_watermark_pos('bl')
#add_info_to_frame('/mnt/ams2/CUSTOM_VIDEOS/to_test.png',"TL",'Mike Hankey Rocks',text_position,extra_text_position,watermark_position,'/mnt/ams2/CUSTOM_VIDEOS/to_test_TL','1920:1080', 0)


#text_position, extra_text_position = get_text_pos('tr',True)
#watermark_position = get_watermark_pos('br')
#add_info_to_frame('/mnt/ams2/CUSTOM_VIDEOS/to_test.png',"TR",'Mike Hankey Rocks',text_position,extra_text_position,watermark_position,'/mnt/ams2/CUSTOM_VIDEOS/to_test_TR','1920:1080', 0)

drawbox_on_vid("/mnt/ams2/meteors/2019_03_07/","2019_03_07_04_47_21_000_010037-trim0989.mp4",10,30,60,120)