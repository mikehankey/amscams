#!/usr/bin/python3

import cv2
import sys

from detectlib import load_video_frames, median_frames
from caliblib import find_bright_pixels

cv2.namedWindow('pepe')
file = sys.argv[1]

frames = load_video_frames(file, 100)
print("FRAMES:", len(frames))

med_stack = median_frames(frames)
star_px, plate_image = find_bright_pixels(med_stack)
print("TOTAL STARS:", len(star_px))
cv2.imshow('pepe', med_stack)
cv2.waitKey(0)
cv2.imshow('pepe', plate_image)
cv2.waitKey(0)
