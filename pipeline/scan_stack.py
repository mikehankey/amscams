
import glob
from MinFile import MinFile
import datetime



def run_scan_and_stack():


   in_dir = "/mnt/ams2/SD/proc2/2021_03_15/"
   files = glob.glob(in_dir + "*.mp4")
   for vfile in sorted(files, reverse=True):
      if "trim" in vfile:
         continue
      print(vfile)
      start = datetime.datetime.now()
      min_file = MinFile(sd_filename= vfile)
      min_file.scan_and_stack()
      end = datetime.datetime.now()
      elp = (end - start).total_seconds()
      print("Elapsed:", elp)

run_scan_and_stack()

