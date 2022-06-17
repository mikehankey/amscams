from Classes.ASAI import AllSkyAI
import cv2
import os 

ASAI = AllSkyAI()
ASAI.load_all_models()

star_dir = "/mnt/f/AI/DATASETS/STAR_YN/xnon_stars/"
files = os.listdir(star_dir)

for ff in files:
   img = cv2.imread(star_dir + ff) 
   star_yn = ASAI.star_yn(img)
   print(star_yn, ff)
   if star_yn > 50:
      cv2.imshow('pepe', img)
      cv2.waitKey(30)
      os.system("rm " + star_dir + ff)
