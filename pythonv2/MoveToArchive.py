# Move a detection (reduced or not) to the Archive

import sys

from lib.FileIO import cfe, load_json_file
from lib.Old_JSON_converter import move_old_detection_to_archive
from lib.MeteorReduce_Tools import * 

# EXAMPLE
# /mnt/ams2/meteors/2019_11_15/2019_11_15_07_49_37_000_010042-trim-263-HD-meteor.mp4
# /mnt/ams2/meteors/2019_11_15/2019_11_15_07_49_40_000_010042-trim0263.mp4
# /mnt/ams2/meteors/2019_11_15/2019_11_15_07_49_40_000_010042-trim0263.json
# python3 MoveToArchive.py /mnt/ams2/meteors/2019_11_15/2019_11_15_07_49_40_000_010042-trim0263.json /mnt/ams2/meteors/2019_11_15/2019_11_15_07_49_37_000_010042-trim-263-HD-meteor.mp4 /mnt/ams2/meteors/2019_11_15/2019_11_15_07_49_40_000_010042-trim0263.mp4

# JSON FILE 
json_file = sys.argv[1]          
# HD VIDEO FILE
hd_video = sys.argv[2]
# SD VIDEO FILE
sd_video = sys.argv[3]

# FOR NOW, WE NEED THE 3 FILES TO PROPERLY MOVE A DETECTION
if(hd_video is None or cfe(hd_video)==0):
   print("HD video is missing.")
   sys.exit(0)

if(sd_video is None or cfe(sd_video)==0):
   print("SD video is missing.")
   sys.exit(0)

if(json_file is None or cfe(json_file)==0):
   print("JSON is missing.")   
   sys.exit(0)
  
# Move everything
new_json,new_hd_vid,new_sd_vid = move_old_detection_to_archive(json_file,sd_video,hd_video, False) 

# Analyse the new_json file name
tmp_analysed_name = name_analyser(new_json) 

# Generate the stuff in the cache
clear_cache = 1
hd_stack = get_stacks(tmp_analysed_name,clear_cache,True)
sd_stack = get_stacks(tmp_analysed_name,clear_cache,False)
HD_frames = get_HD_frames(tmp_analysed_name,clear_cache)

output = ''

# Get the thumbs for the reduced detection (cropped HD frames) 
try:
   HD_frames
except NameError:
   thumbs = ''
else:
   HD = true
   thumbs = get_thumbs(tmp_analysed_name,new_json,HD,HD_frames,clear_cache)
   output = "THUMBS : " + thumbs
   output = "HD FRAMES : " + HD_frames

# Create the temporary media (CACHE) for this detection
print("NEW ARCHIVE:")
print("NEW JSON:" + new_json)
print("NEW HD VID:" + new_hd_vid)
print("NEW SD VID:" +  new_sd_vid)
print("HD STACK:" + hd_stack)
print("SD STACK:" + sd_stack)
print(output) 

