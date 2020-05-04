from random import randint
from sympy import Point3D, Line3D, Segment3D, Plane
import time
import math
import cv2
import cgi
import time
import glob
import os
import json
import cgitb
import re
import datetime
import time  
from pathlib import Path
from lib.MeteorReducePage import create_tab_and_content
from lib.PwdProtect import login_page, check_pwd_ajax
from lib.Pagination import get_pagination
from lib.PrintUtils import get_meteor_date, get_date_from_file, get_meteor_time, get_custom_video_date_and_cam_id
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe, save_meteor
from lib.VideoLib import get_masks, convert_filename_to_date_cam, ffmpeg_trim , load_video_frames
from lib.DetectLib import check_for_motion2 
from lib.SolutionsLib import solutions , sol_detail
from lib.MeteorTests import test_objects
from lib.ImageLib import mask_frame , draw_stack, stack_frames
from lib.CalibLib import radec_to_azel
from lib.WebCalib import calibrate_pic,make_plate_from_points, solve_field, check_solve_status, free_cal, show_cat_stars, choose_file, upscale_2HD, fit_field, delete_cal, add_stars_to_fit_pool, save_add_stars_to_fit_pool, reduce_meteor, reduce_meteor_ajax, find_stars_ajax, man_reduce, pin_point, get_manual_points, del_manual_points, sat_cap, HMS2deg, custom_fit, del_frame, clone_cal, reduce_meteor_new , update_red_info_ajax, update_hd_cal_ajax, add_frame_ajax, update_frame_ajax, clone_meteor_cal
from lib.UtilLib import calc_radiant
from lib.EventLib import EventsMain, EventDetail
from lib.Video_Add_Job import add_video_job   
from lib.Video_Parameters import *
from lib.VIDEO_VARS import * 
from lib.Video_Tools import getLength, delete_video
from lib.LOGOS_VARS import * 
from lib.Logo_Tools import * 
from lib.Frame_Tools import * 
from lib.Get_Cam_ids import get_the_cam_ids
from lib.Get_Operator_info import get_operator_info
from lib.MultiStationMeteors import multi_station_meteors, multi_station_meteor_detail
from lib.Replace_HD_or_SD import replace_HD, replace_SD

# New Reduce Meteor Page
from lib.MeteorReducePage import reduce_meteor2 
from lib.MeteorReduce_Ajax_Tools import get_all_HD_frames, get_reduction_info, delete_frame, update_multiple_frames, update_frame, get_frame, create_thumb, update_cat_stars

# Manual Reduction page
from lib.MeteorManualReducePage import manual_reduction, manual_reduction_cropper, manual_reduction_meteor_pos_selector, manual_reduction_create_final_json, manual_reduction_step1

# Manual Synchronization
from lib.MeteorManualSynchronization import *

# Calibration Tools
from lib.MeteorReduce_Calib_Ajax_Tools import getRADEC

# MOVE TO ARCHIVE
from lib.Old_JSON_converter import move_to_archive

# ARCHIVE LISTING
from lib.Archive_Listing import *

# Pagination Vars
from lib.PAGINATION_VARS import *

# Re-APPLY CALIBRATION
from lib.MeteorReduce_ApplyCalib import apply_calib_ajax

# Fix OLD Detections
from lib.Fix_Old_Detection import fix_hd_vid

# Stats page
from lib.Stats import stats_page

# Minutes page
from lib.Minutes import browse_minute

# Minutes Details Page
from lib.Minutes_Details import *

# Minutes Manual Reduction
from lib.Minutes_Manual_Reductions import *

# API
sys.path.insert(1, '/home/ams/amscams/pythonv2/API')
from  Functions import api_controller
  

def run_detect(json_conf, form):
   temp_sd_video_file = form.getvalue("temp_sd_video_file")
   stack_file = temp_sd_video_file.replace(".mp4", "-stacked.png")
   obj_stack_file = temp_sd_video_file.replace(".mp4", "-stacked-obj.png")
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(temp_sd_video_file)
   frames = load_video_frames(temp_sd_video_file, json_conf)
   objects = check_for_motion2(frames, temp_sd_video_file,hd_cam, json_conf,0)

   print("run:", temp_sd_video_file, len(frames))
   print("<span style=\"color: white>\">")

   objects,meteor_found = test_objects(objects,frames)
   stack_file,stack_img = stack_frames(frames, temp_sd_video_file)
   draw_stack(objects,stack_img,stack_file)
   print("<br><img src=" + obj_stack_file + ">")
   for object in objects:
      print("<HR>")
      for key in object:
         if key == 'test_results':
            for test in object['test_results']:
               (test_name,test_rest, test_desc) = test
               print(test_name,test_rest, test_desc,"<BR>")
         else:
            print(key, object[key], "<BR>")
   if meteor_found == 1:
      wild = temp_sd_video_file.replace(".mp4", ".*")
      el = temp_sd_video_file.split("/")
      fn = el[-1]
      day_dir = fn[0:10]
      proc_dir = json_conf['site']['proc_dir']
      cmd = "cp " + wild + " " + proc_dir + day_dir + "/passed/" 
      os.system(cmd)
      new_video_file = proc_dir + day_dir + "/passed/" + fn
      print("NEW VIDEO FILE:", new_video_file)
      save_meteor(temp_sd_video_file,objects,json_conf)

      cmd2 = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py doHD " + proc_dir + day_dir + "/passed/" + fn
      print("METEOR WAS FOUND! Copied clip to passed dir for final processing. It should appear in meteor archive within a minute. <br>",cmd)
      print(cmd2)
   else:
      print("Meteor was not found by detection code. Override test results here... (todo...)")
   print("</span>")

def manual_detect(json_conf, form):
   sd_video_file = form.getvalue('sd_video_file')
   el = sd_video_file.split("/")
   fn = el[-1]
   temp_sd_video_file = "/mnt/ams2/trash/" + fn
   cmd  = "cp " + sd_video_file + " " + temp_sd_video_file
   os.system(cmd)

   subcmd = form.getvalue('subcmd')
   stack_num = form.getvalue('stack_num')
   print("Manual detect<BR>")
   cmd = "cd /home/ams/amscams/pythonv2/; ./stackVideo.py 10sec " + sd_video_file
   print(cmd)
   os.system(cmd)
   if subcmd is None: 
      for i in range(0,6):

         rand = "?rand=" + str(randint(0,10000))
         stack_file = "/mnt/ams2/trash/stack" + str(i) + ".png" + rand
         print("<a href=webUI.py?cmd=manual_detect&sd_video_file=" + sd_video_file + "&subcmd=pick_stack&stack_num=" + str(i) + "><img src=" + stack_file + ">")


   if subcmd == 'pick_stack' or subcmd == 'retrim':
      if subcmd == 'pick_stack':
         print('trim')      
         trim_start_sec = (int(stack_num) * 10 * 25) / 25
         dur_sec = 10
         out_file_suffix = "-trim" + str(int(stack_num) * 10 * 25) 
      else:
         trim_start_sec = form.getvalue("trim_start_sec")
         dur_sec = form.getvalue("dur_sec")
         stack_num = int(float(trim_start_sec) * 25)
         out_file_suffix = "-trim" + str(int(stack_num) ) 


      ffmpeg_trim(temp_sd_video_file, trim_start_sec, dur_sec, out_file_suffix)
      #print("trimming clip:", temp_sd_video_file, trim_start_sec, dur_sec, out_file_suffix)
      print("<BR>")
      show_file = temp_sd_video_file.replace(".mp4", out_file_suffix + ".mp4")
      rand = "?rand=" + str(randint(0,10000))
      print(" <video autoplay id=\"v1\" loop controls src=\"" + show_file + rand + "\"> </video> ")
      print("<form><input type=hidden name=sd_video_file value='" + sd_video_file + "'>")
      print("<input type=hidden name=cmd value='manual_detect'>")
      print("<input type=hidden name=subcmd value='retrim'>")
      #print(trim_start_sec, dur_sec)
      print("Adjust the start time and duration to re-trim the clip.<BR>")
      print("Trim Start in Seconds (from start of 1 min clip):<input type=textg name=trim_start_sec value='" + str(trim_start_sec) + "'><br>")
      print("Trim Duration in Seconds: <input type=textg name=dur_sec value='" + str(dur_sec) + "'><br>")
      print("<input type=submit name=submit value='Re-Trim Clip'></form><br>")
   if subcmd == 'retrim':
     
      print("<P>If the trim clip looks good, run detect code on this clip: ", show_file)
      print("<form>")
      print("<input type=hidden name=cmd name='subcmd' value='run_detect'>")
      print("<input type=hidden name=temp_sd_video_file value='" + show_file + "'>")
      print("<input type=submit name=submit value='Run Detection Code On This Clip'><br>")
      print("</form>")

def get_template(json_conf, skin = "as6ams"  ):
   template = ""  
   if skin == "as6ams":
      fpt = open("/home/ams/amscams/pythonv2/templates/as6ams.html", "r")
   elif skin == "v2":
      fpt = open("/home/ams/amscams/pythonv2/templates/main_template.html", "r")
   else:
      fpt = open("/home/ams/amscams/pythonv2/templates/as6ams.html", "r")
 

   for line in fpt:
      template = template + line 
   return(template) 

def make_day_preview(day_dir, stats_data, json_conf):
   el = day_dir.split("/")
   day = el[-1]
   if day == "":
      day = el[-2]
   day_str = day
   html_out = ""
   #json_conf['cameras'] = sorted(json_conf['cameras'])
   #for cam in json_conf['cameras']:
   for i in range(1,7):
      #cam = i
      key = "cam" + str(i)
      cam = key
      cams_id = json_conf['cameras'][cam]['cams_id']
      try:
            min_total = stats_data[cams_id] 
      except KeyError:
            min_total = 0
      obj_stack = day_dir + "/" + "images/"+ cams_id + "-night-stack.png"
      meteor_stack = day_dir + "/" + "images/" + cams_id + "-meteors-stack.png"
      if cfe(obj_stack) == 0:
         obj_stack = "./dist/img/proccessing.png"
      if cfe(meteor_stack) == 0:
         meteor_stack = "./dist/img/proccessing.png"

      day=day.replace("_","")
 
      html_out +=  "<div class='preview col-lg-2 col-md-3 '>"
      html_out +=  "<a class='mtt' href='webUI.py?cmd=browse_day&day=" + day_str + "&cams_id="+cams_id+"'  title='Browse all day'>"
      html_out +=  "<img alt='" + day_str + "' class='img-fluid ns lz' src='" + obj_stack + "'>" 
      if(min_total==0):
            html_out +=  "</a><span class='pre-b'>Cam #"+ cams_id+" - <i>processing</i></span></div>"   
      else:
            html_out +=  "</a><span class='pre-b'>Cam #"+ cams_id+" - " + str(min_total) + " minutes</span></div>"   
   return(html_out, day_str)

def parse_jsid(jsid):
   #print("JSID:", jsid)
   year = jsid[0:4]
   month = jsid[4:6]
   day = jsid[6:8]
   hour = jsid[8:10]
   min = jsid[10:12]
   sec = jsid[12:14]
   micro_sec = jsid[14:17]
   cam = jsid[17:23]
   trim = jsid[24:]
   trim = trim.replace(".json", "")
   video_file = "/mnt/ams2/meteors/" + str(year) + "_" + str(month) + "_" + str(day) + "/"  + year + "_" + month + "_" + day + "_" + hour + "_" + min + "_" + sec + "_" + micro_sec + "_" + str(cam) + "-" + trim + ".mp4"
   #print(video_file)
   #print(year,month,day,hour,min,sec,micro_sec,cam,trim)
   return(video_file)

