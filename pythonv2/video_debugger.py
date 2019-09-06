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
_main_title = "BEST OF PERSEIDS 2019"
_producer =  ""
_output_path = '/mnt/ams2/opening_title.mp4'
#create_title_video(_main_title,_producer,_output_path,(255,255,255,255),True)


#CREATE OPERATOR VIDEOS
_operators = ["Mike Hankey","Elizabeth Warner - UMD", "Ed Abel", "Peter Deterline", "Vishnu Reddy", "Bob Lunsford", "Mel Helm - SRO"]
_duration = 75 # In frames at 25fps
_output_path =  '/mnt/ams2/operator_credits.mp4'
_with_line_animation = True # Optional - it's True by default
_line_height = 55 # Optional - it's 45 by default, it works well with <=12 operators (one per line)
_operator_font_size = 40 # Optional - it's 30 by default, it works well with <=12 operators (one per line)
#create_thank_operator_video(_operators, _duration, _output_path,_with_line_animation,_line_height,_operator_font_size) 

#CREATE ALL SKY CAMS VIDEOS
_text1= "Allskycams.com"
_text2= ""
_duration = 100 # In frames at 25fps
_output = '/mnt/ams2/allskycams.mp4'
#create_allskycams_video(_text1,_text2,_duration,_output)

#CREATE MUSIC CREDIT VIDEO
_text1= "Music by"
_text2= "NAKED JUNGLE"
_text3= "nakedjungle.bandcamp.com"
_duration = 50 # In frames at 25fps
_output = '/mnt/ams2/music_credits.mp4'
#create_credit_video(_text1,_text2,_text3,_duration,_output)
# PRODUCE CREEDIT
#create_credit_video("Produced by","Mike Hankey","",_duration,'/mnt/ams2/producedby.mp4')


# CONCAT VIDEOS START
_from = 5 # in seconds
_total_duration = 8 # in seconds
#concat_videos_fade('/mnt/ams2/opening_title.mp4','/mnt/ams2/music_credits.mp4','/mnt/ams2/1.mp4',_from,_total_duration)
_from = 10 # in seconds
_total_duration = 12 # in seconds
#concat_videos_fade('/mnt/ams2/1.mp4','/mnt/ams2/producedby.mp4','/mnt/ams2/START.mp4',_from,_total_duration)

# CONCAT VIDEO END
_from = 5 # in seconds
_total_duration = 12 # in seconds
#concat_videos_fade('/mnt/ams2/operator_credits.mp4','/mnt/ams2/allskycams.mp4','/mnt/ams2/END.mp4',_from,_total_duration) 



############# TEST CV crop
import cv2
import sys
import numpy as np
from lib.VIDEO_VARS import *


