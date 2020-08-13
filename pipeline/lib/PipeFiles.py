'''

   PipeFiles.py - functions for dealing with various types file (sd_queue, meteors, detect files etc)

'''

import glob
import time
import os

def get_pending_files(wildcard=None, mvday=1):
   pfiles = []
   if wildcard is not None:
      glob_dir = "/mnt/ams2/SD/*" + wildcard + "*.mp4"
   else:
      glob_dir = "/mnt/ams2/SD/*.mp4"
   files = sorted(glob.glob(glob_dir), reverse=True)
   new_files =[]
   for file in files:
      if "trim" not in file:
         new_files.append(file)

   for file in sorted(new_files, reverse=True):
      #(f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      #sun_status = day_or_night(f_date_str, json_conf)
      cur_time = int(time.time())
      st = os.stat(file)
      size = st.st_size
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60
      if tdiff < 5:
         continue

      pfiles.append(file)
 
   return(pfiles)
