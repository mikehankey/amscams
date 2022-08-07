from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template
from lib.PipeUtil import cfe, load_json_file, save_json_file



import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe, day_or_night, convert_filename_to_date_cam

from lib.PipeAutoCal import fn_dir

def min_detail_main(amsid, day, min_file, label):

   json_conf = load_json_file("../conf/as6.json")

   date = day
   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(min_file)

   sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
   print(sun_status)

   if sun_status == "day":
      base_dir = "/mnt/ams2/SD/proc2/daytime/" + day + "/"
   else:
      base_dir = "/mnt/ams2/SD/proc2/" + day + "/"

   min_dir = base_dir
   img_dir = base_dir + "/images/"
   data_dir = base_dir + day + "/data/"
   hd_save_dir = base_dir + day + "/hd_save/"
   meteor_dir = "/mnt/ams2/meteors/" + day + "/"
   hd = "/mnt/ams2/HD/"

   
   min_fn, xmin_dir = fn_dir(min_file)
   y,m,d,h,mm,sec,msec,cam = min_file.split("_")
   hd_min_wild = min_fn.replace(sec + "_000", "*_000")
   hd_min_files = glob.glob(hd + hd_min_wild + "*")
   print("HD MIN:", hd_min_files)
   print("HD MIN WILD:", hd + hd_min_wild)
   hd_wild = min_file.replace(sec + "_000", "*_000")

   meteor_files = glob.glob(meteor_dir + min_file + "*.json")
   data_files = glob.glob(data_dir + min_file + "*.json")
   hd_save_files = glob.glob(hd_save_dir + hd_wild + "*.mp4")

   min_thumb = img_dir + min_file + "-stacked-tn.jpg"
   vmin_thumb = min_thumb.replace("/mnt/ams2", "")
   main_template = "min_detail.html"
   template = make_default_template(amsid, main_template, json_conf)
   out = """

      <div class='h1_holder d-flex justify-content-between'>
         <div class='page_h'>Review Minute """ + min_file + """</div></div>
         <div id='main_container' class='container-fluid h-100 mt-4 lg-l'>
            <img src=""" + vmin_thumb + """>
         </div>
   """
   out += "<ul>"
   for mf in meteor_files:
      if "reduced" not in mf:
         mfn, mdir = fn_dir(mf)
         mfn = mfn.replace(".json", ".mp4")
         meteor_link = "/meteor/" + amsid + "/" + date + "/" + mfn + "/"
         out += "<li><a href=" + meteor_link + ">Meteor Detected</a></li>"
   out += "</ul>"

   sd_vid = min_dir + min_file + ".mp4"
   vsd_vid = sd_vid.replace("/mnt/ams2", "")
   out += "<a href='/man_detect/" + min_file + ".mp4/'>Manual Meteor Detect</a><br>"
   out += "Media Files <ul>"
   out += "<li><a href=" + vsd_vid + ">" + vsd_vid + "</a></li>"
   for hds in hd_min_files:
      clip_fn, trash = fn_dir(hds)
      vhds = hds.replace("/mnt/ams2", "")
      out += "<li><a href=" + vhds + ">" + vhds + "</a></li>"
   for hds in hd_save_files:
      clip_fn, trash = fn_dir(hds)
      vhds = hds.replace("/mnt/ams2", "")
      out += "<li><a href=" + vhds + ">" + vhds + "</a></li>"
  
   out += "</ul>"

   out += "Data Files <ul>"
   for df in data_files:
      data_fn, trash = fn_dir(df)
      vdf = df.replace("/mnt/ams2", "")
      out += "<li><a href=" + vdf + ">" + vdf + "</a></li>"


   template = template.replace("{MAIN_TABLE}", out)

   return template 
