# Get info from
# /mnt/ams2/meteors/YYYY_MM_DD
# in order to know if we have a detection for a given day
# (used for the minutes list)
import glob
import os

from lib.Get_Cam_ids import get_the_cam_ids
from lib.FileIO import cfe

METEOR_FOLDER = "/mnt/ams2/meteors/"

# Do we have a detection for this given date & time & cam_id
def get_meteor_date_cam(ms,sec,min,hour,day,month,year,cam_id):

   # Dir to glob
   main_dir = METEOR_FOLDER + os.sep + str(year) + "_" + str(month).zfill(2) + '_' + str(day).zfill(2)  
   cam_ids = get_the_cam_ids(); 

   if(cfe(main_dir)):
      # We glob the folder to get all detection for this day
      all_jsons = glob.glob(main_dir + os.sep + '*' + cam_id + '*.json')

      for json in all_jsons
         print(all_jsons)
