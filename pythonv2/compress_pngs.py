#!/usr/bin/python3

import cv2
import sys

def compress_file(file):
   image = cv2.imread(file)
   img = cv2.imread(file, cv2.IMREAD_UNCHANGED) 
   cv2.imwrite('compress_img1.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
   cv2.imwrite('compress_img1.png', img, [int(cv2.IMWRITE_PNG_COMPRESSION), 90])


file = sys.argv[1]
compress_file(file)
