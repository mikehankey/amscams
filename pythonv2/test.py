#!/usr/bin/python3

import cv2

print(cv2.ocl.haveOpenCL())
cv2.ocl.setUseOpenCL(True)
print(cv2.ocl.useOpenCL())

img = cv2.UMat(cv2.imread("/mnt/ams2/SD/proc2/2020_02_29/images/2020_02_29_23_19_08_000_010005-stacked-tn.png", cv2.IMREAD_COLOR))
imgUMat = cv2.UMat(img)
gray = cv2.cvtColor(imgUMat, cv2.COLOR_BGR2GRAY)
gray = cv2.GaussianBlur(gray, (7, 7), 1.5)
gray = cv2.Canny(gray, 0, 50)

#cv2.imshow("edges", gray)
#cv2.waitKey();
