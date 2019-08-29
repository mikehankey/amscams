import os
import glob
import subprocess 
from lib.VIDEO_VARS import * 
from lib.Video_Tools import * 
from lib.Video_Tools_cv import * 
from os import listdir, remove
from os.path import isfile, join, exists

from lib.Video_Title_cv import *


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
#    'json_conf' : '/mnt/ams2/conversion/2019_08_10_06_41_52_000_010042-trim0777/2019_08_10_06_42_24_280_010042_AMS7_HD.json',
#    'video_file' :'/mnt/ams2/conversion/2019_08_10_06_41_52_000_010042-trim0777/2019_08_10_06_42_24_280_010042_AMS7_HD.mp4',
#    'rad_x': 500,
#    'rad_y': 500,
#    'rad_name': 'Perseids'
#}  
 
#new_remaster(data)  
#remaster(data)  


################### TEST CREATE TILE
 

#CREATE INFO VIDEO FROM FRAMES
import cv2 
import subprocess 


#create_title_video("BEST OF PERSEIDS 2019","Music by Naked Jungle - nakedjungle.bandcamp.com", '/mnt/ams2/test_title3.mp4',(255,255,255,255))
#create_thank_operator_video(['Mike Hankey','Vincent Perlerin','Marcel Duchamp','The Beatles'],125, '/mnt/ams2/test_end_credits.mp4')
create_allskycams_video("Visit Allskycams.com","for more information about our all sky cameras",125, '/mnt/ams2/test_allsky.mp4')