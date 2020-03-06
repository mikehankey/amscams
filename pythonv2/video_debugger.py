import os
import glob
import sys
import subprocess 
from lib.VIDEO_VARS import * 
from lib.Video_Tools import * 
from lib.Video_Tools_cv import * 
from os import listdir, remove
from os.path import isfile, join, exists

from lib.Video_Title_cv import *


# TEST CREATE CROPPED VERSION OF VIDEO
#define_crop_video('/mnt/archive.allsky.tv/AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298.json','/mnt/archive.allsky.tv/AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298-HD.mp4')

define_crop_video('/mnt/archive.allsky.tv/AMS7/METEOR/2019/12/24/2019_12_24_08_29_19_000_010039-trim1168.json','/mnt/archive.allsky.tv/AMS7/METEOR/2019/12/24/2019_12_24_08_29_19_000_010039-trim1168-HD.mp4')

# TEST FIX MP4
#fixmp4('/mnt/ams2/SD/proc2/2020_01_30/2020_01_30_23_49_32_000_010041.mp4')

 


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

#drawbox_on_vid("/mnt/ams2/meteors/2019_03_07/","2019_03_07_04_47_21_000_010037-trim0989.mp4",10,30,60,120)

 

#org =  '/mnt/ams2/TIMELAPSE_IMAGES/2019_08_06_01_02_26_000_010039.png'
#stack = get_stack_from_HD_frame(org)
#print('STACK ' +  str(stack))
#print('ORG ' +  org)
#blend(org,stack,40,'/mnt/ams2/TMP/test.png')


# Create timelapse video 
# with stack blending for night shoots
# INPUT => result of get_all_HD_pic() for a certain date
#       => eventual stack if found
# OUTPUT => video with frame blended with stack if at night and stack found


# TEST CREATE VIDEO WITH BLENDING SD
#array_of_frames, path  = get_hd_frames_from_HD_repo("10041","2019/08/21","2019/08/21 01:00","2019/08/21 23:00",False)
#print("FRAMES")
#print(array_of_frames) 
#print("PATH")
#print(path) 
#if(array_of_frames is None):
#    print('NO FRAME FOUND') 
#else:
#    where_path = add_info_to_frames(array_of_frames, path, "2019/08/21", "10041", "This is a test", "/mnt/ams2/CUSTOM_LOGOS/1.png","tl",HD_DIM, "bl","tr")
#    t = create_vid_from_frames(array_of_frames, where_path, "2019_08_21",  "10041","30")
#   print(t)


# TEST BLENDER
#blend('/mnt/ams2/meteors/2019_08_19/2019_08_19_08_26_48_000_010041-trim-183-HD-meteor-stacked.png','/mnt/ams2/meteors/2019_08_19/2019_08_19_00_08_10_000_010037-trim-1-HD-meteor-crop-stacked-obj.png',BLENDING_SD,'/mnt/ams2/TMP/test.png')
#print('/mnt/ams2/TMP/test.png')

 
# TEST GET METEOR DETECTIONS FROM CAM_ID START DAte / END DATE
#videos, path = get_all_meteor_detections("2019_08_21","2019/08/21 00:00","2019/08/21 23:59","10041")
#print(videos)
#print("PATH")
#print(path)

#get_all_detection_frames(path,'2019_08_21_00_33_15_000_010037-trim-618-HD-meteor.mp4')


############## TEST OVERLAY POSITION CV
#background = cv2.imread('/mnt/ams2/meteors/2019_08_23/2019_08_23_00_03_23_000_010040-trim-1-HD-meteor-stacked.png')
#overlay = cv2.imread(AMS_WATERMARK, cv2.IMREAD_UNCHANGED)
 
#added_image = add_overlay_cv(background,overlay,'tl')
#cv2.imwrite('/mnt/ams2/test_tl.png', added_image)

#added_image = add_overlay_cv(background,overlay,'tr')
#cv2.imwrite('/mnt/ams2/test_tr.png', added_image)
 

#added_image = add_overlay_cv(background,overlay,'bl')
#cv2.imwrite('/mnt/ams2/test_bl.png', added_image)


#added_image = add_overlay_cv(background,overlay,'br')
#cv2.imwrite('/mnt/ams2/test_br.png', added_image)

#added_image = add_overlay_cv(background,overlay,'tr') 


#logo = cv2.imread('/mnt/ams2/CUSTOM_LOGOS/1.png', cv2.IMREAD_UNCHANGED)
#added_image = add_overlay_cv(background,logo,'tl') 

