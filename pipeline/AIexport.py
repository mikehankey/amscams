#!/usr/bin/python3.6

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



def export_fireball_meteors(con, cur, json_conf):
   station_id = json_conf['site']['ams_id']
   exp_dir = export_dir + station_id + "_FIREBALL_METEORS/" 
   cloud_exp_dir = exp_dir.replace("/mnt/ams2", "/mnt/archive.allsky.tv")

   if os.path.exists(exp_dir) is False:
      os.makedirs(exp_dir)

   # first meteors where the YN has failed, the mc_class has failed but the human override exists
   # these are probably our best failures! 
   sql = """
         SELECT root_fn, meteor_yn, fireball_yn, mc_class, mc_class_conf 
           FROM meteors
          WHERE (meteor_yn > 50
            OR fireball_yn > 50)
            AND mc_class like '%fireball%' 
            AND human_confirmed = 1
         """
   cur.execute(sql)
   rows = cur.fetchall()
   dds = {}
   rc = 0
   for row in rows:
      root_fn, meteor_yn, fireball_yn, mc_class, mc_class_conf = row
      day = root_fn[0:10]
      roi_file = "/mnt/ams2/METEOR_SCAN/" + day + "/" + station_id + "_" + root_fn + "-ROI.jpg"
      roi_fn = roi_file.split("/")[-1]
      exp_file = exp_dir + roi_fn
      if os.path.exists(roi_file) is True:
         if os.path.exists(exp_file) is False:
            print("EXPORT", rc, roi_file, meteor_yn, fireball_yn, mc_class, mc_class_conf)
            cmd = "cp " + roi_file + " " + exp_file
            print(cmd)
            os.system(cmd)
         else:
            print("DONE", rc, roi_file, meteor_yn, fireball_yn, mc_class, mc_class_conf)
         rc += 1
      else:
         print("NO ROI!", roi_file)

def export_failed_meteors(con, cur, json_conf):
   # pull meteor learning samples that failed the last set of models
   # so that they can be used in the next model generation

   station_id = json_conf['site']['ams_id']
   exp_dir = export_dir + station_id + "_FAILED_METEORS/" 
   cloud_exp_dir = exp_dir.replace("/mnt/ams2", "/mnt/archive.allsky.tv")

   if os.path.exists(exp_dir) is False:
      os.makedirs(exp_dir)

   # first meteors where the YN has failed, the mc_class has failed but the human override exists
   # these are probably our best failures! 
   sql = """
         SELECT root_fn, meteor_yn, fireball_yn, mc_class, mc_class_conf 
           FROM meteors
          WHERE (meteor_yn < 50
            OR fireball_yn < 50)
            AND mc_class not like '%meteor%' 
            AND human_confirmed = 1
         """
   cur.execute(sql)
   rows = cur.fetchall()
   dds = {}
   rc = 0
   for row in rows:
      root_fn, meteor_yn, fireball_yn, mc_class, mc_class_conf = row
      day = root_fn[0:10]
      roi_file = "/mnt/ams2/METEOR_SCAN/" + day + "/" + station_id + "_" + root_fn + "-ROI.jpg"
      roi_fn = roi_file.split("/")[-1]
      exp_file = exp_dir + roi_fn
      if os.path.exists(roi_file) is True:
         if os.path.exists(exp_file) is False:
            print("EXPORT", rc, roi_file, meteor_yn, fireball_yn, mc_class, mc_class_conf)
            cmd = "cp " + roi_file + " " + exp_file
            print(cmd)
            os.system(cmd)
         else:
            print("DONE", rc, roi_file, meteor_yn, fireball_yn, mc_class, mc_class_conf)
         rc += 1
      else:
         print("NO ROI!", roi_file)

   # now do where the YN is True but the MC class is false. 
   # first meteors where the YN has failed, the mc_class has failed but the human override exists
   # these are probably our best failures! 
   exp_dir = exp_dir.replace("FAILED_METEORS", "FAILED_METEORS2")
   if os.path.exists(exp_dir) is False:
      os.makedirs(exp_dir)


   sql = """
         SELECT root_fn, meteor_yn, fireball_yn, mc_class, mc_class_conf 
           FROM meteors
          WHERE (meteor_yn > 50
            OR fireball_yn > 50)
            AND mc_class not like '%meteor%' 
         """
         #AND human_confirmed = 1
   cur.execute(sql)
   rows = cur.fetchall()
   dds = {}
   rc = 0
   for row in rows:
      root_fn, meteor_yn, fireball_yn, mc_class, mc_class_conf = row
      day = root_fn[0:10]
      roi_file = "/mnt/ams2/METEOR_SCAN/" + day + "/" + station_id + "_" + root_fn + "-ROI.jpg"
      roi_fn = roi_file.split("/")[-1]
      exp_file = exp_dir + roi_fn
      if os.path.exists(roi_file) is True:
         if os.path.exists(exp_file) is False:
            print("EXPORT", rc, roi_file, meteor_yn, fireball_yn, mc_class, mc_class_conf)
            cmd = "cp " + roi_file + " " + exp_file
            os.system(cmd)
         else:
            print("DONE", rc, roi_file, meteor_yn, fireball_yn, mc_class, mc_class_conf)
         rc += 1
      else:
         print("NO ROI!", roi_file)


