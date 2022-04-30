"""
script to export learning dataset
"""
import cv2
import sqlite3
import json
from lib.PipeUtil import load_json_file, save_json_file, mfd_roi

import os
import glob
import time

# GLOBAL VARS
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']
export_dir = "/mnt/ams2/AI/DATASETS/EXPORT/"
meteor_dir = "/mnt/ams2/meteors/"
non_meteor_dir = "/mnt/ams2/non_meteors_confirmed/"

def export_ai_image(root_fn):
    mjrf = meteor_dir + root_fn[0:10] + "/" + root_fn + "-reduced.json" 
    if os.path.exists(mjrf):
       mjr = load_json_file(mjrf)
       roi = mfd_roi(mjr['meteor_frame_data'])
       return(roi)
    else:
       
       print("NO FILE:", mjrf)
       return(None)

def export_meteors(con,cur):
   # export all HUMAN CONFIRMED meteors ONLY 
   sql = "select root_fn,meteor_yn_conf, fireball_yn_conf, mc_class, mc_class_conf, roi from meteors where human_confirmed = 1 order by meteor_yn_conf desc"
   cur.execute(sql)
   rows = cur.fetchall()
   print(len(rows), "ROWS")
   dds = {}
   rc = 0
   meteor_export_dir = export_dir + "METEORS/"
   if os.path.exists(meteor_export_dir) is False:
      os.makedirs(meteor_export_dir)


   vdir = meteor_export_dir.replace("/mnt/ams2","")
   rc = 0
   out = ""
   meteor_data = {}
   for row in rows:
      root_fn = row[0]
      meteor_yn = row[1]
      fireball_yn = row[2]
      mc_class = row[3]
      mc_class_conf = row[4]
      #roi = row[1]
      #roi = [0,224,0,244]
      roi = export_ai_image(root_fn)
      meteor_data[root_fn] = [roi, meteor_yn, fireball_yn, mc_class, mc_class_conf] 
      if isinstance(roi,str):  
         roi = json.loads(roi)
      #if rc > 5:
      #   exit()
      rc += 1
      ai_file = meteor_export_dir + station_id + "_" + root_fn + "-AI.jpg"
      stack_file = meteor_dir + root_fn[0:10] + "/" + root_fn + "-stacked.jpg"
      print(ai_file, stack_file, roi)
      if os.path.exists(stack_file) is False:
         print("MISSING:", stack_file)
         #return()

      if roi is not None and os.path.exists(ai_file) is False and os.path.exists(stack_file) is True :
         x1,y1,x2,y2 = roi
         img = cv2.imread(stack_file)
         img = cv2.resize(img, (1920,1080))
         roi_img = img[y1:y2,x1:x2]
         roi_img = cv2.resize(roi_img, (64,64))
         cv2.imwrite(ai_file, roi_img)

      elif os.path.exists(stack_file) is False:
         print("No stack file:", stack_file)
      else:
         print("Skip done.", ai_file)

      if os.path.exists(ai_file) is True:
         ff = ai_file.split("/")[-1]
         iurl = ff
         mp4 = ff.replace("-AI.jpg", ".mp4")
         date = ff[0:10]
         ilink = "<a href=/meteor/{}/{}/{}/>".format(station_id, date, mp4)
         out += ilink 
         out += "<img alt='{}' src={}></a>".format(str(meteor_yn), iurl)


   fout = open(meteor_export_dir + "meteors.html", "w")
   fout.write(out)
   print(meteor_export_dir + "meteors.html")
   save_json_file(meteor_export_dir + "meteors.json", meteor_data, True)
   


def export_non_meteors(con,cur):

   # export all HUMAN CONFIRMED NON meteors ONLY 
   sql = """
          SELECT sd_vid, roi, meteor_yn, fireball_yn, multi_class, multi_class_conf, human_label 
            FROM non_meteors_confirmed 
           WHERE human_label is not NULL
             AND human_label != ""
        ORDER BY human_label 
         """ 
   cur.execute(sql)
   rows = cur.fetchall()
   non_meteor_data = {}

   non_meteor_export_dir = export_dir + "NON_METEORS/"
   if os.path.exists(non_meteor_export_dir) is False:
      os.makedirs(non_meteor_export_dir)
   out = ""
   cc= 0
   last_mc = "" 
   for row in rows:

      sd_vid, roi, meteor_yn, fireball_yn, multi_class, multi_class_conf, human_label = row
      root_fn = sd_vid.replace(".mp4", "")
      roi = json.loads(roi)
      if last_mc != human_label:
         out += "<h1>" + human_label + "</h1><br>"

      mjrf = non_meteor_dir + root_fn[0:10] + "/" + root_fn + "-reduced.json" 
      if os.path.exists(mjrf):
         mjr = load_json_file(mjrf)
         roi = mfd_roi(mjr['meteor_frame_data'])
      else:
         print("NO RED:", mjrf)

      stack_file = non_meteor_dir + sd_vid[0:10] + "/" + root_fn + "-stacked.jpg"
      non_meteor_data[root_fn] = [roi, meteor_yn, fireball_yn, multi_class, multi_class_conf, human_label]
      ai_file = non_meteor_export_dir + station_id + "_"  + root_fn + "-AI.jpg"
      if os.path.exists(ai_file) is False:
         if os.path.exists(stack_file) is True:
            img = cv2.imread(stack_file)
            img = cv2.resize(img, (1920,1080))
            print(roi)
            x1,y1,x2,y2 = roi
            roi_img = img[y1:y2,x1:x2]
            roi_img = cv2.resize(roi_img,(64,64))
            cv2.imwrite(ai_file, roi_img)
            print("WROTE************")
         else:
            print("MIS:", stack_file)
      print(cc,root_fn, roi, meteor_yn, fireball_yn, multi_class, multi_class_conf, human_label)

      if os.path.exists(ai_file) is True:
         iurl = ai_file.replace("/mnt/ams2", "")
         mp4 = iurl.replace("-AI.jpg", ".mp4")
         out += "<img alt='{}' src={}></a>".format(str(meteor_yn), iurl)

      cc += 1
      last_mc = human_label 
   fout = open(non_meteor_export_dir + "non_meteors.html", "w")
   fout.write(out)
   print(non_meteor_export_dir + "non_meteors.html")
   save_json_file(non_meteor_export_dir + "non_meteors.json", non_meteor_data, True)

if __name__ == "__main__":
   json_conf = load_json_file("../conf/as6.json")
   con = sqlite3.connect(json_conf['site']['ams_id']+ "_ALLSKY.db")
   con.row_factory = sqlite3.Row
   cur = con.cursor()
   export_meteors(con, cur)
   export_non_meteors(con, cur)