def controller(json_conf): 

   cgitb.enable()
 
   form = cgi.FieldStorage()
   cmd = form.getvalue('cmd')
   skin = form.getvalue('skin') 

   if cmd == 'play_vid':
      jsid = form.getvalue('jsid')
      video_file = parse_jsid(jsid)
      print("Location: " + video_file + "\n\n")
      exit() 

   print("Content-type: text/html\n\n")      

   #API
   if cmd == 'API':
      api_controller(form)
      exit() 

   #login
   if cmd == 'login':
      login_page()
      exit() 
   if cmd == 'check_pwd':
      user = form.getvalue("user")
      pwd = form.getvalue("pwd")
      check_pwd_ajax(user,pwd)
      exit()


   # GET LIST OF HD FRAMES FROM A GIVEN DETECTION (AJAX CALL)
   if cmd == 'get_HD_frames':
      get_all_HD_frames(form.getvalue('json_file'))   
      exit();

   # GET REDUCTION JSON DATA (AJAX CALL)
   if cmd == 'get_reduction_info': 
      get_reduction_info(form.getvalue('json_file'))   
      exit()

   if cmd == 'replace_HD':
      replace_HD(form)   
      exit()

   if cmd == 'replace_SD':
      replace_SD(form)   
      exit()
 
   # GET AZ/EL from JSON_FILE & array of values
   # like 
   # 0: {x_org: 372, y_org: 203, x_HD: 744, y_HD: 228.375}
   # 1: {x_org: 303, y_org: 344, x_HD: 606, y_HD: 387} 
   #  (AJAX CALL)
   if cmd == 'getRADEC': 
      getRADEC(form)   
      exit()  

   # Reapply calibration
   if cmd== 'apply_calib':
      apply_calib_ajax(form)
      exit()

   #CUSTOM VIDEOS (AJAX CALL)
   if cmd == 'generate_timelapse': 
   
      #Extra text is optional
      try:
            extra_text = form.getvalue('extra_text')
      except KeyError as e:
            extra_text = ""

      #Do we have an extra logo
      try:
            extra_logo = form.getvalue('extra_logo_yn')
            logo = form.getvalue('logo')
            logo_pos = form.getvalue('logo_pos')
      except KeyError as e:
            extra_logo = "n"
            logo = ""
            logo_pos = ""

      add_video_job('timelapse',form.getvalue('sel_cam[]'),form.getvalue('tl_date'),form.getvalue('tl_time'),form.getvalue('duration'),form.getvalue('fps'),form.getvalue('dim'),form.getvalue('text_pos'),form.getvalue('wat_pos'),form.getvalue('blend_sd'),extra_text,form.getvalue('extra_text_pos'),logo,logo_pos)
      exit()

   # DELETE CUSTOM VIDEO (AJAX CALL)
   if cmd == 'delete_custom_video':
      vid = form.getvalue('vid')
      delete_video(vid)
      exit()

   #CUSTOM LOGOS  (AJAX CALL)       
   if cmd == 'upload_logo': 
      upload_logo(form)   
      exit()


   # Manual Reduction (Fourth Step: creation of the new JSON file for the current detection)
   # WARNING - this page is a redirect 
   if cmd == 'manual_reduction_create_final_json':
      manual_reduction_create_final_json(form)
      exit()


   # Fix an "old" json with a bad link to HD video
   if cmd=='fix_hd_vid':
      fix_hd_vid(form)
      exit()

   # Move Detection to Archive
   if cmd == 'move_to_archive':
      move_to_archive(form)
      exit()

   # do json ajax functions up here and bypass the exta html
   if cmd == 'override_detect':
      video_file = form.getvalue('video_file')
      jsid = form.getvalue('jsid')
      override_detect(video_file,jsid,json_conf)
      exit()

   #Delete multiple detections at once from archives or reduce2 page
   if cmd == 'delete_archive_multiple_detection' or cmd == 'reject_meteor':
      detections = form.getvalue('detections[]')
      delete_multiple_archived_detection(detections)
      exit()
 


   #Delete multiple detections at once 
   if cmd == 'delete_multiple_detection':
      detections = form.getvalue('detections[]')
      delete_multiple_detection(detections,json_conf)
      exit()

  
   #Add new a frame from HD image with x & y
   if(cmd == 'crop_frame'):
      fr_id = form.getvalue('fr_id')
      x = form.getvalue('x')
      y = form.getvalue('y')
      sd_video_file = form.getvalue('sd_video_file')
      real_add_frame(json_conf,sd_video_file,fr_id,x,y)
      exit() 

   # STATS
   if cmd == 'stats':
      stats_page(form)
      exit()

   if cmd == 'add_frame':
      add_frame_ajax(json_conf,form)
      exit()
   if cmd == 'update_frame_ajax':
      update_frame_ajax(json_conf,form)
      exit()
   if cmd == "update_multiple_frames_ajax":
      update_multiple_frames_ajax(json_conf,form)
      exit()
   if cmd == 'update_hd_cal_ajax':
      update_hd_cal_ajax(json_conf,form)
      exit()
   if cmd == 'update_red_info_ajax':
      update_red_info_ajax(json_conf,form)
      exit()


   if cmd == 'clone_cal':
      clone_cal(json_conf,form)
      exit()
   if cmd == 'clone_meteor_cal':
      clone_meteor_cal(json_conf,form)
      exit()
   if cmd == 'custom_fit':
      custom_fit(json_conf,form)
      exit()
   if cmd == 'get_manual_points':
      get_manual_points(json_conf,form)
      exit()
   # Event Pages
   if cmd == 'events':
      EventsMain(form)
      exit()
   if cmd == 'wasabi_cp':
      wasabi_cp(form)
   if cmd == 'event_detail':
      EventDetail(form)
      exit()


   
   # New Reduction Page => DELETE A FRAME
   if cmd == 'delete_frame':
      delete_frame(form)
      exit()

   # New Reduction Page => UPDATE MULTIPLE FRAMES AT ONCE
   if cmd == 'update_multiple_frames':
      update_multiple_frames(form)
      exit()

   # New Reduction Page => UPDATE ONE FRAME AT A TIME
   if cmd == 'update_frame':
      update_frame(form)
      exit()

   #  New Reduction Page =>  Get a HD frame 
   if cmd == 'get_frame':
      get_frame(form)
      exit()
   
   #  New Reduction Page =>  Create a thumb 
   if cmd == 'create_thumb':
      create_thumb(form)
      exit()

   # New Reduction Page => Update list of stars
   if cmd == 'update_cat_stars':
      update_cat_stars(form)
      exit()


   # Old Reduction Page 
   if(cmd == 'get_a_frame'):
      fr_id = form.getvalue('fr')
      sd_vid = form.getvalue('sd_video_file')
      print(get_a_frame(fr_id,sd_vid))
      exit()





   if cmd == 'del_frame':
      del_frame(json_conf,form)
      exit()
   if cmd == 'del_manual_points':
      del_manual_points(json_conf,form)
      exit()
   if cmd == 'pin_point':
      pin_point(json_conf,form)
      exit()
   if cmd == 'upscale_2HD':
      upscale_2HD(json_conf,form)
      exit()
   if cmd == 'make_plate_from_points':
      make_plate_from_points(json_conf,form)
      exit()
   if cmd == 'list_meteors':
      list_meteors(json_conf,form)
      exit()
   if cmd == 'solve_field':
      solve_field(json_conf,form)
      exit()
   if cmd == 'check_solve_status':
      check_solve_status(json_conf,form)
      exit()
   if cmd == 'show_cat_stars':
      show_cat_stars(json_conf,form)
      exit()
   if cmd == 'fit_field':
      fit_field(json_conf,form)
      exit()
   if cmd == 'reset_reduce':
      reset_reduce(json_conf,form)
      exit()
   if cmd == 'reduce_meteor_ajax':
      cal_params_file = form.getvalue("cal_params_file")
      meteor_json_file = form.getvalue("meteor_json_file")
      show= 0
      reduce_meteor_ajax(json_conf,meteor_json_file, cal_params_file, show)
      exit()
   if cmd == 'delete_cal':
      delete_cal(json_conf,form)
      exit()
   if cmd == 'find_stars_ajax':
      stack_file = form.getvalue("stack_file")
      find_stars_ajax(json_conf,stack_file)
      exit()
   if cmd == 'save_add_stars_to_fit_pool':
      save_add_stars_to_fit_pool(json_conf,form)
      exit()


   #print_css()
   jq = do_jquery()
   
   nav_html,bot_html = nav_links(json_conf,cmd)
   nav_html = "" 

   # New Reduce page / Manual Reduce page
   if cmd is not None:
      if cmd == 'reduce2' or 'manual_reduction' or 'archive_listing' in cmd:
         skin = "v2"
      else:
         skin = 'as6ams'

      if cmd=='reduce_new' or cmd=='reduce':
         skin = 'as6ams'
      
      if cmd=='meteors':
         skin = 'as6ams'
 
 
   template = get_template(json_conf, skin)
   stf = template.split("{BODY}")
   top = stf[0]
   bottom = stf[1]
   top = top.replace("{TOP}", nav_html)

   if cmd is not None and "man" in cmd:
      template = template.replace("<!--manred-->", "<script src=\"/pycgi/manreduce.js?\"></script>")
 
   obs_name = json_conf['site']['obs_name']
   op_city =  json_conf['site']['operator_city']
   op_state = json_conf['site']['operator_state']
   station_name = json_conf['site']['ams_id'].upper()

   top = top.replace("{OBS_NAME}", obs_name)
   top = top.replace("{OP_CITY}", op_city)
   top = top.replace("{OP_STATE}", op_state)
   top = top.replace("{STATION_NAME}", station_name)
   top = top.replace("{JQ}", jq)

   if(top is not None):
      print(top)
   extra_html = ""

   #CUSTOM VIDEOS (LIST)
   if cmd== 'video_tools': 
      video_tools(json_conf,form) 
   
   #Custom logos (uploaded by user)
   if cmd == 'custom_logos':
      custom_logos(json_conf,form)


   # Manual Synchronization (HD/SD): step 1- (First step: select start / end position)
   if cmd == 'manual_sync':      
      manual_synchronization(form)

   # Manual Synchronization (HD/SD): step 2 - Sync Chooser
   if cmd == 'manual_sync_chooser':      
      manual_synchronization_chooser(form)

   # Manual Synchronization (HD/SD): step 3 - Finalization
   if cmd == 'update_sync':      
      update_sync(form)   


   # Manual Reduction step 0: select stack
   if cmd == 'manual_reduction':
      manual_reduction(form)

   # Manual Reduction page (First step: select start / end position)
   if cmd == 'manual_reduction_pos_in_stack':
      manual_reduction_step1(form)

   # Manual Reduction (Second Step: crop frames)  
   if cmd == 'manual_reduction_cropper': 
      manual_reduction_cropper(form)   

   # Manual Reduction (Third Step: meteor position within cropped frames)
   if cmd == 'manual_reduction_meteor_pos_selector':
      manual_reduction_meteor_pos_selector(form)
   
   # REAL NEW VERSION
   if cmd == 'reduce2':
      extra_html = reduce_meteor2(json_conf, form)
  
   # OLD VERSION 
   if cmd == 'reduce':
      extra_html = reduce_meteor_new(json_conf, form)

   # ANOTHER OLD VERSION
   if cmd == 'reduce_new':
      extra_html = reduce_meteor_new(json_conf, form)
         
   # ARCHIVE LISTING
   if cmd == 'archive_listing':
      extra_html = archive_listing(form) 

   # BROWSE MINUTES
   if cmd == 'browse_minute': 
      browse_minute(form)

   # MINUTE DETAILS
   if cmd == 'minute_details': 
      minute_details(form)

   # MANUAL REDUCE MINUTE - STEP 1
   if cmd == 'define_ROI_minute':
      define_ROI(form)
   
   # MANUAL REDUCE MINUTE - STEP 2 (find HD, crop frames, etc.)
   if cmd == 'automatic_detect_minute':
      automatic_detect(form)

   if cmd == 'solutions':
      solutions(json_conf, form)
   if cmd == 'sol_detail':
      sol_detail(json_conf, form)
   if cmd == 'rad_calc':
      rad_calc(json_conf, form)

   if cmd == 'free_cal':
      free_cal(json_conf, form)
   if cmd == 'sat_cap':
      sat_cap(json_conf, form)
   if cmd == 'man_reduce':
      extra_html = man_reduce(json_conf,form)

   if cmd == 'choose_file':
      choose_file(json_conf,form)
      
   if cmd == 'manual_detect':
      manual_detect(json_conf,form)
   if cmd == 'run_detect':
      run_detect(json_conf,form)
   if cmd == 'add_stars_to_fit_pool':
      add_stars_to_fit_pool(json_conf,form)

   if cmd == 'asconf':
      asconf(json_conf, form)
 
   if cmd == 'mask_admin':
      mask_admin(json_conf, form)
   if cmd == 'calibrate_pic':
      calibrate_pic(json_conf, form)
   if cmd == 'meteor_index':
      extra_html = meteor_index(json_conf, form)
   if cmd == 'hd_cal_index':
      extra_html = hd_cal_index(json_conf, form)
   if cmd == 'hd_cal_detail':
      extra_html = hd_cal_detail(json_conf, form)
   if cmd == 'calib_hd_cal_detail':
      extra_html = calib_hd_cal_detail(json_conf, form)


   if cmd == 'trim_clip':
      video_file = form.getvalue('video_file')
      start = form.getvalue('start')
      end = form.getvalue('end')
      trim_clip(video_file,start,end)

   if cmd == 'examine_min':
      video_file = form.getvalue('video_file')
      examine_min(video_file,json_conf)
   if cmd == 'browse_day':
      day = form.getvalue('day')
      cams_id = form.getvalue('cams_id')
      browse_day(day, cams_id,json_conf,form)
   if cmd == 'reset':
      video_file = form.getvalue('video_file')
      type = form.getvalue('reset')
      reset(video_file, type)
   if cmd == 'examine':
      video_file = form.getvalue('video_file')
      jsid = form.getvalue('jsid')
      if jsid is not None:
         video_file = parse_jsid(jsid)

      examine(video_file)
   if cmd == '' or cmd is None or cmd == 'home':
      main_page(json_conf,form) 
   if cmd == 'examine_cal':
      examine_cal(json_conf,form)   
   if cmd == 'calibration':
      calibration(json_conf,form)   
   if cmd == 'live_view':
      live_view(json_conf)   
   if cmd == 'meteors':
      meteors_new(json_conf, form)   
   if cmd == 'new_meteors':
      meteors_new(json_conf, form)   
   if cmd == 'config':
      as6_config(json_conf)   
   if cmd == 'browse_detects':
      day = form.getvalue('day')
      type = form.getvalue('type')
      #type = 'meteor'
      #day = '2019_01_27'
      browse_detects(day,type,json_conf,form)   
   if cmd == 'msm':
      multi_station_meteors(json_conf,form)
   if cmd == 'msmd':
      multi_station_meteor_detail(json_conf,form)

   #bottom = bottom.replace("{JQ}", jq)      
   if(bot_html is not None and bottom is not None):
      bottom = bottom.replace("{BOTTOMNAV}", bot_html)      
    
   if(extra_html is not None and bottom is not None):
      bottom = bottom.replace("{EXTRA_HTML}", str(extra_html))
   else:
      bottom = bottom.replace("{EXTRA_HTML}", "")

   if(bottom is not None):
      rand=time.time()
      bottom = bottom.replace("{RAND}", str(rand))
      print(bottom)
     
   #cam_num = form.getvalue('cam_num')
   #day = form.getvalue('day')

def asconf(json_conf, form):
   act = form.getvalue("act")
   fp = open("/home/ams/amscams/pythonv2/templates/asconf.html", "r")
   form = ""
   for line in fp:
      form += line
   form = form.replace("{AMS_ID}", json_conf['site']['ams_id'])
   form = form.replace("{OBS_NAME}", json_conf['site']['obs_name'])
   form = form.replace("{OPERATOR_NAME}", json_conf['site']['operator_name'])
   form = form.replace("{OPERATOR_EMAIL}", json_conf['site']['operator_email'])
   form = form.replace("{OPERATOR_CITY}", json_conf['site']['operator_city'])
   form = form.replace("{OPERATOR_STATE}", json_conf['site']['operator_state'])
   form = form.replace("{OPERATOR_COUNTRY}", json_conf['site']['operator_country'])
   form = form.replace("{LAT}", json_conf['site']['device_lat'])
   form = form.replace("{LON}", json_conf['site']['device_lng'])
   form = form.replace("{ALT}", json_conf['site']['device_alt'])
   form = form.replace("{PASSWD}", json_conf['site']['pwd'])
   print(form)
      

def wasabi_cp(form):
   file = form.getvalue("file")
   cmd = "cd /home/ams/amscams/pythonv2; ./wasabi.py cp " + file
   print(cmd)
   os.system(cmd)

# CUSTOM LOGO PAGE
def custom_logos(json_conf,form):
   header_out = "<div class='h1_holder d-flex justify-content-between'>"      
   header_out += "<h1>Custom Logos</h1></div>"
   
   header_out += '<div id="main_container" class="container-fluid h-100 mt-4 lg-l">'
   header_out += '<div class="alert alert-info" style="max-width: 950px;margin: 0 auto 2rem;""><b>We STRONGLY recommand using clean PNG images (ideally semi-transparent) with the following max dimensions:</b>'
   header_out += '<ul style="border-bottom: 1px solid rgba(255,255,255,.1);padding-bottom: 1rem;margin-bottom: 0;">'
   header_out += '<li> <b>height < 250px</b> and <b>width < 400px</b> for your <b>1920x1080</b> videos</li>' 
   header_out += '<li> <b>height < 170px</b> and <b>width < 270px</b> for your <b>1280x720</b> videos</li>'
   header_out += '<li> <b>height < 170px</b> and <b>width < 270px</b> for your <b>640x360</b> videos</li>' 
   header_out += '</ul><div style="max-width:300px; margin:1rem auto 0.5rem; ">'
   header_out += '<form id="upload_logo" action="/pycgi/webUI.py?cmd=upload_logo" method="post" accept-charset="utf-8" enctype="multipart/form-data">'
   header_out += '<div class="custom-file">'
   header_out += '<input type="file" class="custom-file-input" id="logo_file_upload" name="logo" accept="image/x-png,image/gif,image/jpeg">'
   header_out += '<label class="custom-file-label btn btn-primary text-left" for="logo">UPLOAD a logo</label>'
   header_out += '</div>'
   header_out += '</form></div></div>'


   header_out += '<div class="gallery gal-resize row text-center text-lg-left mr-4 ml-4 mt-2">'

   #Get the existing logos
   all_logos = sorted(glob.glob(LOGOS_PATH + "*.*"), key=os.path.getmtime, reverse=True)
   for logo in all_logos:
      header_out += "<div class='col-lg-3 col-md-3 norm mb-3'>"
      header_out += "<a class='mtt img-link nop' href='"+logo+"'>"
      header_out += "<img class='img-fluid ns ' src='" + logo + "'/>"
      header_out += "</a></div>"
   
   header_out += '</div></div>'
   
   print(header_out)
      

