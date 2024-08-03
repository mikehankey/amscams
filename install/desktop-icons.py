#!/usr/bin/python3 

import os
d = "/home/ams/Desktop"
if os.path.exists(d) is False:
    os.makedirs(d)
cmd = "cp /home/ams/amscams/install/*.desktop /home/ams/Desktop"
os.system(cmd)