#added_image = add_text_to_pos(added_image,'This is a line 1','bl',1)
#added_image = add_text_to_pos(added_image,'This is a , a second line','bl',2) 
#added_image = add_text_to_pos(added_image,'THIS IS A TEST  LINE 1','br',1)
#added_image = add_text_to_pos(added_image,'This is a , a second line','br',2)


#added_image = add_radiant_cv(added_image,500,500,"Perseids")

#cv2.imwrite('/mnt/ams2/test_text.png', added_image)



################### TEST NEW REMASTER


# DOESNT OVERLAP  
#data = {
#    'json_conf' : '/mnt/ams2/meteor_archive/2019_08_14/2019_08_14_03_19_52_640_010042_AMS7_HD.json',
#    'video_file' :'/mnt/ams2/meteor_archive/2019_08_14/2019_08_14_03_19_52_640_010042_AMS7_HD.mp4',
#    'rad_x': 500,
#   'rad_y': 500,
#    'rad_name': 'Perseids'
#}


# OVERLAP WITH LOGO TR
#data = {
#    'json_conf' : '/mnt/ams2/conversion/2019_08_10_02_29_20_000_010037-trim0716/2019_08_10_02_29_52_040_010037_AMS7_HD.json',
#    'video_file' :'/mnt/ams2/conversion/2019_08_10_02_29_20_000_010037-trim0716/2019_08_10_02_29_52_040_010037_AMS7_HD.mp4',
#   'rad_x': 500,
#   'rad_y': 500,
#    'rad_name': 'Perseids'
#}


#data = {
#    'json_conf' : '/mnt/ams2/conversion/2019_08_12_05_37_29_000_010037-trim0945/2019_08_12_05_38_09_920_010037_AMS7_HD.json',
#    'video_file' :'/mnt/ams2/conversion/2019_08_12_05_37_29_000_010037-trim0945/2019_08_12_05_38_09_920_010037_AMS7_HD.mp4',
#    'rad_x': 500,
#    'rad_y': 500,
#    'rad_name': 'Perseids'
#}  
#new_remaster(data)  
#remaster(data)  


################### TEST CREATE TILE
 

#CREATE INFO VIDEO FROM FRAMES
#import cv2 
#import subprocess 

#CREATE TITLE VIDEO
#_main_title = "BEST OF PERSEIDS 2019"
#_producer =  ""
#_output_path = '/mnt/ams2/opening_title.mp4'
#create_title_video(_main_title,_producer,_output_path,(255,255,255,255),True)


#CREATE OPERATOR VIDEOS
#_operators = ["Mike Hankey","Elizabeth Warner - UMD", "Ed Abel", "Peter Deterline", "Vishnu Reddy", "Bob Lunsford", "Mel Helm - SRO"]
#_duration = 75 # In frames at 25fps
#_output_path =  '/mnt/ams2/operator_credits.mp4'
#_with_line_animation = True # Optional - it's True by default
#_line_height = 55 # Optional - it's 45 by default, it works well with <=12 operators (one per line)
#_operator_font_size = 40 # Optional - it's 30 by default, it works well with <=12 operators (one per line)
#create_thank_operator_video(_operators, _duration, _output_path,_with_line_animation,_line_height,_operator_font_size) 

#CREATE ALL SKY CAMS VIDEOS
#_text1= "Allskycams.com"
#_text2= ""
#_duration = 100 # In frames at 25fps
#_output = '/mnt/ams2/allskycams.mp4'
#create_allskycams_video(_text1,_text2,_duration,_output)

#CREATE MUSIC CREDIT VIDEO
#_text1= "Music by"
#_text2= "NAKED JUNGLE"
#_text3= "nakedjungle.bandcamp.com"
#_duration = 50 # In frames at 25fps
#_output = '/mnt/ams2/music_credits.mp4'
#create_credit_video(_text1,_text2,_text3,_duration,_output)
# PRODUCE CREEDIT
#create_credit_video("Produced by","Mike Hankey","",_duration,'/mnt/ams2/producedby.mp4')


# CONCAT VIDEOS START
#_from = 5 # in seconds
#_total_duration = 8 # in seconds
#concat_videos_fade('/mnt/ams2/opening_title.mp4','/mnt/ams2/music_credits.mp4','/mnt/ams2/1.mp4',_from,_total_duration)
#_from = 10 # in seconds
#_total_duration = 12 # in seconds
#concat_videos_fade('/mnt/ams2/1.mp4','/mnt/ams2/producedby.mp4','/mnt/ams2/START.mp4',_from,_total_duration)