# VIDEO TOOLS PAGE
# LIST OF PROCESS/READY VIDEOS
def video_tools(json_conf,form):
   cgitb.enable()

   cur_page  = form.getvalue('p')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   all_vids = sorted(glob.glob(VID_FOLDER + "*.mp4"), key=os.path.getmtime, reverse=True)
   all_vids_out = ""
   vid_counter = 0

   #All vids in the VID_FOLDER
   for vid in all_vids:
         # Get Date & Cam ID
         date, camid = get_custom_video_date_and_cam_id(vid)
 

         length = getLength(vid)
         if(length=='' or length==0):
               length = ''
          
         all_vids_out += "<div class='preview col-lg-2 col-md-3 norm  mb-3'>"
         all_vids_out += "<a class='mtt vid-link nop' href='"+vid+"' title='Play the Video'>"
         all_vids_out += "<img class='img-fluid ns lz' src='" + vid.replace('.mp4','.png') + "'/>"
         all_vids_out += "</a><span>" + date + " - Cam#" + camid +" - " +  length + "</span>"
         all_vids_out += "<button class='btn btn-danger btn-sm mt-1 delete_video' data-rel="+vid+"><i class='icon-delete'></i></button></div>"
         vid_counter+=1


   #READ THE waiting_jobs file if it exist 
   js_file = Path(WAITING_JOBS)
   header_out = '';
   processing_vids = '';

   #Get All Cam IDs
   all_cam_ids = get_the_cam_ids() 
   out_put_all_cam_ids = ''
   for camid in all_cam_ids:
      out_put_all_cam_ids += camid + "|"

   #Get Current Date (default for datepicker)
   now = datetime.now()
   out_put_date = str(now.year) + "/" + str(now.month) + "/" + str(now.day)
 
   if js_file.is_file():

      #Open the waiting_job & Load the data
      with open(WAITING_JOBS, "r+") as jsonFile:
            try:
                  data = json.load(jsonFile)

                  for jobs in data['jobs']:
            
                        if(jobs['status']=='waiting'):
                              processing_vids += "<div class='preview col-lg-2 col-md-3 mb-3 norm'>"
                              processing_vids += "<a class='mtt'>"
                              processing_vids += "<img class='img-fluid ns lz' src='./dist/img/waiting.png'/>"
                              processing_vids += "<span>" + jobs['date'].replace('_','/') + " - " + jobs['cam_id'] +"</span></a></div>"
                              vid_counter+=1

                        jsonFile.close()
            except Exception:
                  data = ""


      #Open the processing_job & Load the data
      with open(PROCESSING_JOBS, "r+") as jsonFile:
            try:
                  jsonFile.seek(0)
                  first_char = jsonFile.read(1)
                  
                  if not first_char:
                        data = {}
                        data['jobs'] = []
                        
                  else:  
                        jsonFile.seek(0)
                        data = json.loads(jsonFile.read()) 
                  
                  for jobs in data['jobs']: 

                        if(jobs['status']=='processing'):
                              processing_vids += "<div class='preview col-lg-2 col-md-3 mb-3 norm'>"
                              processing_vids += "<a class='mtt'>"
                              processing_vids += "<img class='img-fluid ns lz' src='./dist/img/proccessing.png'/>"
                              processing_vids += "<span>" + jobs['date'].replace('_','/') + " - " + jobs['cam_id'] +"</span></a></div>"
                              vid_counter+=1
                  jsonFile.close()
            except Exception:
                  data = ""        

     
   header_out = "<div class='h1_holder d-flex justify-content-between'>"      
   header_out += "<h1>"+str(vid_counter)+" videos found</h1>"
   header_out += "<div class='d-flex'><button class='btn btn-primary mr-3' id='create_timelapse' style='text-transform: initial;'></div>"
   #<span class='icon-youtube'></span> Generate Timelapse Video</button></div></div>"
   
   #Get Default Parameters
   params = get_video_job_default_parameters()
   params = params['param']
   #print(params['extra_text'])
 
   #Get Custom Logos
   all_logos = sorted(glob.glob(LOGOS_PATH + "*.*"), key=os.path.getmtime, reverse=True)
   out_put_all_logos = ''
   for logo in all_logos:
      out_put_all_logos += logo + "|"

   print(header_out)
   # Parameters 
   print("<input type='hidden' name='def_fps' value='"+str(params['fps']) +"'/>")  
   print("<input type='hidden' name='def_dim' value='"+str(params['dim']) +"'/>")  
   print("<input type='hidden' name='def_wat_pos' value='"+params['wat_pos'] +"'/>")  
   print("<input type='hidden' name='def_text_pos' value='"+params['text_pos'] +"'/>")  
   print("<input type='hidden' name='def_logo_pos' value='"+params['logo_pos'] +"'/>")  
   print("<input type='hidden' name='def_extra_text_pos' value='"+params['extra_text_pos'] +"'/>")  
   print("<input type='hidden' name='def_extra_text' value='"+params['extra_text'] +"'/>")  
   print("<input type='hidden' name='def_extra_logo' value='"+params['extra_logo'] +"'/>")  

   #Other Params 
   print("<input type='hidden' name='cam_ids' value='"+out_put_all_cam_ids+"'/>")
   print("<input type='hidden' name='logos' value='"+str(out_put_all_logos)+"'/>")
   print("<input type='hidden' name='delete_after_days' value='"+str(DELETE_VIDS_AFTER_DAYS)+"'/>")
   print("<div class='gallery gal-resize row text-center text-lg-left mt-4'>")
   print(processing_vids)
   print(all_vids_out)
   print("</div>")
   
      

def reset_reduce(json_conf, form):
   mjf = form.getvalue("cal_params_file")
   mjf = mjf.replace(".json", "-reduced.json") 
   if "reduced.json" not in mjf:
      print("BAD FILE!")
      exit()
   if cfe(mjf) == 0:
      print("BAD FILE!")
      exit()
   if "meteors" not in mjf:
      print("BAD FILE!")
      exit()
   if " " in mjf:
      print("BAD FILE!")
      exit()
   if ";" in mjf:
      print("BAD FILE!")
      exit()
   cmd = "rm " + mjf 
   os.system(cmd)

   mf = mjf.replace("-reduced.json", ".json")
   cmd = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py raj " + mf + " > /mnt/ams2/tmp/dmt"
   os.system(cmd)
   print(cmd)
   cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mf + " > /mnt/ams2/tmp/dmt"
   os.system(cmd)
   print(cmd)
   #cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + mf + " > /mnt/ams2/tmp/dmt"
   #os.system(cmd)
   #print(cmd)
   #cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mf + " > /mnt/ams2/tmp/dmt"
   #os.system(cmd)
   #print(cmd)
   #cmd = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py raj " + mf + " > /mnt/ams2/tmp/dmty"
   #os.system(cmd)

   resp = {}
   resp['status'] = "reduction and cal params reset"
   print(json.dumps(resp))

def list_meteors(json_conf, form):
   meteor_date = form.getvalue("meteor_date")
   files = glob.glob("/mnt/ams2/meteors/" + meteor_date + "/*.json")
   meteors = []
   for file in files:
      if "reduced" in file:
         meteors.append(file)

   print(json.dumps(meteors))


def get_cal_params(json_conf,cams_id):
   if cams_id is None:
      files = glob.glob("/mnt/ams2/cal/solved/*.json")
   else:
      files = glob.glob("/mnt/ams2/cal/solved/*" + cams_id + "*.json")
   return(files)

def examine_cal(json_conf,form):

   print("""
      <script>
      function swap_pic(img_id,img_src) {
         document.getElementById(img_id).src=img_src

      }
      </script>

      """)
   print("<p>Exmaine calibration</p>")
   cal_param = form.getvalue('cal_param')
   cal_file = cal_param.replace("-calparams.json", ".jpg") 
   orig_cal_file = cal_param.replace("-calparams.json", "-orig.jpg") 
   rect_file = cal_param.replace("-calparams.json", "-rect.jpg") 
   grid_file = cal_param.replace("-calparams.json", "-grid.png") 
   cal_fit_file = cal_param.replace("-calparams.json", "-calfit.jpg") 

   print("<figure><img id=\"cal_img\" width=1200 src=" + grid_file + ">")
   print("<figcaption>")
   #print("<a href=# onclick=\"swap_pic('cal_img', '" + orig_cal_file + "')\">Orig</a> -" )
   print("<a href=# onclick=\"swap_pic('cal_img', '" + cal_file + "')\">Src</a> -" )
   #print("<a href=# onclick=\"swap_pic('cal_img', '" + cal_file + "')\">Stars</a> -" )
   print("<a href=# onclick=\"swap_pic('cal_img', '" + grid_file + "')\">Grid</a> -" )
   print("<a href=# onclick=\"swap_pic('cal_img', '" + cal_fit_file + "')\">Fit</a> ")
   print("</figcaption></figure>" )
   print("<div style=\"clear: both\"></div>")
   json_data = load_json_file(cal_param )

   #orig_cal_file = cal_p

def get_cal_files(json_conf,cams_id):

   files = glob.glob("/mnt/ams2/cal/freecal/*")
   cal_files = []
   for file in files:
      el = file.split("/")
      fn = el[-1]
      if cfe(file,1) == 1:
         cal_file = file + "/" + fn + "-calparams.json"
         if cfe(cal_file): 
            cal_file = cal_file.replace("-calparams.json", ".png")
            cal_files.append(cal_file)
         else:
            cal_file = file + "/" + fn + "-stacked-calparams.json"
            cal_file = cal_file.replace("-calparams.json", ".png")
            if cfe(cal_file): 
               cal_files.append(cal_file)
     
   return(cal_files)

def get_cam_ids(json_conf):
   cams = []
   cam_options = ""
   for i in range(1,7):
      cam_key ="cam" + str(i)
      cams_id = json_conf['cameras'][cam_key]['cams_id']
      cams.append(cams_id)
      cam_options = cam_options + "<option>" + cams_id + "</option>"
   return(cams, cam_options)

def calib_hd_cal_detail(json_conf, form):
   cfile = form.getvalue("cfile")
   fn = cfile.split("/")[-1]
   base_name = fn.replace("-stacked.png", "")
   freecal_dir = "/mnt/ams2/cal/freecal/" + base_name
   if cfe(freecal_dir) == 0:
      cmd = "mkdir " + freecal_dir
      os.system(cmd)
      print(cmd)
   cmd2 = "cp " + cfile + " " + freecal_dir + "/" + base_name + "-stacked.png"
   print(cmd)
   os.system(cmd)
   cmfile = cfile.replace("-stacked.png", ".mp4")
   print("<script>window.location.href='/pycgi/webUI.py?cmd=free_cal&input_file=" + cfile + "'</script>")
   return("ok")

def hd_cal_detail(json_conf, form):
   rand = str(time.time())
   cfile = form.getvalue("cfile")
   hd_stack_file = cfile
   cal_params_file = hd_stack_file.replace("-stacked.png", "-calparams.json")
   video_file = hd_stack_file.replace("-stacked.png", ".mp4")
   ci = load_json_file("/mnt/ams2/cal/hd_images/hd_cal_index.json")
   cp = load_json_file(cal_params_file)

   half_stack_file = cfile.replace("-stacked", "-half-stack")
   print(half_stack_file)
   if cfe(half_stack_file) == 0:
      img = cv2.imread(hd_stack_file)
      img = cv2.resize(img, (960,540))
      cv2.imwrite(half_stack_file, img)


   az_grid_file = cfile
   print("CAL DETAIL")
   #print("<img src=" + cfile + ">")
   print("""<div style='width: 80%'>
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
   </div>
         <a href="javascript:show_cat_stars('""" + video_file + "','" + hd_stack_file + "','" + cal_params_file + """', 'hd_cal_detail')">Show/Save Catalog Stars</a><BR>
         <a href=/pycgi/webUI.py?cmd=calib_hd_cal_detail&cfile=""" + cfile + """>Calibrate This Image</a><BR>
      <div style='clear: both'></div> 
<div id="star_list"></div>

      <P>&nbsp;</P>
      <P>&nbsp;</P>
      <P>&nbsp;</P>
      <P>&nbsp;</P>
   """)
   for star in cp['cat_image_stars']:
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) = star

      print(ra,dec, "<BR>") 


   js_html = """
     <script>
       var grid_by_default = false;
       var my_image = '""" + half_stack_file + """'
       var hd_stack_file = '""" + hd_stack_file + """'
       var az_grid_file = '""" + az_grid_file + """'
       var stars = [];
     </script>


     <div hidden>
      <img id='""" + half_stack_file + """' id='half_stack_file'>
      <img id='""" + az_grid_file + """' id='az_grid_file'>
      <img id='""" + half_stack_file + """' id='meteor_img'>
     </div>  

      <script>
      window.onload = function () {
            init_load('""" + str(cfile) + """');
      }
     </script>
   """

   return(js_html)

def meteor_index(json_conf, form):
   cgitb.enable() 

   cam_id    = form.getvalue("cam_id")
   day_limit = form.getvalue("limit_day") 
   show_all  = form.getvalue('opt')
   multi     = form.getvalue('multi')

   mmi = load_json_file("/mnt/ams2/cal/hd_images/meteor_index.json")
  
   meteors = {}
   day_defined = 0 
 
  
   #Get First none empty day
   if(day_limit is None and show_all is None and multi is None):
      for day in sorted(mmi, reverse=True):
            day_limit = day 
            break
 
   #Remove not needed
   if(show_all is None):
      if(day_limit is not None):  
            for idx, day in enumerate(mmi): 
                  if(day==day_limit): 
                        meteors[day] = mmi[day] 
      mi = meteors  
   else:
      mi = mmi
             

   results = "<table class='table table-dark table-striped table-hover td-al-m m-auto table-fit'>"
   results += "<thead><tr><th>&nbsp;</th><th>Meteor</th><th>Reduced</th><th>Multi-Station</th><th>AZ/EL FOV</th><th>Pos Ang</th><th>Pixscale</th><th>Stars</th><th>Res Px</th><th>Res Deg</th><th>Dur</th><th>Ang Sep</th><th>Mag</th><th>Seg Res</td><th>Missing Frames</th></tr></thead>"
   results += "<tbody>"

   res_cnt = 0

   for day in sorted(mi, reverse=True):
      results += "<tr><td colspan='15'><h5 class='m-0'>"+day.replace("_", "/")+"</h5></td></tr>"
      
      for meteor_file in mi[day]:
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(meteor_file)
         if cam_id is None:
            show = 1
         elif cam_id == hd_cam:
            show = 1
         else:
            show = 0
         
         if 'multi_station' in mi[day][meteor_file]:
            multi_text = "Y"
         else:
            multi_text = "N"

         if((multi is not None and multi_text=='Y') or (multi is None)):

            fn = meteor_file.split("/")[-1]
            fn = fn.replace(".json", "")
            video_file = meteor_file.replace(".json", ".mp4")
            link = "<a href='/pycgi/webUI.py?cmd=reduce&video_file=" + video_file + "' class='btn btn-primary'>" + get_meteor_time(video_file) + " - " + hd_cam + "</a>"

            if mi[day][meteor_file]['total_res_deg'] > .5:
                  color = "lv1"
            elif .4 < mi[day][meteor_file]['total_res_deg'] < .5:
                  color = "lv2"
            elif .3< mi[day][meteor_file]['total_res_deg'] < .4:
                  color = "lv3"
            elif .2 < mi[day][meteor_file]['total_res_deg'] < .3:
                  color = "lv4"
            elif .1 < mi[day][meteor_file]['total_res_deg'] < .2:
                  color = "lv5"
            elif mi[day][meteor_file]['total_res_deg'] == 0:
                  color = "lv6"
            elif mi[day][meteor_file]['total_res_deg'] == 9999:
                  color = "lv7"
            elif 0 < mi[day][meteor_file]['total_res_deg'] < .1:
                  color = "lv8"
            else:
                  color = "lv7"


            if 'center_az' in mi[day][meteor_file]:
                  az_el = str(mi[day][meteor_file]['center_az'])[0:5] + "/" +  str(mi[day][meteor_file]['center_el'])[0:5]
            else:
                  az_el = ""


            if 'event_start_time' in mi[day][meteor_file]:
                  fn = mi[day][meteor_file]['event_start_time'] + " - " + hd_cam 
            
            pos = ""
            pxs = ""
            ts = 0 
            
            if 'total_stars' in mi[day][meteor_file]:
                  ts = str(mi[day][meteor_file]['total_stars'])
            if 'position_angle' in mi[day][meteor_file]:
                  pos = str(mi[day][meteor_file]['position_angle'])[0:5]

            ass = ""
            dur = ""
            if 'angular_separation' in mi[day][meteor_file]:
                  ass = mi[day][meteor_file]['angular_separation']
            else:
                  ass = ""
            if 'event_duration' in mi[day][meteor_file]:
                  dur = str(mi[day][meteor_file]['event_duration'])
            else:
                  dur = ""
            
            fn = meteor_file.split("/")[-1] 
            if 'pixscale' in mi[day][meteor_file]:
                  pxs = str(mi[day][meteor_file]['pixscale'])[0:5]

            if day_limit is not None:
                  if day_limit == fn[0:10]:
                        show = 1
                  else:
                        show = 0

            if "red_seg_res" in mi[day][meteor_file]:
                  seg_res = mi[day][meteor_file]['red_seg_res']
            else:
                  seg_res = 999
            if "frames_missing_before" in mi[day][meteor_file]:
                  missing_frames = len(mi[day][meteor_file]['frames_missing_before'])
            else:
                  missing_frames = 0

            if seg_res != 999 :
                  if seg_res > 2 or missing_frames > 0:
                        color = "lv1"
            if show == 1:
                  results += "<tr class='" + color + "'>"
                  results += "<td><div class='st'></div></td>"
                  results += "<td>"+link+"</td>"
                  results += "<td>"+ str(mi[day][meteor_file]['reduced'])+"</td>"
                  results += "<td>"+ multi_text+"</td>"
                  results += "<td>"+ az_el+"</td>"
                  results += "<td>"+ pos+"</td>"
                  results += "<td>"+ pxs+"</td>"
                  results += "<td>"+ str(ts)+"</td>"
                  results += "<td>"+ str(mi[day][meteor_file]['total_res_px'])[0:5]+"</td>"
                  results += "<td>"+ str(mi[day][meteor_file]['total_res_deg'])[0:5]+"</td>"
                  results += "<td>"+ str(dur)+"</td>"
                  results += "<td>"+ str(ass)+"</td>"
                  results += "<td>MAG</td>"
                  results += "<td>"+ str(seg_res)+"</td>"
                  results += "<td>"+ str(missing_frames)+"</td>"
            
            res_cnt+= 1

   results += "</tbody></table>" 

  
   if(day_limit is not None):
      header_out = '<div class="h1_holder d-flex justify-content-between mb-4">'
      header_out += '<h1>Meteor Calibration Index for '
      header_out += '<input value="'+day_limit.replace("_", "/")+'" type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="limit_day" data-send-format="YYYY_MM_DD" class="datepicker form-control">'
      header_out += '</h1><div><a href="/pycgi/webUI.py?cmd=meteor_index&opt=show_all" class="btn btn-primary">Show All</a></div></div>' 
      print(header_out)
   else:
      header_out = '<div class="h1_holder d-flex justify-content-between mb-4">'
      header_out += '<h1>Meteor Calibration Index</h1>'
      header_out += '<div><a href="/pycgi/webUI.py?cmd=meteor_index" class="btn btn-primary">Browse by date</a>  <a href="/pycgi/webUI.py?cmd=meteor_index&multi=1" class="btn btn-primary">Multi-station only</a></div></div>'
      print(header_out) 

   if(res_cnt>1):
      print(results)
   else:
      print('<div class="container"><div class="alert alert-error">No result found for your criteria. <a href="/pycgi/webUI.py?cmd=meteor_index" style="color:#fff; text-decoration:underline">Access the latest meteor calibration.</a></div></div>')