def export_scan_rois():
   scan_dir = "/mnt/ams2/SD/proc2/"
   scan_export_dir = export_dir + "/scan_stack_rois/"
   all_ai_data_file = scan_export_dir + station_id + "_ALL_AI_DATA.json"
   if os.path.exists(scan_export_dir) is False:
      os.makedirs(scan_export_dir)
   if os.path.exists(all_ai_data_file) is True:
      all_ai_data = load_json_file(all_ai_data_file)
   else:
      all_ai_data = {}
     
   dirs = os.listdir(scan_dir)
   for dd in dirs:
      if os.path.exists(scan_dir + dd):
         print(scan_dir + dd + "/AI_DATA.json") 
         if os.path.exists(scan_dir + dd + "/data/AI_DATA.json") and "20" in dd:
  
            data = load_json_file(scan_dir + dd + "/data/AI_DATA.json")
            for key in data:
               if key not in all_ai_data:
                  ofile = scan_dir + dd + "/images/" + key
                  print(key, ofile, data[key]['mc_class'], data[key]['mc_class_conf'])
                  exp_fdir = scan_export_dir + data[key]['mc_class'] + "/"
                  efile = exp_fdir + station_id + "_" + key
                  if os.path.exists(efile) is False:
                     cmd = "cp " + ofile + " " + efile 
                     print(cmd)
                     os.system(cmd)
                  if os.path.exists(exp_fdir) is False:
                     os.makedirs(exp_fdir)
                  all_ai_data[key] = data[key]
   save_json_file(all_ai_data_file, all_ai_data)

   export_html(scan_export_dir)

def export_html(scan_export_dir):
   #sexport_dir = "/mnt/ams2/datasets/scan_stack_rois/"
   dirs = os.listdir(scan_export_dir)
   main = ""
   for dd in dirs:
      if os.path.isdir(scan_export_dir + dd) is True:
         main +=  "<a href={}/index.html>{}</a><br>".format(dd, dd)
         html = ""
         files = os.listdir(scan_export_dir + dd)
         for ff in files:
            html += """<img src={} style="float: left">""".format(ff)
            print(ff)
         fp = open(scan_export_dir + dd + "/index.html", "w")
         fp.write(html)
         fp.close()
         print("Saved:", scan_export_dir + dd + "/index.html")

   fp = open(scan_export_dir + "/index.html", "w")
   fp.write(main)
   fp.close()

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
         mp4 = mp4.replace(station_id + "_", "")
         temp = ff.split("_")
         date = temp[1] + "_" + temp[2] + "_" + temp[3]
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

   mc_meteor_export_dir = export_dir + "MULTI_CLASS/"
   non_meteor_export_dir = export_dir + "NON_METEORS/"
   if os.path.exists(non_meteor_export_dir) is False:
      os.makedirs(non_meteor_export_dir)
   out = ""
   cc= 0
   last_mc = "" 
   for row in rows:

      sd_vid, roi, meteor_yn, fireball_yn, multi_class, multi_class_conf, human_label = row
      root_fn = sd_vid.replace(".mp4", "")
      if roi is not None:
         roi = json.loads(roi)
      else:
         continue
      if last_mc != human_label:
         out += "<h1>" + human_label + "</h1><br>"
      mc_dir = mc_meteor_export_dir + human_label + "/"
      if os.path.exists(mc_dir) is False:
         os.makedirs(mc_dir)

      mjrf = non_meteor_dir + root_fn[0:10] + "/" + root_fn + "-reduced.json" 
      if os.path.exists(mjrf):
         mjr = load_json_file(mjrf)
         roi = mfd_roi(mjr['meteor_frame_data'])
      else:
         print("NO RED:", mjrf)

      stack_file = non_meteor_dir + sd_vid[0:10] + "/" + root_fn + "-stacked.jpg"
      non_meteor_data[root_fn] = [roi, meteor_yn, fireball_yn, multi_class, multi_class_conf, human_label]
      ai_file = non_meteor_export_dir + station_id + "_"  + root_fn + "-AI.jpg"
      mc_ai_file = mc_dir + station_id + "_"  + root_fn + "-AI.jpg"

      if os.path.exists(ai_file) is False or os.path.exists(mc_ai_file) is False:
         if os.path.exists(stack_file) is True:
            img = cv2.imread(stack_file)
            img = cv2.resize(img, (1920,1080))
            print(roi)
            x1,y1,x2,y2 = roi
            roi_img = img[y1:y2,x1:x2]
            roi_img = cv2.resize(roi_img,(64,64))
            cv2.imwrite(ai_file, roi_img)
            cv2.imwrite(mc_ai_file, roi_img)
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

   export_failed_meteors(con, cur, json_conf)
   exit()
   #export_meteors(con, cur)
   export_non_meteors(con, cur)
   export_scan_rois()
