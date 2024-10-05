#!/usr/bin/python3 

# make an index of all hd minfiles
import os
import json
hd_files = os.listdir("/mnt/ams2/HD")

# save as json file 
with open('/mnt/ams2/HD/HD.json', 'w') as outfile:
    json.dump(hd_files, outfile)

