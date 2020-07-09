#!/usr/bin/python3
import os
import glob
from lib.FileIO import cfe

dir = "/mnt/ams2/SD/proc2/2020_07_03/data/"

maybe = glob.glob(dir + "*maybe*")
meteors = glob.glob(dir + "*-meteor.json")
non = glob.glob(dir + "*-no*")

for mb in maybe:
   mt = mb.replace("-maybe-meteors.json", "-meteor.json")
   nm = mb.replace("maybe-meteors", "nometeor")
   if cfe(mt) == 1:
      print("METEOR: ", mb, mt )
   elif cfe(nm) == 1:
      os.system("rm " + nm)
      print("NO METEOR: ", mb, nm)
   else:
      print("MAYBE METEOR: ", mb)

for mm in meteors:
   print("Meteors:", mm)
print(len(meteors))
