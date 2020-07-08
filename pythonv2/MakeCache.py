#!/usr/bin/python3
# Move a detection (reduced or not) to the Archive

import sys

from lib.FileIO import cfe, load_json_file
from lib.Old_JSON_converter import move_old_detection_to_archive
from lib.MeteorReduce_Tools import * 

# /mnt/ams2/meteors/2019_11_15/2019_11_15_07_49_40_000_010042-trim0263.json
# python3 MakeCache.py /mnt/ams2/meteors/2019_11_15/2019_11_15_07_49_40_000_010042-trim0263.json

# JSON FILE 
new_json = sys.argv[1]          
new_json_data = load_json_file(new_json) 

if(new_json is None or cfe(new_json)==0):
   print("JSON is missing.")
   sys.exit(0) 

# Analyse the new_json file name
tmp_analysed_name = name_analyser(new_json) 

# Generate the stuff in the cache
clear_cache = 1
hd_stack  = get_stacks(tmp_analysed_name,clear_cache,True)
sd_stack  = get_stacks(tmp_analysed_name,clear_cache,False)
HD_frames = get_HD_frames(tmp_analysed_name,clear_cache)

# Generate the Preview for the archive listing
generate_preview(tmp_analysed_name) 

output = ''

# Get the thumbs for the reduced detection (cropped HD frames) 
try:
   HD_frames
except NameError:
   thumbs = ''
   print("ERROR WITH HD FRAMES => THUMBS")
else:
   HD = True
   thumbs = get_thumbs(tmp_analysed_name,new_json_data,HD,HD_frames,clear_cache)
   output = "THUMBS : \n" + str(thumbs) + "\n"
   output += "HD FRAMES \n: " + str(HD_frames) + "\n"

# Create the temporary media (CACHE) for this detection
print(output)
