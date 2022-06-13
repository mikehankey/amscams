import sys
import os
from lib.PipeAutoCal import make_az_grid
from lib.PipeUtil import load_json_file 
import cv2

json_conf = load_json_file("../conf/as6.json")

cal_file = sys.argv[1]
if os.path.exists(cal_file) is False:
   print(cal_file, " not found")
   exit()

cal_image = cv2.imread(cal_file)

if "meteors" in cal_file:
   json_file = cal_file.replace("-stacked.jpg", ".json")
   grid_file = cal_file.replace("-stacked.jpg", "-grid.jpg")
   mj = load_json_file(json_file)
else:
   json_file = cal_file.replace("-stacked.png", "-stacked-calparams.json")
   if os.path.exists(json_file) is False:
      json_file = cal_file.replace("-stacked.png", "-calparams.json")
   grid_file = cal_file.replace("-stacked.png", "-grid.png")
   cp = load_json_file(json_file)
   mj = {}
   mj['cp'] = cp
   mj['sd_trim'] = cal_file.replace("-stacked.jpg", ".mp4") 

grid_img, grid_blend = make_az_grid(cal_image, mj,json_conf,grid_file)

blend_file = grid_file.replace("-grid", "-blend")
cv2.imwrite(grid_file, grid_img)
cv2.imwrite(blend_file, grid_blend)
print("saved:", grid_file)
