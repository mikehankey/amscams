import re
import cgitb

# PATTERN FOR THE FILE NAMES
# YYYY_MM_DD_HH_MM_SS_MSS_CAM_STATION[_HD].EXTENSION
FILE_NAMES_REGEX = r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{3})_(\d{6})_([^_^.]+)(_HD)?(\.)?(\.[0-9a-z]+$)"
FILE_NAMES_REGEX_GROUP = ["name","year","month","day","hour","min","sec","ms","cam_id","station_id","HD","ext"]

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


# GENERATES THE REDUCE PAGE METEOR
# from a URL 
# cmd=reduce2
# &video_file=[PATH]/[VIDEO_FILE].mp4
def reduce_meteor2(json_conf,form):
   
   # Debug
   cgitb.enable()

   # Get Video File & Analyse the Name to get quick access to all info
   video_file    = form.getvalue("video_file")
   analysed_name = name_analyser(video_file)

   # Test if the name is ok
   if(len(analysed_name)==0):
      print("FILE NAME " + video_file + " is not valid")
      exit
   else:
      print(analysed_name)

   # Is it HD? & retrieve the related JSON file that contains the reduced data
   if("HD" in analysed_name):
      HD = True
      meteor_json_file = video_file.replace("_HD.mp4", ".json") 
   else:
      HD = False
      meteor_json_file = video_file.replace(".mp4", ".json")

   

    