def hd_cal_index(json_conf, form):
   
   cgitb.enable()

   day_limit = form.getvalue("limit_day") 
   show_all  = form.getvalue('opt')
   cam_id_filter = form.getvalue("cam_id")
   js_img_array = {}
 
   cci = load_json_file("/mnt/ams2/cal/hd_images/hd_cal_index.json")
   cam_day_sum = load_json_file("/mnt/ams2/cal/hd_images/hd_cal_index-cam-day-sum.json")
   
   meteors = {}
   day_defined = 0 
  
   #Get First none empty day
   if(day_limit is None and show_all is None):
      for day in sorted(cci, reverse=True):
            day_limit = day 
            break

   #Remove not needed
   if(show_all is None):
      if(day_limit is not None):  
            for idx, day in enumerate(cci): 
                  if(day==day_limit): 
                        meteors[day] = cci[day] 
      ci = meteors  
   else:
      ci = cci
 
   results =  '<div class="m-auto" style="max-width: 1730px;">'
   results += '<table class="table table-dark table-striped table-hover m-3 td-al-m">'
   results += '<thead><tr><th>Date</th><th>Cam ID</th><th>Images w/ Stars</th><th>Images w/o Stars</th><th>Total Stars For Night</th><th>Center AZ/EL</th><th>Position Angle</th><th>PixScale</th><th>Avg Res Px For Night</th><th>Avg Res Deg For Night</th></tr></thead>'
   results += '<tbody>'   
   res_cnt = 0

   for day in sorted(ci,reverse=True): 
         
      results += '<tr><td colspan="10"><h6 class="mb-0">'+day.replace("_","/")+'</h6></td></tr>'

      for cam_id in sorted(ci[day],reverse=False):
         res_cnt+= 1

         if "files_with_stars" in cam_day_sum[day][cam_id]:
            desc = str(cam_day_sum[day][cam_id]['files_with_stars']) + " files with stars / "
            desc = desc + str(cam_day_sum[day][cam_id]['files_without_stars']) + " files without stars "
         else:
            desc = ""
         
         div_id = str(day) + "_" + str(cam_id)
         show_link = '<a class="btn btn-sm btn-primary"><b>'+cam_id+'</b></a>'
 
         if cam_day_sum[day][cam_id]['avg_res_deg_for_night'] > .5:
               color = "lv1"
         elif .4 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .5:
               color = "lv2"
         elif .3 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .4:
               color = "lv3"
         elif .2 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .3:
               color = "lv4"
         elif .1 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .2:
               color = "lv8"
         elif 0 < cam_day_sum[day][cam_id]['avg_res_deg_for_night'] <= .1:
               color = "lv5"
         elif cam_day_sum[day][cam_id]['avg_res_deg_for_night'] == 0:
               color = "lv7"
         else: 
               color = "lv7"

         if cam_id_filter is None:
            show_row = 1
         elif cam_id == cam_id_filter:
            show_row = 1
         else:
            show_row = 0 

         if "position_angle" in cam_day_sum[day][cam_id]:
            fov_pos = str(cam_day_sum[day][cam_id]['position_angle'])[0:5] 
         else : 
            fov_pos = ""

         if "center_az" in cam_day_sum[day][cam_id]:
            az_el = str(str(cam_day_sum[day][cam_id]['center_az'])[0:5] + "/" + str(cam_day_sum[day][cam_id]['center_el'])[0:5])
         else : 
            az_el = ""
         if "position_angle" in cam_day_sum[day][cam_id]:
            pos_ang = str(str(cam_day_sum[day][cam_id]['position_angle'])[0:5])
         else : 
            pos_ang = ""
         if "pixscale" in cam_day_sum[day][cam_id]:
            px_scale = str(str(cam_day_sum[day][cam_id]['pixscale'])[0:5])
         else : 
            px_scale = ""

         if show_row == 1:
            #print("<tr class='" + color + " clickable toggler' data-tog='#fr"+div_id+"'><td><div class='st'>
            # </div></td><td>{:s}</a></td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td>
            # <td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>".format(show_link, str(cam_day_sum[day][cam_id]['files_with_stars']),
            #  str(cam_day_sum[day][cam_id]['files_without_stars']), str(cam_day_sum[day][cam_id]['total_stars_tracked_for_night']),
            #  az_el, pos_ang, px_scale, str(cam_day_sum[day][cam_id]['avg_res_px_for_night'])[0:5],str(cam_day_sum[day][cam_id]['avg_res_deg_for_night'])[0:5]))
            results += "<tr class='" + color + " clickable toggler' data-tog='#fr"+div_id+"'><td><div class='st'></div></td>"
            results += "<td>"+show_link+"</td>"    
            results += "<td>"+str(cam_day_sum[day][cam_id]['files_with_stars'])+"</td>"    
            results += "<td>"+str(cam_day_sum[day][cam_id]['files_without_stars'])+"</td>"  
            results += "<td>"+str(cam_day_sum[day][cam_id]['total_stars_tracked_for_night'])+"</td>"    
            results += "<td>"+az_el+"</td><td>"+pos_ang+"</td><td>"+px_scale+"</td><td>"+str(cam_day_sum[day][cam_id]['avg_res_px_for_night'])[0:5]+"</td>" 
            results += "<td>"+str(cam_day_sum[day][cam_id]['avg_res_deg_for_night'])[0:5]+"</td></tr>"

            results += "<tr><td colspan='11' class='collapse' id='fr"+div_id+"'>"      
            results += "<div class='text-center text-lg-left gallery gal-resize d-flex flex-wrap' style='max-width: 1520px;'>"

            #print("<tr><td colspan='11' class='collapse' id='fr"+div_id+"'>")
            #print("<div class='text-center text-lg-left gallery gal-resize d-flex flex-wrap' style='max-width: 1520px;'>")
            js_img_array["fr"+div_id] = []

            for cfile in sorted(ci[day][cam_id], reverse=True):
               if "total_res_deg" in ci[day][cam_id][cfile]:
                  trd = ci[day][cam_id][cfile]['total_res_deg']
                  trp = ci[day][cam_id][cfile]['total_res_px']
                  ts = ci[day][cam_id][cfile]['total_stars']
               else:
                  trd = 0 
                  trp = 0 
                  ts = 0 

               fn = cfile.split("/")[-1]
               tn = "/mnt/ams2/cal/hd_images/" + day + "/thumbs/" + fn 
               tn = tn.replace(".png", "-tn.png")
               detail_link = "webUI.py?cmd=hd_cal_detail&cfile=" + cfile
               if trp >= 5:
                  color = "style='color: #ff0000'"
               else:
                  color = ""
            
               
               js_img_array["fr"+div_id].append({'col':color, 'lk': detail_link, 'src': tn, 'st': str(ts), 'trp': str(trp)[0:5] , 'trd':  str(trd)[0:5]})            

             
            results += "</div>"
            results += "</td></tr>" 

   results += "</div></table>"  
   results += "</div></div>"           
 

   if(day_limit is not None):
      print('<div class="h1_holder d-flex justify-content-between mb-4"><h1>Auto Calibration Index for <div class="input-group date datepicker" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="limit_day" data-send-format="YYYY_MM_DD"><input value="'+day_limit.replace("_", "/")+'" type="text" class="form-control"><span class="input-group-addon"><span class="icon-clock"></span></span></div></h1><div><a href="/pycgi/webUI.py?cmd=hd_cal_index&opt=show_all" class="btn btn-primary">Show All</a></div></div>')
   else:
      print('<div class="h1_holder d-flex justify-content-between mb-4"><h1>Auto Calibration Index</h1><div><a href="/pycgi/webUI.py?cmd=hd_cal_index" class="btn btn-primary">Browse by date</a></div></div>')

   if(res_cnt>1):
      print(results)
   else:
      print('<div class="container"><div class="alert alert-error">No result found for this date. <a href="/pycgi/webUI.py?cmd=hd_cal_index" style="color:#fff; text-decoration:underline">Access the latest auto-calibration.</a></div></div>')
 
   # Show the details dynamically to we speed up the page load (by A LOT)
   print("<script>var all_cal_details="+json.dumps(js_img_array)+"</script>") 
   return("")

def calibration(json_conf,form):
   cam_id_filter = form.getvalue("cam_id")

   print("<h1>Past Calibrations</h1>")
   freecal_index = "/mnt/ams2/cal/freecal_index.json"
   if cfe(freecal_index) == 1:
      ci = load_json_file("/mnt/ams2/cal/freecal_index.json")   
   else:
      print("No calibrations have been completed yet.")
      exit()
   

   print("<table class='table table-dark table-striped table-hover td-al-m m-auto table-fit'>")
   print("<thead><tr><th>&nbsp;</th><th>Date</th><th>Cam ID</th><th>Stars</th><th>Center AZ/EL</th><th>Pos Angle</th><th>Pixscale</th><th>Res Px</th><th>Res Deg</th></tr></thead>")
   print("<tbody>")
 
   for cf in sorted(ci, reverse=True):
      if 'cal_image_file' in ci[cf]:
         link = "/pycgi/webUI.py?cmd=free_cal&input_file=" + ci[cf]['cal_image_file'] 
      else:
         link = ""
      if ci[cf]['total_res_deg'] > .5:
         color = "lv1"; #style='color: #ff0000'"
      elif .4 < ci[cf]['total_res_deg'] <= .5:
         color = "lv2"; #"style='color: #FF4500'"
      elif .3 < ci[cf]['total_res_deg'] <= .4:
         color = "lv3"; #"style='color: #FFFF00'"
      elif .2 < ci[cf]['total_res_deg'] <= .3:
         color = "lv4"; #"style='color: #00FF00'"
      elif .1 < ci[cf]['total_res_deg'] <= .2:
         color = "lv5"; #"style='color: #00ffff'"
      elif 0 < ci[cf]['total_res_deg'] <= .1:
         color = "lv8"; #"style='color: #0000ff'"
      elif ci[cf]['total_res_deg'] == 0:
         color = "lv7"; #"style='color: #ffffff'"
      else:
         color = "lv7"
      if cam_id_filter is None:
         show_row = 1
      elif cam_id == cam_id_filter:
         show_row = 1
      else:
         show_row = 0

      if show_row == 1: 
         print("<tr class='" + color + "'><td><div class='st'></div></td><td><a class='btn btn-primary' href='{:s}'>{:s}</a></td><td><b>{:s}</b></td><td>{:s}</td><td>{:s}/{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td></tr>".format( link, str(ci[cf]['cal_date']), \
            str(ci[cf]['cam_id']), str(ci[cf]['total_stars']), str(ci[cf]['center_az']), str(ci[cf]['center_el']), str(ci[cf]['position_angle']), \
            str(ci[cf]['pixscale']), str(ci[cf]['total_res_px']), str(ci[cf]['total_res_deg']) ))

   print("</tbody></table></div>")



def calibration_old(json_conf,form):
   cams_id = form.getvalue('cams_id')
   print("<h2>Calibration</h2>")
   print("<p><a href=webUI.py?cmd=free_cal>Make New Calibration</a></P>")
   print("<p>Or select a previous job to work on</p>")
   cal_files = get_cal_files(json_conf,cams_id)
   cams, cam_options = get_cam_ids(json_conf)
   print("""
      <div style="float: top-right">
      <form>
       <select name=cam_id onchange="javascript:goto(this.options[selectedIndex].value, '', 'calib')">
        <option value=>Filter By Cam</option>""")
   print(cam_options)
   print("""    
        </select>
      </form>
      </div>
      """)

   cal_files = sorted(cal_files, reverse=True)

   for file in cal_files:
      el = file.split("/")
      fn = el[-1]
      az_grid_file = file.replace(".png", "-azgrid-half.png")
      if cams_id is not None and cams_id in file:
         print("<figure><a href=webUI.py?cmd=free_cal&input_file=" + file + "><img width=354 src=" + az_grid_file + "><figcaption>"+ fn + "</figcaption></figure>")
   print("<div style=\"clear: both\"></div>")
   #cal_params = get_cal_params(json_conf, cams_id)
 
   stab,sr,sc,et,er,ec = div_table_vars()
   #print(stab)

   #print(sr+sc+"Date"+ec+sc+"Camera" + ec + sc + "Center RA/DEC" + ec + sc + "Center AZ/EL" + ec + sc +"Pixel Scale" + ec + sc + "Position Angle" + ec + sc + "Residual" + ec + er)
   #for cal_param in sorted(cal_params,reverse=True):
   #   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(cal_param)
   #   json_data = load_json_file(cal_param )

   #   az,el = radec_to_azel(json_data['ra_center'],json_data['dec_center'], hd_datetime,json_conf)


   #   print(sr + sc + "<a href=webUI.py?cmd=examine_cal&cal_param=" + cal_param + ">" + hd_date + "</a>" + ec + sc + hd_cam + ec + sc + str(json_data['ra_center'])[0:6] + "/" + str(json_data['dec_center'])[0:5] + ec + sc + str(az)[0:5] + "/" + str(el)[0:5] + ec + sc + str(json_data['pixscale'])[0:5] + ec + sc + str(json_data['position_angle'])[0:5] + ec + sc + str(json_data['x_fun'])[0:4] + "," + str(json_data['y_fun'])[0:4] + ec + er)
   #print(et)

def get_meteor_dirs(meteor_dir):
   files = glob.glob("/mnt/ams2/meteors/*")
   meteor_dirs = []
   
   for f in files:
      if "trash" not in f:
         if cfe(f,1) == 1:
            meteor_dirs.append(f)
   return(meteor_dirs)

def get_meteors(meteor_dir,meteors):
   glob_dir = meteor_dir + "*-trim*.mp4"
   files = glob.glob(meteor_dir + "/*-trim*.json")
   for f in files:
      if "calparams" not in f and "reduced" not in f and "manual" not in f:
         meteors.append(f)
   return(meteors)

 
 
