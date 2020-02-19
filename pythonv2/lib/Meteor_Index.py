# Get info from
# /mnt/ams2/meteors/YYYY_MM_DD
# in order to know if we have a detection for a given day
# (used for the minutes list)
import glob
import os
import sys

from lib.Get_Cam_ids import get_the_cam_ids
from lib.FileIO import cfe

METEOR_FOLDER = "/mnt/ams2/meteors"

# Return list of detection for a given day 
def get_meteor_date_cam(day,month,year):
   toReturn = {}
   # Dir to glob
   main_dir = METEOR_FOLDER + os.sep + str(year) + "_" + str(month).zfill(2) + '_' + str(day).zfill(2)  + os.sep
   
   if(cfe(main_dir,1)==1):
      # We glob the folder to get all detection for this day
      all_jsons = glob.glob(main_dir + "*.json")
       
      for json in all_jsons:
         if('reduced' not in json):
            tmp = json.split("/")[-1]
 
            try:
               toReturn[tmp.split("-trim")[0]]
               toReturn[tmp.split("-trim")[0]].append(json)
            except:
               toReturn[tmp.split("-trim")[0]] = [json]
 
   return toReturn
