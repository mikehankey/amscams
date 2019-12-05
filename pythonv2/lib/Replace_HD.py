import cgitb
import sys
import os

from lib.FileIO import cfe
from VIDEO_VARS import HD_W, HD_H


# Replace HD video by the resized SD video
def replace_HD(form):
   
   # Debug
   cgitb.enable()

   json_file = form.getvalue('json_file')

   # Test if JSON exists
   if(cfe(jsonf_file)==0):
      print("{'error':'JSON File not readable,'status':0}")
      sys.exit(0)

   # Get Paths to SD & HD Video
   video_hd_full_path = json_file.replace('.json','-HD.mp4')
   video_sd_full_path = json_file.replace('.json','-SD.mp4')

   # Test if HD exists
   if(cfe(video_hd_full_path)==0):
      print("{'error':'HD file not found,'status':0}")
      sys.exit(0)

   # Test if SD exists
   if(cfe(video_sd_full_path)==0):
      print("{'error':'SD file not found,'status':0}")
      sys.exit(0)

   # Resize SD and replace HD
   cmd = "ffmpeg -i " + video_sd_full_path + " -vf scale="+HD_W+":"+HD_H+" +  video_hd_full_path"
   os.system(cmd)