def meteors_new(json_conf,form):  

   cgitb.enable()

   limit_day = form.getvalue('limit_day')
   cur_page  = form.getvalue('p')
   meteor_per_page = form.getvalue('meteor_per_page')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)
 
   htclass = "none"
   meteors = []
   meteor_base_dir ="/mnt/ams2/meteors/"
   meteor_dirs = sorted(get_meteor_dirs(meteor_base_dir), reverse=True)
  
   header_out = "<div class='h1_holder  d-flex justify-content-between'>"
   html_out = ""

   norm_cnt = 0
   reduced_cnt = 0
   has_limit_day = 0

   if len(meteor_dirs) == 0:
      print("No meteors saved yet.")
      exit()
 
   for meteor_dir in meteor_dirs:
      el = meteor_dir.split("/")
      this_date = el[-1]
      if limit_day is None: 
         meteors = get_meteors(meteor_dir, meteors)
      elif limit_day == this_date:
         meteors = get_meteors(meteor_dir, meteors)
         has_limit_day = 1
         header_out += "<h1><span class='h'><span id='meteor_count'>"+format(len(meteors))+"</span> meteors</span> captured on " 
         header_out += '<input value="'+limit_day.replace("_", "/")+'" type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="limit_day" data-send-format="YYYY_MM_DD" class="datepicker form-control">'
         header_out += "</h1>"
   
   if limit_day is None and len(meteors)>=1:
      header_out = header_out + "<h1><span class='h'><span id='meteor_count'>"+format(len(meteors))+"</span> meteors</span> captured since inception</h1>"
   
   if len(meteors)>=1 :

      #NUMBER_OF_METEOR_PER_PAGE
      if(meteor_per_page is None):
         nompp = NUMBER_OF_METEOR_PER_PAGE
      else:
         nompp = int(meteor_per_page)

      
      # Build num per page selector
      ppp_select = ''
      for ppp in POSSIBLE_PER_PAGE:
         if(int(ppp)==nompp):
            ppp_select+= '<option selected value="'+str(ppp)+'">'+str(ppp)+' / page</option>'
         else:
            ppp_select+= '<option value="'+str(ppp)+'">'+str(ppp)+' / page</option>'            
      
      header_out += "<div class='d-flex'><div class='mr-2'><select name='rpp' id='rpp' data-rel='meteor_per_page' class='btn btn-primary'>"+ppp_select+"</select></div><div class='btn-group mr-3'><button id='show_gal' class='btn btn-primary act'><i class='icon-list'></i></button></div>"

      meteors_displayed = 0

    
      meteors = sorted(meteors,reverse=True)

      meteor_from       = nompp*cur_page
      total_number_page = math.ceil(len(meteors) / nompp)
      counter = 0
 
      meteor_start = (cur_page -1) * nompp 
      meteor_end = meteor_start + nompp
      all_meteors = meteors

      meteors = meteors[meteor_start:meteor_end]

      for idx, meteor in enumerate(meteors):
         # Minus 1 so we have nompp per page starting at 0
         if(counter<=nompp-1 and idx <= meteor_from):
            stack_file_tn = meteor.replace('.json', '-stacked-tn.png')
            video_file = meteor.replace('.json', '.mp4')
            stack_obj_img = video_file.replace(".mp4", "-stacked-obj-tn.png")
            reduce_file = meteor.replace(".json", "-reduced.json")
            reduced = 0
            if cfe(reduce_file) == 1:
               reduced = 1
            el = meteor.split("/")
            temp = el[-1].replace(".mp4", "")
            xxx = temp.split("-trim")
            desc = xxx[0] 
            desc_parts = desc.split("_")
            desc = desc_parts[1] + "/" + desc_parts[2] + " " + desc_parts[3] + ":" + desc_parts[4] + " - " + desc_parts[7]

            base_js_name = el[-1].replace("_", "")
            base_js_name = base_js_name.replace(".json", "")
            base_js_name_img = "img_" + base_js_name
            fig_id = "fig_" + base_js_name
            del_id =  base_js_name

            #We also can have fail or meteor (the css is ready for that)
            if reduced == 1: 
               htclass = "reduced"
               reduced_cnt = reduced_cnt + 1
            else: 
               htclass = "norm"
               norm_cnt = norm_cnt + 1

            html_out +=  "<div id='"+del_id+"' class='preview col-lg-2 col-md-3 select-to "+ htclass +"'>"
            html_out +=  "<a class='mtt' href='webUI.py?cmd=reduce&video_file=" + video_file + "' data-obj='"+stack_obj_img+"' title='Go to Info Page'>"
            html_out +=  "<img alt='"+desc+"' class='img-fluid ns lz' src='" + stack_file_tn + "'>"
            html_out +=  "<span>" + desc + "</span></a>"  

            html_out +=  "<div class='list-onl'><span>" + desc + "</span></div>"
            html_out +=  '<div class="list-onl sel-box"><div class="custom-control big custom-checkbox"><input type="checkbox" class="custom-control-input" id="chec_' + del_id + '" name="chec_' + del_id + '"><label class="custom-control-label" for="chec_' + del_id + '"></label> </div></div>'
            html_out +=  "<div class='btn-toolbar'><div class='btn-group'>"
            html_out +=  "<a class='vid_link_gal col btn btn-primary btn-sm' title='Play Video' href='./video_player.html?video=" + video_file + "&vid_id="+del_id+"'><i class='icon-play'></i></a>"
            html_out +=  "<a class='delete_meteor_gallery col btn btn-danger btn-sm' title='Delete Detection' data-meteor='" + del_id + "'><i class='icon-delete'></i></a>"
            html_out +=  "</div></div></div>"
            counter = counter + 1


      non_rec_cnt = len(meteors)-reduced_cnt
    
      #Create buttons
      #header_out = header_out + '<div class="btn-group btn-group-toggle" data-toggle="buttons">'
      #header_out = header_out + '<label class="btn btn-secondary active btn-met-all">'
      #header_out = header_out + '<input type="radio" name="meteor_select" id="all" autocomplete="off" checked=""> All '+ format(len(meteors)) +' meteors</label>'
      #header_out = header_out + '<label class="btn btn-secondary btn-met-reduced">'
      #header_out = header_out + '<input type="radio" name="meteor_select" id="reduced" autocomplete="off">All '+  format(reduced_cnt) +' Reduced Meteors Only</label>'
      #header_out = header_out + '<label class="btn btn-secondary">'
      #header_out = header_out + '<input type="radio" name="meteor_select" id="non_reduced" autocomplete="off">All '+ format(non_rec_cnt) +'  Non-Reduced Meteors Only</label>'
       
      if(has_limit_day==0):
         pagination = get_pagination(cur_page,len(all_meteors),"/pycgi/webUI.py?cmd=new_meteors&meteor_per_page="+str(nompp),nompp)
      else:
         pagination = get_pagination(cur_page,len(all_meteors),"/pycgi/webUI.py?cmd=new_meteors&limit_day="+limit_day+"&meteor_per_page="+str(nompp),nompp)

      if(pagination[2] != ''):
         header_out = header_out + "<div class='page_h'>Page  " + format(cur_page) + "/" +  format(pagination[2]) + "</div>"

   else:
      header_out = header_out + "<h1><span class='h'><span id='meteor_count'>0</span> meteor</span> captured on "
      header_out += '<input value="'+str(this_date.replace("_", "/"))+'" type="text" data-display-format="YYYY/MM/DD" data-action="reload" data-url-param="limit_day" data-send-format="YYYY_MM_DD" class="datepicker form-control"></h1>'

   print(header_out+'</div></div>')
   print("<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>")
   print("<div class='gallery gal-resize row text-center text-lg-left'>")
   print("<div class='list-onl'>")
   print("<div class='filter-header d-flex flex-row-reverse '>")
   print('<button id="sel-all" title="Select All" class="btn btn-primary ml-3"><i class="icon-checkbox-checked"></i></button>')
   print('<button id="del-all" class="del-all btn btn-danger"><i class="icon-delete"></i> Delete <span class="sel-ctn">All</span> Selected</button>')
   print("</div>")
   print("</div>")
   print(html_out)
   print("<div class='list-onl'><div class='filter-header d-flex flex-row-reverse '>") 
   print('<button id="del-all" class="del-all btn btn-danger"><i class="icon-delete"></i> Delete <span class="sel-ctn">All</span> Selected</button>')
   print("</div></div>")
   print("</div>")
   #page,total_pages,url for pagination
   if(len(meteors)>=1):
      print(pagination[0])
   
   print("</div>") 
 


def meteors(json_conf,form): 
   print ("""
   


   """)


   limit_day = form.getvalue('limit_day')
   htclass = "none"
   print("<h1>Meteors</h1>")
   meteors = []
   meteor_base_dir ="/mnt/ams2/meteors/"
   meteor_dirs = sorted(get_meteor_dirs(meteor_base_dir), reverse=True)


   for meteor_dir in meteor_dirs:
      el = meteor_dir.split("/")
      this_date = el[-1]
      if limit_day is None: 
         meteors = get_meteors(meteor_dir, meteors)
      elif limit_day == this_date:
         meteors = get_meteors(meteor_dir, meteors)
         print("<p>{:d} meteors captured on {:s}.</p>".format(len(meteors), str(this_date)))
   if limit_day is None:
      print("<p>{:d} meteors captured since inception.</p>".format(len(meteors)))

   span = "<span id=\"{ID}\" class=\"context-menu-one btn btn-neutral\">"  
   end_span = "</span>"

   for meteor in sorted(meteors,reverse=True):
      stack_file_tn = meteor.replace('.json', '-stacked-tn.png')
      video_file = meteor.replace('.json', '.mp4')
      stack_obj_img = video_file.replace(".mp4", "-stacked-obj-tn.png")
      reduce_file = meteor.replace(".json", "-reduced.json")
      reduced = 0
      if cfe(reduce_file) == 1:
         reduced = 1
      

      el = meteor.split("/")
      temp = el[-1].replace(".mp4", "")
      xxx = temp.split("-trim")
      desc = xxx[0] 
      desc_parts = desc.split("_")
      desc = desc_parts[1] + "/" + desc_parts[2] + " " + desc_parts[3] + ":" + desc_parts[4] + " - " + desc_parts[7]


      base_js_name = el[-1].replace("_", "")
      base_js_name = base_js_name.replace(".json", "")
      base_js_name_img = "img_" + base_js_name
      fig_id = "fig_" + base_js_name
      del_id =  base_js_name
      if reduced == 1: 
         htclass = "reduced"
      else: 
         htclass = "norm"

      buttons = "<br><a href=\"javascript:play_meteor_video('" + video_file + " ')\">Play</A> - " 
      #buttons = " <a class=\"vid-link\" href=\"" + video_file + "\">Play</a> -"
      #buttons = """
      #    <a href='""" + video_file + """'>Play</a>
#
#      """

      buttons = buttons + "<a href=\"webUI.py?cmd=reduce&video_file=" + video_file + "\"" + ">Info</A> - " 
      buttons = buttons + "<a href=\"javascript:reject_meteor('" + del_id + "')\">Del</A>" 

      html_out = ""
      this_span = span.replace("{ID}", base_js_name)
      html_out +=  "<figure id=\"" + fig_id + "\">" + this_span + "<a href=\"webUI.py?cmd=reduce&video_file=" + video_file + "\"" \
         + " onmouseover=\"document.getElementById('" + base_js_name_img + "').src='" + stack_obj_img \
         + "'\" onmouseout=\"document.getElementById('" + base_js_name_img + "').src='" + stack_file_tn+ "'\">"
  
      html_out +=  "<img width=282 height=192 class=\"" + htclass + "\" id=\"" + base_js_name_img + "\" src='" + stack_file_tn+ "'></a>" + end_span + "<figcaption>" + desc + str(buttons) + "</figcaption></figure>\n"

      print(html_out)
   print("<div style='clear: both'></div>")
   print("<script>var stars = []; var az_grid_file = '';</script>")



def live_view(json_conf):
 

   print("""<h1>Live</h1>
            <div class="container mt-3" style="max-width: 1500px;">
                  <p class="text-center"><b>Still pictures are updated in 5 minutes intervals. This page will automatically refresh in <span id="cntd">2:00</span>.</b></p>
                  <div class="gallery gal-resize row text-center text-lg-left mb-4">
   """)
 
   rand=time.time()
   for cam_num in range(1,7):
      cam_key = 'cam' + str(cam_num)
      cam_ip = json_conf['cameras'][cam_key]['ip']
      #sd_url = json_conf['cameras'][cam_key]['sd_url']
      #hd_url = json_conf['cameras'][cam_key]['hd_url']
      cams_id = json_conf['cameras'][cam_key]['cams_id']

      img = "/mnt/ams2/latest/" + cams_id + ".jpg"
      

      print('<div class="preview col-lg-4 mb-4"><a class="mtt img-link-gal" href="'+img+'" title="Live View">')
      print('<img alt="'+cams_id+'" class="img-fluid ns lz" src="'+img+'?r=' + str(rand) + '"><span><b>Cam '+cams_id+' ('+cam_ip+')</span></b></a></div>')

   print("</div></div></div>")

   #Countdown
   print("""
      <script>
      var timeoutHandle;
      function countdown(minutes) {
            var seconds = 60;
            var mins = minutes;
            if(mins==0) {
                  location.reload();
            }
            function tick() {
                  var counter = document.getElementById("cntd");
                  var current_minutes = mins-1
                  seconds--;
                  counter.innerHTML = current_minutes.toString() + ":" + (seconds < 10 ? "0" : "") + String(seconds);
                  if( seconds > 0 ) {
                        timeoutHandle = setTimeout(tick, 1000);
                  } else {
                        if(mins > 1){
                              setTimeout(function () { countdown(mins - 1); }, 1000);
                        }
                  }
            }
            tick();
      }
      countdown(5);
      </script>
   """)

def as6_config(json_conf):
   print("AS6 Config")
   print("<UL>")
   print("<LI><a href=webUI.py?cmd=edit_system>Edit System Variables</a></LI>")
   print("<LI><a href=webUI.py?cmd=mask_admin>Mask Admin</a></LI>")
   print("<LI><a href=webUI.py?cmd=manage_alerts>Manage Alerts</a></LI>")
   print("<LI><a href=webUI.py?cmd=api_services>Cloud Sharing</a></LI>")
   print("</UL>")

def get_mask_img(cams_id, json_conf):

   proc_dir = json_conf['site']['proc_dir']
   #days = get_days(json_conf)
   #day = days[0]
   img_dir = "/mnt/ams2/latest/"
   sd_dir = "/mnt/ams2/SD/"

   # first look for img, if made less than 24 hours ago use it, else make new one
   img_files = glob.glob(img_dir + cams_id + "-mask.jpg")
   if len(img_files) == 0:
      print("no mask images exist. Is this a new install? Are cams attached?")
      exit()

   if len(img_files) == 1:
      img = cv2.imread(img_files[0])
   else:
      files = glob.glob(sd_dir + "*" + cams_id + "*.mp4")
      frames = load_video_frames(files[0], json_conf, 10)
      img = frames[0]
   sd_h, sd_w = img.shape[:2]
   file = img_dir + cams_id + ".jpg"
   sfile = img_dir + cams_id + "-mask.jpg"
   #img = cv2.imread(file)
   #simg = cv2.resize(img, (704,576))
   simg = img
   cv2.imwrite(sfile, simg)
   files = [sfile]

   return(sfile, sd_w, sd_h)

def save_masks(form,camera,cams_id, json_conf):
   sd_w = int(form.getvalue('sd_w'))
   sd_h = int(form.getvalue('sd_h'))
   hdm_x = 1920 / sd_w 
   hdm_y = 1080 / sd_h 

   print("<h1>SAVE MASKS</h1>")
   total_masks = int(form.getvalue('total_masks'))
   mask_data = {}
   hd_mask_data = {}


   for i in range(0,total_masks) :
      field = "x" + str(i)
      x = int(form.getvalue(field))
      field = "y" + str(i)
      y = int(form.getvalue(field))
      field = "w" + str(i)
      w = int(form.getvalue(field))
      field = "h" + str(i)
      h = int(form.getvalue(field))
      mask_str = str(x) + "," + str(y) + "," + str(w) + "," + str(h)
      hd_mask_str = str(int(x*hdm_x)) + "," + str(int(y*hdm_y)) + "," + str(int(w*hdm_x)) + "," + str(int(h*hdm_y))
      mask_key = "mask" + str(i)
      hd_mask_key = "hd_mask" + str(i)
      mask_data[mask_key] = mask_str
      hd_mask_data[hd_mask_key] = hd_mask_str

   # check if new entry exists
   nx = form.getvalue("nx")
   ny = form.getvalue("ny")
   nw = form.getvalue("nw")
   nh = form.getvalue("nh")
   if nx is not None:
      nx,ny,nw,nh = int(nx),int(ny),int(nw),int(nh)
      mask_str = str(nx) + "," + str(ny) + "," + str(nw) + "," + str(nh)
      hd_mask_str = str(int(nx*hdm_x)) + "," + str(int(ny*hdm_y)) + "," + str(int(nw*hdm_x)) + "," + str(int(nh*hdm_y))
      mask_key = "mask" + str(i+1)
      hd_mask_key = "hd_mask" + str(i+1)
      mask_data[mask_key] = mask_str
      hd_mask_data[hd_mask_key] = hd_mask_str

   # save mask file for thumbnailer
   fp = open("/home/ams/amscams/conf/mask-" + cams_id  + ".txt", "w")
   for mask_key in mask_data:
      x,y,w,h = mask_data[mask_key].split(",")
      fp.write(x + " " + y + " " + w + " " +  h + "\n")
   fp.close()

   json_conf['cameras'][camera]['masks'] = mask_data
   json_conf['cameras'][camera]['hd_masks'] = hd_mask_data
   save_json_file('/home/ams/amscams/conf/as6.json', json_conf)


