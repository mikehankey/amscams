"""

review / clean excess false meteors using strict rules 

"""
from ransac_lib import ransac_outliers
from lib.PipeUtil import load_json_file, save_json_file, calc_dist
import os

import sys

date = sys.argv[1]
trash_dir = "/mnt/ams2/trash/" + date + "/" 
if os.path.exists(trash_dir) is False:
   os.makedirs(trash_dir)

rejects = 0
keep = 0
mdir = "/mnt/ams2/meteors/" + date + "/" 
reds = 0
mets = 0
files = os.listdir(mdir)
meteors = {}
for ff in files:
   if "json" in ff:
      if "reduced" in ff:
         reds += 1
         ff = ff.replace("-reduced.json", "")
         if ff not in meteors:
            meteors[ff] = {}
         meteors[ff]['red'] = True
      else:
         ff = ff.replace(".json", "")
         meteors[ff] = {}
         mets += 1

mc = 0

by_min = {}
for met in meteors:
   min_key = met[0:16]
   if min_key not in by_min:
      by_min[min_key] = 0
   else:
      by_min[min_key] += 1
   if os.path.exists(mdir + met + ".json") is True and os.path.exists(mdir + met + ".trash") is False :
      print(mdir + met + ".json")
      mj = load_json_file(mdir + met + ".json")
   else:
      print("No MJ?", mdir + met + ".json")
      continue 
   oc = 1 
   for obj in mj['sd_objects']:
      last_y = 0
      last_x = 0
      XS = []
      YS = []
      xdir_changes = 0
      ydir_changes = 0
      x_dir =0
      y_dir =0
      last_dy = 0
      last_dx = 0
      last_y_dir = 0
      last_x_dir = 0
      if len(obj['history']) < 5:
         short_fail = True
      else:
         short_fail = False 
      for row in obj['history']:
         fn, x, y, w, h, z, z = row
         if last_x == 0:
            last_x = x
            last_y = y
            last_d = 0
         else:
            last_d = calc_dist((last_x, last_y), (x,y))
         last_dx = x - last_x
         if last_dx > 0:
            x_dir = 1
         else: 
            x_dir = 0

         if last_dy > 0:
            y_dir = 1
         else: 
            y_dir = 0
         
         if y_dir != last_y_dir: 
            ydir_changes += 1
         if x_dir != last_x_dir: 
            xdir_changes += 1


         last_x_dir = x_dir
         last_y_dir = y_dir
         last_dy = y - last_y
         last_x = x
         last_y = y
         XS.append(x)
         YS.append(y)
         print(oc, x,y,last_dx,last_dy, last_d, xdir_changes, ydir_changes)
      changes_failed = False
      if xdir_changes + ydir_changes >= 3: 
         changes_failed = True
      rfailed = False
      try:
         resp = ransac_outliers(XS,YS,"")
         #(IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac.tolist(),inlier_mask.tolist(),outlier_mask.tolist())
         inx = resp[0]
         iny = resp[1]
         ox = resp[2]
         oy = resp[3]
         print(len(inx), len(iny), len(ox), len(oy))
         ratio = 0
         if len( ox) > 0:
            ratio = len(inx) / (len(ox) + len(inx))
            if ratio < .7:
               rfailed = True
         oc += 1
      except:
         print("RAN FAILED")
         rfailed = True
         ratio = 0
     
      print("Changes Failed", changes_failed,  xdir_changes + ydir_changes )
      print("RANSAC RATIO/FAIL STATUS", ratio, rfailed)
      if changes_failed is True or rfailed is True or short_fail is True:
         rejects += 1
         print("REJECT", mj['sd_video_file'])
         cmd = "mv " + mj['sd_video_file'].replace(".mp4", "*") + " " + trash_dir
         print(cmd)
         os.system(cmd)
         print("REJECT", mj['hd_trim'])
         cmd = "mv " + mj['hd_trim'].replace(".mp4", "*") + " " + trash_dir
         print(cmd)
         os.system(cmd)
      else:
         keep += 1
      print("REJECTED SO FAR:", rejects)
      print("KEEP SO FAR:", keep)
   mc += 1

print("REJECT:", rejects)

os.system("./Process.py mmi_day " + date)

for min_key in by_min:
   print(min_key, by_min[min_key])

