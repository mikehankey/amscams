#!/usr/bin/python3

import glob
import sys
import os
dir = "/mnt/ams2/SD/proc2/"

day = sys.argv[1]

dir += day + "/data/" 
print(dir)
nom = glob.glob(dir + "*nometeor.json")
for no in nom:
   maybe = no.replace("nometeor", "maybe-meteors")
   cmd = "mv " + no + " " + maybe
   os.system(cmd)
   print(cmd)
