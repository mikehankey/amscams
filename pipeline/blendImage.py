#!/usr/bin/python3

import cv2
import sys

img1f = sys.argv[1]
img2f = sys.argv[2]

img1 = cv2.imread(img1f)
img2 = cv2.imread(img2f)

blend_image = cv2.addWeighted(img1, .5, img2, .5,0)
blendf = img1f.replace(".jpg", "-blend.jpg")
cv2.imwrite(blendf, blend_image)
