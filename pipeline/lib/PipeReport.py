'''

   functions for making reports and html pages

'''

from PIL import Image, ImageDraw, ImageFont

from lib.PipeUtil import cfe , convert_filename_to_date_cam, load_json_file
from lib.PipeImage import thumbnail, quick_video_stack
from lib.DEFAULTS import *
from lib.PipeUtil import cfe, load_json_file, save_json_file 
from datetime import datetime
import glob
import cv2

def mk_css():
   css = """
      <style>
         .float_div {
            float: left;
            padding: 20px;
            margin: 10px;
            background-color: #ccc;
            text-align: center;

         }
      </style>
   """
   return(css)

def det_table(files, type = "meteor"):
   rpt = ""
   for mf in sorted(files):
      print(mf)
      fn = mf.split("/")[-1]
      img = mf.replace("data/", "images/")
      vid = mf.replace("data/", "")
      img = img.replace("-" + type + ".json", "-stacked-tn.png")
      vid = vid.replace("-" + type + ".json", ".mp4")
      if cfe(img) == 0:
         if cfe(vid) == 1:
            print("Image missing stack vid", type, mf)
            stack = quick_video_stack(vid)
            thumb = thumb = cv2.resize(stack, (PREVIEW_W, PREVIEW_H)) 
            cv2.imwrite(img, thumb)
             
      rpt += "<div class='float_div'>"
      rpt += "<img src=" + img + ">"
      link = "<a href=" + mf + ">"
      rpt += "<br><label style='text-align: center'>" + link + fn + "</a> <br>"  
      rpt += "</label></div>"
   return(rpt)

def detect_report(day, json_conf):
   """ Make html page of days detection queue """
   rpt = mk_css()
   rpt += "<h1>Detection Report for " + STATION_ID + " on " + day + "</h1>";   
   data_dir = "/mnt/ams2/SD/proc2/" + day + "/data/"
   image_dir = "/mnt/ams2/SD/proc2/" + day + "/images/"
   video_dir = "/mnt/ams2/SD/proc2/" + day + "/hd_save/"
   meteor_files = glob.glob(data_dir + "*-meteor.json")
   non_meteor_files = glob.glob(data_dir + "*-nometeor.json")
   detect_files = glob.glob(data_dir + "*-detect.json")
   rpt += "<h2>" + str(len(meteor_files)) + " Meteors detected </h2>" 
   for mf in sorted(meteor_files):
      print(mf)
      fn = mf.split("/")[-1]
      img = mf.replace("data/", "images/")
      vid = mf.replace("data/", "")
      img = img.replace("-meteor.json", "-stacked-tn.png")
      vid = vid.replace("-meteor.json", ".mp4")
      if cfe(img) == 0:
         if cfe(vid) == 1:
            print("Image missing stack vid")
            stack = quick_video_stack(vid)
            thumb = thumb = cv2.resize(stack, (PREVIEW_W, PREVIEW_H)) 
            cv2.imwrite(img, thumb)
            print("THUMB:", thumb)
             
      rpt += "<div class='float_div'>"
      rpt += "<img src=" + img + ">"
      rpt += "<br><label style='text-align: center'>" + fn + " <br>"  
      rpt += "</label></div>"

   table = det_table(non_meteor_files, "nometeor")
   rpt += "<div style='clear: both'></div>"
   rpt += "<h2>" + str(len(non_meteor_files)) + " Auto Rejected Meteor Detections</h2>"
   rpt += table

   if False:
      table = det_table(detect_files, "detect")
      rpt += "<div style='clear: both'></div>"
      rpt += "<h2>" + str(len(detect_files)) + " Non Meteor Detections</h2>"
      rpt += table


   out = open(data_dir + "report.html", "w")
   out.write(rpt)
   out.close()
   print(data_dir + "report.html")


def cal_status(json_conf, year = None):
   arc_cal_dir = ARC_DIR + "CAL/" + year + "/" + type + "/" 
   auto_cal_dir = arc_cal_dir + "AUTO_CAL/" + year + "/solved/"
   free_cal_dir = "/mnt/ams2/cal/freecal/"