def mask_admin(json_conf,form):
   print("<h1>Mask Admin</h1>")
   subcmd = form.getvalue('subcmd')
   camera = form.getvalue('camera')
   cams_id = form.getvalue('cams_id')
   if subcmd == 'save_mask':
      save_masks(form, camera, cams_id, json_conf)

   if camera is None:
      for camera in json_conf['cameras']:
         cid = json_conf['cameras'][camera]['cams_id']
         print("<a href=webUI.py?cmd=mask_admin&camera=" + camera + "&cams_id=" + cid + ">" + cid + "<BR>")
   else:
      print("Masks for ", cams_id, "<BR>")
      imgf,sd_w,sd_h = get_mask_img(cams_id, json_conf) 
      #print(imgf) 
      masks = get_masks(cams_id, json_conf)
      img = cv2.imread(imgf, 0)
      tmasks = []
      for mask in masks:
         x,y,w,h = mask.split(",")
         x,y,w,h = int(x), int(y), int(w), int(h)
         #x,y,w,h = int(x), int(int(y) * .83), int(w), int(int(h) * .83) + 1
         cv2.rectangle(img, (x, y), (x + w, y + h), (128, 128, 128), -1)      
         tmasks.append((x,y,w,h))
      cv2.imwrite("/mnt/ams2/tmp.jpg", img)
      print("<img src=/mnt/ams2/tmp.jpg><br>")
      c = 0
      print("<p><form>")
      for mask in tmasks:
         (x,y,w,h) = mask
         print("MASK " + str(c) + ": " )
         print("X:<Input size=3 type=text name=x" + str(c) + " value=" + str(x) + ">")
         print("Y:<Input size=3 type=text name=y" + str(c) + " value=" + str(y) + ">")
         print("W:<Input size=3 type=text name=w" + str(c) + " value=" + str(w) + ">")
         print("H:<Input size=3 type=text name=h" + str(c) + " value=" + str(h) + "><BR>")
         c = c + 1
      print("<P>ADD NEW MASK " ": " )

      print("X:<Input size=3 type=text name=nx value=>")
      print("Y:<Input size=3 type=text name=ny value=>")
      print("W:<Input size=3 type=text name=nw value=>")
      print("H:<Input size=3 type=text name=nh value=>")
      print("<P><input type=hidden name=cmd value=mask_admin>")
      print("<input type=hidden name=subcmd value=save_mask>")
      print("<input type=hidden name=camera value=" + camera + ">")
      print("<input type=hidden name=cams_id value=" + cams_id + ">")
      print("<input type=hidden name=sd_w value=" + str(sd_w) + ">")
      print("<input type=hidden name=sd_h value=" + str(sd_h) + ">")
      print("<input type=hidden name=total_masks value="+str(c) +">")
      print("<input type=submit value=\"Save Masks\">")
      print("</form>")



def nav_links(json_conf, cmd):

   nav_top = """
      <div class="collapse navbar-collapse" id="navbar1">
         <ul class="navbar-nav ml-auto">
   """

   nav_item_active = """
      <li class="nav-item active">
         <a class="nav-link" href="{LINK}">{DESC}<span class="sr-only">(current)</span></a> </li>
   """

   nav_item = """
      <li class="nav-item">
         <a class="nav-link" href="{LINK}"> {DESC}</a></li>
   """

   nav_item_drop_down = """
      <li class="nav-item dropdown">
        <a class="nav-link  dropdown-toggle" href="#" data-toggle="dropdown">  Dropdown  </a>
          <ul class="dropdown-menu">
             <li><a class="dropdown-item" href="#"> Menu item 1</a></li>
             <li><a class="dropdown-item" href="#"> Menu item 2 </a></li>
          </ul>
      </li>
   """
   nav_bottom = """
<li class="nav-item">
<a class="btn ml-2 btn-warning" href="http://bootstrap-ecommerce.com">Download</a></li>
    </ul>
  </div>

   """

   # home - meteors - archive - calibration - config
   nav_links = {}
   nav_links['home'] = "Home"
   nav_links['meteors'] = "Meteors"
   nav_links['calibration'] = "Calibration"
   nav_links['live_view'] = "Live View"
   nav_links['video_tools'] = "Video Tools"
   nav_links['config'] = "Config"

  
   nav = ""
   bot_nav = ""
   for link in nav_links:
      if nav != "":
         #nav = nav + " - "
         bot_nav = bot_nav + " - "
      if cmd != link:
         temp = nav_item.replace("{LINK}", "webUI.py?cmd=" + link) 
         temp = temp.replace("{DESC}", nav_links[link]) 
      else:
         temp = nav_item_active.replace("{LINK}", "webUI.py?cmd=" + link) 
         temp = temp.replace("{DESC}", nav_links[link]) 
      nav = nav + temp 
      bot_nav = bot_nav + "<a href=\"webUI.py?cmd=" + link + "\">" + nav_links[link] + "</a>"
   
   return(nav, bot_nav)



def reset(video_file, type):
   if "passed" in video_file:
      out_file = video_file.replace("passed/","")
   if "failed" in video_file:
      out_file = video_file.replace("failed/","")

   stack_file = video_file.replace(".mp4", "-stacked.png")
   json_file = video_file.replace(".mp4", ".json")
   cmd = "mv " + video_file + " " + out_file
   mv_cmd = cmd
   print(cmd)
   os.system(cmd)
   cmd = "rm " + stack_file 
   os.system(cmd)
   cmd = "rm " + json_file 
   os.system(cmd)
   print("reset:", out_file)  
   cmd = "cd /home/ams/amscams/pythonv2/; ./detectMeteors.py sf " + out_file + " > tmp.txt"
   os.system(cmd)
   fp = open("/home/ams/amscams/pythonv2/tmp.txt", "r")
   print("<PRE>")
   for line in fp:
      print(line)
   cmd2 = "echo \"" + mv_cmd + "\" >> /home/ams/amscams/pythonv2/tmp.txt"
   os.system(cmd2)
   cmd2 = "echo \"" + cmd + "\" >> /home/ams/amscams/pythonv2/tmp.txt"
   os.system(cmd2)

def trim_clip(video_file, start, end):
   print("trim clip")
   outfile = video_file.replace(".mp4", "-trim" + str(start) + ".mp4")
   cmd = "/usr/bin/ffmpeg -y -i " + video_file + " -vf select=\"between(n\," + str(start) + "\," + str(end) + "),setpts=PTS-STARTPTS\" " + outfile + " 2>&1 > /dev/null"
   if cfe(outfile) == 0:
      print(cmd)
      os.system(cmd)
   print("Trim clip made:", outfile)


def examine_min(video_file,json_conf):
   failed_files, meteor_files, pending_files = get_trims_for_file(video_file)
   stack_file = stack_file_from_video(video_file)
   vals_file = stack_file.replace("-stacked.png", "-vals.json")
   vals_file = vals_file.replace("images", "data")
   detect_file = vals_file.replace("-vals.json", "-detect.json")
   meteor_file = vals_file.replace("-vals.json", "-meteor.json")
   toomany_file = vals_file.replace("-vals.json", "-toomany.json")

   detect_info = None
   meteor_info = None
   toomany = None
   if cfe(meteor_file) == 1:
      meteor_files = []
      meteor_info = load_json_file(meteor_file)
      meteor_files.append( meteor_info['hd_trim'])
      meteor_files.append(meteor_info['sd_trim'])
   elif cfe(toomany_file) == 1:
      toomany = load_json_file(toomany_file)
      for key in toomany:
         print(key)


   elif cfe(detect_file) == 1:
      detect_info = load_json_file(detect_file)
      detect_html = "Events<BR>"
      ec = 1
      for event in detect_info['events']:
         detect_html += "Frames:" + str(event['frames'])  + "<BR>"
         detect_html += "Sum Vals:" + str(event['sum_vals'])  + "<BR>"
         detect_html += "Max Vals:" + str(event['max_vals'])  + "<BR>"
         detect_html += "Pos:" + str(event['pos_vals'])  + "<BR>"
         detect_html += str(ec) + "<BR>"
         ec += 1
      detect_html += "Objects<BR>"
      for id in detect_info['objects']:
         obj = detect_info['objects'][id]
         detect_html += str(obj) + " " + "<BR>"


   #print(detect_html)
   if cfe(vals_file) == 1:
      vals = load_json_file(vals_file)

   next_stack_file = stack_file_from_video(video_file)
  

   print("<h1>Examine One-Minute Clip - " +  get_meteor_date(video_file) +"</h1>")
   print("<div id='main_container' class='container-fluid d-flex h-100 mt-4 position-relative'>")

   print("<div class='h-100 flex-fixed-canvas'>")
   stack_file = stack_file.replace(".png", "-tn.png")
   if os.path.isfile(stack_file):
      print("<a href='" + video_file + "' class='vid_link_gal mx-auto d-block' title='Click to Play'><img src='" + stack_file + "' class='mx-auto d-block img-fluid' style='width:100%'></a>")
   else:
      print("<div class='alert error'>The Stack Image isn't ready yet.</div>")

   print("</div>")


   print("<div class='flex-fixed-r-canvas h-100'>")
   print("<div class='box'><h2 class='mb-4'>Actions</h2>")
   print("<a class='btn btn-primary mx-auto d-block mb-2' href='webUI.py?cmd=manual_detect&sd_video_file=" + video_file + "'>Manually Detect</a>")
   print("</div>")

   print("<div class='box'><h2>Status</h2>")
   print("<div class='p-3'>")
 
   #if len(pending_files) > 0:
   #   print("<p>Trim files for this clip are still pending processing. Please wait before manually processing this file.</p>")
   #   print("<ul>")
   #   for pending in pending_files:
   #      print("<li><a href=" + pending + ">" + pending + "</a></li>")
   #   print("</ul>")

   if len(meteor_files) > 0 or meteor_info is not None:
      print("<p class='text-center alert success'><b>Meteor DETECTED</b></p>")
      for meteor_file in meteor_files:
         meteor_stack = meteor_file.replace(".mp4", "-stacked.png")
         print("<a href='" + meteor_file + "' class='mx-auto d-block'>" + meteor_file + "</a><br>")
         sfn = meteor_file.split("/")[-1]
         mdir = meteor_file.replace(sfn, "")
         meteor_stack = mdir + "images/" + sfn
         #print("<img src='" + meteor_stack + "' class='mx-auto d-block img-fluid'></a>")
         #print("<a class='btn btn-primary mx-auto d-block mt-1 mb-3' href='webUI.py?cmd=examine&video_file=" + meteor_file + "'>Examine</a>")

   if len(failed_files) > 0: 
      print("<p class='text-center alert error'><b>NON METEOR Detection</b></p>")
      for fail_file in failed_files:
         fail_stack = fail_file.replace(".mp4", "-stacked.png")
         print("<a href='" + fail_file + "' class='mx-auto d-block'>")
         print("<img src='" + fail_stack + "' class='mx-auto d-block img-fluid'></a>")
         print("<a class='btn btn-primary mx-auto d-block  mt-1 mb-3' href='webUI.py?cmd=examine&video_file=" + fail_file + "'>Examine</a>")
        
   if len(failed_files) == 0 and len(meteor_files) == 0:
      print("<p class='text-center alert error'><b>NO Detection</b></p>")
   #print(failed_files,meteor_files)


   print("</div>")
   print("</div>")
   print("</div>")
   print("</div>")

   object_html = ""

   if detect_info is not None:
      print(detect_info)
   if meteor_info is not None:
      #<th></th><th></th><th>#</th><th>Sum Val</th><th>Max Val</th><th>Max X,Y</th><th>CM</th><th></th><th></th><th></th><th colspan="4"></th>
      meteor_html = """
      <table border=1 class="table table-dark table-striped table-hover td-al-m mb-2 pr-5 mt-2">
         <thead>
            <tr>
            </tr>
         </thead>
      """

      meteor_html += "<tr><td COLSPAN=2>Meteor Info<BR></td></tr>"
      meteor_html += "<tr><td>HD TRIM FILE: </td><td>" + meteor_info['hd_trim'] + "</td></tr>"
      meteor_html += "<tr><td>SD TRIM FILE: </td><td>" + meteor_info['sd_trim'] + "</td></tr>"
      meteor_html += "<tr><td colspan=2>HD OBJECTS:</td></tr>"
      for key in meteor_info['hd_motion_objects']: 
         obj = meteor_info['hd_motion_objects'][key]
         if obj['report']['meteor_yn'] == "Y":
            meteor_html += "<tr><td>Frames</td><td>" + str(obj['ofns']) + "</td></tr>"
            meteor_html += "<tr><td>Xs</td><td>" + str(obj['oxs']) + "</td></tr>"
            meteor_html += "<tr><td>Ys</td><td>" + str(obj['oys']) + "</td></tr>"
            meteor_html += "<tr><td>Ws</td><td>" + str(obj['ows']) + "</td></tr>"
            meteor_html += "<tr><td>Hs</td><td>" + str(obj['ohs']) + "</td></tr>"
            meteor_html += "<tr><td>Intensity</td><td>" + str(obj['oint']) + "</td></tr>"
            for key in obj['report']:
               val = obj['report'][key]
               if key != 'classify':
                  meteor_html += "<tr><td>" + str(key) + "</td><td>" + str(val) + "</td></tr>"

            meteor_html += "<tr><td colspan=2>Classify:</td></tr>"
            for key in obj['report']['classify']:
               val = obj['report']['classify'][key]
               meteor_html += "<tr><td>" + str(key) + "</td><td>" + str(val) + "</td></tr>"


      meteor_html += "SD OBJECTS:<BR>"
      for key in meteor_info['motion_objects']:
         obj = meteor_info['motion_objects'][key]
         if obj['report']['meteor_yn'] == "Y":
            meteor_html += key + str(obj['report']) + "<BR>"
      object_html = meteor_html
      meteor_html += "</table>"
   if toomany is not None:
      for key in toomany['objects']:
         obj = toomany['objects'][key]
         if "max_cm" in obj['report']:
            if obj['report']['max_cm'] > 2:
               object_html += key + " " + str(obj['report']['max_cm']) + " " + str( obj['ofns']) + " " + str(obj['report']['obj_class']) +  "<BR>"
               #print(key)


   out = """
      <table class="table table-dark table-striped table-hover td-al-m mb-2 pr-5 mt-2">
         <thead>
            <tr>
               <th></th><th></th><th>#</th><th>Sum Val</th><th>Max Val</th><th>Max X,Y</th><th>CM</th><th></th><th></th><th></th><th colspan="4"></th>
            </tr>
   """
   last_i = None
   if cfe(vals_file) == 1:
      for i in range (0, len(vals['sum_vals'])):
         sum_val = vals['sum_vals'][i] 
         if last_i is not None and last_i + 1 == i:
            cm += 1
         else: 
            cm = 0
         if sum_val > 0:
            max_val = vals['max_vals'][i] 
            mx, my = vals['pos_vals'][i] 
            #print(i,sum_val,max_val,mx,my,"<BR>")
            out += """
            <tr><td></td><td></td><td>{:s}</td>
            <td class='td'>{:s}</td>
            <td class='td'>{:s}</td>
            <td class='td'>{:s}, {:s}</td>
            <td class='td'>{:s}</td>
            <td class='td' colspan=4></td>

            </tr>
            """.format(str(i), str(sum_val), str(max_val), str(mx), str(my), str(cm))
            last_i = i

   out += """
         </thead>
         <tbody>
         </tbody>
      </table>
   """

   print("<div style='width: 48%; margin: 0 auto; padding: 20px;'>")

   tabs = "" 
   tabs_content = "" 
   frame_data_html=out
   tabs1, tabs_content1 = create_tab_and_content( tabs   , tabs_content   ,'frame_data','FRAME DATA', frame_data_html , True)

   tabs = "" 
   tabs_content = "" 
   object_data = object_html 
   tabs2, tabs_content2 = create_tab_and_content( tabs   , tabs_content   ,'object_data','OBJECT DATA', object_data)

   print("<ul class='nav nav-tabs mt-3'>")
   print(tabs1)
   print(tabs2)
   print("</ul>")

   print("<div class='tab-content box'>")
   print(tabs_content1)
   print(tabs_content2)
   print("</div>")

   #print("</div>")
   print("</div>")

   start = ""
   end = ""

   print("<form>")
   print("<input type=hidden name=cmd value='trim_clip'>") 
   print("<input type=hidden name=video_file value='{:s}'>".format(video_file)) 
   print("<input type=text name=start value='{:s}'>".format(start)) 
   print("<input type=text name=end value='{:s}'>".format(end)) 
   print("<input type=submit name=submit value='Trim Clip'> ")
   print("</form>")


#Delete multiple detections at once
def delete_multiple_detection(detections,json_conf):
      

      # If there's only one it's treated as a string (?)
      if(type(detections) is str):
            det = []
            det.append(detections)
            detections = det
      
      for to_delete in detections:
            #print("TO DELETE " + str(to_delete))
            override_detect('',to_delete,'')



