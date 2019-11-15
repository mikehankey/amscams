# Move a detection (reduced or not) to the Archive

import sys


from FileIO import cfe
from Old_JSON_converter import move_old_detection_to_archive
 
# JSON FILE 
json_file = sys.argv[0]          
# HD VIDEO FILE
hd_video = sys.argv[1]
# SD VIDEO FILE
sd_video = sys.argv[2]

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

# Create the temporary media (CACHE) for this detection
print("NEW ARCHIVE:")
print("NEW JSON:" + new_json)
print("NEW HD VID:" + new_hd_vid)
print("NEW SD VID:" +  new_sd_vid)

