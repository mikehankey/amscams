#!/usr/bin/python3

import cv2
from detectlib import *
import sys
import datetime
import json


json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']


trim_file = sys.argv[1]

print ("FILE:", trim_file)

frames = load_video_frames(trim_file)
#trim_stack = stack_frames(frames)
print("FRAMES: ", len(frames))
max_cons_motion, frame_data, moving_objects, trim_stack = check_for_motion(frames, trim_file)
stacked_image_np = np.asarray(trim_stack)

stacked_image = draw_obj_image(stacked_image_np, moving_objects)

cv2.namedWindow('pepe')
cv2.imshow('pepe', stacked_image)
cv2.waitKey(0)