def override_detect(video_file,jsid, json_conf):
   cgitb.enable()
    
   if jsid is not None:
      video_file = parse_jsid(jsid) 

   vfn = video_file.split("/")[-1]
   el = vfn.split("-trim")
   bs = el[0]
   date = vfn[0:10]
   json_data = None
   proc_file = "/mnt/ams2/SD/proc2/" + date + "/data/" + bs + "-meteor.json"
   non_proc_file = "/mnt/ams2/SD/proc2/" + date + "/data/" + bs + "-nonmeteor.json"
   if cfe(proc_file) == 1:
      cmd = "mv " + proc_file + " " + non_proc_file
      print(cmd)
   else:
      print(proc_file + " Not found")

   base = video_file.replace(".mp4", "")
   el = base.split("/")
   base_dir = base.replace(el[-1], "")
 
   if "meteors" in base:
      new_dir = "/mnt/ams2/trash/"
      json_file = video_file.replace(".mp4", ".json")
      json_data = load_json_file(json_file)
      hd_trim = json_data['hd_trim']
      sd_video_file = json_data['sd_video_file']
      el = sd_video_file.split("/")
      sd_dir  = sd_video_file.replace(el[-1], "") 
      sd_fail = sd_dir.replace("passed","failed")
      sd_wild = sd_video_file.replace(".mp4", "*")
   
      cmd = "mv "  + sd_wild + " " + sd_fail   
      os.system(cmd)

      if hd_trim is not None and str(hd_trim) != "0":
         el = hd_trim.split("-trim-")
         ttt = el[0]
         xxx = ttt.split("/")
         hd_wild = base_dir + "/" + xxx[-1] + "*"
         cmd2 = "mv " + hd_wild + " /mnt/ams2/trash/"
         os.system(cmd2)
      else:
         cmd2 = ""

      cmd3 = "mv " + base + "* " + new_dir
      #print(cmd, "<BR>")
      os.system(cmd3)
      print("Detection moved to /mnt/ams2/trash (if you made a mistake the files can be retrieved from the trash folder.)<BR>" ) 
      print(cmd, "<BR>")
      print(cmd2, "<BR>")
      print(cmd3, "<BR>")
     
   if "archive_file" in json_data :
      if json_data['archive_file'] is not "":
         delete_multiple_archived_detection(json_data['archive_file'])
   
   if "passed" in base:
      new_dir = base_dir.replace("passed", "failed")
      cmd = "mv " + base + "* " + new_dir
      os.system(cmd)
      print("Files moved to failed dir.")

   if "failed" in base: 
      new_dir = base_dir.replace("failed", "passed")
      cmd = "mv " + base + "* " + new_dir
      os.system(cmd)
      print("Files moved to meteor dir.")
      base_fn = base.split("/")[-1]
      sd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(base)
      hd_wild = "/mnt/ams2/HD/" + hd_y + "_" + hd_m + "_" + hd_d + "_" + hd_h + "_" + hd_M + "*" + hd_cam + "*.mp4"
      print(hd_wild)
      hd_files = glob.glob(hd_wild)
      print(hd_files)
      el = base.split("-trim")
      trim_num = int(el[-1])
      trim_sec = trim_num * (1/25)
     
      print("SD TRIM NUM:", trim_num)
      if len(hd_files) > 0:
         hd_file = hd_files[0]
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         hd_fn = hd_file.split("/")[-1]
         elapsed_time = sd_datetime - hd_datetime
         print("<h1>SD-HD TIME DIFF", elapsed_time.total_seconds(), sd_datetime, hd_datetime, "<h1>")
         hd_trim_sec = (trim_num * (1/25)) + elapsed_time.total_seconds()

         hd_trim_num = 0
         hd_outfile = "/mnt/ams2/meteors/"+ hd_y + "_" + hd_m + "_" + hd_d + "/" +  hd_fn
         hd_outfile = hd_outfile.replace(".mp4", "-trim-" + str(hd_trim_num) + "-HD-meteor.mp4")

      cmd = "/usr/bin/ffmpeg -i " + hd_file + " -ss 00:00:" + str(hd_trim_sec) + " -t 00:00:12 -c copy " + hd_outfile 
      os.system(cmd)
      print("HD LINK:", hd_outfile)
      print(cmd)
      
      

def examine(video_file):
   
   #print_css()
   print("<h1>Examine Trim File</h1>")
   el = video_file.split("/")
   fn = el[-1]
   meteor_dir = video_file.replace(fn, "")
   stack_img = video_file.replace(".mp4", "-stacked.png")
   stack_obj_img = video_file.replace(".mp4", "-stacked-obj.png")
   base_js_name = "123"
   htclass='norm'
   print("<a href=" + video_file + ">")
   #print("<p><img src=" + stack_img + " ></a></p>")
   html_out = ""
   html_out +=  "<a href=\"" + video_file + "\"" \
         + " onmouseover=\"document.getElementById('" + base_js_name + "').src='" + stack_obj_img \
         + "'\" onmouseout=\"document.getElementById('" + base_js_name + "').src='" + stack_img+ "'\">"
   html_out +=  "<img class=\"" + htclass + "\" id=\"" + base_js_name + "\" src='" + stack_img+ "'></a><br>\n"
   print("<figure>")
   print(html_out)
   if "meteors" in video_file or "passed" in video_file:
      print("<a href=webUI.py?cmd=override_detect&video_file=" + video_file + " >Reject Meteor</a>  ")
   else:
      print("<a href=webUI.py?cmd=override_detect&video_file=" + video_file + " >Tag as Meteor</a>  ")

   #print("<a href=webUI.py?cmd=reset&type=meteor&video_file=" + video_file + " >Re-run Detection</a>")

   print("</figure>")
   print("<p style='clear: both'></p>")
   json_file = video_file.replace(".mp4", ".json")


   json_data= load_json_file(json_file)
   object_info = object_info_table(json_data)
   meteor_info = meteor_info_table(video_file, json_data)
   if meteor_info is not None:
      print(meteor_info)
   

   if "hd_trim" in json_data:
      hd_trim = json_data['hd_trim']
      hd_crop = json_data['hd_crop_file']
   else:
      hd_trim = None
      hd_crop = None
   if hd_trim is not None:
      print("<h2>HD Files</h2>")
      if "meteors" not in hd_trim:
         el = hd_trim.split("/")
         hd_trim = meteor_dir + el[-1]
         el = hd_crop.split("/")
         hd_crop= meteor_dir + el[-1]

      hd_trim_stacked = hd_trim.replace(".mp4", "-stacked.png")
      hd_crop_stacked = hd_crop.replace(".mp4", "-stacked.png")
      hd_trim_stacked_tn = hd_trim.replace(".mp4", "-stacked-tn.png")
      hd_crop_stacked_tn = hd_crop.replace(".mp4", "-stacked-tn.png")
      print("<figure><a href=" + hd_trim + "><img width=300 src=" + hd_trim_stacked_tn + "></a><figcaption>HD Video</figcaption></figure>")
      print("<figure><a href=" + hd_crop+ "><img src=" + hd_crop_stacked + "></a><figcaption>HD Crop Video</figcaption></figure><div style='clear: both'></div>")
      print("<a href=" + hd_trim_stacked + ">HD Stacked Image</a> - ")
      print("<a href=" + hd_crop_stacked + ">HD Cropped Image</a><br>")

   print(object_info)


def get_obj_test_score(object):
   print("YO")

def default_tests():
   tests = {}
   tests['score'] = 0 
   tests['Moving'] = 0
   tests['Distance'] = 0
   tests['Hist Len']  = 0
   tests['Elp Frames'] = 0
   tests['AVL'] = 0
   tests['Big CNT'] = 0
   tests['Big/CM'] = 0
   tests['CM/Gaps'] = 0 
   tests['CM To Hist'] = 0
   tests['PX/Frame'] = 0
   tests['Moving'] = 0
   tests['Dupe Px'] = 0
   tests['Line Fit'] = 0
   tests['Peaks'] = 0
   return(tests)

def object_info_table(json_data):
   if "sd_objects" in json_data:
      sd_objects = json_data['sd_objects']
   else:
      sd_objects = json_data
   stab,sr,sc,et,er,ec = div_table_vars()
   oit = "<h3>Object Details</h3>" + stab
   oit = oit + sr + sc + "ID" + ec + sc + "Meteor" + ec + sc + "Score" + ec + sc + "Moving" + ec + sc + "Dist" + ec + sc + "Len" + ec + sc + "Elp Frms" + ec + sc + "AVL" + ec + sc + "Trailer" + ec + sc + "Big CNT" + ec + sc + "Big/CM" + ec + sc + "CM/Gaps" + ec + sc + "CM/Hist" + ec + sc + "PX/Frm" + ec + sc + "Dupe PX" + ec + sc +"Noise" + ec + sc + "Line Fit" + ec + sc + "Peaks" + ec + er  
   for obj in sd_objects:
      tests= default_tests()
      tests['score']  = 0
      test_detail = stab
      meteor_yn = obj['meteor']
      if meteor_yn == 1:
         meteor_yn = "Y"
      else:
         meteor_yn = "N"
    
      for test in obj['test_results']:
         name, result, descr = test
         tests[name] = result 
         test_detail = test_detail + sr + sc + str(name) + ec + sc + str(result) + ec + sc + str(descr) + ec + er
         tests['score']  = tests['score'] + int(result)
      test_detail = test_detail + et 
      total_tests = len(obj['test_results'])

      oit = oit + sr + sc + "<a href=\"javascript:show_hide_div('" + str(obj['oid']) + "')\">" + str(obj['oid']) + "</a>" + ec
      oit = oit +  sc + str(meteor_yn) + ec + sc + str(tests['score']) + ec + sc + str(tests['Moving']) + ec + sc + str(tests['Distance']) + ec + sc + str(tests['Hist Len']) + ec + sc + str(tests['Elp Frames']) + ec + sc + str(tests['AVL']) + ec + sc + str(tests['Trailer']) + ec + sc + str(tests['Big CNT']) + ec + sc + str(tests['Big/CM']) + ec + sc + str(tests['CM/Gaps']) + ec + sc + str(tests['CM To Hist']) + ec + sc + str(tests['PX/Frame']) + ec + sc + str(tests['Moving']) + ec + sc + str(tests['Dupe Px']) + ec + sc + str(tests['Line Fit']) + ec + sc + str(tests['Peaks']) + ec + er  
      oit = oit + sr + "<div id=\"" + str(obj['oid']) + "\" style=\"display: none; width: 100%\">" + test_detail + "</div>" + er
   oit = oit + et
   return(oit)
   return(oit)

def meteor_info_table(video_file,json_data):
   if "meteor_data" not in json_data:
      mi = "This meteor has not been reduce yet. "
      mi = mi + "<a href=webUI.py?cmd=reduce&video_file=" + video_file + ">Reduce Meteor Now</a>"
   return(mi) 

def div_table_vars():
   start_table = """
      <div class="divTable" style="border: 1px solid #000;" >
      <div class="divTableBody">
   """
   start_row = """
      <div class="divTableRow">
   """
   start_cell = """
      <div class="divTableCell">
   """
   end_table = "</div></div>"
   end_row = "</div>"
   end_cell= "</div>"
   return(start_table, start_row, start_cell, end_table, end_row, end_cell)
  
def stack_file_from_video(video_file):
   el = video_file.split("/")
   fn = el[-1]
   base_dir = video_file.replace(fn, "")
   stack_file = base_dir + "images/" + fn 
   stack_file = stack_file.replace(".mp4", "-stacked.png")
   return(stack_file)


def do_jquery():



#$body = $("body");

#$(document).bind({
#    ajaxStart: function() {
#       $("#waiting").show();
#       //$body.addClass("waiting");
#       console.log("starting ajax")
#    },
#    ajaxStop: function() {
#       $("#waiting").hide();
#       //$body.removeClass("waiting");
#       console.log("ending ajax")
#    }
#});

#<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>
#<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.contextMenu.min.css">
#<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.contextMenu.min.js"></script>
#<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery-contextmenu/2.7.1/jquery.ui.position.js"></script>

   jq = """
<script>



</script>


   """

                #"confirm": {name: "Confirm Meteor"},
                #"satellite": {name: "Mark as Satellite"},
                #"quit": {name: "Quit", icon: function(){
                    #return 'context-menu-icon context-menu-icon-quit';


   return(jq)

def print_css():
   print ("""
<!--
      <script>
         function goto(var1,var2, type) {
            if (type == "calib") {
               url_str = "webUI.py?cmd=calibration&cams_id=" + var1
               window.location.href=url_str
            }
            if (type == "reduce") {
            
               url_str = "webUI.py?cmd=reduce&video_file=" + var1 + "&cal_params_file=" + var2
               window.location.href=url_str
            }
         }
      </script>
-->
      <style> 


.divTable{
   display: table;
}
.divTableRow {
   display: table-row;
}
.divTableHeading {
   background-color: #EEE;
   display: table-header-group;
}
.divTableCell, .divTableHead {
   border: 1px solid #999999;
   display: table-cell;
   padding: 3px 10px;
        vertical-align: top;
}
.divTableCellDetect {
   border: 1px solid #ff0000;
   display: table-cell;
   padding: 3px 10px;
        vertical-align: top;
}
.divTableHeading {
   background-color: #EEE;
   display: table-header-group;
   font-weight: bold;
}
.divTableFoot {
   background-color: #EEE;
   display: table-footer-group;
   font-weight: bold;
}
.divTableBody {
   display: table-row-group;
}



         figure {
            text-align: center;
            font-size: smaller;
            float: left;
            padding: 0.1em;
            margin: 0.1em;
         }
         img.reduced {
            border: thin ff9900 solid;
            background-color: ff9900;
            margin: 0.1em;
            padding: 0.1em;
         }

         img.meteor {
            border: thin red solid;
            background-color: red;
            margin: 0.1em;
            padding: 0.1em;
         }
         img.fail {
            border: thin silver solid;
            background-color: orange ;
            margin: 0.3em;
            padding: 0.3em;
         }
         img.none {
            width: 300px;
            margin: 0.1em;
            padding: 0.1em;
            border: thin silver solid;
         }
         img.norm {
            border: thin silver solid;
            margin: 0.1em;
            padding: 0.1em;
         }
      </style>
   """)


def browse_day(day,cams_id,json_conf,form):
   #cgitb.enable()
   sun = form.getvalue("sun")
   hour = form.getvalue("hour")
   detect = form.getvalue("detect")
   day_files = get_day_files(day,cams_id,json_conf, sun, hour,detect)
 
   cc = 0
   all_files = []
   for base_file in sorted(day_files,reverse=True):
      all_files.append(base_file)
 
   #Get CAM IDs from drop_dow & Javascript
   all_cam_ids = get_the_cam_ids() 

   print("<div class='h1_holder d-flex justify-content-between'><h1><span class='h'><span id='meteor_count'>"+format(len(day_files))+"</span> detections</span> on")
   print("<input value='"+str(day.replace("_", "/"))+"' type='text' data-display-format='YYYY/MM/DD' data-action='reload' data-url-param='limit_day' data-send-format='YYYY_MM_DD' class='datepicker form-control'>")
   print(" by Cam #")
   
   #Cam selector
   print("<select id='cam_id' name='cam_id' data-url-param='cams_id' class='cam_picker'>")
   for ccam_id in all_cam_ids:
      if ccam_id == cams_id:
            sel='selected'
      else:
            sel=''
      print('<option value="'+ccam_id+'" '+sel+'>'+ccam_id+'</option>')
   print("</select>") 
   print("<select id='sun' class='cam_picker' data-url-param='sun' ><option value=0>DAY/NIGHT</option><option value=0>NIGHT</option><option value=1>DAY</select></h1>")
   
   print("<div class='d-flex'><!--<a class='btn btn-primary mr-3' href='/pycgi/webUI.py?cmd=video_tools' style='text-transform: initial;'><span class='icon-youtube'></span> Generate Timelapse Video</a>--><button class='btn btn-primary' id='play_anim_thumb' style='text-transform: initial;'><span class='icon-youtube'></span> Timelapse Preview</button></div></div>") 
  
   print("<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>")
   print("<div class='gallery gal-resize row text-center text-lg-left '>")

   #For timelapse anim
   print("<input type='hidden' name='cur_date' value='"+str(day)+"'/>")


   for base_file in sorted(day_files,reverse=True):

      if cc + 1 < len(day_files) - 2:
         next_stack_file = all_files[cc+1]
      else:
         next_stack_file = all_files[cc] 
      
      video_file = base_file + ".mp4"
      stack_file = stack_file_from_video(video_file)
      stack_file_tn = stack_file.replace(".png", "-tn.png") 

      if day_files[base_file] == 'meteor':
         htclass = "meteor"
      elif day_files[base_file] == 'failed':
         htclass = "fail"
      else:
         htclass = "none"
      el = base_file.split("/")
      base_js_name = el[-1].split('_')

      html_out =  "<div class='preview col-lg-2 col-md-3 "+ htclass +"'>"
      html_out +=  "<a class='mtt mb-3' href='webUI.py?cmd=examine_min&video_file=" + video_file + "&next_stack_file=" + next_stack_file  + "' title='Examine'>"
      html_out +=  "<img class='ns lz' src='" + stack_file_tn + "'>"
      html_out +=  "<span>"+base_js_name[0] +"/" +base_js_name[1]+"/" +base_js_name[2] + " " +  base_js_name[3]+ ":" +  base_js_name[4]+ ":" +  base_js_name[5] +"</span>"
      html_out +=  "</a></div>"
      print(html_out) 
      cc = cc + 1

   print('</div></div>')

