from lib.PipeImage import quick_video_stack
import os
import sys 
import glob

day = sys.argv[1]

files = glob.glob(f"/mnt/ams2/meteors/{day}/*.mp4")
for vf in files:
    if "HD" in vf:
        continue
    hfile = vf.replace(".mp4", "-half-stack.jpg")
    if os.path.exists(hfile) is False:
        print(vf)
        quick_video_stack(vf, count = 0, save=1)
    else:
        print("half ok", hfile)
