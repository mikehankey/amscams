from lib.PipeUtil import load_json_file, save_json_file, cfe, bound_cnt, convert_filename_to_date_cam
from lib.PipeDetect import analyze_object, get_trim_num, make_base_meteor_json
from lib.PipeAutoCal import get_image_stars, get_catalog_stars , pair_stars, eval_cnt, update_center_radec, fn_dir
from lib.PipeDetect import fireball, apply_frame_deletes, find_object, analyze_object, make_base_meteor_json, fireball_fill_frame_data, calib_image, apply_calib, grid_intensity_center
from lib.PipeVideo import ffprobe, load_frames_fast
from lib.PipeImage import restack_meteor
import datetime
import os
import cv2
from FlaskLib.FlaskUtils import parse_jsid, make_default_template
import glob
import numpy as np


def import_meteor(data):
   out = "<h1>MANUAL DETECT METEOR</h1>"
   if data['step'] is None:
      out += "<p>From here you can manually detect and import for your station or a remote station."
      out += """
           <form method=GET action="/import_meteor/">
           Enter the meteor video local file and pathname or a URL for remote stations.<br>
           <input type=text name=meteor_file size=50> <br>
           If this is a remote station detection, enter the remote station ID, otherwise leave it blank.<br>
           <input type=text nam=station_id><br>
           <input type=submit value="Next">
           <input type=hidden name=step value="2">
           </form>
      """
   if data['step'] == "2":
      out += "Step 2"
   return(out)

def man_detect(min_file, data):
   fps = 25
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   step = data['step']
   ff = data['ff']
   lf = data['lf']
   mf = min_file 
   out = "<P>Select the first and last image that contains the meteor.</p>"
   if step == "2":
      out = ""
   date = min_file[0:10]
   min_dir = "/mnt/ams2/SD/proc2/" + date + "/" 
   min_file = min_dir + min_file
   if cfe("/mnt/ams2/TEMP/", 1) == 0:
      os.makedirs("/mnt/ams2/TEMP/")
   files = glob.glob("/mnt/ams2/TEMP/*" + mf + ".jpg")
   if len(files) == 0 and step is None:
      print("MAKE FILES!")
      os.system("rm /mnt/ams2/TEMP/*.jpg")
      min_fn = min_file.split("/")[-1]
      min_dir = min_file.replace(min_fn, "")
      day_dir = "/mnt/ams2/SD/proc2/daytime/" + date  + "/"
      if os.path.exists(min_file) is False:
         print("NO MINFILE", min_file)
         print("TRY ", day_dir + min_fn)
         if os.path.exists(day_dir + min_fn) is True:
            min_file = day_dir + min_fn
            cmd = "cp " + day_dir + min_fn + " " + min_dir + min_fn
            os.system(cmd)


      cmd = "./FFF.py slow_stack " +min_file + " /mnt/ams2/TEMP/ " + str(fps)
      print(cmd)
      os.system(cmd)
      files = glob.glob("/mnt/ams2/TEMP/*.jpg")
   if step is None:
      for file in sorted(files):
         tn = file.replace(".jpg", "-tn.jpg")
         img = cv2.imread(file)
         timg = cv2.resize(img, (320,180))
         vfile = tn.replace("/mnt/ams2", "")
         cv2.imwrite(tn, timg)
         el = file.split("-")
         fr = el[1].replace(".jpg", "")
         out += "<a href=javascript:select_frame('" + str(fr) + "')>"
         out += "<img src=" + vfile + ">" 
   elif step == "2":
    
      ff = int(ff)
      lf = int(lf)
      ff = ff - fps
      if ff <= 0:
         ff = 0
      lf += fps 
      ts = ff / fps 
      te = lf / fps 
   
      trim_num = "{:04d}".format(ff)
      trim_file = min_file.replace(".mp4", "-trim-" + trim_num + ".mp4")
      #cmd = "./FFF.py splice_video " + min_file + " " + str(ts) + " " + str(te)  + " " + trim_file + " sec"

      # do the splice with frames instead?
      cmd = "./FFF.py splice_video " + min_file + " " + str(ff) + " " + str(lf)  + " " + trim_file + " frame"
      print(cmd)
      out += cmd
      os.system(cmd) 
      vtrim_file = trim_file.replace("/mnt/ams2", "")
      out += "<p><a href=" + vtrim_file + ">SD Trim File</a><BR>"

      # try to find the hd file that goes with this SD.
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(min_file)   
      hd_str = "/mnt/ams2/HD/" + fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm + "*" + cam + "*.mp4"
      hd_files = []
      hd_trims = []
      temp = glob.glob(hd_str)
      for hdf in temp:
         if "trim" in hdf:
            hd_trims.append(hdf)
         else:
            hd_files.append(hdf)
      if len(hd_files) == 1:
         hd_file = hd_files[0]
         hd_trim = hd_file.replace(".mp4", "-HD-meteor-trim-" + trim_num + ".mp4")
         cmd = "./FFF.py splice_video " + hd_file + " " + str(ts) + " " + str(te)  + " " + hd_trim + " sec"
         print(cmd)
         os.system(cmd)
         vhdtrim_file = hd_trim.replace("/mnt/ams2", "")
         out += "<a href=" + vhdtrim_file + ">HD Trim File</a><BR>"
      else:
         hd_trim = None

      mj, mjr = make_base_meteor_json(trim_file,hd_trim, None, None) 
      out += str(mj)
      
      os.system("cp " + trim_file + " " + mj['sd_video_file'])
      if hd_trim is not None:
         os.system("cp " + hd_trim + " " + mj['hd_trim'])
      mjf = mj['sd_video_file'].replace(".mp4", ".json")
      mj['hc'] = 1
      save_json_file(mjf, mj)
      # make the stacks
      os.system("./Process.py restack_meteor " + mj['sd_video_file'])
      vidfn = mj['sd_video_file'].split("/")[-1]
      date = vidfn[0:10]
      murl = "/meteor/" + amsid + "/" + date + "/" + vidfn + "/" 
      out += "<a href=" + murl + ">goto meteor</a>"

   out += javascript(mf)
   return(out)

def javascript(min_file):
   js = """
   <script>
      frames = []
      min_file = '""" + min_file + """'

      function select_frame(fn) {
         frames.push(fn)
         if (frames.length == 2) {
            // goto step 2
            next_step_url = "/man_detect/" + min_file + "?step=2&ff=" + frames[0] + "&lf=" + frames[1]
            window.location.href = next_step_url
         }
      }
   </script>
   """
   return(js)
