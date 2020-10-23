#!/usr/bin/python3

import sys
import os
from lib.UtilLib import fn_dir
from lib.FileIO import cfe 
min_file = sys.argv[1]

fn,dir = fn_dir(min_file)
vals_file = dir + "data/" + fn
vals_file = vals_file.replace(".mp4", "-vals.json")
mm_file = vals_file.replace("-vals.json", "-maybe-meteors.json")
tm_file = vals_file.replace("-vals.json", "-toomany.json")

cmd = "./scan_stack.py ss " + min_file + " night"
print(cmd)
os.system(cmd)
cmd = "./flex-detect.py dv " + vals_file
os.system(cmd)
if cfe(mm_file):
   cmd = "./flex-detect.py vm " + mm_file 
   os.system(cmd)
elif cfe(tm_file) :
   cmd = "./flex-detect.py vtm " + tm_file
   os.system(cmd)
else:
   print("No meteors detect in vals.")


#./flex-detect.py dv /mnt/ams2/SD/proc2/2020_10_23/data/2020_10_23_00_38_00_000_010004-vals.json
#/mnt/ams2/SD/proc2/2020_10_23/data/2020_10_23_00_38_00_000_010004-maybe-meteors.json
