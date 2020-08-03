'''

   functions for making reports and html pages

'''

from lib.PipeUtil import cfe , convert_filename_to_date_cam, load_json_file

from lib.PipeImage import thumbnail
from lib.DEFAULTS import *
from datetime import datetime
import glob

def autocal_report():
   year = datetime.now().strftime("%Y")
   cal_dir = ARC_DIR + "CAL/AUTOCAL/" + year + "/solved/" 
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
   cal_files = glob.glob(cal_dir + "*calparams.json")
   
   for cf in sorted(cal_files, reverse=True):
      (f_datetime, cam, f_date_str,y,m,d, h, mm, s) = convert_filename_to_date_cam(cf)
      if cam not in output:
         output[cam] = ""
      print(cf)
      cp = load_json_file(cf)
      
      org = cf.replace("-calparams.json", ".png")
      azgrid = cf.replace("-calparams.json", "-azgrid.png")
      azgrid_tn = azgrid.replace(".png", "-tn.png")
      grid = cf.replace("-calparams.json", "-grid.png")
      grid_tn = grid.replace(".png", "-tn.png")
      stars = cf.replace("-calparams.json", "-stars.png")
      stars_tn = stars.replace(".png", "-tn.png")

      if cfe(azgrid_tn) == 0:
         thumbnail(azgrid, MEDIUM_W, MEDIUM_H)
         print(azgrid_tn)
      if cfe(grid_tn) == 0:
         thumbnail(grid, MEDIUM_W, MEDIUM_H)
         print(grid_tn)
      if cfe(stars_tn) == 0:
         thumbnail(stars, MEDIUM_W, MEDIUM_H)
         print(stars_tn)

      output[cam] += "<div class='float_div'>"
      output[cam] += "<img src=" + azgrid_tn + ">"
      output[cam] += "<br><label style='text-align: center'>CAM: " + cam + " @ " + f_date_str + " <br>"  
      output[cam] += "AZ/EL: " + str(cp['center_az'])[0:5] + " / " + str(cp['center_el'])[0:5] + "<BR>"
      output[cam] += "Stars/Res: " + str(len(cp['cat_image_stars'])) + " / " + str(cp['total_res_deg'])[0:5] + "&deg; <BR>"
      output[cam] += "<a href=" + azgrid + ">AZ Grid</a> - " 
      output[cam] += "<a href=" + grid + ">RA Grid</a> - " 
      output[cam] += "<a href=" + stars + ">Stars</a> - " 
      output[cam] += "<a href=" + org + ">Original</a> " 
      output[cam] += "</div>\n"

      print(f_date_str, cam)
   fp = open(outfile, "w")
   fp.write(out_head)
   for cam in sorted(output.keys()):
      fp.write("<h1 style='clear: both'>" + cam + "</h1>")
      fp.write(output[cam])

   fp.close()

