#!/usr/bin/python3
import math
import numpy as np
import cv2
import sys
from lib.PipeAutoCal import get_cal_files
from lib.PipeUtil import cfe, load_json_file, save_json_file

def rotate_bound(image, angle):
    # grab the dimensions of the image and then determine the
    # center
    (h, w) = image.shape[:2]
    (cX, cY) = (w // 2, h // 2)
    # grab the rotation matrix (applying the negative of the
    # angle to rotate clockwise), then grab the sine and cosine
    # (i.e., the rotation components of the matrix)
    M = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cos = np.abs(M[0, 0])
    sin = np.abs(M[0, 1])
    # compute the new bounding dimensions of the image
    nW = int((h * sin) + (w * cos))
    nH = int((h * cos) + (w * sin))
    # adjust the rotation matrix to take into account translation
    M[0, 2] += (nW / 2) - cX
    M[1, 2] += (nH / 2) - cY
    # perform the actual rotation and return the image
    return cv2.warpAffine(image, M, (nW, nH))


img_files = [
"/mnt/ams2/SD/proc2/daytime/2020_09_22/images/2020_09_22_11_46_26_000_010001-stacked-tn.jpg",
"/mnt/ams2/SD/proc2/daytime/2020_09_22/images/2020_09_22_11_46_32_000_010002-stacked-tn.jpg",
"/mnt/ams2/SD/proc2/daytime/2020_09_22/images/2020_09_22_11_46_40_000_010003-stacked-tn.jpg",
"/mnt/ams2/SD/proc2/daytime/2020_09_22/images/2020_09_22_11_46_46_000_010004-stacked-tn.jpg",
"/mnt/ams2/SD/proc2/daytime/2020_09_22/images/2020_09_22_11_46_54_000_010005-stacked-tn.jpg",
"/mnt/ams2/SD/proc2/daytime/2020_09_22/images/2020_09_22_11_46_47_000_010006-stacked-tn.jpg"
]

ch = 1200
cw = 1200
comp = np.zeros((ch,cw,3),dtype=np.uint8)
cv2.line(comp, (600,0), (int(600),int(1200)), (100,100,100), 1)
iws = []
ihs = []
expand = 0
for i in range(0, 6):

   cf = get_cal_files(img_files[i], None)
   cal_file = cf[0][0]
   cp = load_json_file(cal_file)
   print("RA", cp['ra_center'])
   print("DEC", cp['dec_center'])
   print("AZ", cp['center_az'])
   print("EL:", cp['center_el'])
   print("Pos Ang:", cp['position_angle'])
   print("PX Scale:", cp['pixscale'])
   img = cv2.imread(img_files[i])
   line_x1 = int(img.shape[1] / 2)
   line_y1 = int(img.shape[0] / 2)
   line_d = 100
   line_x2 = line_x1 + 360-(line_d * math.cos(cp['position_angle']))
   line_y2 = line_y1 + 360-(line_d * math.sin(cp['position_angle']))
   cv2.line(img, (line_x1,line_y1), (int(line_x2),int(line_y2)), (100,100,255), 1)
   line_x2 = line_x1 + (line_d * math.cos(cp['position_angle']))
   line_y2 = line_y1 + (line_d * math.sin(cp['position_angle']))
   cv2.line(img, (line_x1,line_y1), (int(line_x2),int(line_y2)), (255,100,100), 1)
   #img= cv2.flip(img,0)

   #img = cv2.rotate(img,cv2.ROTATE_180)
   if expand == 0:
      expand = int(img.shape[1] / 8)
   a = i * 72
   print("ANG vs POS ANG:", a, cp['position_angle'], a - cp['position_angle'])
   y_off = 100
   print(i, a)
   a = cp['position_angle'] + 90
   rimage = rotate_bound(img, int(a))
   #rimage = cv2.flip(rimage,1)
   ih,iw = rimage.shape[0:2]
   ihs.append(ih)
   iws.append(iw)
   # TOP / NORTH
   if i == 0:
      cx = int(cw / 2) - int(iw / 2)
      cy = 0 + y_off
   # TOP RIGHT / NE
   if i == 1:
      cx = int(cw / 2) + expand #+ int(iw / 3)
      cy = 0 + y_off #int(ihs[0]/4)
   # BOTTOM RIGHT / SE
   if i == 2:
      cx = int(cw / 2) - int(iws[0]/4 )
      cy = ihs[0] + int(ihs[1] / 4) + y_off
   # BOTTOM LEFT / SW
   if i == 3:
      cx = int(cw / 2) - int(iw) + int(iws[0]/4 )
      cy = ihs[0] + int(ihs[1] / 4) + y_off
   # TOP LEFT NW
   if i == 4:
      cx = int(cw / 2) - int(iw) - expand
      cy = 0 + y_off
   # MIDDLE ZENITH 
   if i == 5:
      cx = int(cw / 2) - int(iws[0]/2)
      cy = int(ihs[0]) + int(ihs[0]/8) + y_off
   mask_ind = (rimage==0)
   bgcp = comp[cy:cy+ih,cx:cx+iw]
   rimage[mask_ind] = bgcp[mask_ind]
   comp[cy:cy+ih,cx:cx+iw] = rimage
   cv2.imshow('pepe', rimage)
   cv2.imshow('pepe', comp)
   cv2.waitKey(0)