def browse_detects(day,type,json_conf,form):
   cgitb.enable()

   cur_page  = form.getvalue('p')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   
   proc_dir = json_conf['site']['proc_dir']
   failed_files, meteor_files, pending_files,min_files = get_day_stats(day,proc_dir + day + "/", json_conf)

   show_day = day.replace("_", "/")

   title = "<div class='h1_holder d-flex justify-content-between'>"
  
   if type == 'meteor':
      files = meteor_files
      title = title + "<h1>" + format(len(files)) + " Meteor Detections on "+format(show_day)+"</h1>" 
   else:
      files = failed_files
      title = title + "<h1>" + format(len(files)) + " Non-Meteor Detections on " + format(show_day)+"</h1>" 
 
   html_out = "<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>" 
   html_out +=  "<div class='gallery gal-resize row text-center text-lg-left'>"

   files = sorted(files, reverse=True)
   _from = (cur_page-1) * NUMBER_OF_METEOR_PER_PAGE
   _to = _from + NUMBER_OF_METEOR_PER_PAGE

   # slice the array for pagination
   real_files   = files[_from:_to] 

   for file in real_files:
      stack_img = file.replace(".mp4", "-stacked.png")
      stack_obj_img = file.replace(".mp4", "-stacked-obj.png")
      el = stack_img.split("/")
      short_name = get_meteor_date(file) 
      base_js_name=short_name.replace("_", "")

      html_out +=  "<div class='preview col-lg-2 col-md-3 mb-4 fail'>"
      html_out +=  "<a class='mtt' href='webUI.py?cmd=examine&video_file=" + file +"'  title='Examine'>"
      html_out +=  "<img alt='" + short_name + "' class='img-fluid ns lz' src='" + stack_img + "'>"
      html_out +=  "<span>" + short_name + "</span></a></div>"     
       
   
   html_out +=  "</div>"
   pagination =  get_pagination(cur_page,len(files),"/pycgi/webUI.py?cmd=browse_detects&type="+type+"&day="+day,NUMBER_OF_METEOR_PER_PAGE)
   
   print( title + "<div class='page_h'>Page  " + format(cur_page) + "/" +  format(pagination[2]) + "</div></div>")
   print(html_out)
   print(pagination[0])
   print("</div>")



def main_page(json_conf,form):

   cgitb.enable()   
   cur_page  = form.getvalue('p')
   end_day   = form.getvalue('limit_day')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   if(end_day is not None):
      end_day_date = datetime.strptime(end_day,"%Y_%m_%d")
   
   days = sorted(get_proc_days(json_conf),reverse=True)
   if len(days) <= 2:
      print("No data has been collected yet. ")
      exit() 
   # We remove the days we don't care about to speed up the page
   if(end_day is not None):
         for idx, d in enumerate(days):
            test_ends_with_int = re.search(r'\d+$', d)
            
            if test_ends_with_int is not None:
                  ddd = get_date_from_file(d) 


   json_file = json_conf['site']['proc_dir'] + "json/" + "main-index.json"
   stats_data = load_json_file(json_file)
  
   detections = sorted(stats_data,reverse=True)
   detections_form = NUMBER_OF_DAYS_PER_PAGE*cur_page
   total_number_page = math.ceil(len(detections) / NUMBER_OF_DAYS_PER_PAGE)
   counter = 0

   to_display = ""
   first_day = ""
   real_detections = []
   real_detections_to_display = []
   

   # Need a fist loop to cleanup (big waist of time & resources here)
   for idx, day in enumerate(detections): 
         
      #Default day if not defined
      if(end_day is None and idx==0):
         now =  datetime.now()
         end_day_date = now
         end_day = end_day_date.strftime('%Y/%m/%d')

      day_str = day
      day_dir = json_conf['site']['proc_dir'] + day + "/" 

      try:
         # Use to compare with end
         day_cur_date = datetime.strptime(day_str,"%Y_%m_%d")
      
         if "meteor" not in day_dir and "daytime" not in day_dir and "json" not in day_dir and "trash" not in day_dir:
            real_detections.append(day) 

            if(end_day_date >= day_cur_date):
                  real_detections_to_display.append(day)
      except:
         # The day_str is not a day (but a year for instance)
         x=0
  
   all_real_detections = real_detections

   day_start = (cur_page-1) * NUMBER_OF_DAYS_PER_PAGE
   day_end   = day_start + NUMBER_OF_DAYS_PER_PAGE
   
   # slice the array to just the values you want.
   real_detections = all_real_detections[day_start:day_end] 
   real_detections_to_display_d = real_detections_to_display[day_start:day_end] 
   
   for idx, day in enumerate(real_detections_to_display_d): 
      day_str = day
      day_dir = json_conf['site']['proc_dir'] + day + "/" 
      failed_files = stats_data[day]['failed_files']
      meteor_files = stats_data[day]['meteor_files']
      pending_files = stats_data[day]['pending_files']

      html_row, day_x = make_day_preview(day_dir,stats_data[day], json_conf)
      day_str = day.replace("_", "/")

      to_display  = to_display + "<div class='h2_holder  d-flex justify-content-between'>"
      to_display  = to_display + "<h2>"+day_str+" - <a class='btn btn-primary' href=webUI.py?cmd=meteors&limit_day=" + day + ">" + str(meteor_files) + " Meteors </a></h2>"
      to_display  = to_display + "<p><a href=webUI.py?cmd=browse_detects&type=failed&day=" + day + ">" + str(failed_files) + " Non-Meteors </a>"

      if(pending_files>0):
            to_display  = to_display + " - " + str(pending_files) + " Files Pending</a>"

      to_display  = to_display +"</div><div class='gallery gal-resize row text-center text-lg-left mb-5 mr-5 ml-5'>"
      to_display  = to_display + html_row
      to_display = to_display + "</div>"
      counter = counter + 1
 
   pagination =  get_pagination(cur_page,len(all_real_detections),"/pycgi/webUI.py?cmd=home",NUMBER_OF_DAYS_PER_PAGE)

   header_out = "<div class='h1_holder d-flex justify-content-between'><h1>Review Stacks by Day" 
 
   if end_day is None:
      end_day = ""
 
   header_out = header_out + "<input value='"+ end_day +"' type='text' data-display-format='YYYY/MM/DD'  data-action='reload' data-url-param='limit_day' data-send-format='YYYY_MM_DD' class='datepicker form-control'></h1>" 
   header_out = header_out + "<div class='page_h'>Page  " + format(cur_page) + "/" +  format(pagination[2]) + "</div></div>" 

   print(header_out)
   print("<div id='main_container' class='container-fluid h-100 mt-4 lg-l'>")
   print(to_display)
   print(pagination[0])
   print("</div>")

def rad_calc(json_conf, form):
   event_date = form.getvalue("event_date")
   start_lon = form.getvalue("start_lon")
   if start_lon is not None:
      start_lon = float(form.getvalue("start_lon"))
      start_lat = float(form.getvalue("start_lat"))
      start_alt = float(form.getvalue("start_alt"))
      end_lon = float(form.getvalue("end_lon"))
      end_lat = float(form.getvalue("end_lat"))
      end_alt = float(form.getvalue("end_alt"))
      velocity= float(form.getvalue("velocity"))
   print("<h1>Meteor Orbit Calculator</h1>" )
   stab,sr,sc,et,er,ec = div_table_vars()

   if start_lon is None:
      print("""
          <form>
            Event Date: <input type=text name=event_date VALUE=YYYY-MM-DD HH:MM:SS> UTC<BR>
            Start Lat: <input type=text name=start_lat><BR>
            Start Lon: <input type=text name=start_lon><BR>
            Start Alt: <input type=text name=start_alt><BR>
            End Lat: <input type=text name=end_lat><BR>
            End Lon: <input type=text name=end_lon><BR>
            End Alt: <input type=text name=end_alt><BR>
            Velocity: <input type=text name=velocity><BR>
            <input type=submit name=submit value="Submit">
            <input type=hidden name=cmd value="rad_calc">
          </form>
      """)
   else:
      arg_date, arg_time = event_date.split(" ")

      rad_rah,rad_dech,rad_az,rad_el,track_dist,entry_angle = calc_radiant(end_lon,end_lat,end_alt,start_lon,start_lat,start_alt, arg_date, arg_time)
      rad_rah = str(rad_rah).replace(":", " ")
      rad_dech = str(rad_dech).replace(":", " ")
      ra,dec = HMS2deg(str(rad_rah),str(rad_dech))

      print("<h3>Input Data</h3>")
      print(stab)
      print(sr + sc + "Event Date" + ec +sc +str(event_date) + ec + er)
      print(sr + sc + "Start Point" + ec + sc + str(start_lon) + "," + str(start_lat) + "," + str(start_alt) + ec + er)
      print(sr + sc + "End Point" + ec + sc + str(end_lon) + "," + str(end_lat) + "," + str(end_alt) + ec + er)
      print(sr + sc + "Velocity" + ec + sc + str(velocity) + ec + er)
      print(et)

      print("<h3>Preprocess Input Data and get ready for Orbit</h3>")
      print("<h3>Determine Radiant Az, El, RA, Dec</h3>")
      #print("<h4>Step 1 - Determine 0KM and 80KM altitude end and start points</h4>")
      #print(stab)
      #print(sr + sc + "0KM Point" + ec + sc + str(zero_lon) + "," + str(zero_lat) + "," +  str(0) + ec + er)
      #print(sr + sc + "80KM Point" + ec + sc + str(hund_lon) + "," + str(hund_lat) + "," +  str(80) + ec + er)
      #print(et)
      print("<h4>Step 2 - Determine track distance and entry angle</h4>")
      print("<h5>Step 2a - Use haversine between end and start lat,lon,alt points to determine track ground length and radiant azimuth from the 0KM point</h5>")
      print(stab)
      print(sr + sc + "Track Distance" + ec + sc + str(track_dist) + ec + er)
      print(sr + sc + "Radiant AZ" + ec + sc + str(rad_az) + ec + er)
      print(et)
      print("<h5>Step 2b - To determine entry angle. Use pythagorian theorum to compute ground track distance between 0km and 80km longitude and latitude points. </h5>")
      print(stab)
      print(sr + sc + "Entry Angle (Radiant Elevation)" + ec + sc + str(entry_angle) + ec + er)
      print(et)

      print("<h4>Step 3 Convert Az,El to RA,Dec using pyehem and HMS2Deg</h4>")
      print(stab)
      print(sr + sc + "Radiant RA (HMS)" + str(rad_rah) + ec + er)
      print(sr + sc + "Radiant Dec (DMS)" + str(rad_dech) + ec + er)
      print(sr + sc + "Radiant RA " + str(ra) + ec + er)
      print(sr + sc + "Radiant Dec " + str(dec) + ec + er)
      print(et)

      # run orbit
      metorb = load_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json")
      event_start_time = event_date.replace(" ", "T")
      metorb['orbit_vars']['meteor_input']['start_time'] = event_start_time
      metorb['orbit_vars']['meteor_input']['end_point'] = [end_lon,end_lat,end_alt]
      metorb['orbit_vars']['meteor_input']['rad_az'] = rad_az
      metorb['orbit_vars']['meteor_input']['rad_el'] = entry_angle 
      metorb['orbit_vars']['meteor_input']['velocity'] = velocity

      save_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json",metorb)
      os.system("cd /home/ams/amscams/pythonv2/; ./mikeOrb.py > /dev/null")  
      time.sleep(1)
      new_metorb = load_json_file("/home/ams/amscams/pythonv2/orbits/orbit-vars.json")

      metorb = new_metorb
      #parsed = json.dumps(new_metorb)
      #parsed = json.loads(new_parsed)
      print("<h1>Orbit Calculation Steps</h1>")
      print("<h2>Step 1 : Determine Observed Radiant Sidereal Time, Hour Angle, RA,Dec & J2000 RA & Dec</h2>")
      print("<h2>Step 1a : Calculate JD from input UTC date</h2>")
      print(stab)
      print(sr + sc +"Event Time UTC " + ec + sc + str(metorb['orbit_vars']['date_vars']['event_time_utc']) + ec + er)
      print(sr + sc +"Julian Date For Time of Event" + ec + sc + str(metorb['orbit_vars']['date_vars']['jd_at_t']) + ec + er)
      print(et)
      print("<h2>Step 1b : Calculate T, Theta Rad & Maal3650 from the event JD </h2>")
      print(stab)
      print(sr + sc + "T" + ec + sc + str(metorb['orbit_vars']['date_vars']['T']) + ec + sc + "(JD-2451545)/36525" + ec +  er)
      theta_rad_formula = "(280.46061837+360.98564736629*(JD_AT_T-2451545)+((0.000387933*(T^2))-(T^3/38710000)))"
      print(sr + sc + "theta_rad" + ec + sc + str(metorb['orbit_vars']['date_vars']['theta_rad']) + ec + sc + theta_rad_formula + ec + er)

      print(sr + sc + "maal_360" + ec + sc + str(metorb['orbit_vars']['date_vars']['maal_360']) + ec + sc + "theta_rad/360" + ec +er)
      print(et)
      print("<h2>Step 1c : Calculate Greenwich Sidreal time & Local Sidereal Time</h2>")
      greenwich_formula = "theta_rad - (maal_360 * 360)"
      print(sr + sc + "Greenwich Sidereal" + ec + sc + str(metorb['orbit_vars']['date_vars']['greenwich_sidereal_time']) + ec + sc + greenwich_formula + ec +er)
      local_sr_formula = "impact longitude + greenwhich_sidereal"
      print(sr + sc + "Impact Point Sidereal " + ec + sc + str(metorb['orbit_vars']['date_vars']['local_sidereal_time_deg']) + ec + sc + local_sr_formula + ec +er)
      print("<h2>Step 1d : Calculate Hour Angle </h2>")
      print(stab)
      print(sr + sc + "Hour Angle " + ec + sc + str(metorb['orbit_vars']['date_vars']['local_sidereal_hour_angle']) + ec + sc + "" + ec +er)
      print(et)
      print("<h2>Step 1e : Calc Radiant RA/DEC</h2>")
      print(stab)
      print(sr + sc + "Observed Radiant RA " + ec + sc + str(metorb['orbit_vars']['radiants']['observed_radiant_position']['rad_ra']) + ec + sc + "" + ec +er)
      print(sr + sc + "Observed Radiant Dec " + ec + sc + str(metorb['orbit_vars']['radiants']['observed_radiant_position']['rad_dec']) + ec + sc + "" + ec +er)
      print(et)
      print("<h2>Step 1f : Calc Radiant J2000 RA/DEC</h2>")
      print(stab)
      print(sr + sc + "J2000 Observed Radiant RA " + ec + sc + str(metorb['orbit_vars']['radiants']['observed_radiant_position']['rad_raJ2']) + ec + sc + "" + ec +er)
      print(sr + sc + "J2000 Observed Radiant Dec " + ec + sc + str(metorb['orbit_vars']['radiants']['observed_radiant_position']['rad_decJ2']) + ec + sc + "" + ec +er)
      print(et)
      print("<h2>Part 2 : Convert Observed Radiant Position Geocentric Radiant Position</h2>")
      print("<h2>Step 1 : Compute Zenith Attraction, apparent radiant altitude, true radiant altitude</h2>")
      print("<h2>Step 2 : Compute Geocentric Hour Angle</h2>")
      print("<PRE><font color=white>")
      print(json.dumps( new_metorb, indent=4))