def create_crop(file,x,y,dest):
   HD = True
   img = cv2.imread(file)

   
 
   # Destination
   thumb_w = 50
   thumb_h = 50

   # Box of origin (selected by user)
   org_select_w = 50
   org_select_h = 50

   if(HD is True):
      org_w_HD = HD_W
      org_h_HD = HD_H
   else:
      org_w_HD = SD_W
      org_h_HD = SD_H

   # Create empty image 50x50 in black so we don't have any issues while working on the edges of the original frame 
   crop_img = np.zeros((thumb_w,thumb_h,3), np.uint8)
   
   # Default values
   org_x = int(x - org_select_w/2)
   org_w = int(org_select_w + org_x)
   org_y = int(y  - org_select_h/2)
   org_h = int(org_select_h + org_y)    

   thumb_dest_x = 0
   thumb_dest_w = thumb_w
   thumb_dest_y = 0
   thumb_dest_h = thumb_h

   # We don't want to crop where it isn't possible
   diff_x_left  = (x-(org_select_w/2))
   diff_x_right = org_w_HD-(x+(org_select_w/2)) 
   diff_y_top   = (y-(org_select_h/2))
   diff_y_bottom = org_h_HD - (y+(org_select_h/2))

   # If the x is too close to the edge

   # ON THE LEFT
   if(diff_x_left<0): 

      # Destination in thumb (img)
      thumb_dest_x = int(thumb_w/2 - diff_x_left)

      # Part of original image
      org_x = 0
      org_w = org_select_w - thumb_dest_x  

   # ON RIGHT 
   elif(diff_x_right<0):

      
      print("CASE TWO")

      # Destination in thumb (img) 
      thumb_dest_w = int(thumb_w+diff_x_right)  

      # Part of original image 
      org_x = org_w_HD - thumb_dest_w
      org_w = org_w_HD   

   # ON TOP
   if(diff_y_top<0):

      
      print("CASE THREE")

      # Destination in thumb (img)
      thumb_dest_y = int(thumb_h/2 - diff_y_top)

      # Part of the original image
      org_y = 0
      org_h = org_select_h - thumb_dest_y

   elif(diff_y_bottom<0): 

      
      print("CASE FOUR")
      
      # Destination in thumb (img)
      thumb_dest_h = int(thumb_h+diff_y_bottom)  

      # Part of the original image
      org_y =  org_h_HD - thumb_dest_h   
      org_h =  org_h_HD


   print("IN CROP")
   print(" X "  + str(thumb_dest_x))
   print(" W "  + str(thumb_dest_w))
   print(" Y "  + str(thumb_dest_y))
   print(" H "  + str(thumb_dest_h))
   print(" ")
   print("IN ORG")
   print(" X "  + str(org_x))
   print(" W "  + str(org_w))
   print(" Y "  + str(org_y))
   print(" H "  + str(org_h))

   img1 = crop_img[thumb_dest_y:thumb_dest_h,thumb_dest_x:thumb_dest_w]
   print("CROP")
   print(str(img1.shape[1]) + "x" + str(img1.shape[0]) )

   print("ORG IMG")
   print(str(img.shape[1]) + "x" + str(img.shape[0]) )
   img2 = img[org_y:org_h,org_x:org_w]
   print("CROPPED IMG")
   print(str(img2.shape[1]) + "x" + str(img2.shape[0]) )


   crop_img[thumb_dest_y:thumb_dest_h,thumb_dest_x:thumb_dest_w] = img[org_y:org_h,org_x:org_w]
   cv2.imwrite(dest,crop_img)
   print(dest)



print("1359,620")
create_crop("/mnt/ams2/CACHE/AMS7/2019/08/14/2019_08_14_09_32_02_520_010040_AMS7_HD/THUMBS/2019_08_14_09_32_02_520_010040_AMS7_HD_frm32.png",1359,620,"/mnt/ams2/test1.png")  
#print("1910,500")
#create_crop("/mnt/ams2/CACHE/AMS7/2019/08/14/2019_08_14_09_32_02_520_010040_AMS7_HD/FRAMES/2019_08_14_09_32_02_520_010040_AMS7_HD_HDfr_0032.png",1910,500,"/mnt/ams2/test2.png")  
#print("500,10")
#create_crop("/mnt/ams2/CACHE/AMS7/2019/08/14/2019_08_14_09_32_02_520_010040_AMS7_HD/FRAMES/2019_08_14_09_32_02_520_010040_AMS7_HD_HDfr_0032.png",500,10,"/mnt/ams2/test3.png")  
#print("500,1060")
#create_crop("/mnt/ams2/CACHE/AMS7/2019/08/14/2019_08_14_09_32_02_520_010040_AMS7_HD/FRAMES/2019_08_14_09_32_02_520_010040_AMS7_HD_HDfr_0032.png",500,1060,"/mnt/ams2/test4.png")  
#print("500,500")
#create_crop("/mnt/ams2/CACHE/AMS7/2019/08/14/2019_08_14_09_32_02_520_010040_AMS7_HD/FRAMES/2019_08_14_09_32_02_520_010040_AMS7_HD_HDfr_0032.png",500,500,"/mnt/ams2/test5.png")  
