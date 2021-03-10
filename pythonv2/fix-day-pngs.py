#!/usr/bin/python3
import os

os.system("find /mnt/ams2/SD/proc2/daytime/ |grep png > /tmp/png_list.txt")

fp = open("/tmp/png_list.txt")
for line in fp:
   old_file = line.replace("\n", "")
   new_file = old_file.replace(".png", ".jpg") 
   cmd = "convert -quality 70 " + old_file + " " + new_file 
   os.system(cmd)
   print(cmd)

   cmd = "rm " + old_file 
   os.system(cmd)
   print(cmd)
  
os.system("echo 1 > fixed-day-pngs.txt") 
