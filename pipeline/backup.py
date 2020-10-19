#!/usr/bin/python3

import os
from lib.DEFAULTS import *

from lib.PipeUtil import cfe

BK_MNT_PT = "/mnt/backup/"
BK_DEV = "/dev/sda1/"
BK_UUID = ""

if cfe(BK_MNT_PT + "/meteors/", 1) == 0:
   cmd = "sudo mount " + BK_DEV + " " + BK_MNT_PT
   print("DRIVE IS NOT MOUNTED!")
   print(cmd)
   exit()

cmd = "/usr/bin/rsync -av /mnt/ams2/meteors " + BK_MNT_PT 
os.system(cmd)
cmd = "/usr/bin/rsync -av /mnt/ams2/cal " + BK_MNT_PT 
os.system(cmd)
cmd = "/usr/bin/rsync -av /home/ams/amscams/conf " + BK_MNT_PT 
os.system(cmd)
cmd = "/usr/bin/rsync -av /mnt/ams2/meteor_archive " + BK_MNT_PT 
os.system(cmd)
print(cmd)
