import os
import subprocess 
import sys

from lib.FileIO import load_json_file, cfe
from lib.VIDEO_VARS import HD_H, HD_W

PREDEFINED_CROPPED_SIZE =  [[1280,720],[1152,648],[1024,576],[869,504],[768,432], [640,360], [512, 288], [384, 216], [256, 144], [128,72]]


# Get dimension of a file (w,h)
def get_media_file_dimensions(video_file):
   
   cmd = "ffprobe "+ video_file + " > /tmp/ffprobe.txt 2>&1"

   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")   
      print(cmd + " was successfull >> " +  output) 
   except subprocess.CalledProcessError as e:
      print("Command " + cmd + "  return on-zero exist status: " + str(e.returncode))
      sys.exit(0)   

   cmd = "grep Stream /tmp/ffprobe.txt"
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")   
      print(cmd + " was successfull >> " +  output) 
   except subprocess.CalledProcessError as e:
      print("Command " + cmd + "  return on-zero exist status: " + str(e.returncode))
      sys.exit(0)  

   # Read ouput
   el = output.split(",")
   dim = el[3].replace(" ", "")
   w, h = dim.split("x") 

   return(w,h) 

# Returns x,y,w,h 
def find_crop_size(min_x,min_y,max_x,max_y):
   sizes = PREDEFINED_CROPPED_SIZE

   w = max_x - min_x 
   h = max_y - min_y
   
   mid_x = int(((min_x + max_x) / 2))
   mid_y = int(((min_y + max_y) / 2))

   best_w = HD_W -1 
   best_h = HD_H -1

   for mw,mh in sizes: 
      if w * 2 < mw and h * 2 < mh :
         best_w = mw
         best_h = mh
 
   if (best_w/2) + mid_x > HD_W:
      cx1 = mid_x + (best_w + mid_x ) - HD_W 
      cx1 = (HD_W-1) - best_w 
   elif mid_x - (best_w/2) < 0:
      cx1 = 0
   else:
      cx1 = int(mid_x - (best_w/2))
   if (best_h/2) + mid_y > HD_H:
      cy1 = (HD_H-1) - best_h 
   elif mid_y - (best_h/2) < 0:
      cy1 = 0
   else:
      cy1 = int(mid_y -  (best_h/ 2)) 

   return(int(cx1),int(cy1),int(cx1+best_w),int(cy1+best_h),mid_x,mid_y)

 

# Find ROI = Region Of Interest for a given video (Crop Dimension)
def get_ROI(data_with_xy,is_hd=True):

   xs = []
   ys = [] 

   for xy in data_with_xy:
      print("data_with_xy[xy]")
      print(xy)
      xs.append(int(xy['x']))
      ys.append(int(xy['y']))

   return find_crop_size(min(xs), min(ys), max(xs), max(ys))


# Find ROI based on archive json 
def get_ROI_from_arc(arc_json_file):

   json_data = load_json_file(arc_json_file)

   if(json_data is not False):
      
      if('frames' in json_data): 
         if(len(json_data['frames'])>0):  
            if('info' in json_data):
               
               # Do we have the HD?
               HD = False
               arc_video_file = arc_json_file.replace('.json','-HD.mp4')
               if(cfe(arc_video_file)):
                  HD = True
                  roi = get_ROI(json_data['frames'],HD)          
                  print("ROI !")
                  print(roi)
   else:
      print(arc_json_file + ' not found or corrupted.')



