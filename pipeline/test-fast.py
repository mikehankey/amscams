from stack_fast import stack_only, get_patch_objects_in_stack, get_stars_in_stack
import os
import numpy as np 
import sys
from time import time
from Classes.ASAI import AllSkyAI
ASAI = AllSkyAI()
ASAI.load_all_models()


vdir = sys.argv[1]
if "mp4" in vdir:
   files = [vdir]
else:
   files = os.listdir(vdir)

for tfile in files :
   vfile = vdir + tfile
   print("VFILE:", vfile)
   if "trim" in vfile:
      continue
   if "mp4" not in vfile:
      continue
   if "0001" not in vfile:
      continue 
   jfile = vfile.replace(".mp4", "-stacked.jpg")
   if os.path.exists(jfile) is True:
      print("STACK EXISTS")
      continue

   cam_id = vfile.split("_")[-1].replace(".mp4", "")
   station_id = "AMS1"
   mask_img = np.zeros((1080,1920,3),dtype=np.uint8)

   t = time()
   print(type(mask_img), mask_img.shape)
   stacked_image = stack_only(vfile, mask_img )
   e = time() - t 
   print("E:", e)
   stack_file = vfile.replace(".mp4", "-stacked.jpg")

   t = time()
   get_patch_objects_in_stack(stack_file, ASAI)
   print(stack_file)
   e = time() - t 
   print("E2:", e)
