import cv2

import sys

f = sys.argv[1]
img = cv2.imread(f)
img = cv2.resize(img, (1920,1080))
cv2.imshow('pepe', img)
cv2.waitKey(0)

20221119_0319019_03_19_01_000_010883-trim-0000-stacked
