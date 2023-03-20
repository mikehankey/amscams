import cv2
import sys
from lib.PipeVideo import ffmpeg_cats, load_frames_simple


vid = sys.argv[1]

sd_frames = load_frames_simple(vid)


for fr in sd_frames:
   cv2.imshow('pepe', fr)
   cv2.waitKey(30)