def autocal_report(type="solved", cal_files=[]):
   year = datetime.now().strftime("%Y")
   cal_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/" + type + "/" 
   outfile = cal_dir + "cal_report.html"

   out_head = """
      <style>
         .float_div {
            float: left;
            padding: 20px;
            margin: 10px;
            background-color: #ccc;
            text-align: center;

         }
      </style>
   """
   output = {} 
   #if type == "solved":
   #   cal_files = glob.glob(cal_dir + "*calparams.json")
   #else:
   #   cal_files = glob.glob(cal_dir + "*.png")
   
   for cf in sorted(cal_files, reverse=True):
      (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cf)
      if "-tn" in cf :
         continue
      if cam not in output:
         output[cam] = ""
      print(cf)
      if type=="solved":
         cp = load_json_file(cf)
      
         org = cf.replace("-calparams.json", ".png")
         marked_img = cf.replace("-calparams.json", "-marked.jpg")
         azgrid = cf.replace("-calparams.json", "-azgrid.png")
         if "stacked-stacked" in azgrid :
            azgrid = azgrid.replace("stacked-stacked", "stacked")
         azgrid_tn = azgrid.replace(".png", "-tn.png")
         if cfe(azgrid) == 0:
            temp = azgrid.replace("-stacked", "")
            if cfe(temp) == 1:
               azgrid = temp
               azgrid_tn = azgrid.replace(".png", "-tn.png")
            else:
               print("PROBLEM FILE!", azgrid)
               continue 

         grid = cf.replace("-calparams.json", "-grid.png")
         grid_tn = grid.replace(".png", "-tn.png")
         #stars = cf.replace("-calparams.json", "-stars.png")
         #stars_tn = stars.replace(".png", "-tn.png")


      if type == 'solved':
         print("AZ:", azgrid)
         thumbnail(azgrid, MEDIUM_W, MEDIUM_H)
         print(azgrid_tn)
         #thumbnail(grid, MEDIUM_W, MEDIUM_H)
         #print(grid_tn)

         output[cam] += "<div class='float_div'>"
         output[cam] += "<img src=" + azgrid_tn + ">"
         output[cam] += "<br><label style='text-align: center'>CAM: " + cam + " @ " + f_date_str + " <br>"  
         output[cam] += "AZ/EL: " + str(cp['center_az'])[0:5] + " / " + str(cp['center_el'])[0:5] + "<BR>"
         output[cam] += "Pos/Pix: " + str(cp['position_angle'])[0:5] + " / " + str(cp['pixscale'])[0:5] + "<BR>"
         if "cat_image_stars" in cp:
            output[cam] += "Stars: " + str(len(cp['user_stars'])) + " / " + str(len(cp['cat_image_stars'])) + "<BR>"
         else:
            output[cam] += "Res: MISSING STAR DATA "
         output[cam] += "Res: " +  str(cp['total_res_px'])[0:5]+ " px / " + str(cp['total_res_deg'])[0:5] + "&deg; <BR>"
         output[cam] += "<a href=" + azgrid + ">AZ Grid</a> - " 
         #output[cam] += "<a href=" + grid + ">RA Grid</a> - " 
         #output[cam] += "<a href=" + stars + ">Stars</a> - " 
         output[cam] += "<a href=" + org + ">Original</a> - " 
         output[cam] += "<a href=" + marked_img + ">Marked</a> " 
         output[cam] += "</div>\n"
      else:
         cf_tn = cf.replace(".png", "-tn.png")
         if cfe(cf_tn) == 0:
            thumbnail(cf, MEDIUM_W, MEDIUM_H)
            print(cf_tn)
         output[cam] += "<div class='float_div'>"
         output[cam] += "<a href=" + cf + "><img src=" + cf_tn + "></a><br>"
         output[cam] += "<a target=_blank href=/pycgi/webUI.py?cmd=free_cal&input_file=" + cf + ">Manual Calibration<br>"
         output[cam] += "</div>\n"

      print(f_date_str, cam)
   fp = open(outfile, "w")
   fp.write(out_head)
   for cam in sorted(output.keys()):
      fp.write("<h1 style='clear: both'>" + cam + "</h1>")
      fp.write(output[cam])

   fp.close()
   print(outfile)
