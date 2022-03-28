#!/usr/bin/python3

from lib.PipeUtil import load_json_file
import os

cmds = load_json_file("cloud_purge.json")
for cmd in cmds:
   print(cmd)
   os.system(cmd)
