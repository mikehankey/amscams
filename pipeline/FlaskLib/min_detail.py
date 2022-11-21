from flask import Flask, request
from FlaskLib.FlaskUtils import get_template, make_default_template
from lib.PipeUtil import cfe, load_json_file, save_json_file
import datetime
from lib.PipeVideo import ffmpeg_cats
import os

import glob
from lib.PipeUtil import load_json_file, save_json_file, cfe, day_or_night, convert_filename_to_date_cam

from lib.PipeAutoCal import fn_dir

def remove_join_files(in_files):
   temp = []
   for ff in in_files:
      if "__" not in ff:
         print("INFILES:", ff)
         temp.append(ff)
   return(temp)

def join_min_files(amsid, min_file, next_file, seconds):
   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(min_file) 

   if os.path.exists("tmp_vids") is False:
      os.makedirs("tmp_vids")
 
   day = min_file[0:10] 
   day_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   clip1 = day_dir + min_file + ".mp4"
   clip2 = day_dir + next_file 
   outfile = min_file + "__" + next_file 

   out = "Minute files joined:" + clip1 + " " + clip2  + "<br>"


   out += " SD outfile: " + outfile + "<br>"
   ffmpeg_cats([clip1, clip2], outfile)

   # now join the HD files
   hd_min_dir = "/mnt/ams2/HD/"
   next_minute = f_datetime + datetime.timedelta(minutes=1)

   hd_wild = hd_min_dir + f_datetime.strftime("%Y_%m_%d_%H_%M") + "*" + cam + "*.mp4"
   next_hd_wild = hd_min_dir + next_minute.strftime("%Y_%m_%d_%H_%M") + "*" + cam + "*.mp4"

   # get ride of previously joined files!

   print("<BR>HD WILD:", hd_wild)
   print("<BR>NEXT HD WILD", next_hd_wild)
   hd_files = glob.glob(hd_wild)
   hd_files = remove_join_files(hd_files)
   next_hd_files = glob.glob(next_hd_wild)
   next_hd_files = remove_join_files(next_hd_files)

   if len(hd_files) > 0 and len(next_hd_files) > 0:
      hd_clip1 = hd_files[0]
      hd_clip2 = next_hd_files[0] 
      hd_fn1 = hd_clip1.split("/")[-1].replace(".mp4", "")
      hd_fn2 = hd_clip2.split("/")[-1].replace(".mp4", "")
      hd_outfile = hd_fn1 + "__" + hd_fn2 + ".mp4"
      out += "<br><br>HD Minute files joined:" + hd_clip1 + " " + hd_clip2 
      out += "<br>HD Outfile:" + hd_outfile

      ffmpeg_cats([hd_clip1, hd_clip2], hd_outfile)
   

   # if the outfile(s) exist move the original first 1 min file and then move the joined 2 minute file in its place 
   if os.path.exists(day_dir + outfile) is True:
      out += "<br>SD join looks like it worked.<br>"
      # move cmd
      cmd = "mv " + clip1 + " " + clip1.replace(".mp4", "-orig.mp4")
      print(cmd)
      os.system(cmd)

      cmd = "cp " + day_dir + outfile + " " + clip1
      print(cmd)
      os.system(cmd)


   if os.path.exists(hd_min_dir + hd_outfile) is True:
      out += "HD join looks like it worked.<br> "
      cmd = "mv " + hd_clip1 + " " + hd_clip1.replace(".mp4", "-orig.mp4")
      print(cmd)
      os.system(cmd)

      cmd = "cp " + hd_min_dir + hd_outfile + " " + hd_clip1 
      print(cmd)
      os.system(cmd)

   orig_link = "/min_detail/" + amsid + "/" + day + "/" + min_file + "/"
   out += "<p><a href=" + orig_link + ">Return to the minute page to use the new joined clip that contains 2 minutes!</a></p>"

   return(out)

def min_detail_main(amsid, day, min_file, label):
   date = day 
   json_conf = load_json_file("../conf/as6.json")
   min_fn = min_file.split("/")[-1]
   min_dir = min_file.replace(min_fn, "")
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
   sd_min_files = glob.glob(min_dir + hd_min_wild + "*")

   print("HD MIN:", hd_min_files)
   print("HD MIN WILD:", hd + hd_min_wild)

   next_minute = f_datetime + datetime.timedelta(minutes=1)
   next_wild = min_dir + next_minute.strftime("%Y_%m_%d_%H_%M") + "*" + cam + "*.mp4"
   next_files = glob.glob(next_wild)
   print("NEXT WILD:", next_wild)
   print("NEXT FILES:", next_files)


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
   #out += "<li><a href=" + vsd_vid + ">" + vsd_vid + "</a></li>"


   for sds in sd_min_files:
      clip_fn, trash = fn_dir(sds)
      vhds = sds.replace("/mnt/ams2", "")
      out += "<li><a href=" + vhds + ">" + vhds + "</a></li>"

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
   out += "</ul>"

   out += "Join with <ul>"
   join_link = "/join_min_files/" + amsid + "/" + min_file + "/?next_file=" 
   for df in next_files:
      dfn = df.split("/")[-1]
      join_link += dfn
      out += "<li><a href=" + join_link + ">" + df + "</a></li>"

   out += "</ul>"

   template = template.replace("{MAIN_TABLE}", out)

   return template 
