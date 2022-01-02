import cv2
import os
from lib.PipeUtil import load_json_file
meteor_dir = "/mnt/ams2/meteors/"
star_dir = "/mnt/ams2/datasets/learning/stardb/"

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

def myround(x, prec=2, base=.05):
  return round(base * round(float(x)/base),prec)


if os.path.exists(star_dir) is False:
   os.makedirs(star_dir)

all_days = os.listdir("/mnt/ams2/meteors/")
for day in sorted(all_days,reverse=True):
   if os.path.isdir(meteor_dir + day) is False:
      continue
   all_files = os.listdir(meteor_dir + day + "/")
   for file in all_files:
      if "reduced" not in file and "json" in file:
         stack_img_file = meteor_dir + day + "/" + file.replace(".json", "-stacked.jpg")
         if os.path.exists(stack_img_file) is False:
            continue
         stack_img = cv2.imread(stack_img_file)
         stack_img = cv2.resize(stack_img, (1920,1080))
         data = load_json_file(meteor_dir + day + "/" + file)
         if "cp" in data:
            if "cat_image_stars" in data["cp"]:
               print("Cat image stars found...")
               for row in data['cp']['cat_image_stars']:
                  dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = row 

                  x1 = int(six - 16)
                  x2 = int(six + 16)
                  y1 = int(siy - 16)
                  y2 = int(siy + 16)
                  star_cnt = stack_img[y1:y2,x1:x2]
                  try: 
                     w,h = star_cnt.shape[:2]
                  except:
                     continue
                 
                  mag = myround(mag,2,.5)
                  star_key = str(ra) + "_" + str(dec)
                  if float(mag) < 0:

                     mags = "m" + str(mag)   
                     mags = mags.replace("-", "")
                  else:
                     mags = str(mag)   
                  star_img_file = star_dir + mags + "/" + station_id + "_" + file.replace(".json", "-st-" + star_key + ".jpg")
 
                  print(dcname, star_key ,star_img_file, mags, six,siy)
                  if os.path.exists(star_dir + mags) is False:
                     os.makedirs(star_dir + mags)
                  cv2.imwrite(star_img_file, star_cnt)


