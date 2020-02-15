#!/usr/bin/python3

""" 
   Install script for S3 cloud storage and related modules. 
   Must be run as sudo
"""

import os
os.system("fusermount -u /mnt/wasabi")
os.makedirs("/mnt/archive.allsky.tv")
os.system("chown ams:ams /mnt/archive.allsky.tv")
os.system("chmod 777 /mnt/archive.allsky.tv")
os.system("cd /home/ams/amcams/pythonv2; ./wasabi.py mnt")

