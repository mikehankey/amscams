import re
import cgitb
import sys
import os.path
from pathlib import Path

# PATTERN FOR THE FILE NAMES
# YYYY_MM_DD_HH_MM_SS_MSS_CAM_STATION[_HD].EXT
FILE_NAMES_REGEX = r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{3})_(\w{6})_([^_^.]+)(_HD)?(\.)?(\.[0-9a-z]+$)"
FILE_NAMES_REGEX_GROUP = ["name","year","month","day","hour","min","sec","ms","cam_id","station_id","HD","ext"]

# PATTERN FOR THE CACHE FOLDER
 



# Parses a regexp (FILE_NAMES_REGEX) a file name
# and returns all the info defined in FILE_NAMES_REGEX_GROUP
def name_analyser(file_names):
   matches = re.finditer(FILE_NAMES_REGEX, file_names, re.MULTILINE)
   res = {}
  
   for matchNum, match in enumerate(matches, start=1):
      
      for groupNum in range(0, len(match.groups())):
         if(match.group(groupNum) is not None):
            res[FILE_NAMES_REGEX_GROUP[groupNum]] = match.group(groupNum)
         groupNum = groupNum + 1

   return res


# Test if a file exist in the CACHE
# /mnt/ams2/CACHE/[STATION_ID]/[YEAR]/[MONTH]/[DAY]/FRAMES/YEAR_MONTH_DAY_HH_MM_SS_sss_[CAM_ID]-trim[xxxx]/



# GENERATES THE REDUCE PAGE METEOR
# from a URL 
# cmd=reduce2
# &video_file=[PATH]/[VIDEO_FILE].mp4
def reduce_meteor2(json_conf,form):
   
   # Debug
   cgitb.enable()

   # Get Video File & Analyse the Name to get quick access to all info
   video_full_path   = form.getvalue("video_file")
   analysed_name = name_analyser(video_full_path)
      
   # Test if the name is ok
   if(len(analysed_name)==0):
      print("<div id='main_container' class='container mt-4 lg-l'><div class='alert alert-danger'>"+ video_full_path + " <b>is not valid video file name.</b></div></div>")
      sys.exit(0)
   elif(os.path.isfile(video_full_path) is False):
      print("<div id='main_container' class='container mt-4 lg-l'><div class='alert alert-danger'>"+ video_full_path + " <b>not found.</b></div></div>")
      sys.exit(0)
   else:
      print(analysed_name)

   # Is it HD? & retrieve the related JSON file that contains the reduced data
   if("HD" in analysed_name):
      HD = True
      meteor_json_file = video_full_path.replace("_HD.mp4", ".json") 
   else:
      HD = False
      meteor_json_file = video_full_path.replace(".mp4", ".json")


   # Does the JSON file exists?
   if(os.path.isfile(meteor_json_file) is False):
      print("<div id='main_container' class='container mt-4 lg-l'><div class='alert alert-danger'>"+ meteor_json_file + " <b>not found.</b><br>This detection hasn't been reduced yet.</div></div>")
      sys.exit(0)   
   

    

