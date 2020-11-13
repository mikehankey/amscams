#!/usr/bin/python3 
import os
fp = open("010309.txt")
for line in fp:
   old = line.replace("\n", "")
   new = old.replace("010309", "010339")
   cmd = "mv " + old + " " + new
   print(cmd)
   os.system(cmd)