# CONCAT VIDEO END
#_from = 5 # in seconds
#_total_duration = 12 # in seconds
#concat_videos_fade('/mnt/ams2/operator_credits.mp4','/mnt/ams2/allskycams.mp4','/mnt/ams2/END.mp4',_from,_total_duration) 



############# TEST CV crop
#import cv2
#import sys
#import numpy as np
#from lib.MeteorReduce_Tools import *
#from lib.VIDEO_VARS import *
#from lib.Video_Timelapse import *
#from lib.Video_Tools import *

#new_crop_thumb("/mnt/ams2/CACHE/AMS7/2019/09/30/2019_09_30_00_36_31_400_010042_AMS7_HD/FRAMES/2019_09_30_00_36_31_400_010042_AMS7_HD_HDfr0081.png",826,7,"/mnt/ams2/test1.png",True)  
#print("/mnt/ams2/test1.png") 



# ADD THUMBS TO VIDEO #############################################################################################
# from lib.Video_Tools_cv import *

#HD_video = "/mnt/ams2/meteor_archive/AMS16/METEOR/2020/01/05/2020_01_05_03_01_32_000_010093-trim0597-HD.mp4"
#json_conf = "/mnt/ams2/meteor_archive/AMS16/METEOR/2020/01/05/2020_01_05_03_01_32_000_010093-trim0597.json"
#thumb_path = "/mnt/ams2/CACHE/AMS16/2020/01/05/2020_01_05_03_01_32_000_010093-trim0597/THUMBS/"
##x = 900
#y = 250
#hd_sync=50
#sd_sync=49
#thumb_name = "2020_01_05_03_01_32_000_010093-trim0597_frm"
#thumbs_start_at = 100-(sd_sync-hd_sync) 
#thumbs_end_at = 278-(sd_sync-hd_sync) 
#output_video_path = "/mnt/ams2/andre_with_zoom.mp4"
#zoom = 6
#add_thumbs_to_video(hd_sync,sd_sync,HD_video,json_conf,thumb_path,thumb_name,thumbs_start_at,thumbs_end_at,x,y,zoom,output_video_path)
#output_video_path = "/mnt/ams2/andre_without_zoom.mp4"
#zoom = 0
#add_thumbs_to_video(hd_sync,sd_sync,HD_video,json_conf,thumb_path,thumb_name,thumbs_start_at,thumbs_end_at,x,y,zoom,output_video_path)

#sys.exit(0)
##############################################################################################################
#HD_video = "/mnt/ams2/meteor_archive/AMS22/METEOR/2020/01/05/2020_01_05_03_01_23_000_010029-trim736-HD.mp4"
#json_conf = "/mnt/ams2/meteor_archive/AMS22/METEOR/2020/01/05/2020_01_05_03_01_23_000_010029-trim736.json"
#thumb_path = "/mnt/ams2/CACHE/AMS22/2020/01/05/2020_01_05_03_01_23_000_010029-trim736/THUMBS/"
#x = 1180
#y = 250
#hd_sync=46
#sd_sync=208
#thumbs_start_at = 202-(sd_sync-hd_sync) 
#thumbs_end_at = 396-(sd_sync-hd_sync) 
#thumb_name = "2020_01_05_03_01_23_000_010029-trim736_frm"
#output_video_path = "/mnt/ams2/sirko_with_zoom.mp4"
#zoom = 6
#add_thumbs_to_video(hd_sync,sd_sync,HD_video,json_conf,thumb_path,thumb_name,thumbs_start_at,thumbs_end_at,x,y,zoom,output_video_path)

#output_video_path = "/mnt/ams2/sirko_without_zoom.mp4"
#zoom = 0
#add_thumbs_to_video(hd_sync,sd_sync,HD_video,json_conf,thumb_path,thumb_name,thumbs_start_at,thumbs_end_at,x,y,zoom,output_video_path)
 
############# TEST TIMELAPSES FROM JPEGs
#job = {
#   "cam_id": "010042",
#   "date": "2019_09_17",
#   "start_date": "2019/09/17 00:00",
#   "end_date": "2019/09/17 23:59",
#   "fps": 25,
#   "dim":"1920x1080",
#   "text_pos": "bl",
#   "wat_pos": "tl",
#   "extra_text": "br",
#  "logo": "",
#   "logo_pos": "",
#   "blend_sd": 0
#}
#video_path =  generate_timelapse(job['cam_id'],job['date'],job['start_date'],job['end_date'],job['fps'],job['dim'],job['text_pos'],job['wat_pos'],job['extra_text'],job['logo'],job['logo_pos'],job['blend_sd'],0) 
#print(video_path)       