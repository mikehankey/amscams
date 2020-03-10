import os
import subprocess 

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



# Mike's functions for Videos
def find_crop_size(min_x,min_y,max_x,max_y):
   sizes = [[1280,720],[1152,648],[1024,576],[869,504],[768,432], [640,360], [512, 288], [384, 216], [256, 144], [128,72]]
   w = max_x - min_x 
   h = max_y - min_y
   mid_x = int(((min_x + max_x) / 2))
   mid_y = int(((min_y + max_y) / 2))
   best_w = 1919
   best_h = 1079
   for mw,mh in sizes: 
      if w * 2 < mw and h * 2 < mh :
         best_w = mw
         best_h = mh
         print("CROP AREA:", w, h, w* 2, h* 2, mw,mh)
 
   if (best_w/2) + mid_x > 1920:
      cx1 = mid_x + (best_w + mid_x ) - 1920 
      cx1 = 1919 - best_w 
   elif mid_x - (best_w/2) < 0:
      cx1 = 0
   else:
      cx1 = int(mid_x - (best_w/2))
   if (best_h/2) + mid_y > 1080:
      cy1 = 1079 - best_h 
   elif mid_y - (best_h/2) < 0:
      cy1 = 0
   else:
      cy1 = int(mid_y -  (best_h/ 2))
   cx1 = int(cx1)
   cy1 = int(cy1) 
   cx2 = int(cx1 + best_w)
   cy2 = int(cy1 + best_h)
   print(mid_x, mid_y, cx1,cy1,cx2,cy2)
   return(cx1,cy1,cx2,cy2,mid_x,mid_y)

def get_roi(pos_vals=None, object=None, hdm_x=1, hdm_y=1):
   xs = []
   ys = []
   if pos_vals is not None:
      for x,y in ev['pos_vals']:
         xs.append(int(x*hdm_x))
         ys.append(int(y*hdm_y))
         fn += 1
   elif object is not None:
      print("OBJ:", object)
      for i in range(0, len(object['oxs'])):
         xs.append(int(object['oxs'][i]) * hdm_x)
         ys.append(int(object['oys'][i]) * hdm_y)
   min_x = min(xs)
   max_x = max(xs)
   max_y = max(ys)
   min_y = min(ys)
   cx1,cy1,cx2,cy2,mid_x,mid_y = find_crop_size(min_x, min_y, max_x,max_y)

   return(cx1,cy1,cx2,cy2,mid_x,mid_y)



