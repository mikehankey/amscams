# Get info from
# /mnt/ams2/meteors/YYYY_MM_DD
# in order to know if we have a detection for a given day
# (used for the minutes list)
import glob
import os
import sys

from lib.Get_Cam_ids import get_the_cam_ids
from lib.FileIO import cfe

METEOR_FOLDER = "/mnt/ams2/meteors/"

# Do we have a detection for this given date & time & cam_id
def get_meteor_date_cam(ms,sec,_min,hour,day,month,year,cam_id):

   # Dir to glob
   main_dir = METEOR_FOLDER + os.sep + str(year) + "_" + str(month).zfill(2) + '_' + str(day).zfill(2)  
   pseud_name = str(year) + "_" + str(month).zfill(2) + '_' + str(day).zfill(2) + '_' + str(hour).zfill(2) + '_' + str(_min).zfill(2) + '_' + str(sec).zfill(2) + '_' + str(ms).zfill(3) + '_' + str(cam_id) + "*" + ".json"
   cam_ids = get_the_cam_ids(); 

   print("MAIN DIR<br>")
   print(main_dir)
   print("<br>PSEUD_NAME<br>")
   print(pseud_name)

   if(cfe(main_dir)):
      # We glob the folder to get all detection for this day
      all_jsons = glob.glob(main_dir + os.sep + pseud_name)
      print(all_jsons)
      sys.exit(0)
      for json in all_jsons:
         print(all_jsons)
