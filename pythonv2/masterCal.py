#!/usr/bin/python3

import json
import os
from lib.FileIO import load_json_file

# Batch calibrate entire archive!
# Running this sequence of scripts will:
# find cat_image_star pairs for all meteors and hd_cal_files
# minimize FOV for all meteors and hd_cal_files
# re-find cat_image_star pairs for all meteors and hd_cal_files
# build the meteor index, build the hd_cal_index
# run meteor_cal_all & night_cal to merge all stars from the meteors & hd_cals
# run master_merge to combine all files across nights by cam
# run_merge on all master_merge files
# re-find cat_image_star pairs for all meteors and hd_cal_files
# remake meteor & hd_cal_index
json_conf = load_json_file("../conf/as6.json")

# find all stars in meteors and minimize center fov params

cmd = "./autoCal.py meteor_index imgstars"
print(cmd)
cmd = "./autoCal.py meteor_index cfit"
print(cmd)
os.system(cmd)
# find all stars in hd_cal and minimize center fov params
# this will also run night cal for each night
cmd = "./autoCal.py hd_cal_index cfit"
print(cmd)
os.system(cmd)

# make meteor-star merge files for every night
cmd = "./autoCal.py meteor_cal_all"
print(cmd)
os.system(cmd)


# remake the index based on lastest star find
cmd = "./autoCal.py hd_cal_index "
print(cmd)
os.system(cmd)

# remake the index based on lastest star find
cmd = "./autoCal.py meteor_index "
print(cmd)
os.system(cmd)


# make merge files for each meteor day
cmd = "./autoCal.py meteor_cal_all"
print(cmd)
os.system(cmd)
#

cmd = "./autoCal.py master_merge 010001"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py master_merge 010002"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py master_merge 010003"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py master_merge 010004"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py master_merge 010005"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py master_merge 010006"
print(cmd)
os.system(cmd)
#
cmd = "./autoCal.py run_merge /mnt/ams2/cal/hd_images/master_merge_010001.json 010001 1 &"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py run_merge /mnt/ams2/cal/hd_images/master_merge_010002.json 010002 1 &"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py run_merge /mnt/ams2/cal/hd_images/master_merge_010003.json 010003 1 &"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py run_merge /mnt/ams2/cal/hd_images/master_merge_010004.json 010004 1 &"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py run_merge /mnt/ams2/cal/hd_images/master_merge_010005.json 010005 1 &"
print(cmd)
os.system(cmd)
cmd = "./autoCal.py run_merge /mnt/ams2/cal/hd_images/master_merge_010006.json 010006 1 &"
print(cmd)
os.system(cmd)
