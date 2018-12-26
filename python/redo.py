#!/usr/bin/python3

import glob
import os
import sys

file = sys.argv[1]

# move motion file up one dir
# remove all data files
# remove all trim files
# remove all meteor trim files
# rerun parse motion
# rerun reject filters
# rerun meteor trim (if meteor found)

#/mnt/ams2/SD/proc2/2018_12_17/2018_12_17_22_45_12_000_010002.mp4

el = file.split("/") 
filename = el[-1]
base_dir = file.replace(filename, "")

motion_file = filename.replace(".mp4", "-motion.txt")
data_wildcard = filename.replace(".mp4", "*.txt")
trim_wildcard = filename.replace(".mp4", "*trim*.mp4")
meteor_wildcard = filename.replace(".mp4", "*meteor.mp4")

cmd = "mv " + base_dir + "data/" + motion_file + " " + base_dir
print (cmd)
os.system(cmd)

cmd = "rm " + base_dir + "data/" + data_wildcard
print (cmd)
os.system(cmd)

cmd = "rm " + base_dir + trim_wildcard
print (cmd)
os.system(cmd)


cmd = "./parse-motion.py " + base_dir + motion_file
print(cmd)
os.system(cmd)

files = glob.glob(base_dir + trim_wildcard)
for trim_file in files: 
   if "meteor" not in trim_file:
      cmd = "./reject-filters.py scan_file " + trim_file
      print(cmd)
      os.system(cmd)
      cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
      print(cmd)
      os.system(cmd)


files = glob.glob(base_dir + meteor_wildcard)
for trim_file in files: 
   cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
   print("METEOR:", cmd)
   os.system(cmd)

