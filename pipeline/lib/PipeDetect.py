''' 

   Pipeline Detection Routines - functions for detecting

'''
import math
import scipy.optimize
from lib.UIJavaScript import *
import glob
from datetime import datetime as dt
import datetime
#import math
import os
from lib.FFFuncs import imgs_to_vid
from lib.PipeAutoCal import fn_dir, get_cal_files, get_image_stars, get_catalog_stars, pair_stars, update_center_radec, cat_star_report, minimize_fov, XYtoRADec
from lib.PipeVideo import ffmpeg_splice, find_hd_file, load_frames_fast, find_crop_size, ffprobe
from lib.PipeUtil import load_json_file, save_json_file, cfe, get_masks, convert_filename_to_date_cam, buffered_start_end, get_masks, compute_intensity , bound_cnt, day_or_night
from lib.DEFAULTS import *
from lib.PipeMeteorTests import big_cnt_test, calc_line_segments, calc_dist, unq_points, analyze_intensity, calc_obj_dist, meteor_direction, meteor_direction_test, check_pt_in_mask, filter_bad_objects, obj_cm, meteor_dir_test, ang_dist_vel, gap_test
from lib.PipeImage import stack_frames

import numpy as np
import cv2

json_conf = load_json_file(AMS_HOME + "/conf/as6.json")


def make_meteor_index_all(json_conf):
   amsid = json_conf['site']['ams_id']
   mr_dir = "/mnt/ams2/meteors/"
   mdirs = []
   all_meteors = []
   files = glob.glob(mr_dir + "*")
   for mdir in files:
      #print(mdir)
      day, dir = fn_dir(mdir)
      if cfe(mdir, 1) == 1:
         mi_file = mdir + "/" + day + "-" + amsid + ".meteors"
         print(mi_file)
         mi_file, mdata = make_meteor_index_day(day, json_conf)
         for data in mdata:
            print("ADDING:", day, len(mdata))
            all_meteors.append(data)
   amf = mr_dir + amsid + "-meteors.info"    
   all_meteors = sorted(all_meteors, key=lambda x: (x[0]), reverse=True)
   save_json_file(amf, all_meteors)
   print("Saved:", amf)

def make_meteor_index_day(day, json_conf):
   amsid = json_conf['site']['ams_id']
   mdir = "/mnt/ams2/meteors/" + day + "/"
   files = glob.glob(mdir + "*.json")
   meteors = []
   mi = {}
   meteor_data = []
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf and "star" not in mf and "import" not in mf and "archive" not in mf:
         meteors.append(mf)

   for meteor in meteors:
      mi[meteor] = {}
      fn, dir = fn_dir(meteor)
      el = fn.split("-")
      print("FN:", fn) 
      ddd = el[0].split("_")
      if len(ddd) == 8:
         y,m,d,h,mm,s,ms,cam = ddd
      else:
         print("BAD FILE:", ddd, len(ddd))
         continue
      start_time = y + "-" + m + "-" + d + " " + h + ":" + m + ":" + s
      mj = load_json_file(meteor)
      if "best_meteor" in mj:
         reduced = 1
         print(mj['best_meteor'])
         if "dt" in mj['best_meteor']:
            start_time = str(mj['best_meteor']['dt'][0])
         dur = str(len(mj['best_meteor']['ofns']) / 25)[0:4]
         report = mj['best_meteor']['report']
         ang_vel = report['ang_vel']
         ang_dist = report['ang_dist']
      else:
         reduced = 0
         dur = 0
         ang_vel = 0
         ang_dist = 0
      mi[meteor]['start_time'] = start_time
      mi[meteor]['dur'] = dur
      mi[meteor]['ang_vel'] = ang_vel
      mi[meteor]['ang_dist'] = ang_dist
      meteor_data.append((meteor, reduced, start_time, dur, ang_vel, ang_dist))

   mid = sorted(meteor_data, key=lambda x: (x[0]), reverse=True)
   mi_file = mdir + day + "-" + amsid + ".meteors"
   save_json_file(mi_file, mid)
   print("saved", mi_file)
   return(mi_file, mid)
   

def confirm_meteors(date ):
   meteor_dir = "/mnt/ams2/meteors/" + date + "/"
   trash_dir = "/mnt/ams2/trash/" + date + "/"
   files = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   meteors = []
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf:
         meteors.append(mf)
   for meteor in meteors:
      meteor_vid = meteor.replace(".json", ".mp4")
      mj = load_json_file(meteor)
      if "rejected" in mj or "best_meteor" in mj:
         print("ALREADY DONE.")
      else:
         cmd = "./Process.py fireball " + meteor_vid
         os.system(cmd)
         print(cmd)
#      exit()

def reject_meteors(date, jsfs):
   meteor_dir = "/mnt/ams2/meteors/" + date + "/"
   trash_dir = "/mnt/ams2/trash/" + date + "/"
   files = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   meteors = []
   for mf in files:
      if "reduced" not in mf and "stars" not in mf and "man" not in mf:
         meteors.append(mf)

   rejects = 0
   rej_html = """
      <style>
         .detect_image {
            float :left; 
            padding: 25px 25px 25px 25px;
            background-color: #cccccc;
         }
         .objects_div {
            float :left; 
            padding: 25px 25px 25px 25px;
            background-color: #cccccc;
            font-family: "Lucida Console", Courier, monospace;
            font-size:1vw;
         }
      </style>
   """
   rejected_meteors = []
   rej_html += JS_SHOW_HIDE
   total_detects = len(meteors)
   for file in sorted(meteors):
      fn, dir = fn_dir(file) 
      base_fn = fn.replace(".json", "")
      sd_video_file = file.replace(".json", ".mp4")
      (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      sun_status, sun_az, sun_el = day_or_night(f_date_str, json_conf,1)
      if -10 < float(sun_el) < 0:
         if float(sun_az) > 180:
            sun_status = "dusk"
         else:
            sun_status = "dawn"

      mj = load_json_file(file)
      #print(mj['sd_objects'])
      #print(file, sun_status, sun_az, sun_el)
      #if "meteor_data" not in mj :
      #if (sun_status == "dawn" or sun_status == "dusk"):
      if "meteor_data" not in mj:
      #if True:
         # detect without the mask
         best_meteor,sd_stack_img,bad_objs,cp = fireball(sd_video_file, json_conf, 1)
         mj['meteor_data'] = {}
         mj['meteor_data']['sd_meteor'] = best_meteor
         mj['meteor_data']['cal_params'] = cp
         mj['meteor_data']['bad_objs'] = bad_objs
         save_json_file(file, mj)
         if best_meteor is not None:
            sd_stack_img = cv2.resize(sd_stack_img, (640, 360))
            #cv2.imshow('pepe2', sd_stack_img)
            #cv2.waitKey(180)
         else:
            sf = sd_video_file.replace(".mp4", "-stacked.jpg")
            if cfe(sf) == 0:
               sf = sd_video_file.replace(".mp4", "stacked.png")
            if cfe(sf) == 1:
               sd_stack_img = cv2.imread(sf)
               sd_stack_img = cv2.resize(sd_stack_img, (1280, 720))
               #cv2.imshow('pepe2', sd_stack_img)
               #cv2.waitKey(180)
      # DUSK / DAWN REJECT CHECK -- MAKE SURE IT IS NOT A BIRD BY CHECKING INTENSITY VALS
      #if sun_status == "dawn" or sun_status == "dusk" or sun_status == "day":
      if (mj['meteor_data']['sd_meteor']) is None:
         print(mj['meteor_data']['sd_meteor'], mj['sd_stack'], mj['sd_video_file'])
         rejected_meteors.append(mj)
         rejects += 1 

         rej_html += "<div id='row_container'><div class='detect_image'><a href='" + mj['sd_video_file'] + "'><img width=640 height=320 src='" + mj['sd_stack'] + "'></a></div><div class='objects_div'>" 
         tot_obj = 0
         for obj in mj['meteor_data']['bad_objs']:
            if mj['meteor_data']['bad_objs'][obj]['report']['class'] == 'star' or mj['meteor_data']['bad_objs'][obj]['report']['unq_points'] < 3:
               continue 
            div_id = base_fn + "-" + str(obj)
            if mj['meteor_data']['bad_objs'][obj]['report']['meteor'] == 1:
               met_desc = "METEOR"
            else:
               met_desc = "NON METEOR"

            fn_desc = len(mj['meteor_data']['bad_objs'][obj]['ofns'])
            bi_desc = ""
            for item in mj['meteor_data']['bad_objs'][obj]['report']['bad_items']:
               if bi_desc != "":
                  bi_desc += ","
               print("ITEM:", item)
               its = item.split(".")
               bi_desc += its[0]
            rej_html += "<a href=\"javascript: show_hide('" + div_id + "')\">Object:" + str(obj)+ "</a> - " + mj['meteor_data']['bad_objs'][obj]['report']['class'].upper() + " " + met_desc + " " + str(fn_desc) + " frames " + bi_desc
            
            rej_html += "<br>"
            rej_html += "<div id='" + div_id + "' style='display: none' >"
            rej_html += "<ul>"
            rej_html += "<li> fns" + str(mj['meteor_data']['bad_objs'][obj]['ofns'])  
            rej_html += "<li> xs" + str(mj['meteor_data']['bad_objs'][obj]['oxs'])  
            rej_html += "<li> ys" + str(mj['meteor_data']['bad_objs'][obj]['oys'])  
            rej_html += "<li> ws" + str(mj['meteor_data']['bad_objs'][obj]['ohs'])  
            rej_html += "<li> hs" + str(mj['meteor_data']['bad_objs'][obj]['ows'])  
            rej_html += "<li> is" + str(mj['meteor_data']['bad_objs'][obj]['oint'])  
            for key in mj['meteor_data']['bad_objs'][obj]['report']:
               rej_html += "<li>" + str(key) + " " + str(mj['meteor_data']['bad_objs'][obj]['report'][key]) + "</li>"
            rej_html += "</ul>"
            rej_html += "</li></div>"
            tot_obj += 1 
         rej_html += "</div><div style='clear:both'></div></div>"
   print(meteor_dir + "/rejected.html")
   fp = open(meteor_dir + "/rejected.html", "w")
   fp.write(rej_html)
   fp.close()
   print(total_detects, rejects)
  
   if len(rejected_meteors) > 0:
      if cfe(trash_dir, 1) == 0:
         os.makedirs(trash_dir)
   for mj in rejected_meteors:
      base_sd_fn, xx = fn_dir(mj['sd_video_file'])
      base_hd_fn, xx = fn_dir(mj['hd_video_file'])
      base_hd_trim_fn, xx = fn_dir(mj['hd_trim'])
      base_sd_fn = base_sd_fn.replace(".mp4", "")
      base_hd_fn = base_hd_fn.replace(".mp4", "")
      base_hd_trim_fn = base_hd_trim_fn.replace(".mp4", "")
      if "archive_file" in mj:
         base_archive = mj['archive_file'].replace(".json", "")
         cmd = "rm " + base_archive + "*" + " " + trash_dir
         print(cmd)
         os.system(cmd)

      cmd = "mv " + meteor_dir + base_sd_fn + "*" + " " + trash_dir
      print(cmd)
      os.system(cmd)
      cmd = "mv " + meteor_dir + base_hd_fn + "*" + " " + trash_dir
      print(cmd)
      os.system(cmd)
      cmd = "mv " + meteor_dir + base_hd_trim_fn + "*" + " " + trash_dir
      print(cmd)
      os.system(cmd)
   # move reject report to trash dir for this day
   os.system("mv " + meteor_dir + "rejected.html" + " " + trash_dir)
   make_trash_index(trash_dir)

   make_meteor_confirmed_index(meteor_dir)

def make_meteor_summary(mj, div_id):
   sum_html = "<div>"
   msd = mj['meteor_data']['sd_meteor'] 
   msbo = mj['meteor_data']['bad_objs'] 
   mcp = mj['meteor_data']['cal_params'] 
   ang_vel = msd['report']['ang_vel']
   ang_dist = msd['report']['ang_dist']
   tf = len(msd['ofns'])
   dur_sec = tf / 25
   sum_html +=  "<div class='info'>Ang Velocity: " + str(ang_vel)[0:4] + " </div>"
   sum_html +=  "<div class='info'>Ang Distance: " + str(ang_dist)[0:4] + " </div>"
   sum_html +=  "<div class='info'>Duration: " + str(dur_sec) + "s (" + str(tf) + "f)</div>"
   vdiv_id = div_id + "-vid"
   js_play_link = "\"javascript:SwapDivsWithClick('" + div_id + "', '" + vdiv_id + "',1)\""
   sum_html +=  "<div class='info'><a href=" + js_play_link + ">Play</a></div>"
   sum_html +=  "<div class='info'><a href=\"javascript:reject_meteor('" + mj['sd_video_file'] +"','" + div_id + "')\">Reject</a></div>"
   #sum_html +=  "<div class='info'>Frames : " + str(msd['ofns']) + "</div>"
   sum_html += "</div>"
   return(sum_html)

def make_final_meteor_vids(meteor_dir, mjf, msd, cp=None, frames=None, hd=0):
    tf = len(frames)
    tmf = len(msd['ofns'])
    mjfn, mdir = fn_dir(mjf)
    (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(mjf)
    orig_trim_num = int(get_trim_num(mjf))

    final_dir = meteor_dir + "final/"
    ff = msd['ofns'][0]
    if ff > 10:
       print("FIRST FRAME > 10 retrim!")
       frame_shift = 10 - ff  - 1
       new_frame_start = abs(frame_shift)
       new_frame_end = ff + abs(frame_shift) + tmf + 10 
       if new_frame_end > tf:
          new_frame_end = tf 
    else:
       print("FIRST < 10 no trim start! check end")
       frame_shift = 0
       new_frame_start = 0
       new_frame_end = msd['ofns'][-1] + 10 
       if new_frame_end >= tf + frame_shift:
          new_frame_end = tf - 1
    new_frames = frames[new_frame_start:new_frame_end]
    print("MJF:", mjf)

    print("NEW FRAMES:", len(new_frames), new_frame_start, new_frame_end)
    print("FRAME SHIFT:", frame_shift)
    print("OFNS:", msd['ofns'])

    if False:
       for i in range(0, len(msd['ofns'])):
          fn = msd['ofns'][i] + frame_shift
          frame = new_frames[fn].copy()

          x = msd['oxs'][i]
          y = msd['oys'][i]
          w = msd['ows'][i]
          h = msd['ohs'][i]
          cx = x + int(w/2)
          cy = y + int(h/2)


          cv2.circle(frame,(cx,cy), 3, (0,255,255), 1)
          cv2.rectangle(frame, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)
          
          cv2.imshow('pepe', frame)
          cv2.waitKey(30)
    new_trim_num = int(orig_trim_num) + abs(frame_shift)
    base_final_file = final_dir + fy + "_" + fmin + "_" + fd + "_" + fh + "_" + fm + "_" + fs + "000" + "-trim-" + str(new_trim_num) 
    msd['final_media'] = remaster_frames(final_dir, base_final_file, new_frames, 0)
    
    return(msd)

def remaster_frames(final_dir, base_final_file, frames, hd=0):
   bfn, bdir = fn_dir(base_final_file)
   tmp_dir = "/mnt/ams2/remaster/"
   if cfe(final_dir, 1) == 0:
      os.makedirs(final_dir)
   if cfe(tmp_dir, 1) == 0:
      os.makedirs(tmp_dir)
   cmd = "rm " + tmp_dir + "*.jpg"
   os.system(cmd)
   vid_360 = base_final_file + "-360p.mp4" 
   vid_180 = base_final_file + "-180p.mp4" 
   for i in range(0, len(frames)):
      frame = frames[i]
      if hd == 0:
         sd_360= cv2.resize(frame, (640, 360))
         sd_180= cv2.resize(frame, (320, 180))
         fc = "{:04d}".format(i)
         frame_file = tmp_dir + bfn + "-360p-" + fc + ".jpg"
         cv2.imwrite(frame_file, sd_360)
         frame_file = tmp_dir + bfn + "-180p-" + fc + ".jpg"
         cv2.imwrite(frame_file, sd_180)
         final_media = [vid_360, vid_180]
   imgs_to_vid (tmp_dir, vid_360, wild="360p", fps=25, crf=20, img_type= "jpg")
   imgs_to_vid (tmp_dir, vid_180, wild="180p", fps=25, crf=20, img_type= "jpg")
   cmd = "rm " + tmp_dir + "*.jpg"
   os.system(cmd)
   final_media = [vid_360, vid_180]
   return(final_media)
 

def make_meteor_confirmed_index(meteor_dir):
   el = meteor_dir.split("/")
   fn = el[-2]
   y,m,d = fn.split("_") 
   print(el)
   meteor_html = HTML_HEADER + "<head><style>" +  STYLE_IMAGE_OVERLAY + "</style>"
   meteor_html += "<script>" + JS_SWAP_DIV_WITH_CLICK + JS_REJECT_METEOR + "</script></head>"
   meteor_html += "<div class='main'>"
   meteor_html += """
      <div class='header'>
         <div class="header-title">Meteor Admin v2.0 </div>
         <div class="header-links">
         Home | Meteors | Calibration | Time Lapse | Config | Live
         </div>
         <div style="clear: both"></div>
         <div class="breadcrumbs"> 
            Meteors -> """ + y + """ -> """ + m + """ -> """ + d + """
         </div>
      </div>

   """

   meteor_html += "<div style='clear: both'></div>"
   jsons = glob.glob(meteor_dir + "*.json")
   for mjf in sorted(jsons):
      fn, dir = fn_dir(mjf)
      base = fn.replace(".json", "")
      tn =mjf.replace(".json", "-stacked-tn.jpg")
      vid = mjf.replace(".json", ".mp4")

      if cfe(tn) == 0:
         tn =mjf.replace(".json", "-stacked-tn.png")
      mj = load_json_file(mjf)
      vid = sorted(mj['meteor_data']['sd_meteor']['final_media'])[1]
      #print("FINAL:", mj['meteor_data']['sd_meteor']['final_media'])
      #exit()
      cdiv_id = base
      vdiv_id = base + "-vid"
      ddiv_id = base + "-del"
      ms = make_meteor_summary(mj,cdiv_id) 
      js_link = "\"javascript:SwapDivsWithClick('" + cdiv_id + "', '" + vdiv_id + "',1)\""
      js_undo_link = "\"javascript:SwapDivsWithClick('" + ddiv_id + "', '" + cdiv_id + "',0)\""
      vjs_link = "\"javascript:SwapDivsWithClick('" + vdiv_id + "', '" + cdiv_id + "',0)\""
      meteor_html += """

         <div class='container' id='""" + vdiv_id + """' style="display: None">
            <a href=""" + vjs_link + """>
            <video autoplay loop controls id='video_""" + cdiv_id + """'>
               <source src='""" + vid + """' type="video/mp4">
            </video> 
            </a>
         </div>
         <div class='container' id='""" + cdiv_id + """'>
            <a href=""" + js_link + """><img class='image' src='""" + tn + """'></a>
            <div class='middle'><div class='text'>""" + ms + """</div></div>
         </div>
         <div class='container' id='""" + ddiv_id + """' style="display: None">
            <a href=""" + js_link + """><img class='image-deactive' src='""" + tn + """'></a>
            <div class='deactive'><div class='text'><a href=""" + js_undo_link + """>undo</a></div></div>
         </div>
      """



   fp = open(meteor_dir + "/confirmed.html", "w")
   meteor_html += "</div><!--end main div-->"
   meteor_html += HTML_FOOTER
   fp.write(meteor_html)
   fp.close()
   print("Saved." + meteor_dir + "/confirmed.html")


def make_trash_index(trash_dir):
   el = trash_dir.split("/")
   fn = el[-2]
   print(el)
   trash = """
      <style>
         .detect_image {
            float :left; 
            padding: 25px 25px 25px 25px;
            background-color: #cccccc;
            font-family: "Lucida Console", Courier, monospace;
            font-size:1vw;
         }
         .h1 {
            font-family: "Lucida Console", Courier, monospace;
            font-size:1vw;
         }
      </style>
      <h1>Rejected Detections """ + fn + """</h1>
   """
   jsons = glob.glob(trash_dir + "*.json")
   for mjf in sorted(jsons):
      #mj = load_json_file(mjf)
      tn =mjf.replace(".json", "-stacked-tn.jpg")
      vid =mjf.replace(".json", ".mp4")
      if cfe(tn) == 0:
         tn =mjf.replace(".json", "-stacked-tn.png")
      trash += "<div class='detect_image'><a href=" + vid + "><img src='" + tn + "'></a></div>"


   fp = open(trash_dir + "/trash.html", "w")
   fp.write(trash)
   fp.close()
   print("Saved." + trash_dir + "/trash.html")
 



def biggest_cnts(cnts, count=5):
   ci = []
   cij = []
   for cx,cy,cw,ch in cnts:
      size = cw * ch
      ci.append((cx,cy,cw,ch,size))
      ci = sorted(ci , key=lambda x: (x[4]), reverse=True)
   for cx,cy,cw,ch,size in ci:
      #print("BIGGEST CNTS:", cx,cy,cw,ch,size)
      inside = 0
      if len(cij) > 0:
         inside = check_cnt_inside(cij, (cx,cy,cw,ch))
      if inside == 0:
         cij.append((cx,cy,cw,ch))
   return(cij[0:count])

def check_cnt_inside(cnt_list, this_cnt):
   tx,ty,tw,th = this_cnt
   ctx = tx + (tw/2)
   cty = ty + (th/2)
   inside = 0
   bl = 50
   for x,y,w,h in cnt_list:
      if w > bl:
         bl = w   
      if h > bl:
         bl = h   
      x1,y1,x2,y2 = bound_cnt(x, y,1920,1080, bl)
      if x1 < tx < x2 and y1 < ty < y2:
         inside = 1
      if x1 < tx + tw < x2 and y1 < ty + th < y2:
         inside = 1
      if x1 < ctx < x2 and y1 < cty < y2:
         inside = 1
      if inside == 0:
         dist = calc_dist((tx,ty),(x1,y1))
         dist2 = calc_dist((tx,ty),(x2,y1))
         dist3 = calc_dist((tx,ty),(x1,y2))
         dist4 = calc_dist((tx,ty),(x2,y2))
         dist5 = calc_dist((tx,ty),(tx,y1))
         dist6 = calc_dist((tx,ty),(tx,y2))
         dist7 = calc_dist((tx,ty),(x1,ty))
         dist8 = calc_dist((tx,ty),(x2,ty))
         min_dist = min(dist,dist2,dist3,dist4,dist5,dist6,dist7,dist8)
         #print("NOT INSIDE MIN DIST:", min_dist)
         if min_dist < 10:
            inside = 1
   return(inside)


def best_thresh(img, thresh, i=0):
   cnts,rects = find_contours_in_frame(img, thresh=thresh)
   for cnt in cnts:
      x,y,w,h = cnt
      #if w >= img.shape[1]:
      #   thresh = thresh + 50
   for i in range(1,20):
      thresh = thresh + (i*10)
      cnts,rects = find_contours_in_frame(img, thresh=thresh)
      if len(cnts) < 15:
         return(thresh)
      if thresh > 200:
         thresh = 200
   return(thresh)

def verify_meteor(meteor_file, json_conf):
   fn, dir = fn_dir(meteor_file)
   base = fn.split("-")[0]
   day = fn[0:10]
   sd_dir = "/mnt/ams2/SD/proc2/" + day + "/" 
   files = glob.glob(sd_dir + base + "*trim*.mp4")
   print(files)
   media = {}
   for file in files:
      w,h,frames = ffprobe(file)
      media[file] = (w,h,frames)

   meteors = {}
   SD = 0
   sd_stack_img = None
   hd_stack_img = None
   sd_images = {}
   hd_images = {}
   for file in media:
      if "crop" not in file and "HD" not in file:
         print(file, media[file])
         best_meteor,sd_stack_img,bad_objs = fireball(file, json_conf)
         if best_meteor is not None:
            sd_images[file] = sd_stack_img
            meteors[file] = best_meteor
            SD = 1
   if len(meteors) == 0:
      print("Sorry we found no meteors here.")
      return(None)

   # if we made it this far we have at least found the meteor in one file
   # lets check the HD files to see if we have a meteor there too
   HD = 0
   for file in media:
      if "HD" in file and "crop" not in file:
         best_meteor, stack_img,bad_objs = fireball(file, json_conf)
         if best_meteor is not None:
            best_meteor, hd_stack_img, bad_objs = fireball(file, json_conf)
            if best_meteor is not None:
               hd_images[file] = hd_stack_img
               meteors[file] = best_meteor
               HD = 1

   if SHOW == 1:
      for file in sd_images:
         print("SD IMGS:", file) 
         cv2.imshow('pepe', sd_images[file])
      for file in hd_images:
         print("HD IMGS:", file) 
         cv2.imshow('pepe', hd_images[file])

   for file in meteors:
      print(file, meteors[file])


   if SD == 1 and HD == 1:
      print("WIN! we have SD and HD meteors.")
   if SD == 0 and HD == 1:
      print("we have only HD meteors.")
   if SD == 1 and HD == 0:
      print("we have only SD meteors.")
   for file in meteors:
      print("METEOR:", file, media[file])
      print(meteors[file])
   save_old_meteor(meteors, media, sd_images, hd_images)

def obj_to_mj(sd_file, hd_file, sd_objects, hd_objects):
   sd_fn, dir = fn_dir(sd_file)
   if hd_file is not None and hd_file != 0:
      hd_fn, dir = fn_dir(hd_file)
   date = sd_fn[0:10]
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   mj = {}
   mj['meteor'] = 1
   mj['sd_trim'] = sd_file
   mj['sd_stack'] = mdir + sd_fn.replace(".mp4", "-stacked.png")
   mj['sd_objects'] = sd_objects
   mj['hd_trim'] = hd_file
   if hd_file != "":
      mj['hd_stack'] = mdir + hd_fn.replace(".mp4", "-stacked.png")
   else:
      mj['hd_stack'] = ""
      
   mj['hd_objects'] = hd_objects
   mj['trim_clip'] = sd_file
   mj['sd_video_file'] = sd_file
   mj['org_sd_vid'] = sd_file
   mj['orig_hd_vid'] = hd_file
   mj['hd_video_file'] = hd_file
   return(mj)

def save_old_meteor(meteors, media, sd_images, hd_images):
   for key in sd_images:
      print("SD IMG:", key)
   for key in hd_images:
      print("HD IMG:", key)
   mj = {}
   for file in meteors:
      if meteors[file] is None:
         continue
      print("METEOR FILE:", file, meteors[file])

      fn, dir = fn_dir(file)
      date = fn[0:10]
      mdir = "/mnt/ams2/meteors/" + date + "/" 
      w,h,num_frames = media[file]
      print("WH:", w, h)
      if int(w) == 1920:
         HD = 1
         mj['hd_trim'] = mdir + fn
         mj['hd_video_file'] = mdir + fn 
         mj['org_hd_vid'] = file 
         mj['hd_stack'] = mdir + fn.replace(".mp4", "-stacked.png")
         mj['hd_objects'] = meteors[file]
         #mj['hd_objects'].append(meteors[file][id])
         mj['meteor'] = 1
         mj['archive_file'] = ""
         hd_stack_img = hd_images[file]
         hd_stack_img = cv2.resize(hd_stack_img, (THUMB_W, THUMB_H))
      else:
         SD = 1
         mj['sd_trim'] = mdir + fn 
         mj['archive_file'] = ""
         mj['org_sd_vid'] = file 
         mj['sd_video_file'] = mdir + fn 
         mj['trim_clip'] = mdir + fn 
         mj['sd_stack'] = mdir + fn.replace(".mp4", "-stacked.png")
         mj['sd_objects'] = []
         mj['sd_objects'].append( meteors[file])
         #for id in meteors[file]:
         #   print("SD OBJ:", meteors[file][id])
         #   mj['sd_objects'].append(meteors[file][id])
         print("FILE:", file)
         sd_stack_img = sd_images[file]
         sd_stack_img_tn = cv2.resize(sd_stack_img, (THUMB_W, THUMB_H))
         obj_img = sd_stack_img.copy()
         min_x = min(mj['sd_objects'][0]['oxs'])
         min_y = min(mj['sd_objects'][0]['oys'])
         max_x = max(mj['sd_objects'][0]['oxs'])
         max_y = max(mj['sd_objects'][0]['oys'])
         cv2.rectangle(obj_img, (min_x, min_y), (max_x, max_y), (255,255,255), 3, cv2.LINE_AA)
         obj_tn = cv2.resize(obj_img, (THUMB_W, THUMB_H))
   if "hd_trim" not in mj:
      # Here we find trim and detect the HD meteor
      for obj in mj['sd_objects']:
         dur_fr = (len(obj['oxs'])) 
      hd_trim = find_hd(mj['sd_trim'],dur_fr, mj['sd_objects'][0]['ofns'][0])
      best_meteor, hd_stack_img, bad_objs  = fireball(file, json_conf)
      print("HD TRIM:", hd_trim)
      print("BEST HD METEOR:", best_meteor)
      if best_meteor is not None:
         # We found the HD file and obj so copy it into the meteor dir and update the json
         mj['hd_objects'] = []
         mj['hd_objects'].append( best_meteor)
         fn, dir = fn_dir(hd_trim)
         mj['hd_trim'] = mdir + fn
         mj['hd_video_file'] = mdir + fn 
         mj['org_hd_vid'] = file 
         mj['hd_stack'] = mdir + fn.replace(".mp4", "-stacked.png")
         hd_stack_img_tn = cv2.resize(hd_stack_img, (THUMB_W, THUMB_H))
         cmd = "cp " + hd_trim + " " + mdir + fn
         print(cmd)
         os.system(cmd)

      else:
         mj['hd_trim'] = "0"
   print(mj)
   fn,dir = fn_dir(mj['sd_trim'])
   date = fn[0:10]
   mdir = "/mnt/ams2/meteors/" + date + "/" 
   js = fn.replace(".mp4", ".json")
   save_json_file(mdir + js, mj)
   # copy vids
   if "sd_trim" in mj:
      cmd = "cp " + mj['org_sd_vid'] + " " + mdir
      os.system(cmd)
      print(sd_stack_img.shape)
      print(mj['sd_stack'])
      cv2.imwrite(mj['sd_stack'], sd_stack_img)
      cv2.imwrite(mj['sd_stack'].replace(".png", "-tn.png"), sd_stack_img_tn)
      cv2.imwrite(mj['sd_stack'].replace(".png", "-obj-tn.png"), obj_tn)
   if "hd_trim" in mj:
      if mj['hd_trim'] != "0":
         cmd = "cp " + mj['org_hd_vid'] + " " + mdir
         os.system(cmd)
         cv2.imwrite(mj['hd_stack'], hd_stack_img)
         cv2.imwrite(mj['hd_stack'].replace(".png", "-tn.png"), hd_stack_img_tn)
   print("Saved json:", js)


def mark_up_meteor_frame(frame, mark_objs,cp):

   oh,ow = frame.shape[:2]
   frame = cv2.resize(frame, (1280,720))
   full_frame = cv2.resize(frame, (1920,1080))
   hdm_x = 1280 / ow
   hdm_y = 720 / oh

   half_x = 1920 / 1280
   half_y = 1080 / 720
   
   rsize = 5 
   #for star in cp['cat_image_stars']:
   #   dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
   #   six = int(six / half_x)
   #   siy = int(siy / half_y)
   #   rx1,ry1,rx2,ry2 = bound_cnt(six, siy,1280,720, rsize)
   #   cv2.putText(frame, str(dcname),  (six-10,siy-10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      #cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (255,0,0), 1, cv2.LINE_AA)
   #   cv2.circle(frame,(six,siy), 10, (255,255,255), 1)
   #cv2.imshow('pepe', full_frame)

   for data in mark_objs:
      #print("DATA:", data)
      obj_id, obj_data, ccx, ccy = data
      obj_class = obj_data['report']['class']
      cx = int(ccx * hdm_x)
      cy = int(ccy * hdm_y)
      #print("CCX:", obj_id, hdm_x, hdm_y, ccx, ccy, cx,cy, obj_class)
      if obj_class == "meteor":
         rsize = 50
         cv2.line(frame, (cx-10,cy), (cx+10,cy), (200,200,200), 1)
         cv2.line(frame, (cx,cy-10), (cx,cy+10), (200,200,200), 1)
         desc = str(obj_id) + " " + str(obj_class) + str(obj_data['oint'][-1])
         cv2.putText(frame, desc,  (cx-10,cy-10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      elif obj_class != 'star':
         rsize = 10
         desc = str(obj_id) + " " + str(obj_class) + str(obj_data['oint'][-1])
         cv2.putText(frame, desc,  (cx-10,cy-10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      rx1,ry1,rx2,ry2 = bound_cnt(cx, cy,1280,720, rsize)
      cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (255,0,0), 1, cv2.LINE_AA)
   return(frame)

def calib_image(file, image=None,json_conf=None):
   print("CALIB IMAGE")
   before_cp, after_cp = get_cal_params(file)
   print("AFTER GET CAL")

   print(before_cp, after_cp)
   before_cp = update_center_radec(file,before_cp,json_conf)
   after_cp = update_center_radec(file,after_cp,json_conf)
   print("AFTER UPDATE")
   if image is None:
      print("READ FILE:", file)
      image = cv2.imread(file)
   image = cv2.resize(image, (1920,1080))
   print("OK1")
   before_cp['user_stars'] = get_image_stars(file, image.copy(), json_conf, 1)
   after_cp['user_stars'] = before_cp['user_stars']

   # do cal for before
   cat_stars = get_catalog_stars(before_cp)
   before_cp = pair_stars(before_cp, file, json_conf, image)
   for star in before_cp['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
   temp_stars, before_res_px,before_res_deg = cat_star_report(before_cp['cat_image_stars'], 4)
   print("OK2")

   # do cal for after 
   cat_stars = get_catalog_stars(after_cp)
   after_cp = pair_stars(after_cp, file, json_conf, image)
   for star in after_cp['cat_image_stars']:
      dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
   temp_stars, after_res_px,after_res_deg = cat_star_report(after_cp['cat_image_stars'], 4)

   print("BEFORE RES:", before_res_px, before_res_deg, len(before_cp['user_stars']), len(before_cp['cat_image_stars']))
   print(before_cp['center_az'])
   print("AFTER RES:", after_res_px, after_res_deg,len(before_cp['user_stars']), len(before_cp['cat_image_stars']))
   print(after_cp['center_az'])

   if before_res_px < after_res_px:
      cp = dict(before_cp)
   else:
      cp = dict(after_cp)

   if len(cp['cat_image_stars']) > 15 and cp['total_res_px'] > 2:
      cp = minimize_fov(file, cp, file ,image,json_conf ) 
   else:
      print("This meteor calib is good!")

   return(cp)


def mask_points(img, points ):
   hdm_x = 1920 / img.shape[1]
   hdm_y = 1080 / img.shape[0]
   tp = len(points)
   tc = 0
   for x,y,size in points:
      if size > 2:
         size = 2
      if tp - tc > 3:
         size = 5 
      if tp - tc > 5:
         size = 10
      if tp - tc > 10:
         size = 20

      bx1,by1,bx2,by2 = bound_cnt(x, y,img.shape[1],img.shape[0], size)
      if len(img.shape) == 2:
         img[by1:by2,bx1:bx2] = [0]
      else:
         img[by1:by2,bx1:bx2] = [0,0,0]
      tc += 1
   return(img)



def mask_stars(img, cp):
   hdm_x = 1920 / img.shape[1]
   hdm_y = 1080 / img.shape[0]
   for star in cp['user_stars']:
      #dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,bp = star
      six, siy, oint = star
      sd_six = int(six / hdm_x)
      sd_siy = int(siy / hdm_y)
      bx1,by1,bx2,by2 = bound_cnt(sd_six, sd_siy,img.shape[1],img.shape[0], 2)
      if len(img.shape) == 2:
         img[by1:by2,bx1:bx2] = [0]
      else:
         img[by1:by2,bx1:bx2] = [0,0,0]
      #cv2.circle(img,(sd_six,sd_siy), 10, (255,255,255), 1)
   #cv2.imshow('pepe', img)
   return(img)

def mfd_to_cropbox(mfd):
   xs = []
   ys = []
   for row in mfd:
      (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
      xs.append(x)
      xs.append(x+w)
      ys.append(y)
      ys.append(y)
   if len(xs) > 0:
      crop_box = [min(xs),min(ys),max(xs),max(ys)]
   else:
      crop_box = [0,0,0,0]
   return(crop_box)

def make_roi_video_mfd(video_file, json_conf):
   roi_size = 50
   vid_fn, vid_dir = fn_dir(video_file)
   vid_base = vid_fn.replace(".mp4", "")
   mjf = video_file.replace(".mp4", ".json")
   mjrf = video_file.replace(".mp4", "-reduced.json")

   date = vid_fn[0:10]
   year = vid_fn[0:4]
   mon = vid_fn[5:7]
   cache_dir = "/mnt/ams2/CACHE/" + year + "/" + mon + "/" + vid_base + "/"
   prefix = cache_dir + vid_base + "-frm"

   hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])

   updated_frame_data = []
   if cfe(mjf) == 1:
      mj = load_json_file(mjf)
   if cfe(mjrf) == 1:
      mjr = load_json_file(mjrf)
   if "user_mods" in mj:
      if "frames" in mj['user_mods']:
         ufd = mj['user_mods']['frames']
      else:
         ufd = {}
   else:
      ufd = {}
      mj['user_mods'] = {}
   used = {}
   if "meteor_frame_data" in mjr:
      for row in mjr['meteor_frame_data']:
         (dt, fn, x, y, w, h, oint, ra, dec, az, el) = row
         frame = hd_color_frames[fn]
         sfn = str(fn)
         if sfn in ufd:
            x,y = ufd[sfn]
            tx, ty, ra ,dec , az, el = XYtoRADec(x,y,video_file,mjr['cal_params'],json_conf)
            #AZEL HERE!
            print("UPDATED POINT", fn, x,y)
         if fn not in used:
            updated_frame_data.append((dt, fn, x, y, w, h, oint, ra, dec, az, el))
            #cx = x + int(w/2)
            #cy = y + int(h/2)
            rx1,ry1,rx2,ry2 = bound_cnt(x, y,1920,1080, roi_size)
            of = cv2.resize(frame, (1920,1080))
            roi_img = of[ry1:ry2,rx1:rx2]

            #cv2.rectangle(of, (rx1, ry1), (rx2, ry2), (255,255,255), 1, cv2.LINE_AA)
            #cv2.imshow('pepe', of)
            #cv2.waitKey(0)

            ffn = "{:04d}".format(int(fn))
            outfile = prefix + ffn + ".jpg"
            cv2.imwrite(outfile, roi_img)
            print("WROTE:", outfile, x,y)
         used[fn] = 1

   crop_box = mfd_to_cropbox(updated_frame_data)

   mjr['crop_box'] = crop_box 
   mjr['meteor_frame_data'] = updated_frame_data

   # NEXT LOOP THE CCXS CCYS fields 720p update from user mod

   save_json_file(mjrf, mjr)      
   save_json_file(mjf, mj)      

   print("COP:", mjr['crop_box'])
         

   

def make_roi_video(video_file,bm, frames, json_conf):
   mjf = video_file.replace(".mp4", ".json")
   mjrf = video_file.replace(".mp4", "-reduced.json")
   mj = load_json_file(mjf)
   mjr = load_json_file(mjrf)
   vid_fn, vdir = fn_dir(video_file)
   vid_base = vid_fn.replace(".mp4", "")
   date = vid_fn[0:10]
   year = vid_fn[0:4]
   mon = vid_fn[5:7]
   cache_dir = "/mnt/ams2/CACHE/" + year + "/" + mon + "/" + vid_base + "/"
   prefix = cache_dir + vid_base + "-frm"
   if cfe(cache_dir, 1) == 0:
      os.makedirs(cache_dir)
   roi_size = 50
   roi_size2 = roi_size * 2
   roi_frames = []

   if "user_mods" in mj:
      if "frames" in mj['user_mods']:
         ufd = mj['user_mods']['frames']
      else:
         ufd = {}
   else:
      ufd = {}
   used = {}

   hdm_x_720 = 1920 / 1280
   hdm_y_720 = 1080 / 720
   updated_frame_data = []
   xs19 = []
   ys19 = []
   for j in range(0, len(frames)):
      i = j - bm['ofns'][0]  
      fns = str(j)

      if fns in ufd:
         mod_x,mod_y = ufd[fns] 
         mod_x_720 = int(mod_x / hdm_x_720)
         mod_y_720 = int(mod_y / hdm_y_720)
         bm['ccxs'][i] = mod_x_720
         bm['ccys'][i] = mod_y_720

      if bm['ofns'][0] <= j < bm['ofns'][-1] - 1:
         # meteor is active
         rx = bm['ccxs'][i]
         ry = bm['ccys'][i]
         rw = bm['ows'][i]
         rh = bm['ohs'][i]
         oint = bm['oint'][i]
         hd_x = int(rx * hdm_x_720)
         hd_y = int(ry * hdm_y_720)
         tx, ty, ra ,dec , az, el = XYtoRADec(hd_x,hd_y,video_file,mjr['cal_params'],json_conf)
         date_str = bm['dt'][i]
         updated_frame_data.append((date_str, j, hd_x, hd_y, rw, rh, oint, ra, dec, az, el))
      else:
         # meteor is inactive (use 1st frame / last frame for crop location on missing frames)
         if j < bm['ofns'][0]:
            rx = bm['ccxs'][0]
            ry = bm['ccys'][0]
         elif j > bm['ofns'][-1]:
            rx = bm['ccxs'][-1]
            ry = bm['ccys'][-1]
      
 
         hd_x = int(rx * hdm_x_720)
         hd_y = int(ry * hdm_y_720)
      xs19.append(hd_x)
      ys19.append(hd_y)
      rx1,ry1,rx2,ry2 = bound_cnt(hd_x, hd_y,1920,1080, roi_size)
      of = frames[j].copy()
      of = cv2.resize(of, (1920,1080))
      roi_img = of[ry1:ry2,rx1:rx2]
      roi_frames.append(roi_img)
         # this only handles the left side now BUG/FIX
      side = None
      if roi_img.shape[0] != roi_size2 or roi_img.shape[1] != roi_size2:
         roi_p = np.zeros((roi_size2,roi_size2,3),dtype=np.uint8)
         px1 = 0
         px2 = roi_img.shape[1]
         if ry > 1080/2:
            # object is near the bottom edge
            py1 = 0
            py2 = roi_img.shape[0]
         else:
            py1 = roi_size2 - roi_img.shape[0]  
            py2 = roi_size2 
         roi_p[py1:py2, px1:px2] = roi_img
      else:
         roi_p = roi_img
 
      ffn = "{:04d}".format(int(j))
      outfile = prefix + ffn + ".jpg"
      cv2.imwrite(outfile, roi_p)
      if SHOW == 1:
         cv2.rectangle(of, (rx1, ry1), (rx2, ry2), (255,255,255), 1, cv2.LINE_AA)
         cv2.imshow("pepe", of)
         cv2.waitKey(30)
  
   mjr['crop_box'] = [min(xs19)-25, min(ys19)-25,max(xs19)+25,max(ys19)+25]
   print("UPD:", updated_frame_data)
   mjr['meteor_frame_data'] = updated_frame_data
   save_json_file(mjrf, mjr)
   tracking_outfile = "/mnt/ams2/meteors/" + date + "/" + vid_base + "-tracking.mp4"
   cmd = "./FFF.py imgs_to_vid " + cache_dir + " " + year + " " + tracking_outfile + " 25 27"
   os.system(cmd)
   print(cmd)
   

def fireball(video_file, json_conf, nomask=0):
   fn, meteor_dir = fn_dir(video_file)
   jsf = video_file.replace(".mp4", ".json")
   best_meteor = None
   if cfe(jsf) == 1:
      jdata = load_json_file(jsf)
      print("LOADING:", jsf)
      if "best_meteor" not in jdata:
         best_meteor = None
      else:
         best_meteor = jdata['best_meteor']
         #if "hd_trim" in jdata:
         #   hd_trim = jdata['hd_trim']
         #base_js, base_jsr = make_base_meteor_json(video_file, hd_trim,best_meteor)
         #jdata = base_js
   else:
      # update this to find the HD file in the meteor dir, or the min_save dir if it is not present.
      hd_trim = None
      base_js, base_jsr = make_base_meteor_json(video_file, hd_trim,best_meteor)
      jdata = base_js
      #jdata = None
   print("JDATA:", jdata)
   hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])
   tracking_updates = {}
   print("FIREBALL2!")

   #make_roi_video(video_file,best_meteor, hd_color_frames, json_conf)
   #exit()
   print("LEN :", len(hd_frames))
   fh, fw = hd_frames[0].shape[:2]
   hdm_x_720 = 1280 / fw
   hdm_y_720 = 720 / fh
   print("BP1")
   best_meteor, hd_frames, hd_color_frames, median_frame, mask_img,cp = fireball_phase1(hd_frames, hd_color_frames, subframes,sum_vals,max_vals,pos_vals, video_file, json_conf, jsf, jdata, best_meteor, nomask)
   print("AP1")
   gap_test_res = None
   jdata['cp'] = cp
   if best_meteor is not None:
      gap_test_res , gap_test_info = gap_test(best_meteor['ofns'])
      if gap_test_res == 0:
         print("GAP TEST FAILED. PLANE!")
         best_meteor = None
   if best_meteor is None:
      # detection failed, flag JSF.
      jdata['rejected'] = 1
      jdata['rejected_desc'] = "No best meteor found."
      if gap_test_res is not None and gap_test_res == 0:
         jdata['gap_test_info'] = gap_test_info
      save_json_file(jsf, jdata)
      print("No meteor detected.", jsf)
      return()


   best_meteor, frame_data = fireball_fill_frame_data(video_file,best_meteor, hd_color_frames)
   #tracking_file = video_file.replace(".mp4", "-tracking.mp4")
   #tracking_updates = fireball_tracking_center(tracking_file)
   #best_meteor, frame_data = fireball_fill_frame_data(video_file,best_meteor, hd_color_frames, tracking_updates)

   print("FNS",best_meteor['ofns'])
   print("XS",best_meteor['oxs'])
   print("YS",best_meteor['oys'])
   print("INTS",best_meteor['oint'])
   print("DIST:", best_meteor['fs_dist'])
      


   if jdata is None:
      jdata = {}
      if "cp" in best_meteor:
         if "x_poly" in best_meteor['cp']:
            if type(best_meteor['cp']['x_poly']) is not list:
               best_meteor['cp']['x_poly'] = best_meteor['cp']['x_poly'].tolist()
               best_meteor['cp']['y_poly'] = best_meteor['cp']['y_poly'].tolist()
               best_meteor['cp']['x_poly_fwd'] = best_meteor['cp']['x_poly_fwd'].tolist()
               best_meteor['cp']['y_poly_fwd'] = best_meteor['cp']['y_poly_fwd'].tolist()

      jdata['best_meteor'] = best_meteor

      save_json_file(jsf, jdata)
   #fireball_plot_points(best_meteor)

   if max(best_meteor['oint']) < 1000000:
      best_meteor['ccxs'] = []
      best_meteor['ccys'] = []
      for i in range(0, len(best_meteor['oxs'])):
         cx = int((best_meteor['oxs'][i] + int(best_meteor['ows'][i]/2)) * hdm_x_720)
         cy = int((best_meteor['oys'][i] + int(best_meteor['ohs'][i]/2)) * hdm_y_720)
         best_meteor['ccxs'].append(cx)
         best_meteor['ccys'].append(cy)
      jdata['best_meteor'] = best_meteor
      if "hd_trim" in jdata:
         hd_trim = jdata['hd_trim']
      else:
         hd_trim = None
      #print(base_js['meteor_frame_data'])
      print("APPLY CALIB!")
      best_meteor = apply_calib(video_file, best_meteor, cp, json_conf)
      base_js, base_jsr = make_base_meteor_json(video_file, hd_trim,best_meteor,cp)
      print("BASE:", base_js)
      jsfr = jsf.replace(".json", "-reduced.json") 

      if "cp" in best_meteor:
         print("YES1")
         if "x_poly" in best_meteor['cp']:
            print("YES2")
            if type(best_meteor['cp']['x_poly']) is not list:
               print("YES3")
               best_meteor['cp']['x_poly'] = best_meteor['cp']['x_poly'].tolist()
               best_meteor['cp']['y_poly'] = best_meteor['cp']['y_poly'].tolist()
               best_meteor['cp']['x_poly_fwd'] = best_meteor['cp']['x_poly_fwd'].tolist()
               best_meteor['cp']['y_poly_fwd'] = best_meteor['cp']['y_poly_fwd'].tolist()

      save_json_file(jsf, jdata)
      save_json_file(jsfr, base_jsr)
      print("saved:", jsfr)
      print("Small meteor don't need to refine", max(best_meteor['oint']))
      print("CCXS:", best_meteor['ccxs'])
      print("CCYS:", best_meteor['ccys'])
      make_roi_video(video_file,best_meteor, hd_color_frames, json_conf)
      return()
   else:

      if "cp" in best_meteor:
         print("YES1")
         if "x_poly" in best_meteor['cp']:
            print("YES2")
            if type(best_meteor['cp']['x_poly']) is not list:
               print("YES3")
               best_meteor['cp']['x_poly'] = best_meteor['cp']['x_poly'].tolist()
               best_meteor['cp']['y_poly'] = best_meteor['cp']['y_poly'].tolist()
               best_meteor['cp']['x_poly_fwd'] = best_meteor['cp']['x_poly_fwd'].tolist()
               best_meteor['cp']['y_poly_fwd'] = best_meteor['cp']['y_poly_fwd'].tolist()

      jdata['best_meteor'] = best_meteor
      save_json_file(jsf, jdata)
      print("big meteor lets refine", max(best_meteor['oint']))
      #return()


   best_meteor = fireball_phase3(video_file, json_conf, jsf, jdata, best_meteor, nomask, hd_frames, hd_color_frames, median_frame, mask_img,5)

   fireball_plot_points(best_meteor)
   best_meteor = apply_calib(video_file, best_meteor,cp,json_conf)
   jdata['best_meteor'] = best_meteor
   save_json_file(jsf, jdata)
   print("Saved:", jsf)
   jsfr = jsf.replace(".json", "-reduced.json")
   if "hd_trim" in jdata:
      hd_trim = jdata['hd_trim']
   else:
      hd_trim = None
   mj, mjr = make_base_meteor_json(video_file,hd_trim, best_meteor, cp)
   make_roi_video(video_file,best_meteor, hd_color_frames, json_conf)
   save_json_file(jsfr, mjr)
   #best_meteor = fireball_decel(video_file, json_conf, jsf, jdata, best_meteor, nomask, hd_frames, hd_color_frames, median_frame, mask_img,5)

def make_base_meteor_json(video_file, hd_video_file,best_meteor=None ,cp=None):
   mj = {}
   mjr = {}
   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(video_file)
   sd_fn, dir = fn_dir(video_file)
   if hd_video_file is not None:
      hd_fn, dir = fn_dir(hd_video_file)
      hd_stack_fn = hd_fn.replace(".mp4", "-stacked.jpg")
   stack_fn = sd_fn.replace(".mp4", "-stacked.jpg")

   date = sd_fn[0:10]
   mdir = "/mnt/ams2/meteors/" + date + "/"
   mj["sd_video_file"] = mdir + sd_fn
   mj["sd_stack"] = mdir + stack_fn
   mj["sd_objects"] = []
   if hd_video_file is not None:
      mj["hd_trim"] = mdir + hd_fn
      mj["hd_stack"] = mdir + hd_stack_fn
      mj["hd_video_file"] = mdir + hd_fn
      mj["hd_trim"] = mdir + hd_fn
      mj["hd_objects"] = []
   mj["meteor"] = 1

   # reduce
   mjr['api_key'] = "123"
   mjr['station_name'] = STATION_ID
   mjr['device_name'] = cam
   mjr["sd_video_file"] = mdir + sd_fn
   mjr["sd_stack"] = mdir + stack_fn
   if hd_video_file is not None:
      mjr["hd_video_file"] = mdir + sd_fn
      mjr["hd_stack"] = mdir + stack_fn
   mjr["event_start_time"] = ""
   mjr["event_duration"] = ""
   mjr["peak_magnitude"] = ""
   mjr["start_az"] = ""
   mjr["start_el"] = ""
   mjr["end_az"] = ""
   mjr["end_el"] = ""
   mjr["start_ra"] = ""
   mjr["start_dec"] = ""
   mjr["end_ra"] = ""
   mjr["end_dec"] = ""
   # dt, fn, x,y,w,h,ra,dec,az,el (FLUX)
   mjr["meteor_frame_data"] = []
   mjr["crop_box"] = []
   hdm_x_720 = 1920 / 1280
   hdm_y_720 = 1080 / 720
   if best_meteor is not None:
      mjr["cal_params"] = cp
      min_x = min(best_meteor['oxs'])
      max_x = max(best_meteor['oxs'])
      min_y = min(best_meteor['oys'])
      max_y = max(best_meteor['oys'])
      mjr['crop_box'] = [min_x,min_y,max_x,max_y]
      for i in range(0, len(best_meteor['ofns'])):
         #dt = "1999-01-01 00:00:00"
         fn = best_meteor['ofns'][i]
         x = int(best_meteor['ccxs'][i] * hdm_x_720)
         y = int(best_meteor['ccys'][i] * hdm_y_720)
         w = best_meteor['ows'][i]
         h = best_meteor['ohs'][i]
         ra = best_meteor['ras'][i]
         dec = best_meteor['decs'][i]
         az = best_meteor['azs'][i]
         el = best_meteor['els'][i]
         oint = best_meteor['oint'][i]
         dt = best_meteor['dt'][i]
         #FLUX
         oint = best_meteor['oint'][i]
         mjr['meteor_frame_data'].append((dt, fn, x, y, w, h, oint, ra, dec, az, el))

   mjr['crop_box'] = mfd_to_cropbox(mjr['meteor_frame_data'])
   return(mj, mjr)

def apply_frame_deletes(mjf, mj=None, mjr=None, json_conf=None):
   dd = {}
   if mj is None:
      mj = load_json_file(mjf)
   if "user_mods" in mj:
      
      if "del_frames" in mj['user_mods']:
         for fn in mj['user_mods']['del_frames']:
            print("DD:", fn)
            dd[int(fn)] = 1
      else:
         print("NO FRAME DELETES.")
         return(0)
   else:
      print("NO USER MODS IN MJ FRAME DELETES.")
      return(0)
   if mjr is None:
      mjrf = mjf.replace(".json", "-reduced.json")
      mjr = load_json_file(mjrf)

   n_ofns = []
   n_oxs = []
   n_oys = []
   n_ows = []
   n_ohs = []
   n_oint = []
   n_ccxs = []
   n_ccys = []
   for i in range(0,len(mj['best_meteor']['ofns'])):
      fn = mj['best_meteor']['ofns'][i]
      if fn not in dd:
         n_ofns.append(mj['best_meteor']['ofns'][i])
         n_oxs.append(mj['best_meteor']['oxs'][i])
         n_oys.append(mj['best_meteor']['oys'][i])
         n_ows.append(mj['best_meteor']['ows'][i])
         n_ohs.append(mj['best_meteor']['ohs'][i])
         n_oint.append(mj['best_meteor']['oint'][i])
         n_ccxs.append(mj['best_meteor']['ccxs'][i])
         n_ccys.append(mj['best_meteor']['ccys'][i])
   mj['best_meteor']['ofns'] = n_ofns
   mj['best_meteor']['oxs'] = n_oxs
   mj['best_meteor']['oys'] = n_oys
   mj['best_meteor']['ows'] = n_ows
   mj['best_meteor']['ohs'] = n_ohs
   mj['best_meteor']['oint'] = n_oint
   mj['best_meteor']['ccxs'] = n_ccxs
   mj['best_meteor']['ccys'] = n_ccys

   mfd,crop_box = make_meteor_frame_data(mj['best_meteor'], mj['cp'])
   mj['crop_box'] = crop_box
   mjr['crop_box'] = crop_box
   mjr['meteor_frame_data'] = mfd
   save_json_file(mjf, mj)
   save_json_file(mjrf, mjr)
   print("NEW MFD:", len(mfd))
   for fd in mfd:
      print(fd)
   return(mj, mjr)

def make_meteor_frame_data(best_meteor,cp):
   meteor_frame_data = []
   hdm_x_720 = 1920 / 1280
   hdm_y_720 = 1080 / 720
   if best_meteor is not None:
      min_x = min(best_meteor['oxs'])
      max_x = max(best_meteor['oxs'])
      min_y = min(best_meteor['oys'])
      max_y = max(best_meteor['oys'])
      crop_box = [min_x,min_y,max_x,max_y]
      for i in range(0, len(best_meteor['ofns'])):
         #dt = "1999-01-01 00:00:00"
         fn = best_meteor['ofns'][i]
         x = int(best_meteor['ccxs'][i] * hdm_x_720)
         y = int(best_meteor['ccys'][i] * hdm_y_720)
         w = best_meteor['ows'][i]
         h = best_meteor['ohs'][i]
         ra = best_meteor['ras'][i]
         dec = best_meteor['decs'][i]
         az = best_meteor['azs'][i]
         el = best_meteor['els'][i]
         oint = best_meteor['oint'][i]
         dt = best_meteor['dt'][i]
         #FLUX
         oint = best_meteor['oint'][i]
         print("new MFD:", fn)
         meteor_frame_data.append((dt, fn, x, y, w, h, oint, ra, dec, az, el))
   return(meteor_frame_data, crop_box)



def fireball_plot_points(bm):
   plot = np.zeros((720,1280,3),dtype=np.uint8)
   for i in range(0, len(bm['oxs'])):
      fn = bm['ofns'][i]
      ox = int(bm['oxs'][i] )
      oy = int(bm['oys'][i] )
      ow = int(bm['ows'][i] )
      oh = int(bm['ohs'][i] )
      oint = int(bm['oint'][i])
      if "ccxs" in bm:
         nx = bm['ccxs'][i]
         ny = bm['ccys'][i]
      else:
         nx = int(ox + (ow/2))
         ny = int(oy + (oh/2))
      plot[ny,nx] = 255
      print(i, fn, ox, oy, nx, ny)
   cv2.imshow('pepe', plot)
   cv2.waitKey(30)

def fireball_fill_frame_data(video_file, bm, frames, tracking_updates = None):
   trim_num = get_trim_num(video_file) 
   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(video_file)
   oh, ow = frames[0].shape[:2]
   hdm_x = 1280 / ow
   hdm_y = 720 / oh
   # fill in frame data object first

   (dom_dir, quad, ideal_pos, ideal_roi_big_img) = get_movement_info(bm, 640, 640)
   print("DOM:", dom_dir, quad)

   frame_data = {}
   ff = bm['ofns'][0]
   lf = bm['ofns'][-1] + 1
   for fn in range(ff, lf):
      frame_data[fn] = {}

   for i in range(0, len(bm['ofns'])):
       
      fn = bm['ofns'][i]
      ox = int(bm['oxs'][i] )
      oy = int(bm['oys'][i] )
      ow = int(bm['ows'][i] )
      oh = int(bm['ohs'][i] )
      if i <= len(bm['oint'])-1:
         oint = int(bm['oint'][i])
      else:
         oint = 0
      if "ccxs" in bm:
         nx = bm['ccxs'][i]
         ny = bm['ccys'][i]
      else:
         nx = int((bm['oxs'][i] + bm['ows'][i]/2) * hdm_x)
         ny = int((bm['oys'][i] + bm['ohs'][i]/2) * hdm_y)
      frame_data[fn]['ox'] = ox
      frame_data[fn]['oy'] = oy
      frame_data[fn]['ow'] = ow
      frame_data[fn]['oh'] = oh
      frame_data[fn]['nx'] = nx
      frame_data[fn]['ny'] = ny
      frame_data[fn]['oint'] = oint

   extra_sec = int(trim_num) / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)
   print("")
   print("")
   print("")
   print("")
   bad_frames = []
   for fn in sorted(frame_data.keys()):
      print(fn, frame_data[fn])
      prev_frame = None
      next_frame = None
      next_found = 0
      prev_found = 0
      if "ox" not in frame_data[fn]:
         print("MISSING/FIX!")
         for i in range(1, 5):
            prev_frame = fn - i
            if "ox" in frame_data[prev_frame]:
               print("PREV FRAME IS: ", prev_frame)
               prev_found = 1
               break
         for i in range(1, 5):
            next_frame = fn + i
            if "ox" in frame_data[next_frame]:
               print("NEXT FRAME IS: ", next_frame)
               next_found = 1
               break
         print("PN F:", prev_found, next_found)
         if (next_found == 0 or prev_found == 0):
            print("FDP:", frame_data[prev_frame])
            print("FDN:", frame_data[next_frame])
            print("There is no prev or next frame", prev_frame, next_frame, next_found, prev_found)
            bad_frames.append(fn)
         else:
            gap_len = next_frame - prev_frame
            if gap_len > 1:
               print("GAP prev/next:", gap_len, prev_frame, next_frame)
               print("FDP:", frame_data[prev_frame])
               print("FDN:", frame_data[next_frame])
               print("PREVX:", frame_data[prev_frame]['ox'] , frame_data[next_frame]['ox'])
               print("PREVY:", frame_data[prev_frame]['oy'] , frame_data[next_frame]['oy'])
               dif_x = int((frame_data[next_frame]['ox'] - frame_data[prev_frame]['ox']) / 2 )
               dif_y = int((frame_data[next_frame]['oy'] - frame_data[prev_frame]['oy']) / 2)
               frame_data[fn]['ox'] = frame_data[prev_frame]['ox'] + dif_x
               frame_data[fn]['oy'] = frame_data[prev_frame]['oy'] + dif_y
               frame_data[fn]['nx'] = frame_data[prev_frame]['nx'] + dif_x
               frame_data[fn]['ny'] = frame_data[prev_frame]['ny'] + dif_y
               frame_data[fn]['ow'] = frame_data[prev_frame]['ow']
               frame_data[fn]['oh'] = frame_data[prev_frame]['oh']
               frame_data[fn]['oint'] = 0
               print("FILL DIF XY:", fn, frame_data[fn])
               #exit()

            # here we have the easiest fix of just 1 missing frame in the middle with entries on both sides
            elif fn+1 < len(frame_data.keys()) and fn-1 > 0:
               frame_data[fn]['ox'] = int((frame_data[fn-1]['ox'] + frame_data[fn+1]['ox']) / 2)
               frame_data[fn]['oy'] = int((frame_data[fn-1]['oy'] + frame_data[fn+1]['oy']) / 2)
               frame_data[fn]['nx'] = int((frame_data[fn-1]['nx'] + frame_data[fn+1]['nx']) / 2)
               frame_data[fn]['ny'] = int((frame_data[fn-1]['ny'] + frame_data[fn+1]['ny']) / 2)
               frame_data[fn]['ow'] = frame_data[fn-1]['ow'] 
               frame_data[fn]['oh'] = frame_data[fn-1]['oh'] 
               frame_data[fn]['oint'] = 0
            else:
               print("Can't fix", fn, frame_data[fn])
      if "dt" not in frame_data[fn]:
         extra_sec = fn / 25
         frame_time = start_trim_frame_time + datetime.timedelta(0,extra_sec)
         frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         frame_data[fn]['dt'] = frame_time_str

   ofns = []
   oxs = []
   oys = []
   ohs = []
   ows = []
   oint = []
   ccxs = []
   ccys = []
   dts= []
   # Loop over new frame data and add to BM arrays
   for fn in frame_data:
      if tracking_updates is not None:
         if fn in tracking_updates:
            mod_x, mod_y = tracking_updates[fn]
         else:
            mod_x, mod_y = 0,0
      else:
            mod_x, mod_y = 0,0
      print("MOD XY:", fn, mod_x, mod_y, frame_data[fn]['nx'], frame_data[fn]['ny'])
      print("FD BEFORE MOD:", fn, frame_data[fn])
      if 'ox' in frame_data[fn]:
         ofns.append(fn)
         frame_data[fn]['ox'] = frame_data[fn]['ox']+mod_x
         frame_data[fn]['oy'] = frame_data[fn]['oy']+mod_y
         frame_data[fn]['nx'] = frame_data[fn]['nx']+mod_x
         frame_data[fn]['ny'] = frame_data[fn]['ny']+mod_y
         oxs.append(frame_data[fn]['ox'])
         oys.append(frame_data[fn]['oy'])
         ows.append(frame_data[fn]['ow'])
         ohs.append(frame_data[fn]['oh'])
         ccxs.append(frame_data[fn]['nx'])
         ccys.append(frame_data[fn]['ny'])
         oint.append(frame_data[fn]['oint'])
         dts.append(frame_data[fn]['dt'])
      print("FD AFTER MOD:", fn, frame_data[fn])

   # update the BM object
   bm['ofns'] = ofns
   bm['oxs'] = oxs
   bm['oys'] = oys
   bm['ows'] = ows
   bm['ohs'] = ohs
   bm['ccxs'] = ccxs
   bm['ccys'] = ccys
   bm['oint'] = oint
   bm['dt'] = dts


   for d in frame_data:
      print(d, frame_data[d])
   return(bm, frame_data)




   exit()
   #return(bm, frame_data)
   # Loop over frames, identify missing frame data, acquire data for those frames, reformat data to BM 
   for fn in frame_data:
      frame = frames[fn]
      if "ox" not in frame_data[fn]:
         print("MISSING!", fn, frame_data[fn])
         bx1,by1,bx2,by2 = bound_cnt(last_ocx, last_ocy,frame.shape[1],frame.shape[0], 50)
         roi = frame[by1:by2,bx1:bx2] 

         roi_bw = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(roi_bw)
         thresh = max_val - 25
         _, threshold = cv2.threshold(roi.copy(), thresh, 255, cv2.THRESH_BINARY)

         cnts = get_contours_in_image(threshold)
         if len(cnts) > 1:
            cnts = lead_cnts(cnts, dom_dir, quad)
         if len(cnts) == 1:
            cnt_x, cnt_y, cnt_w, cnt_h = cnts[0]
            cnt_x += bx1
            cnt_y += by1
            cnt_img = frame[cnt_y:cnt_y+cnt_h,cnt_x:cnt_x+cnt_w]
            cnt_int = int(np.sum(cnt_img))
            
            hframe = cv2.resize(frame, (1280, 720))
            cur_x = int((cnt_x  ) + ((cnt_w )/2))
            cur_y = int((cnt_y ) + ((cnt_h )/2))
            if cnt_w > cnt_h:
               avg_size = cnt_h
            else:
               avg_size = cnt_w
            new_x, new_y = center_roi_blob(hframe, cur_x, cur_y,avg_size) 
            frame_data[fn]['ox'] = cnt_x
            frame_data[fn]['oy'] = cnt_y
            frame_data[fn]['ow'] = cnt_w
            frame_data[fn]['oh'] = cnt_h
            frame_data[fn]['ny'] = new_x
            frame_data[fn]['nx'] = new_y
            frame_data[fn]['oint'] = cnt_int
         else:
            # NO CNT FOUND IN THIS FRAME AREA
            frame_data[fn]['ox'] = 0
            frame_data[fn]['oy'] = 0
            frame_data[fn]['ow'] = 0
            frame_data[fn]['oh'] = 0
            frame_data[fn]['ny'] = 0
            frame_data[fn]['nx'] = 0
            frame_data[fn]['oint'] = 0 

      else:
         ox = frame_data[fn]['ox']
         oy = frame_data[fn]['oy']
         ow = frame_data[fn]['ow']
         oh = frame_data[fn]['oh']
         ocx = int(ox + (ow/2))
         ocy = int(oy + (oh/2))
         last_ocx = ocx
         last_ocy = ocy

   ofns = []
   oxs = []
   oys = []
   ohs = []
   ows = []
   oint = []
   ccxs = []
   ccys = []
   # Loop over new frame data and add to BM arrays
   for fn in frame_data:
      ofns.append(fn)
      oxs.append(frame_data[fn]['ox'])
      oys.append(frame_data[fn]['oy'])
      ows.append(frame_data[fn]['ow'])
      ohs.append(frame_data[fn]['oh'])
      ccxs.append(frame_data[fn]['nx'])
      ccys.append(frame_data[fn]['ny'])
      oint.append(frame_data[fn]['oint'])

   # update the BM object
   bm['ofns'] = ofns
   bm['oxs'] = oxs
   bm['oys'] = oys
   bm['ows'] = ows 
   bm['ohs'] = ohs 
   bm['ccxs'] = ccxs
   bm['ccys'] = ccys
   bm['oint'] = oint
   return(bm, frame_data)

def fireball_decel(video_file, json_conf, jsf, jdata, best_meteor, nomask, hd_frames, hd_color_frames, median_frame, mask_img,med_dist):
   nxs = best_meteor['ccxs']
   nys = best_meteor['ccys']
   for i in range(0, len(nxs)):
      x = nxs[i]
      y = nys[i]
      if i > 0:
         dist = calc_dist((x,y),(last_x,last_y))
         dist_x = x - last_x
         dist_y = y - last_y
         print(i, x,y,last_x,last_y,dist, dist_x, dist_y)
      else:
         dist = 0
      last_x = x
      last_y = y

def grid_intensity_center(roi_p, cnt_size=5): 

   rh, rw = roi_p.shape[:2]
   scale_xy = 360/rw
   roi_p = cv2.resize(roi_p, (360, 360))
   cnt_size = cnt_size * scale_xy 
   grid_size = 5 
   best_sum = 0
   best_grid = None
   grid_squares = []
   roi_size = rh
   roi_size2 = roi_size 
   roi_div = 360 / roi_size2
   cx = 180
   cy = 180
   for col in range(0, int(360/grid_size)):
      for row in range(0, int(360/grid_size)):
         gx1 = col * grid_size
         gy1 = row * grid_size
         gx2 = gx1 + grid_size
         gy2 = gy1 + grid_size
         grid_sum_img = roi_p[gy1:gy2,gx1:gx2]
         grid_sum = int(np.sum(grid_sum_img))
         grid_squares.append((gx1,gy1,gx2,gy2,grid_sum))

   grid_lim = 3


   sorted_grids = sorted(grid_squares, key=lambda x: (x[4]), reverse=True)
   gxs = []
   gys = []
   for best_grid in sorted_grids[0:grid_lim]:
      gx1,gy1,gx2,gy2,grid_sum = best_grid
      print("GRID SUM:", gx1, gy1, gx2, gy2, grid_sum)
      gxs.append((gx1, gx2))
      gys.append((gy1, gy2))
      cv2.rectangle(roi_p, (gx1, gy1), (gx2, gy2), (150,150,150), 1, cv2.LINE_AA)
   mgx = int(np.mean(gxs))
   mgy = int(np.mean(gys))
  
   adj_x = int((mgx - 180) / roi_div)
   adj_y = int((mgy - 180) / roi_div)
   cv2.imshow('ROIPPPP', roi_p)
   cv2.waitKey(0)
   return(adj_x, adj_y)

def fireball_tracking_center(tracking_file):
   hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(tracking_file, json_conf, 0, 0, 1, 1,[])
   tracking_updates = {}
   th, tw = hd_frames[0].shape[:2]
   tcx = int(tw / 2)
   tcy = int(th / 2)
   fn = 0
   for frame in hd_frames:
      subframe = cv2.subtract(frame, hd_frames[0])
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)

      pxd = max_val - min_val
      print("PX DIFF, MIN, MAX:", pxd, min_val, max_val)
      if pxd > 20:
         thresh = int(max_val - (pxd / 2))
      else:
         thresh = 40 
      _, thresh_img = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(thresh_img)
      if len(cnts) > 1:
         cnts_a = biggest_cnts(cnts, 10)
         cnts = cnts_a[0]
         if cnts[2] > cnts[3]:
           cnt_size = cnts[2]
         else:
           cnt_size = cnts[3]
      else:
         cnt_size = 5

      if pxd > 25:
         adj_x, adj_y = grid_intensity_center(frame, cnt_size) 
         ccx = tcx + adj_x
         ccy = tcy + adj_y
         cv2.rectangle(thresh_img, (ccx-2, ccy-2), (ccx+2, ccy+2), (255,255,255), 1, cv2.LINE_AA)
         cv2.putText(thresh_img, str(fn) + " " + str(adj_x) + " " + str(adj_y),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .2, (255, 255, 255), 1)
         tracking_updates[fn] = [adj_x, adj_y]


      fn += 1
      #cv2.imshow("ROITHRESH", thresh_img)
      #cv2.waitKey(30)
   for key in tracking_updates:
      print(key, tracking_updates[key])
   #exit()
   return(tracking_updates)

def fireball_phase1(hd_frames, hd_color_frames, subframes,sum_vals,max_vals,pos_vals, video_file, json_conf, jsf, jdata, best_meteor, nomask):
   print("FRAMES:", len(hd_frames), len(hd_color_frames))
   #PHASE 1
   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(video_file)

   objects = {}
   # load up the frames
   if len(hd_frames) == 0:
      hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(video_file, json_conf, 0, 0, 1, 1,[])
   i = 0
   med_file = video_file.replace(".mp4", "-med.jpg")

   stack_img = stack_frames(hd_color_frames)
   stack_img = cv2.resize(stack_img, (1280, 720))

   gray_img = cv2.cvtColor(stack_img, cv2.COLOR_BGR2GRAY)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   #thresh =max_val - 100 
   thresh = 80
   if thresh < 0:
      thresh = 10
   _, thresh_img = cv2.threshold(gray_img.copy(), thresh, 255, cv2.THRESH_BINARY)
   fb_mask = cv2.bitwise_not(thresh_img)


   fh, fw = hd_frames[0].shape[:2]
   if fh == 1080:
      HD = 1
   else:
      HD = 0
   # load mask file if it exists
   mask_file = MASK_DIR + cam + "_mask.png"
   if cfe(mask_file) == 1 and nomask == 0:
      mask_img = cv2.imread(mask_file,0)
      mask_img = cv2.resize(mask_img, (fw,fh))

   else:
      mask_img = None

   do_cal = 0
   for key in jdata:
      print("JD:", key)
   if "cp" in jdata:
      cp = jdata['cp']
   else:
      cp = calib_image(video_file, hd_frames[0], json_conf)

   if "user_mods" in jdata:
      print("USERMODS")
      print(cp)
      print(jdata['user_mods'])
      user_mods = jdata['user_mods']
      cp['user_stars'] = get_image_stars(video_file, hd_frames[0].copy(), json_conf, 1)
      if "user_stars" in user_mods:
         for star in user_mods['user_stars']:
            print("ADDING USER STARS", star)
            cp['user_stars'].append(star)
      stack_img_l = cv2.resize(stack_img, (1920, 1080))
      cp = pair_stars(cp, video_file, json_conf, stack_img_l)
      #exit() 
   else:
      user_mods = None
      cp['user_stars'] = get_image_stars(video_file, hd_frames[0].copy(), json_conf, 1)
      stack_img_l = cv2.resize(stack_img, (1920, 1080))
      cp = pair_stars(cp, video_file, json_conf, stack_img_l)


   print("FIREBALL4!")
   print("NEW CP:", cp['cat_image_stars'])
   print("NEW US:", cp['user_stars'])
   #exit()
   x = cp['total_res_px']
   if math.isnan(x) is True:
      print("ISNANA")
      cp['total_res_deg'] = 999
      cp['total_res_px'] = 999

   if cfe(med_file) == 0:
      median_frame = cv2.convertScaleAbs(np.median(np.array(hd_frames), axis=0))
       
      median_frame = cv2.GaussianBlur(median_frame, (7, 7), 0)
      cv2.imwrite(med_file, median_frame)
   else:
      median_frame = cv2.imread(med_file)
      median_frame = cv2.cvtColor(median_frame, cv2.COLOR_BGR2GRAY)

   print("PHASE 1 MAIN", len(hd_frames))
   # PHASE 1 MAIN Loop
   last_sub = None
   frame_num = 0
   subs = []
   if hd_frames[0].shape[0] != fb_mask.shape[0] and hd_frames[0].shape[1] != fb_mask.shape[1] :
      fb_mask = cv2.resize(fb_mask, (hd_frames[0].shape[1], hd_frames[0].shape[0]))
   past_points = []
   for frame in hd_frames:
      color_frame = hd_color_frames[frame_num]
      #if best_meteor is not None:
      #   continue
      frame = mask_stars(frame, cp)

      #frame = mask_points(frame, past_points )
      #cv2.imshow("FR", frame)
      #cv2.waitKey(30)
      frame = cv2.subtract(frame, fb_mask)
      meteor_on = 0
      # This causes problems for dim meteors...
      subframe = frame
      #subframe = cv2.subtract(frame, median_frame)
      if last_sub is None:
         last_sub = subframe
      if frame_num > 10:
         last_sub = subs[-10]
      if frame_num > 25:
         last_sub = subs[-25]
      sub_diff = cv2.subtract(subframe, last_sub)
      last_sub = subframe.copy()
      subs.append(last_sub)
      subframe = sub_diff

      sdframe = cv2.resize(sub_diff, (640, 360))

      #if mask_img is not None and nomask ==0:
      #   subframe = cv2.subtract(frame, mask_img)
      #   sub_diff = cv2.subtract(sub_diff, mask_img)


      bx,by = pos_vals[i]
      bx1,by1,bx2,by2 = bound_cnt(bx, by,frame.shape[1],frame.shape[0], 50)

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub_diff)
      avg_val = np.mean(sub_diff)
      half_max = ((max_val - avg_val) / 4) + avg_val

      thresh = best_thresh(sub_diff, half_max, i)
      cnts,rects = find_contours_in_frame(sub_diff, thresh=thresh)
      if len(cnts) > 2:
         cnts = biggest_cnts(cnts, 10)
      #cnts = get_contours_in_image(subframe)
     
      # Here we are inside 1 single frame and loop over all contours 
      mark_objs = []
      for cx,cy,cw,ch in cnts:
         #cv2.rectangle(subframe, (cx, cy), (cx+cw, cy+ch), (255,255,255), 3, cv2.LINE_AA)
         ccx = cx + int(cw / 2)
         ccy = cy + int(ch / 2)
         rx1,ry1,rx2,ry2 = bound_cnt(ccx, ccy,frame.shape[1],frame.shape[0], 50)
         size = int((cw+ch)/2)
         past_points.append((ccx,ccy,size))
         cnt_img = frame[cy:cy+ch,cx:cx+cw]
         roi_img = frame[ry1:ry2,rx1:rx2]
         cnt_int = int(np.sum(cnt_img))

         if False:
            adj_x, adj_y = grid_intensity_center(roi_img, cw) 
            ccx = ccx + adj_x
            ccy = ccy + adj_y
            new_cx = ccx - int(cw/2)
            new_cy = ccy - int(ch/2)
         #new_x, new_y = center_roi_blob(color_frame, ccx, ccy,int((cw+ch)/2)) 
         object, objects = find_object(objects, frame_num,cx, cy, cw, ch, cnt_int, HD, 0, None)
         #print(objects[object]['fs_dist'])
         #print(objects[object]['segs'])
         objects[object] = analyze_object(objects[object], 1,1)
         if "meteor" in objects[object]:
            if objects[object]['meteor'] == 1 and objects[object]['non_meteor'] == 0:
               objects[object]['class'] = 'meteor'

         if "class" in objects[object]['report']: 
            #desc += " - " + objects[object]['report']['class'] + " " + str(objects[object]['report']['meteor']) + str(objects[object]['report']['non_meteor']) + str(objects[object]['report']['bad_items']) + str(objects[object]['oxs'])
            if objects[object]['report']['meteor'] == 1 and objects[object]['report']['non_meteor'] == 0:
                objects[object]['report']['class'] = "meteor"
                #rx1,ry1,rx2,ry2 = bound_cnt(ccx, ccy,frame.shape[1],frame.shape[0], 50)
                #cv2.rectangle(subframe, (rx1, ry1), (rx2, ry2), (255,0,0), 1, cv2.LINE_AA)
            desc = "OBJ:" + str(object) + " - " + objects[object]['report']['class'] 
            meteor_on = 1
            mark_objs.append([object, objects[object], ccx,ccy])
      if SHOW == 1:
         subframe = mark_up_meteor_frame(subframe, mark_objs, cp)
      


      #if meteor_on == 1:
      if True:

         if SHOW == 1:
            sframe = cv2.resize(subframe, (1280, 720))
            #sframe = cv2.resize(frame, (1280, 720))
            desc = "Frame:" + str(i)
            cv2.putText(sframe, desc,  (10,40), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            #desc = str(sum_vals[i][0]) + " " + str(max_vals[i][0]) + " " + str(pos_vals[i][0]) + " " + str(len(cnts))
            #desc = str(obj)
            #cv2.putText(sframe, desc,  (10,70), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
            cv2.imshow('pepe', sframe)
            cv2.waitKey(0)
         i += 1
      frame_num = frame_num + 1

   m = 0
   meteors = []

   print(objects)
   for obj in objects:
      print("MIKE OBJ:", obj, objects[obj]['ofns'], objects[obj]['report']['bad_items'], objects[obj]['fs_dist'])
   #print("BEST:", best_meteor)
   #if best_meteor is None:
   if True:
      max_int = 0
      best = None
      for obj in objects:
         objects[obj] = analyze_object(objects[obj], 1,1)
         if len(objects[obj]['report']['bad_items']) == 0:
            if max(objects[obj]['oint']) > max_int:
               best = obj
               max_int = max(objects[obj]['oint'])
      obj = best
      if best is not None:
         best_meteor = objects[best]
      else:
         print("No best object." )
         for obj in objects:
            print(obj, len(objects[obj]['ofns']), objects[obj]['report']['bad_items'])
   return(best_meteor, hd_frames, hd_color_frames, median_frame,mask_img,cp )

def fireball_phase2(video_file, json_conf, jsf, jdata, best_meteor, nomask,hd_frames, hd_color_frames, median_frame, mask_img):
   # PHASE 2
   # HERE THE 1st RUN OF THE METEOR SHOULD BE DONE. WE EITHER JUST RAN IT OR LOADED IT. 
   # NOW TIME TO REFINE. 
   # IF NO BEST METEOR EXISTS WE SHOULD END WITH NO DETECT. 

   #best_meteor['ccxs'] = []
   #best_meteor['ccys'] = []

   stack_img = stack_frames(hd_color_frames)
   stack_img = cv2.resize(stack_img, (1280, 720))

   gray_img = cv2.cvtColor(stack_img, cv2.COLOR_BGR2GRAY)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_img)
   thresh =max_val - 45 
   if thresh < 0:
      thresh = 10 
   _, thresh_img = cv2.threshold(gray_img.copy(), thresh, 255, cv2.THRESH_BINARY)
   fb_mask = cv2.bitwise_not(thresh_img)
   masked_stack = cv2.subtract(gray_img, fb_mask)

   mfh, mfw = hd_frames[0].shape[:2]
   fb_mask = cv2.resize(fb_mask, (1280, 720))
   median_frame = cv2.resize(fb_mask, (1280, 720))
   fb_mask_c = cv2.cvtColor(fb_mask,cv2.COLOR_GRAY2BGR)
   fh, fw = hd_frames[0].shape[:2]
   hdm_x = 1280 / fw
   hdm_y = 720 / fh 

   #LOOP OVER THE METEOR AGAIN AND REFINE THE BLOBS 
   # INSIDE A ZOMMED DROP
   x_segs = []
   y_segs = []
   new_cxs = []
   new_cys = []
   objects = {}
   for i in range(0, len(best_meteor['oxs'])):
      fn = best_meteor['ofns'][i] 
      if fn == 0:
         last_frame = hd_frames[fn]
      elif fn <= 5:
         last_frame = hd_frames[fn-1]
      elif 5 < fn <= 10:
         last_frame = hd_frames[fn-5]
      elif 10 < fn <= 20:
         last_frame = hd_frames[fn-10]
      elif 20 < fn <= 30:
         last_frame = hd_frames[fn-20]
      else:
         last_frame = hd_frames[fn-30]
     
      #fn = ff + i
      img = hd_frames[fn]
      last_frame = cv2.resize(last_frame, (1280,720))
      img = cv2.resize(img, (1280,720))
      print("MSK, IMG,", fb_mask_c.shape, img.shape)
      masked_img = cv2.subtract(img, fb_mask)
      masked_img = cv2.subtract(masked_img, median_frame)
      masked_img = cv2.subtract(masked_img, last_frame)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(masked_img)
      thresh =max_val - 35 
      if thresh < 0:
         thresh = 10 

      if "ccxs" not in best_meteor:
         x = int(best_meteor['oxs'][i] * hdm_x)
         y = int(best_meteor['oys'][i] * hdm_y)
         w = int(best_meteor['ows'][i] * hdm_x)
         h = int(best_meteor['ohs'][i] * hdm_y)
         cx = x + int(w/2)
         cy = y + int(h/2)
      else:
         print("CCXS:", i, best_meteor['ccxs'])
         x = int(best_meteor['oxs'][i] * hdm_x)
         y = int(best_meteor['oys'][i] * hdm_y)
         w = int(best_meteor['ows'][i] * hdm_x)
         h = int(best_meteor['ohs'][i] * hdm_y)
         cx = best_meteor['ccxs'][i]
         cy = best_meteor['ccys'][i]
      new_cx = cx
      new_cy = cy
      lim = 50
      rx1,ry1,rx2,ry2 = bound_cnt(cx, cy,1280,720, lim)
      new_x = cx
      new_y = cy
       
      if True:
         of = hd_color_frames[fn].copy()
         of = cv2.resize(of, (1280,720))
         cf = hd_color_frames[fn].copy()
         cf = cv2.resize(cf, (1280,720))
         cv2.rectangle(cf, (x, y), (x+w, y+h), (255,0,0), 1, cv2.LINE_AA)
         roi_img = of[ry1:ry2,rx1:rx2] 
         if roi_img.shape[0] != 100 or roi_img.shape[1] != 100:
            roi_p = np.zeros((100,100,3),dtype=np.uint8)
            px = 100 - roi_img.shape[1]
            py = 100 - roi_img.shape[0]
            roi_p[py:100, px:100] = roi_img
         else:
            roi_p = roi_img
         
         rh, rw = roi_p.shape[:2]
         cv2.rectangle(cf, (rx1, ry1), (rx2, ry2), (0,0,255), 1, cv2.LINE_AA)
         cv2.rectangle(masked_img, (rx1, ry1), (rx2, ry2), (128,0,0), 1, cv2.LINE_AA)
         cv2.rectangle(masked_img, (x, y), (x+w, y+h), (255,0,0), 1, cv2.LINE_AA)
         masked_img = cv2.resize(masked_img, (640,360))
         cci = np.zeros((720,1280,3),dtype=np.uint8)
         masked_img_c = cv2.cvtColor(masked_img,cv2.COLOR_GRAY2BGR)
         roi_p_b = cv2.resize(roi_p, (640,640))
         #cv2.line(roi_p_b, (320,0), (320,640), (255,255,255), 1)

         (dom_dir, quad, ideal_pos, ideal_roi_big_img) = get_movement_info(best_meteor, 640, 640)
         ipx1,ipy1,ipx2,ipy2 = ideal_pos
         #cv2.rectangle(roi_p_b, (ipx1, ipy1), (ipx2, ipy2), (255,255,0), 2, cv2.LINE_AA)

         roi_p_b_g = cv2.cvtColor(roi_p_b, cv2.COLOR_BGR2GRAY)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(roi_p_b_g)
         _, threshold = cv2.threshold(roi_p_b_g.copy(), max_val - 5, 255, cv2.THRESH_BINARY)
         thresh_obj = cv2.dilate(threshold.copy(), None , iterations=6)

         cnts,rects = find_contours_in_frame(thresh_obj, 100)
         if len(cnts) > 1:
            cnts = lead_cnts(cnts, dom_dir, quad)
         for scx, scy, scw, sch in cnts:
            sccx = int(scx + (scw/2))
            sccy = int(scy + (sch/2))
            adj_x = sccx - 320
            adj_y = sccy - 320
            cv2.rectangle(thresh_obj, (scx, scy), (scx+scw, scy+sch), (255,255,0), 2, cv2.LINE_AA)
            cv2.line(thresh_obj, (sccx,sccy), (320,320), (255,255,255), 1)
            print("ADJ:", adj_x, adj_y)
            adj_x = int(adj_x / 6.4)
            adj_y = int(adj_y / 6.4)
            adj_x = 0
            adj_y = 0
            if roi_img.shape[0] == 100 and roi_img.shape[1] == 100:
               new_x = cx + adj_x
               new_y = cy + adj_y
            nrx1,nry1,nrx2,nry2 = bound_cnt(new_x, new_y,1280,720, 50)
            cv2.rectangle(cf, (nrx1, nry1), (nrx2, nry2), (255,0,255), 2, cv2.LINE_AA)
            cv2.imshow('crop', thresh_obj)
            cv2.waitKey(30)
            roi_img = of[nry1:nry2,nrx1:nrx2] 

         cv2.circle(cf,(new_cx,new_cy), 10, (255,255,255), 1)
         new_cxs.append(new_cx)
         new_cys.append(new_cy)

         threshold = cv2.convertScaleAbs(thresh_obj)
         threshold_c = cv2.cvtColor(threshold,cv2.COLOR_GRAY2BGR)

         #cv2.line(roi_p_b_g, (0,320), (640,320), (255,255,255), 1)
         #cci[0:640,640:1280] = roi_p_b
         new_roi = cv2.resize(roi_img, (640,640))
         cci[0:640,640:1280] = new_roi 
         #cci[0:640,640:1280] = threshold_c
         orig_img = cv2.resize(cf, (640,360))
         cci[0:360,0:640] = orig_img
         #cci[0:rh,0:rw] = roi_p
         #cci[360:720,640:1280] = roi_img



         cv2.imshow('pepe', cci)
         cv2.waitKey(30)
   print("NEW:", len(new_cxs))
   exit()
   best_meteor['ccxs'] = new_cxs
   best_meteor['ccys'] = new_cys


   #for i in range(0, len(best_meteor['oxs'])):
   #   fn = best_meteor['ofns'][i] 
   #   frame = hd_color_frames[fn]
   #   frame = cv2.resize(frame, (1280,720))


   return(best_meteor)

def center_roi_blob(frame, cx, cy,cnt_size): 
   fh, fw = frame.shape[:2]
   oframe = frame.copy()
   roi_size = 100 
   roi_size2 = roi_size * 2 
   rx1,ry1,rx2,ry2 = bound_cnt(cx, cy,fw,fh, roi_size)
   roi_img = frame[ry1:ry2,rx1:rx2]
   if roi_img.shape[0] != roi_size2  or roi_img.shape[1] != roi_size2:
      roi_p = np.zeros((roi_size2,roi_size2,3),dtype=np.uint8)
      px = (roi_size2 ) - roi_img.shape[1]
      py = (roi_size2)- roi_img.shape[0]
      roi_p[py:roi_size2, px:roi_size2] = roi_img
   else:
      roi_p = roi_img

   gray_roi = cv2.cvtColor(roi_p, cv2.COLOR_BGR2GRAY)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_roi)
   thresh = max_val - 40
   _, threshold = cv2.threshold(gray_roi.copy(), thresh, 255, cv2.THRESH_BINARY)
   threshold = cv2.cvtColor(threshold, cv2.COLOR_GRAY2BGR)

   roi_disp = np.zeros((720,1280,3),dtype=np.uint8)
   roi_div = 360 / roi_size2
   roi_p = cv2.resize(roi_p, (360,360))
   threshold = cv2.resize(threshold, (360,360))
   grid_size = 5
   best_sum = 0
   best_grid = None
   grid_squares = []
   for col in range(0, int(360/grid_size)):
      for row in range(0, int(360/grid_size)):
         gx1 = col * grid_size
         gy1 = row * grid_size
         gx2 = gx1 + grid_size 
         gy2 = gy1 + grid_size 
         grid_sum_img = roi_p[gy1:gy2,gx1:gx2]
         grid_sum = np.sum(grid_sum_img)
         grid_squares.append((gx1,gy1,gx2,gy2,grid_sum))
         if grid_sum > best_sum: 
            best_sum = grid_sum
            best_grid = [gx1,gy1,gx2,gy2]

   print("SIZE:", cnt_size)
   if cnt_size < 20:
      grid_lim = 3
   elif 20 <= cnt_size <= 30:
      grid_lim = 5
   elif 30 <= cnt_size <= 40:
      grid_lim = 7 
   elif 40 <= cnt_size <= 50:
      grid_lim = 10
   elif 50 <= cnt_size <= 60:
      grid_lim = 15
   else:
      grid_lim = 25 

   sorted_grids = sorted(grid_squares, key=lambda x: (x[4]), reverse=True)
   gxs = []
   gys = []
   for best_grid in sorted_grids[0:grid_lim]:
      gx1,gy1,gx2,gy2,grid_sum = best_grid 
      gxs.append((gx1, gx2))
      gys.append((gy1, gy2))
      cv2.rectangle(roi_p, (gx1, gy1), (gx2, gy2), (255,255,0), 1, cv2.LINE_AA)
   mgx = int(np.mean(gxs))
   mgy = int(np.mean(gys))

   adj_x = int((mgx - 180) / roi_div)
   adj_y = int((mgy - 180) / roi_div)
   new_x = cx+adj_x
   new_y = cy+adj_y
   if False:
      rx1,ry1,rx2,ry2 = bound_cnt(cx+adj_x, cy+adj_y,fw,fh, roi_size)
      new_roi_img = oframe[ry1:ry2,rx1:rx2]
      if new_roi_img.shape[0] != roi_size2  or new_roi_img.shape[1] != roi_size2:
         new_roi_p = np.zeros((roi_size2,roi_size2,3),dtype=np.uint8)
         px = (roi_size2 ) - new_roi_img.shape[1]
         py = (roi_size2)- new_roi_img.shape[0]
         new_roi_p[py:roi_size2, px:roi_size2] = new_roi_img
      else:
         new_roi_p = new_roi_img
      cv2.imshow('new roi_p', new_roi_p)
      new_roi_p = cv2.resize(new_roi_p, (360,360))

      cv2.circle(roi_p,(mgx,mgy), 3, (0,0,255), 1)
      cv2.line(new_roi_p, (0,180), (360,180), (255,255,255), 1)
      cv2.line(new_roi_p, (180,0), (180,360), (255,255,255), 1)
      cv2.line(roi_p, (0,180), (360,180), (255,255,255), 1)
      cv2.line(roi_p, (180,0), (180,360), (255,255,255), 1)

      roi_disp[0:360, 0:360] = roi_p
      roi_disp[0:360, 360:720] = new_roi_p 
      cv2.imshow('roi_center', roi_disp)
      cv2.waitKey(30)
   return(new_x, new_y)





def fireball_phase3(video_file, json_conf, jsf, jdata, best_meteor, nomask,hd_frames, hd_color_frames, median_frame, mask_img,med_times):
   fh, fw = hd_frames[0].shape[:2]
   hdm_x = 1280 / fw
   hdm_y = 720 / fh 

   vid_fn, vid_dir = fn_dir(video_file)
   # PHASE 3
   p_res_tot = 0 
   p_res_pt = 0

   # loop over points and correct the worst ones based on the estimate
   new_xs = []
   new_ys = []
   for i in range(0, len(best_meteor['oxs'])):
      fn = best_meteor['ofns'][i]
      frame = hd_color_frames[fn].copy()
      frame = cv2.resize(frame, (1280,720))
      ox = int(best_meteor['oxs'][i]*hdm_x)
      oy = int(best_meteor['oys'][i]*hdm_y)
      ow = int(best_meteor['ows'][i]*hdm_x)
      oh = int(best_meteor['ohs'][i]*hdm_y)
      cur_x = int(ox + (ow/2))
      cur_y = int(oy + (oh/2))
      if ow < oh:
         avg_size = ow
      else:
         avg_size = oh
      new_x, new_y = center_roi_blob(frame, cur_x, cur_y,avg_size) 
      new_xs.append(new_x)
      new_ys.append(new_y)



   best_meteor['ccxs'] = new_xs
   best_meteor['ccys'] = new_ys

   fireball_plot_points(best_meteor)
   new_new_xs = []
   new_new_ys = []
   est_xs = []
   est_ys = []
   past_points = []
   for i in range(0, len(best_meteor['oxs'])):
      tf = len(best_meteor['oxs']) -1 
      fn = best_meteor['ofns'][i]
      frame = hd_color_frames[fn].copy()
      frame = cv2.resize(frame, (1280,720))
      cur_x = best_meteor['ccxs'][i]
      cur_y = best_meteor['ccys'][i]

      ox1 = int(best_meteor['oxs'][i] * hdm_x)
      oy1 = int(best_meteor['oys'][i] * hdm_y)
      ow = best_meteor['ows'][i]*hdm_x
      oh = best_meteor['ohs'][i]*hdm_x
      ox2 = int(best_meteor['oxs'][i] * hdm_x) + int(best_meteor['ows'][i]*hdm_x)
      oy2 = int(best_meteor['oys'][i] * hdm_y) + int(best_meteor['ohs'][i]*hdm_y)
      size = int((ow+oh)/2) 
      past_points.append((cur_x,cur_y,size))

      avg_size = (ow + oh) / 2
      rects = []

      # we are at the start, so use same array len for before and after up until frame 10
      if i < 10:
         if i + 1 + i < tf :
            array_len = i
         else:
            array_len = tf - i + 1 + i
      # we are past the start and not yet at the end. it is safe to use est of +/- 10 on each side of the current frame
      elif i + 11 < tf:
         array_len = 11 
      elif i + 11 >= tf:
         array_len = tf - i + 1 + i

         

      if i > 12 and i <= tf-11:
         last_10_x = int(sum(best_meteor['ccxs'][i-array_len-1:i-1])  / array_len)
         last_10_y = int(sum(best_meteor['ccys'][i-array_len-1:i-1])  / array_len)
  
         next_10_x = int(sum(best_meteor['ccxs'][i+1:i+array_len+1])  / array_len)
         next_10_y = int(sum(best_meteor['ccys'][i+1:i+array_len+1])  / array_len)
      else:
         next_10_x = None
         next_10_y = None
         last_10_x = None
         last_10_y = None

      #print("LAST/NEXT:", array_len, last_10_x, last_10_y, next_10_x, next_10_y)

      if last_10_x is not None and next_10_x is not None and i > 10:
         est_x = int((last_10_x + next_10_x) / 2)
         est_y = int((last_10_y + next_10_y) / 2)
      else:
         est_x = cur_x
         est_y = cur_y
      cv2.circle(frame,(est_x,est_y), 10, (0,255,0), 1)
      p_res_err = calc_dist((est_x,est_y), (cur_x, cur_y))
      p_res_tot += p_res_err
      p_res_pt += 1
      avg_res = p_res_tot/p_res_pt
      cv2.putText(frame, "ARES:"+ str(p_res_tot/p_res_pt)[0:4],  (30,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      cv2.putText(frame, "TRES:"+ str(p_res_err)[0:4],  (30,30), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

      circles = []
      text_info = []
      text_info.append(("File: " + vid_fn, 10,30))
      text_info.append(("Frame: " + str(fn), 10,45))
      text_info.append(("Frame Res: " + str(p_res_err), 10,60))
      text_info.append(("Total Res: " + str(avg_res), 10,70))
      circles.append((last_10_x, last_10_y, (0,255,0), "last 10 mean"))
      circles.append((next_10_x, next_10_y, (0,0,255), "next 10 mean"))
      circles.append((cur_x, cur_y, (255,255,255), "cur "))
      circles.append((est_x, est_y, (0,255,255), "est "))
      circles = []
      if p_res_err > (avg_res * med_times):
         new_new_xs.append(cur_x)
         new_new_ys.append(cur_y)
         est_xs.append(est_x)
         est_ys.append(est_y)
         frame =  make_meteor_frame(hd_color_frames[fn], est_x,est_y, fn, circles, rects, text_info,new_xs,new_ys )
      else:
         new_new_xs.append(cur_x)
         new_new_ys.append(cur_y)
         est_xs.append(cur_x)
         est_ys.append(cur_y)
         frame =  make_meteor_frame(hd_color_frames[fn], cur_x,cur_y, fn, circles, rects, text_info, new_xs,new_ys)
      cv2.imshow('pepe', frame)
      if p_res_err > (avg_res * 3) and p_res_err > 2:
         cv2.waitKey(30)
      else:
         cv2.waitKey(30)

   best_meteor['ccxs'] = new_new_xs
   best_meteor['ccys'] = new_new_ys
   best_meteor['est_xs'] = est_xs
   best_meteor['est_ys'] = est_ys 

   for i in range(0, len(best_meteor['oxs'])):
      fn = best_meteor['ofns'][i]
      est_x = best_meteor['est_xs'][i]
      est_y = best_meteor['est_ys'][i]
      cx = best_meteor['ccxs'][i]
      cy = best_meteor['ccys'][i]

      frame =  make_meteor_frame(hd_color_frames[fn], est_x,est_y, fn, [], [], [], [],[])
      cv2.imshow('pepe', frame)
      cv2.waitKey(30)

   #best_meteor = make_final_meteor_vids(meteor_dir, jsf, best_meteor, cp, hd_color_frames, 0)
   jdata = {}
   jdata['best_meteor'] = best_meteor
   save_json_file(jsf, jdata)
   print("saved:" , jsf)
   return(best_meteor)

def apply_calib(video_file, best_meteor, cp,json_conf):
   best_meteor['ras'] = []
   best_meteor['decs'] = []
   best_meteor['azs'] = []
   best_meteor['els'] = []
   for i in range(0, len(best_meteor['oxs'])):
      fn = best_meteor['ofns'][i]
      if "est_x" in best_meteor:
         est_x = best_meteor['est_xs'][i]
         est_y = best_meteor['est_ys'][i]
      cx = best_meteor['ccxs'][i]
      cy = best_meteor['ccys'][i]
      tx, ty, ra ,dec , az, el = XYtoRADec(cx,cy,video_file,cp,json_conf)
      best_meteor['ras'].append(ra) 
      best_meteor['decs'].append(dec) 
      best_meteor['azs'].append(az) 
      best_meteor['els'].append(el) 
   return(best_meteor)
  
def make_meteor_frame(frame, cx,cy, fn=None, circles=None, rects=None, text_info=None, new_xs=None, new_ys=None):
   frame = cv2.resize(frame, (1280,720))
   rx1,ry1,rx2,ry2 = bound_cnt(cx, cy,1280,720, 50)
   roi_img = frame[ry1:ry2,rx1:rx2]


   if circles is not None:
      for x,y,color,text in circles:
         if x is not None:
            cv2.circle(frame,(x,y), 2, color, 1)

   if rects is not None:
      for x1,y1,x2,y2 in rects:
         cv2.rectangle(frame, (x1, y1), (x2, y2), (255,128,128), 1, cv2.LINE_AA)
   point_plot = np.zeros((720,1280,3),dtype=np.uint8)

   cci = np.zeros((720,1280,3),dtype=np.uint8)
   if roi_img.shape[0] != 100 or roi_img.shape[1] != 100:
      roi_p = np.zeros((100,100,3),dtype=np.uint8)
      px = 100 - roi_img.shape[1]
      py = 100 - roi_img.shape[0]
      roi_p[py:100, px:100] = roi_img
   else:
      roi_p = roi_img


   new_roi_big = cv2.resize(roi_p, (640,640))
   point_plot = cv2.resize(point_plot, (640,360))
   cv2.line(new_roi_big, (0,320), (640,320), (255,255,255), 1)
   cv2.line(new_roi_big, (320,0), (320,640), (255,255,255), 1)
   #cv2.line(roi_p_b_g, (0,320), (640,320), (255,255,255), 1)
   #cci[0:640,640:1280] = roi_p_b
   cci[0:640,640:1280] = new_roi_big
   orig_img = cv2.resize(frame, (640,360))
   cci[0:360,0:640] = orig_img
   cci[360:720,0:640] = point_plot 

   if text_info is not None:
      for data in text_info:
         desc, tx, ty = data 
         cv2.putText(cci, desc,  (tx,ty), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)

   return(cci)


def lead_cnts(cnts, dom_dir, quad):
   hor_mov = quad[0]
   vert_mov = quad[1]
   if hor_mov == "right":
      best_x = 0
   else:
      best_x = 9999
   if vert_mov == "down":
      best_y = 0
   else:
      best_y = 9999
   best_y = 0
   best_cnt = []
   print(dom_dir, hor_mov, vert_mov)
   print(cnts)
   for x,y,w,h in cnts:
      x1 = x
      y1 = y
      x2 = x + w
      y2 = y + h
      if dom_dir == 'x' and hor_mov == "right":
         if x2 > best_x:
            best_x = x2
            best_cnt = [[x,y,w,h]]
      if dom_dir == 'x' and hor_mov == "left":
         if x1 < best_x:
            best_x = x1
            best_cnt = [[x,y,w,h]]
      if dom_dir == 'y' and hor_mov == "down":
         if y2 > best_x:
            best_y = y2
            best_cnt = [[x,y,w,h]]
      if dom_dir == 'y' and hor_mov == "top":
         if y1 < best_y:
            best_y = y1
            best_cnt = [[x,y,w,h]]
   return(best_cnt)
def meteor_detect_image(mo, dimg, objects, cp):

   for i in range(0,len(mo['ofns'])):
      x = mo['oxs'][i]
      y = mo['oys'][i]
      print(i, x,y)
   cv2.imshow('pepe', dimg)
   cv2.waitKey(30)

def dom_meteor(meteors, json_conf):
   mcache = {}
   scores = {}
   durs = []
   sizes = []
   dists = []
   for m in meteors:
      id = m['obj_id']
      mcache[id] = m
      maxw = max(m['ows'])
      maxh = max(m['ohs'])
      size = maxw * maxh

      durs.append((id, m['report']['cm']))
      sizes.append((id, size))
      dists.append((id, m['report']['ang_dist']))
      print(m)

   sorted_durs = sorted(durs, key=lambda x: (x[1]), reverse=True)
   sorted_sizes = sorted(sizes, key=lambda x: (x[1]), reverse=True)
   sorted_dists = sorted(dists, key=lambda x: (x[1]), reverse=True)
   m1 =  sorted_durs[0][0]
   m2 =  sorted_sizes[0][0]
   m3 =  sorted_dists[0][0]
   if m1 not in scores:
      scores[m1] = 1
   else:
      scores[m1] += 1
   if m2 not in scores:
      scores[m2] = 1
   else:
      scores[m2] += 1
   if m3 not in scores:
      scores[m3] = 1
   else:
      scores[m3] += 1
   print("\n*******DOM DUR*********\n")
   print(mcache[m1])
   print("\n*******DOM SIZE*********\n")
   print(mcache[m2])
   print("\n*******DOM DIST*********\n")
   print(mcache[m3])
   print("Longest dur :", sorted_durs[0])
   print("Biggest Size:", sorted_sizes[0])
   print("Longest Dist:", sorted_dists[0])
   bm = 0
   bs = 0
   for m in scores:
      score = scores[m]
      if score > bs:
         bs = score
         mb = m
   print("The best meteor is:", m, mcache[m])
   best_meteor = mcache[m]
   return(best_meteor)
  
def first_last_dist(obj, objects):
   fx = objects[obj]['xs'][0]
   fy = objects[obj]['ys'][0]
   lx = objects[obj]['xs'][-1]
   ly = objects[obj]['ys'][-1]
   dist = calc_dist((fx,fy),(lx,ly))
   return(dist)

def frames_to_image(frames):
   h,w = frames[0].shape[:2]
   print(w,h)
   total = len(frames)
   fr_per_row = int(1920 / w)  
   cols = int(total / fr_per_row ) + 1
   print("FRAMES PER ROW:", fr_per_row)
   print("COLS :", cols)
   big_img_w = int(w * fr_per_row) + 1
   big_img_h = int(h * cols) 
   print("SIZE NEEDED FOR BIG IMAGE:", big_img_w, big_img_h)

   big_img = np.zeros((big_img_h,big_img_w),dtype=np.uint8)
   i = 0
   col = 0
   row = 0
   for frame in frames: 
      print("COL:", col, cols)
      print("ROW:", row, cols)
      if col >= fr_per_row:
         col = 0
         row += 1
   
      px1 = col * w 
      py1 = row * h 
      px2 = px1 + w
      py2 = py1 + h
      big_img[py1:py2,px1:px2] = frame
      cv2.imshow('pepe', big_img)
      cv2.waitKey(90)

      col += 1
   
def make_roi_image(frame, thresh_frame, x1,y1,x2,y2):
   marked_frame = frame.copy()
   cv2.rectangle(marked_frame, (x1, y1), (x2, y2), (255,0,0), 1, cv2.LINE_AA)
   roi_img = frame[y1:y2,x1:x2] 
   roi_sub_img = thresh_frame[y1:y2,x1:x2] 
   roi_big_img = cv2.resize(roi_img, (300, 300))
   roi_big_sub_img = cv2.resize(roi_sub_img, (300, 300))
   roi_scale_x = 300 / roi_img.shape[1] 
   roi_scale_y = 300 / roi_img.shape[0] 
   return(marked_frame, roi_img, roi_big_img, roi_big_sub_img, roi_scale_x, roi_scale_y)


def get_leading_cnt(dom_dir, x_dir, y_dir, cnt_x, cnt_y, cnt_w, cnt_h):
   if dom_dir == 'x':
      if x_dir == 'left_to_right':
         # we want the far right side of original cnt x+w
         nx = cnt_x + cnt_w


      elif x_dir == 'right_to_left':
         # we want the far left side of original cnt x
         nx = cnt_x 
      else:
         # no x movement (center cnt) x + (cnt_w/2)
         nx = int(cnt_w/2) + cnt_x 

      if y_dir == 'up_to_down':
         #pick bottom side
         ny = int(cnt_y) + int(cnt_h)
         if cnt_h > 4:
            ny -= int(cnt_h/4)
      elif y_dir == 'down_to_up':
         ny = int(cnt_h) 
      else:
         ny = int(cnt_y) + int(cnt_h)
  


   if dom_dir == 'y':
      if y_dir == 'up_to_down':
          # we want the far down side of original cnt y+h
          ny = cnt_y + cnt_h
 
      elif y_dir == 'down_to_up':
         # we want the far top side of original cnt y
          ny = cnt_y
      else:
         # no x movement (center cnt) x + (cnt_w/2)
         ny = int(cnt_h/2) + cnt_y
      if x_dir == 'left_to_right':
          nx = int(cnt_w) + cnt_x - int(cnt_w/5)
      elif x_dir == 'right_to_left':
          nx = cnt_x + int(cnt_w/5)
      else:
         nx = cnt_x + int(cnt_w/2)


   return(nx,ny)


def get_roi_cnts(meteor, image, median_image, ox,oy, dom_dir, x_dir, y_dir):


   (show_frame, sub_frame, show_subframe, thresh_img, avg_val, max_val, thresh_val) = make_subframe(image, median_image)
   rx1,ry1,rx2,ry2 = bound_cnt(ox, oy,image.shape[1],image.shape[0], 50)
   cnt_img = thresh_img[ry1:ry2,rx1:rx2]
   cnts = get_contours_in_image(cnt_img)

   show_image = cv2.cvtColor(image,cv2.COLOR_GRAY2BGR)
   show_cnt_img = show_image[ry1:ry2,rx1:rx2]

   for x,y,w,h in cnts:
      cv2.rectangle(show_cnt_img, (x,y), (x+w, y+h), (100,0,0), 1, cv2.LINE_AA)


   #if len(cnts) > 1:
   #   cnts,dom_dir,x_dir,y_dir = get_best_cnt(cnts, meteor)
   shift_x = 0
   shift_y = 0
   w= 5
   h = 5
   for x,y,w,h in cnts:
      #lcx, lcy = get_leading_cnt(dom_dir, x_dir, y_dir, x, y, w, h)
      shift_x = x - 50  
      shift_y = y - 50
      #cv2.circle(show_cnt_img,(lcx,lcy), 10, (255,255,255), 1)
      #cv2.rectangle(show_cnt_img, (x,y), (x+w, y+h), (100,0,0), 1, cv2.LINE_AA)
      #cv2.rectangle(show_cnt_img, (lcx-4,lcy-4), (lcx+4, lcx+4), (100,0,0), 1, cv2.LINE_AA)

   if len(cnts) > 0 :

      off_frame = check_off_frame(image, rx1+shift_x,ry1+shift_y,rx2+shift_x,ry2+shift_y)
      if off_frame == 0:
         new_cnt_img = thresh_img[ry1+shift_y:ry2+shift_y,rx1+shift_x:rx2+shift_x]

         # THIS SHOULD BE THE REFINED x,y inside the "crop" frame.
         new_cnt = [ ox+shift_x, oy+shift_y, w, h]
         #big_cnt = cv2.resize(show_cnt_img, (300, 300))
         #big_new_cnt = cv2.resize(new_cnt_img, (300, 300))
         #cv2.waitKey(30)
         return(new_cnt)

   return(None)


def check_off_frame(frame, x1,y1,x2,y2):
   h,w = frame.shape[:2]
   if x1 < 0 or y1 < 0 or x2 < 0 or y2 < 0:
      return(1)
   if x1 > w or y1 > h or x2 > w or y2 > h:
      return(1)
   return(0)

def get_dist_info(crop_frames, ofns, oxs, oys):
   cx1 = 0
   cy1 = 0
   x_dist = []
   y_dist = []
   # get the distance info for all points (move to function)
   fn = 0
   mc = 0
   last_x = None
   for frame in crop_frames:
      if ofns[0] <= fn <= ofns[-1]:
         inside_meteor = 1
      else:
         inside_meteor = 0
      if inside_meteor == 1 and fn in ofns:

         if last_x is not None:
            xd = oxs[mc] - cx1 - last_x
            yd = oys[mc] - cy1 -  last_y
            fr_diff = fn - last_fn
            if last_fn > 1:
               xd = int(xd/fr_diff)
               yd = int(yd/fr_diff)
            x_dist.append(xd)
            y_dist.append(yd)

         last_x = oxs[mc]-cx1
         last_y = oys[mc]-cy1
         last_fn = ofns[mc]
         mc = mc + 1
      elif inside_meteor == 1 and fn not in ofns:
         print("MISSING A GAP FRAME HERE!", fn, inside_meteor, ofns)

      fn = fn + 1
   med_x = np.median(x_dist)
   med_y = np.median(y_dist)
   return(x_dist, y_dist, med_x, med_y)

def refine_meteor_points(meteor, crop_frames, json_conf):
   fn = 0
   mc = 0
   ofns = meteor['ofns']
   oxs = meteor['oxs']
   oys = meteor['oys']
   ohs = meteor['ows']
   ows = meteor['ohs']
   print(meteor)
   cx1,cy1,cx2,cy2,mx,my = meteor['cropbox_1080']
   inside_meteor = 0
   x_dist = []
   y_dist = []
   dist = []
   last_x = None
   last_y = None
   gap_frames = []

   median_frame = cv2.convertScaleAbs(np.median(np.array(crop_frames), axis=0))
   median_frame = cv2.GaussianBlur(median_frame, (7, 7), 0)

   #(dom_dir, quad, ideal_pos, ideal_roi_big_img) = get_movement_info(meteor, 10, 10)
   dom_dir, x_dir, y_dir = get_move_info(meteor, 10, 10)
   past_cnts = []

   dist_x, dist_y, med_x, med_y = get_dist_info(crop_frames, ofns, oxs, oys)


   # redraw the frames filling in est position for all frames and gap frames based on the start x,y and med_dist
   nfns = []
   nxs = []
   nys = []
   exs = []
   eys = []
   start_x = oxs[0]
   start_y = oys[0] 
   c = 0
   ic = 0
   for i in range(ofns[0], ofns[-1]+1):
      ex = int(start_x+med_x*ic)
      ey = int(start_y+med_y*ic)
      exs.append(ex)
      eys.append(ey)

      if i in ofns:
         ox = oxs[c]
         oy = oys[c]
         xd = ox - ex
         yd = oy - ey
         if xd > 200:
            #nxs.append(ex)
            nxs.append(ox)
         else:
            nxs.append(ox)
         if yd > 200:
            #nys.append(ey)
            nys.append(oy)
         else:
            nys.append(oy)
         c += 1
         ic += 1
      else:
         nxs.append(ex)
         nys.append(ey)
         ic += 1
      nfns.append(i)
      

   # now step through each frame and look for a cnt near the point.  
   # if you find one, update the shift_x, shift_y 
   new_cnts = []
   past_cnts = []
   c = 0
   for i in range(nfns[0], nfns[-1]+1):
      frame = crop_frames[i]
     
      (show_frame, sub_frame, show_subframe, thresh_img, avg_val, max_val, thresh_val) = make_subframe(frame, median_frame,2,past_cnts,dom_dir,x_dir,y_dir)
      off_frame = check_off_frame(frame, nxs[c]-cx1, nys[c]-cy1, 10, 10)
      if off_frame == 1:
         
         new_cnts.append(None)
         continue
      cnts = get_roi_cnts(meteor, frame, median_frame, nxs[c]-cx1, nys[c]-cy1, dom_dir, x_dir, y_dir)
      new_cnts.append(cnts)
      if cnts is not None:
         # update the final x,y for the 'leading edge' and blob center 
         # BLOB CENTER X,Y
         nxs[c] = cnts[0] + int(cnts[2]/2)
         nys[c] = cnts[1] + int(cnts[3]/2)
         # LEADING X,Y 
         lcx, lcy = get_leading_cnt(dom_dir, x_dir, y_dir, cnts[0], cnts[1], cnts[2], cnts[3])
         past_cnts.append(cnts)
      else:
         lcy = None
         lcx = None
         past_cnts.append((nxs[c],nys[c],10,10))
      #if lcy is not None:
      #   cv2.circle(frame,(lcx, lcy), 2, (0,0,255), 1)
      #cv2.circle(frame,(nxs[c], nys[c]), 10, (255,255,255), 1)
      #cv2.imshow('final-check-new_cnts', frame)
      #cv2.waitKey(30)
      c += 1


   status, nfns, nxs, nys, new_cnts = check_last_frame(nfns, nxs, nys, new_cnts)
   status, nfns, nxs, nys, new_cnts = check_last_frame(nfns, nxs, nys, new_cnts)
   status, nfns, nxs, nys, new_cnts = check_last_frame(nfns, nxs, nys, new_cnts)
   status, nfns, nxs, nys, new_cnts = check_last_frame(nfns, nxs, nys, new_cnts)

   # We should be almost done here just check to see how it looks and apply the leading x,y area?
   c = 0
   leading_xs = []
   leading_ys = []
   for i in range(nfns[0], nfns[-1]+1):
      frame = crop_frames[i]
      show_frame = cv2.cvtColor(frame,cv2.COLOR_GRAY2BGR)
      x = nxs[c]
      y = nys[c]
      if new_cnts[c] is not None:
         sx, sy, cw, ch = new_cnts[c]
         #cx = x - (sx -50)
         #cy = y - (sy -50)
         cx = x
         cy = y
      else:
         cx = x
         cy = y
         cw = 10
         ch = 10
      leading_xs.append(cx)
      leading_ys.append(cy)
      c += 1
      #cv2.rectangle(show_frame, (cx-2, cy-2), (cx+2, cy+2), (255,0,0), 1, cv2.LINE_AA) 
      #cv2.imshow('final final', show_frame)
      #cv2.waitKey(30)
   return(nfns, nxs,nys,new_cnts)


def check_last_frame(fns, xs, ys, new_cnts):
   lf = len(fns) - 1
   if new_cnts[lf] is None:
      fns.pop(lf)
      xs.pop(lf)
      ys.pop(lf)
      new_cnts.pop(lf)
      status = 0
   else:
      status = 1
   return(status, fns, xs, ys, new_cnts)

def block_past_cnts(img, cnts):
   for x,y,w,h in cnts:
      img[y:y+h,x:x+w] = 0
   return(img)


def make_subframe(frame, median_frame, thresh_div=2, past_cnts=None,dom_dir=None,x_dir=None,y_dir=None):
   show_frame = frame.copy()
   show_frame = cv2.cvtColor(show_frame,cv2.COLOR_GRAY2BGR)
   subframe = cv2.subtract(frame, median_frame)
   print("DOM:", dom_dir, x_dir, y_dir)
   print("PAST CNT:", past_cnts)
   if past_cnts is not None:
      for cnt in past_cnts:
         if cnt is not None:
            x,y,w,h = cnt
            if dom_dir is None:
               subframe[y:y+h,x:x+w] = 0
            else:
               if dom_dir == "x":
                  if x_dir == "right_to_left":
                     subframe[0:subframe.shape[0],x:subframe.shape[1]] = 0
                  else:
                     print("XY CNT:", x,y,w,h)
                     subframe[y:y+h,0:x] = 0
   cv2.imshow("SUB", subframe)
   cv2.waitKey(30)

   avg_val = np.mean(subframe)
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(frame)
   thresh = max_val - int(max_val / thresh_div)
   thresh = find_best_thresh(subframe, max_val)
   _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)

   cnts = get_contours_in_image(threshold)
   print("LEN CNTS:", len(cnts))
   if len(cnts) == 0:
      thresh = thresh - 10
      _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(threshold)
      print("NEW LEN CNTS:", len(cnts))
   if len(cnts) > 1:
      thresh = thresh + 10
      _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(threshold)
      print("NEW LEN CNTS:", len(cnts))


   show_subframe = cv2.cvtColor(subframe,cv2.COLOR_GRAY2BGR)

   return(show_frame, subframe, show_subframe, threshold, avg_val, max_val, threshold)

def find_best_thresh(subframe, thresh):
   tvals = []
   tvals2 = []
   last_cnts = None
   # starting at max val lower thresh until there is more than 1 cnt, the step before this is the ideal thresh
   for i in range(0, 50):
      thresh = thresh - 5
      _, threshold = cv2.threshold(subframe.copy(), thresh, 255, cv2.THRESH_BINARY)
      cnts = get_contours_in_image(threshold)
      last_thresh = thresh
      last_cnts = len(cnts)
      if len(cnts) <= 1:
         tvals.append((thresh,len(cnts)))
      elif len(cnts) == 2:
         tvals2.append((thresh,len(cnts)))
      #print("THRESH:", thresh, last_thresh, len(cnts), last_cnts)
      if thresh < 5:
         break
   if len(tvals) > 0:
      temp = sorted(tvals, key=lambda x: (x[0]), reverse=False)
   elif len(tvals2) > 0:
      temp = sorted(tvals2, key=lambda x: (x[0]), reverse=False)
   else:
      # NO BEST THRESH
      return(20)

   best_thresh = temp[0][0]
   print("BEST THRESH!", best_thresh)
   return(best_thresh)


def refine_all_meteors(day, json_conf):
   mfs = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")
   for mf in mfs:
      if "reduced" not in mf:
         print("REFINE:", mf)
         refine_meteor(mf, json_conf)

def refine_meteor(meteor_file, json_conf):
   console_image = np.zeros((720,1280),dtype=np.uint8)
   color_console_image = np.zeros((720,1280,3),dtype=np.uint8)
   leading_xs = []
   leading_ys = []
   intensity = []
   max_pxs = []
   js = load_json_file(meteor_file)

   # first make sure we are dealing with a  'good' meteor. 
   # if detection info is missing re-decect and confirm the crop is good.
   if "hd_trim" in js:
      hd_trim = js['hd_trim']
      sd_trim = meteor_file.replace(".json", ".mp4")
      hd_frames,hd_color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 0, [], 1,[])
   if "cropbox_1080" in js:
      print("CROP:", js['cropbox_1080'])
      cx1, cy1, cx2, cy2, mx1, mx2 = js['cropbox_1080']
   else:
      print("NO CROP BOX!", meteor_file)
      exit()
  
   # make the crop frames 
   crop_file = hd_trim.replace(".mp4", "-crop.mp4")
   if True:
      crop_frames = []
      for hd_frame in hd_frames:
         cf = hd_frame[cy1:cy2,cx1:cx2]
         crop_frames.append(cf)
      SHOW = 0
      hd_objects, crop_frames = detect_meteor_in_clip(crop_file, crop_frames, 0, cx1, cy1, 1)
      hd_meteors = []
      for id in hd_objects:
         hd_objects[id] = analyze_object(hd_objects[id], 1,1)
         hd_objects[id]['cropbox_1080'] = js['cropbox_1080']
         if hd_objects[id]['report']['meteor'] == 1:
            hd_meteors.append(hd_objects[id])

   # make sure we have a meteor here. If not try to detect in the SD obj. 
   # TODO: still need to handle re-crop from the SD
   if len(hd_meteors) == 0:
      print("NO METEORS? MAYBE CROP LOCATION WAS BAD. TRY REFINDING IT. ")
      sd_frames,sd_color_frames,sd_subframes,sum_vals,max_vals,pos_vals = load_frames_fast(sd_trim, json_conf, 0, 1, [], 1,[])
      sd_objects, frames = detect_meteor_in_clip(sd_trim, sd_frames, 0, 0, 0, 0)
      return(None, None, None, None) 
      for id in hd_objects:
         print(hd_objects[id]['ofns'])
         print(hd_objects[id]['oint'])
         print(hd_objects[id]['report'])
         # log failure

   sfn = hd_meteors[0]['ofns'][0]
   lfn = hd_meteors[0]['ofns'][-1]
   print("FIRST/LAST:", sfn, lfn)


   # since we might be dealing with more than 1 meteor per file, 
   # process all meteors in the array.

   for meteor in hd_meteors:
      # check to see if our crop is ok, if not we need to redo it. 
      #print("OXS:", meteor['oxs'][0] - cx1, cx2-cx1)
      #print("OYS:", meteor['oys'][0] - cy1, cy2-cy1)
      #print("OXS:", meteor['oxs'][-1] - cx1)
      #print("OYS:", meteor['oys'][-1] - cy1)

      nfns, nxs, nys, new_cnts = refine_meteor_points(meteor, crop_frames, json_conf)


   print("REFINED METEOR:")
   print("NFNS:", nfns)
   print("NXS:", nxs)
   print("NYS:", nys)
   print("NCNT:", new_cnts)
   meteor['final'] = {}
   meteor['final']['fns'] = nfns
   for i in range(0, len(nfns)):
      if new_cnts[i] is not None:
         new_cnts[i][0] + cx1
         new_cnts[i][1] + cy1
         nxs[i] += cx1
         nys[i] += cy1
   meteor['final']['xs'] = nxs
   meteor['final']['ys'] = nys
   meteor['final']['cnts'] = new_cnts

   dist_x, dist_y, med_x, med_y = get_dist_info(crop_frames, nfns, nxs, nys)
   print("XD:", med_x, dist_x)
   print("YD:", med_y, dist_y)

   (dom_dir, quad, ideal_pos, ideal_roi_big_img) = get_movement_info(meteor, 10, 10)
   dom_dir, x_dir, y_dir = get_move_info(meteor, 10, 10)

   past_cnts = []
   median_frame = cv2.convertScaleAbs(np.median(np.array(hd_frames), axis=0))
   roi_size = 25 
   for i in range(0, len(nfns)):
      fn = nfns[i]
      frame= hd_frames[fn]
      x = nxs[i]
      y = nys[i]
      if new_cnts[i] is not None:
         cnt_w = new_cnts[i][2]
         cnt_h = new_cnts[i][3]
      else:
         cnt_w = 10
         cnt_h = 10


      rx1,ry1,rx2,ry2 = bound_cnt(x,y,frame.shape[1],frame.shape[0], roi_size)
      r_w = rx2 - rx1
      r_h = ry2 - ry1
      scale_x = 300 / (rx2-rx1)
      scale_y = 300 / (ry2-ry1)
      if cnt_h > cnt_w:
         line_w = int(int(cnt_w * scale_x) )
      else:
         line_w = int(int(cnt_h * scale_y) )
      adj_x = int(int(cnt_w/ 4) * scale_x)
      adj_y = int(int(cnt_h/ 4) * scale_y)

      (dom_dir, quad, ideal_pos, ideal_roi_big_img) = get_movement_info(meteor, int(cnt_w*scale_x), int(cnt_h*scale_y)) 
      # line should change based on x/y dir??
      adj_y = 0
      adj_x = 0
      if x_dir == 'left_to_right':
         # add the adj
         line_start_x = 150 - int(adj_x)
      else:
         line_start_x = 150 + int(adj_x)
      if y_dir == 'up_to_down':
         # add the adj
         line_start_y = 150 - int(adj_y)
      else:
         line_start_y = 150 + int(adj_y)
   
      line_w = 5
      med_multi = get_med_multi(line_start_x, line_start_y, med_x,med_y, max(cnt_w, cnt_h))
      
      cv2.line(ideal_roi_big_img, (line_start_x,line_start_y), (line_start_x-int(med_x*3),line_start_y-int(med_y*3)), (255,255,255), line_w)
      (show_frame, sub_frame, show_subframe, thresh_img, avg_val, max_val, thresh_val) = make_subframe(frame, median_frame,2,past_cnts,dom_dir,x_dir,y_dir)
      aroi_x1, aroi_y1, aroi_x2, aroi_y2, shift_x, shift_y = align_images(thresh_img, ideal_roi_big_img, rx1,ry1,rx2,ry2,cnt_w,cnt_h,dom_dir,x_dir,y_dir)
      if -10 <= shift_x < 10 and -10 <= shift_y <= 10:
         print("ADJUST SHIFT", shift_x, shift_y)
         nxs[i] = nxs[i] + shift_x
         nys[i] = nys[i] + shift_y
      if new_cnts[i] is not None:
         past_cnts.append((new_cnts[i][0]+cx1,new_cnts[i][1]+cy1,new_cnts[i][2],new_cnts[i][3]))
      else:
         past_cnts.append((nxs[i],nys[i],10,10))
   
   meteor['final']['xs'] = nxs
   meteor['final']['ys'] = nys

   make_roi_comp_img(hd_color_frames, meteor)

def get_med_multi(line_start_x, line_start_y, med_x,med_y, max_size):
   print("GET MED MULTI:")

def make_roi_comp_img(frames, meteor):

   stack_img = stack_frames(frames)
   stack_img.setflags(write=1) 
   fns = meteor['final']['fns']
   xs = meteor['final']['xs']
   ys = meteor['final']['ys']
   cnts = meteor['final']['cnts']
   dc = 0
   # determine ROI big size based on number of frames
   tf = len(fns)
   roi_size = 25 
   roi_big_size = 100 
   i_per_row = int(1920 / roi_big_size)
   i_per_row = i_per_row - 1
   rows = int(tf / i_per_row)
   rows += 1
   comp_h = rows * roi_big_size
   rimgs = []
   roi_row = np.zeros((comp_h,1920,3),dtype=np.uint8)
   rc = 0
   ic = 0
   for i in range(fns[0], fns[-1]+1):
      frame = frames[i]
      y_start = rc * roi_big_size
      fn = fns[dc]
      x = xs[dc]
      y = ys[dc]
      stack_img[y,x] = [0,0,255]
      rx1,ry1,rx2,ry2 = bound_cnt(x,y,frame.shape[1],frame.shape[0], roi_size)
      cnt = cnts[dc]
      rimg = frame[ry1:ry2,rx1:rx2]
      sx = ic * roi_big_size 
      ex = (ic * roi_big_size) + roi_big_size

      rimg_big = cv2.resize(rimg, (roi_big_size, roi_big_size))
      roi_scale_x = roi_big_size / rimg.shape[1] 
      roi_scale_y = roi_big_size / rimg.shape[0] 
      print("IMG:", rimg_big.shape)
      #roi_row[0:100,0:100] = rimg_big
      cv2.line(rimg_big, (0,50), (100,50), (100,100,100), 1)
      cv2.line(rimg_big, (50,0), (50,100), (100,100,100), 1)
      roi_row[y_start:y_start+roi_big_size,sx:ex] = rimg_big
      


      rimgs.append(rimg_big)
      if ic >= i_per_row:
         rc += 1
         ic = 0
      else:
         ic += 1

      dc += 1
   fh = rows * roi_big_size
   fy = 1080 - fh
   fy2 = 1080
   stack_img[fy:fy2,0:1920] = roi_row


   stack_img = cv2.resize(frame, (640, 360))
   cv2.imshow('pepe2', stack_img)
   cv2.waitKey(180)
   

   

def old_delete():
   fn = 0
   mc = 0
   lxs = []
   lys = []
   print("LEN FRAMES:", len(meteor['ofns']))
   print("LEN LEADING XS:", len(lead_xs))
   for frame in hd_color_frames:
      if meteor['ofns'][0] <= fn < meteor['ofns'][-1] :
         if fn in meteor['ofns']:
            color_console_image = np.zeros((720,1280,3),dtype=np.uint8)
            if len(meteor['ofns']) == len(lead_xs):
               lx = lead_xs[mc] + cx1
               ly = lead_ys[mc] + cy1
               print("CROP TOP:", cx1, cy1)
               print("ORG POINTS:", meteor['oxs'][mc],  meteor['oys'][mc])
               print("LEAD POINTS:", lx,  ly)
            else:
               # leading x,y refine didn't work?
               print(meteor['ofns'])
               print(meteor['oxs'])
               print(meteor['oys'])
               lx = meteor['oxs'][mc]
               ly = meteor['oys'][mc]
            lxs.append(lx)
            lys.append(ly)
            rx1,ry1,rx2,ry2 = bound_cnt(lx,ly,frame.shape[1],frame.shape[0], 10)
            print("ROI", ry1,ry2,rx1,rx2)
            cv2.rectangle(frame, (lx-5, ly-5), (lx+5, ly+5), (0,0,255), 1, cv2.LINE_AA)
            cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (255,255,0), 1, cv2.LINE_AA)
            cv2.rectangle(frame, (cx1, cy1), (cx2, cy2), (255,0,0), 1, cv2.LINE_AA)
            # orig meteor x,y
            cv2.rectangle(frame, (meteor['oxs'][mc]-2, meteor['oys'][mc]-2), (meteor['oxs'][mc]+2, meteor['oys'][mc]+2), (0,255,0), 1, cv2.LINE_AA)

            full_frame_sm = cv2.resize(frame, (640, 360))
            crop_frame = frame[cy1:cy2,cx1:cx2]
            crop_frame = cv2.resize(crop_frame, (640, 360))
            roi_frame = frame[ry1:ry2,rx1:rx2]
            print("ROI", ry1,ry2,rx1,rx2)
          
            roi_frame = cv2.resize(roi_frame, (300, 300))
            color_console_image[0:360,0:640] = full_frame_sm
            color_console_image[0:360,640:1280] = crop_frame 
            color_console_image[360:660,490:790] = roi_frame 
            cv2.imshow('Final', color_console_image)
            cv2.waitKey(800)
            mc += 1
         else:
            print("GAP / MISSING FRAME DETECTED:", fn)
      fn += 1
   return(lxs, lys, intensity, max_pxs)

def align_images(full_frame, ideal_roi, rx1,ry1,rx2,ry2,orig_w,orig_h,dom_dir,x_dir,y_dir) :

   orig_x = int((rx1 + rx2)/2)
   orig_y = int((ry1 + ry2)/2)

   poly = np.zeros(shape=(2,), dtype=np.float64)
   shift_x = 0
   shift_y = 0



   #ideal_roi[0:300,149:151] = 255
   #ideal_roi[149:151,0:300] = 255
   axis_reduce = 0
   if axis_reduce == 1:
   
      # align the y with center
      lowest_sub  = 9999999999
      best_shift_y = 0
      for i in range (-30,30):
         if ry1 + i > 0 and ry2+i < full_frame.shape[0]:
            new_roi= full_frame[ry1+i:ry2+i,rx1+0:rx2+0]
            new_roi_big = cv2.resize(new_roi, (300, 300))
            sub = cv2.subtract(ideal_roi, new_roi_big)
            if np.sum(sub) < lowest_sub:
               lowest_sub = np.sum(sub)
               best_shift_y = i
            #cv2.imshow('sub', sub)
            #cv2.waitKey(30)

      # align the x with center
      lowest_sub  = 9999999999
      best_shift_x = 0
      for i in range (-30,30):
         if rx1 + i > 0 and rx2+i < full_frame.shape[1]:
            new_roi= full_frame[ry1:ry2,rx1+i:rx2+i]
            new_roi_big = cv2.resize(new_roi, (300, 300))
            sub = cv2.subtract(ideal_roi, new_roi_big)
            if np.sum(sub) < lowest_sub:
               lowest_sub = np.sum(sub)
               best_shift_x = i
            #cv2.imshow('sub', sub)
            #cv2.waitKey(30)


   #rx1 = rx1 + best_shift_x
   #ry1 = ry1 + best_shift_y
   #rx2 = rx2 + best_shift_x
   #ry2 = ry2 + best_shift_y
   
   # REDUCE BOTH AXIS
   res = scipy.optimize.minimize(reduce_align_roi_images, poly, args=(full_frame,ideal_roi,rx1,ry1,rx2,ry2,orig_x,orig_y,orig_w,orig_h,dom_dir,x_dir,y_dir), method='Nelder-Mead')
   new_poly = res['x']
   shift_x = int(new_poly[0] * ((rx1+1)**2))
   shift_y = int(new_poly[1] * ((ry1+1)**2))
   print("NEW SHIFT:", shift_x, shift_y)

   new_rx1 = rx1+shift_x
   new_ry1 = ry1+shift_y
   new_rx2 = rx2+shift_x
   new_ry2 = ry2+shift_y

   #cv2.rectangle(full_frame, (rx1, ry1), (rx2, ry2), (100,100,100), 1, cv2.LINE_AA)
   #cv2.rectangle(full_frame, (new_rx1, new_ry1), (new_rx2, new_ry2), (100,100,255), 1, cv2.LINE_AA)
   #cv2.imshow('pepe', full_frame)
   #cv2.waitKey(30)





   return(new_rx1,new_ry1,new_rx2,new_ry2, shift_x, shift_y)


def get_leading_corner(x,y,w,h,dom_dir, x_dir, y_dir):
   if x_dir == "right_to_left":
      corner_x = x 
   elif x_dir == "left_to_right":
      corner_x = x + w
   else:
      corner_x = x + int(w/2)
   if y_dir == "up_to_down":
      corner_y = y + h 
   elif y_dir == "down_to_up":
      corner_y = y 
   else:
      corner_y = y + int(h/2)
   return(corner_x, corner_y)

def reduce_align_roi_images(poly, full_frame, ideal_roi, rx1,ry1,rx2,ry2, x,y,w,h,dom_dir,x_dir,y_dir):
   #shift image per poly and then re-subtract to minimize alignment 
   show_img = np.zeros((300,900),dtype=np.uint8)
   shift_x = int(poly[0] * ((rx1+1)**2))
   shift_y = int(poly[1] * ((ry1+1)**2))

   org_roi= full_frame[ry1:ry2,rx1:rx2]
   org_roi_big = cv2.resize(org_roi, (300, 300))
   org_roi_val = np.sum(org_roi_big)

   mx = int((rx1+shift_x+rx2+shift_x)/2)
   my = int((ry1+shift_y+ry2+shift_y)/2)
   corner_x, corner_y = get_leading_corner(x-rx1+shift_x,y-ry1+shift_y,w,h,dom_dir,x_dir,y_dir)
   center_dist_from_center = calc_dist((mx-rx1,my-ry1),(25,25))
   corner_dist_from_center = calc_dist((corner_x,corner_y),(25,25))

   #print("CENTER:", mx-rx1, my-ry1, center_dist_from_center)
   #print("CORNER:", corner_x, corner_y, corner_dist_from_center)

   if center_dist_from_center <= 0:
      center_dist_from_center = 1

   sf_y1 = ry1+shift_y 
   sf_y2 = ry2+shift_y
   sf_x1 = rx1+shift_x
   sf_x2 = rx2+shift_x
   if sf_x1 <= 0:
      print("BOUNDS PROB x1", shift_x, shift_y)
      print("SF 1 X/Y", sf_x1, sf_y1)
      sf_x1 = 0
   if sf_x2 >= full_frame.shape[1]:
      sf_x1 = full_frame.shape[0] - (sf_x2 - sf_x1)
      sf_x2 = full_frame.shape[0]
      print("BOUNDS PROB x2", sf_x1, sf_x2)
   if sf_y1 <= 0:
      print("BOUNDS PROB y1")
      sf_y1 = 0
   if sf_y2 >= full_frame.shape[0]:
      print("BOUNDS PROB y2", sf_y2, full_frame.shape)
      sf_y1 = full_frame.shape[0] - (sf_y2 - sf_y1)
      sf_y2 = full_frame.shape[0]
   #cv2.imshow('pepe', full_frame)
   #cv2.waitKey(30)
 
   new_roi= full_frame[sf_y1:sf_y2,sf_x1:sf_x2]

   new_roi_big = cv2.resize(new_roi, (300, 300))

   sub = cv2.subtract(ideal_roi, new_roi_big)
   new_val = np.sum(new_roi_big)  
   dif_val = org_roi_val - new_val
   sub_val = np.sum(sub) 

   cv2.line(sub, (0,150), (int(300),int(150)), (100,100,100), 1)
   cv2.line(sub, (150,0), (int(150),int(300)), (100,100,100), 1)

   show_img[0:300,0:300] = ideal_roi
   show_img[0:300,300:600] = new_roi_big
   show_img[0:300,600:900] = sub
   if center_dist_from_center > 20:
      center_dist_from_center = 999

   score = sub_val + (center_dist_from_center**2)
   cv2.imshow('pepe', show_img)
   cv2.waitKey(100)

   return(score)


def get_move_info(meteor, cnt_w, cnt_h):
   moving_x = meteor['oxs'][0] - meteor['oxs'][-1]
   moving_y = meteor['oys'][0] - meteor['oys'][-1]
   if abs(moving_x) > abs(moving_y):
      dom_dir = "x"
   else:
      dom_dir = "y"
   if moving_x > 0:
      x_dir = "right_to_left"
   else:
      x_dir = "left_to_right"
   if moving_y > 0:
      y_dir = "down_to_up"
   else:
      y_dir = "up_to_down"
   if moving_x == 0:
      x_dir = None
   if moving_y == 0:
      y_dir = None

   qw = int(cnt_w/3)
   qh = int(cnt_h/3)

   return(dom_dir, x_dir, y_dir)


def get_movement_info(meteor, cnt_w, cnt_h):
   hw = int(cnt_w / 2)
   hh = int(cnt_h / 2)
   moving_x = meteor['oxs'][0] - meteor['oxs'][-1]
   moving_y = meteor['oys'][0] - meteor['oys'][-1]
   if abs(moving_x) > abs(moving_y):
      dom_dir = "x"
   else:
      dom_dir = "y"
   if moving_x > 0:
      x_dir = "right_to_left"
   else:
      x_dir = "left_to_right"
   if moving_y > 0:
      y_dir = "down_to_up"
   else:
      y_dir = "up_to_down"
   if moving_x == 0:
      x_dir = None
   if moving_y == 0:
      y_dir = None

   qw = int(cnt_w/3)
   qh = int(cnt_h/3)
   if y_dir is None:
      # The meteor is moving perfectly horizontally
      ideal_y1 = hh - qh
      ideal_y2 = hh + qh
      y_quad_loc = "center"
   if x_dir is None:
      # The meteor is moving perfectly vertically 
      ideal_x1 = hw - qw
      ideal_x2 = hw + qw
      x_quad_loc = "center"

   # based on the dom dir and x,y movement choose the best ROI quad for placing the meteor
   if x_dir == "right_to_left":
      x_quad_loc = "left" 
      ideal_x1 = hh 
      ideal_x2 = 0 
   if x_dir == "left_to_right":
      x_quad_loc = "right" 
      ideal_x1 = hw 
      ideal_x2 = hw * 2 
   if y_dir == "up_to_down":
      y_quad_loc = "bottom"
      ideal_y1 = hh 
      ideal_y2 = hh * 2
   if y_dir == "down_to_up":
      y_quad_loc = "top"
      ideal_y1 = 0 
      ideal_y2 = hh 
   

   ideal = [ideal_x1, ideal_y1, ideal_x2, ideal_y2]
   quad = [x_quad_loc, y_quad_loc]

   ideal_img = np.zeros((300,300),dtype=np.uint8)
   #ideal_img[ideal_y1:ideal_y2, ideal_x1:ideal_x2] = 255
   #cv2.imshow("IDEAL", ideal_img)
   return(dom_dir, quad, ideal, ideal_img)


def get_best_cnt(cnts, meteor):
   moving_x = meteor['oxs'][0] - meteor['oxs'][-1]
   moving_y = meteor['oys'][0] - meteor['oys'][-1]
   if abs(moving_x) > abs(moving_y):
      dom_dir = "x"
   else: 
      dom_dir = "y"
   if moving_x > 0:
      x_dir = "right_to_left"
   else:
      x_dir = "left_to_right"
   if moving_y > 0:
      y_dir = "down_to_up"
   else:
      y_dir = "up_to_down"
   if moving_x == 0:
      x_dir = None
   if moving_y == 0:
      y_dir = None

   #print("Dom direction:", dom_dir)
   #print("Moving X:", moving_x)
   #print("Moving Y:", moving_y)
   #print("X Dir:", x_dir)
   #print("Y DirY:", y_dir)
   # Biggness override - if one cnt is way bigger than all the others (3x or more) 
   # use that as the best / dom 
   temp = sorted(cnts, key=lambda x: (x[2]+x[3]), reverse=True)
   best_cnt = temp[0]
   return([best_cnt], dom_dir, x_dir, y_dir)

   if dom_dir == "x":
      if x_dir == "right_to_left":
         # pick cnt with lowest x val 
         temp = sorted(cnts, key=lambda x: x[0], reverse=False)
         best_cnt= temp[0]
         return([best_cnt], dom_dir, x_dir, y_dir)
      else: 
         temp = sorted(cnts, key=lambda x: x[0], reverse=True)
         best_cnt= temp[0]
         return([best_cnt], dom_dir, x_dir, y_dir)

   if dom_dir == "y":
      if y_dir == "top_to_bottom":
         # pick cnt with highest y val 
         temp = sorted(cnts, key=lambda x: x[1], reverse=True)
         best_cnt= temp[0]
         return([best_cnt], dom_dir, x_dir, y_dir)
      else: 
         temp = sorted(cnts, key=lambda x: x[1], reverse=False)
         best_cnt= temp[0]
         return([best_cnt], dom_dir, x_dir, y_dir)

   
   # if we made it this far, then the x or y dir is perfectly veritical or horizontal
   # in this case we should use the dom dir val
   # figure out later

def objects_to_clips(meteor_objects):
   clips = []
   good_objs = []
   for obj in meteor_objects:
      if len(obj['ofns']) > 2:
         ok = 1
         for clip in clips:
            if abs(obj['ofns'][0] - clip) < 25:
               ok = 0
         if ok == 1:
            clips.append(obj['ofns'][0])
            good_objs.append(obj)

   return(good_objs)


def clean_bad_frames(object):
   #print("CLEAN BEFORE:", object)
   return(object)
   if len(object['ofns']) < 5:
      return(object)
   bad_frames = {} 
   for i in range(0,len(object['ofns'])-1):
      last_i = len(object['ofns']) - 1 - i
      if i < 4:
         if object['report']['line_segments'][last_i] <= 0 :
            bad_frames[last_i] = 1
         if object['oint'][last_i] < 10:
            bad_frames[last_i] = 1

   print("BAD FRAMES:", bad_frames)
   # check for a gap at the from 
   first_frame_diff = object['ofns'][1] - object['ofns'][0]
   if False:
      if first_frame_diff > 1:
         # REMOVE FIRST FRAME 
         bf = 0
         object['ofns'].pop(bf)
         object['oxs'].pop(bf)
         object['oys'].pop(bf)
         object['ows'].pop(bf)
         object['ohs'].pop(bf)
         object['oint'].pop(bf)
         object['report']['object_px_length'].pop(bf)
         object['report']['line_segments'].pop(bf)
         object['report']['x_segs'].pop(bf)
         object['report']['ms'].pop(bf)
         object['report']['bs'].pop(bf)


   no = {}
   if len(bad_frames) == 0:
      return(object)
   if len(bad_frames) > 0:
      no['ofns'] = []
      no['oxs'] = []
      no['oys'] = []
      no['ows'] = []
      no['ohs'] = []
      no['oint'] = []
      no['report'] = {}
      no['report']['object_px_length'] = []
      no['report']['line_segments'] = []
      no['report']['x_segs'] = []
      no['report']['ms'] = []
      no['report']['bs'] = []
   for i in range(0, len(object['ofns'])):
      if i < min(bad_frames.keys()):
         #print("ADD GOOD FRAME.", i, object['ofns'][i])
         no['ofns'].append(object['ofns'][i])
         no['oxs'].append(object['oxs'][i])
         no['oys'].append(object['oys'][i])
         no['ows'].append(object['ows'][i])
         no['ohs'].append(object['ohs'][i])
         no['oint'].append(object['oint'][i])
         no['report']['object_px_length'].append(object['report']['object_px_length'][i])
         no['report']['line_segments'].append(object['report']['line_segments'][i])
         no['report']['x_segs'].append(object['report']['x_segs'][i])
         no['report']['ms'].append(object['report']['ms'][i])
         no['report']['bs'].append(object['report']['bs'][i])
   if len(bad_frames) > 0:
      o = object 
      o['ofns'] =  no['ofns']
      o['oxs'] =    no['oxs']
      o['oys'] =   no['oys']
      o['ows'] =   no['ows']
      o['ohs'] =   no['ohs']
      o['oint'] =  no['oint']
      o['report']['object_px_length'] =      no['report']['object_px_length']
      o['report']['line_segments'] =    no['report']['line_segments']
      o['report']['x_segs'] =  no['report']['x_segs']
      o['report']['ms'] =  no['report']['ms']
      o['report']['bs'] =  no['report']['bs']
      object = o


   #print("CLEAN AFTER:", object)
   #print("NEW OBJ :", no)
   return(object) 


def analyze_object(object, hd = 0, strict = 0):
   ''' 
      perform various tests to classify the type of object
      when strict == 1 perform more meteor strict tests
   '''
   if hd == 0:
      # if we are working with an HD file we need to mute the HD Multipliers
      global HDM_X, HDM_Y
      HDM_X = 1
      HDM_Y = 1

   bad_items = []
   good_items = []

   #if "report" not in object:
   obj_id = object['obj_id'] 
   if True:
      object['report'] = {}
      object['report']['non_meteor'] = 0
      object['report']['meteor'] = 0
      object['report']['bad_items'] = []

   max_int = 0
   max_times = 0
   fb = 0
   for intv in object['oint']:
      if intv > 2000:
         fb += 1


   # basic initial tests for vals-detect/stict = 0, if these all pass the clip should be video detected
   object['report']['cm'] = obj_cm(object['ofns'])
   # consecutive motion filter 
   if object['report']['cm'] < 3:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0

   object['report']['unq_perc'], object['report']['unq_points'] = unq_points(object)
   if object['report']['unq_points'] > 3 and object['report']['unq_perc'] < .4 :
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("Unq Points/Perc too low. " + str(object['report']['unq_points']) + " / " + str(object['report']['unq_perc']) )
   if object['report']['unq_points']  <= 3 and object['report']['unq_perc'] < .8 :
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("Unq Points/Perc too low. " + str(object['report']['unq_points']) + " / " + str(object['report']['unq_perc']) )

   object['report']['object_px_length'], object['report']['line_segments'], object['report']['x_segs'], object['report']['ms'], object['report']['bs'] = calc_line_segments(object)
   med_seg = np.median(object['report']['line_segments'])
   bad_segs = 0
   for seg in object['report']['line_segments']:
      if seg <= 0:
         bad_segs += 1
      med_diff = abs(med_seg - seg)
      if med_diff > med_seg * 3:
         bad_segs += 1

   bad_seg_perc = bad_segs / len(object['oxs'])
   #if bad_seg_perc > .40:
   if False:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['class'] = "unknown"
      object['report']['bad_seg_perc'] = bad_seg_perc
      object['report']['bad_items'].append("Bad seg perc too high. " + str(object['report']['bad_seg_perc']) )

   object['report']['min_max_dist'] = calc_dist((min(object['oxs']), min(object['oys'])), (max(object['oxs']),max(object['oys']) ))

   #object = clean_bad_frames(object)


   # ANG DIST / VEL
   # HD PXSCALE = 155 arcseconds per pixel 
   hd_pxscale = 155
   pxscale = 155
   if hd == 0:
      sd_pxscale = hd_pxscale * (2.25)
      pxscale = sd_pxscale

   #if object['report']['non_meteor'] == 0:
   if True:
      ang_dist, ang_vel = ang_dist_vel(object['oxs'],object['oys'], [],[],pxscale)
      object['report']['ang_dist'] = ang_dist
      object['report']['ang_vel'] = ang_vel

      # filter out detections that don't match ang vel or ang sep desired values
      if float(ang_vel) > .3 and float(ang_vel) < 80:
         foo = 1
      else:
         object['report']['non_meteor'] = 1
         object['report']['meteor'] = 0
         object['report']['bad_items'].append("bad ang vel: " + str(ang_vel))

      if ang_dist < .3:
         object['report']['non_meteor'] = 1
         object['report']['meteor'] = 0
         object['report']['bad_items'].append("bad ang sep: " + str(ang_dist))



   if (object['report']['unq_perc'] < .1 or object['report']['min_max_dist'] <= 3) and len(object['oxs']) > 3:
      object['report']['class'] = "star"
   else:
      if "class" not in object['report']:
         object['report']['class'] = "unknown"




   object['report']['big_perc'] = big_cnt_test(object, hd)
   if object['report']['big_perc'] > .5:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("Big Perc % too high. " + str(object['report']['big_perc']))

   # meteor dir tests
   if len(object['ofns']) > 4:
      object['report']['dir_test_perc'] = meteor_dir_test(object['oxs'],object['oys'])
   else:
      object['report']['dir_test_perc'] = 1

   # NOT SURE THIS WORKS?!
   if object['report']['dir_test_perc'] < .80:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("% direction too low. " + str(object['report']['dir_test_perc']))

   # intensity
   #if sum(object['oint']) < 0:
      # DISABLED FOR NOW
   #   object['report']['non_meteor'] = 0
   #   object['report']['bad_items'].append("Negative intensity, possible bird. ")
    
                                         
   (max_times, pos_neg_perc, perc_val) = analyze_intensity(object['oint'])
   object['report']['int_pos_neg_perc'] = pos_neg_perc
   object['report']['int_max_times'] = max_times
   object['report']['pos_perc'] = perc_val
   if pos_neg_perc < .5:
      object['report']['non_meteor'] = 1
      object['report']['meteor'] = 0
      object['report']['bad_items'].append("% pos/neg intensity too low. " + str(object['report']['int_pos_neg_perc']))


   if object['report']['non_meteor'] == 0 :
      object['report']['meteor'] = 1
      object['report']['class'] = "meteor"

   #print("FB:", obj_id, fb)
   #if fb > 5:
   #   object['report']['meteor'] = 1
      #object['report']['class'] = "fireball meteor"
      

   return(object)    

def analyze_object_old(object, hd = 0, sd_multi = 1, final=0):
   # HD scale pix is .072 degrees per px
   # SD scale pix is .072 * sd_multi
   pix_scale = .072  # for HD

   if hd == 1:
      deg_multi = 1
      sd = 0
   else:
      deg_multi = 3
      sd = 1

   bad_items = []
   perc_big = big_cnt_test(object, hd)
   if "ofns" not in object:
      if "report" not in object:
         object['report'] = {}
         object['report']['meteor_yn'] = "no"
      else:
         object['report']['meteor_yn'] = "no"
      return(object)
   if len(object['ofns']) == 0:
      if "report" not in object:
         object['report'] = {}
         object['report']['meteor_yn'] = "no"
      else:
         object['report']['meteor_yn'] = "no"
      return(object)

   object = calc_leg_segs(object)
   unq_perc = unq_points(object)

   if len(object['ofns']) > 4:
      dir_test_perc = meteor_direction_test(object['oxs'],object['oys'])
   else:
      dir_test_perc = 0


   id = object['obj_id']
   meteor_yn = "Y"
   obj_class = "undefined"
   ff = object['ofns'][0]
   lf = object['ofns'][-1]
   elp = (lf - ff ) + 1
   min_x = min(object['oxs'])
   max_x = max(object['oxs'])
   min_y = min(object['oys'])
   max_y = max(object['oys'])
   max_int = max(object['oint'])
   min_int = min(object['oint'])
   max_h = max(object['ohs'])
   max_w = max(object['ows'])
   #max_x = max_x + max_w
   #max_h = max_y + max_h

   int_max_times, int_neg_perc, int_perc_list = analyze_intensity(object['oint'])

   med_int = float(np.median(object['oint']))
   intense_neg = 0
   for intense in object['oint']:
      if intense < 0:
         intense_neg = intense_neg + 1
   min_max_dist = calc_dist((min_x, min_y), (max_x,max_y))
   if len(object['ofns']) > 0:
      if final == 0:

         dist_per_elp = min_max_dist / len(object['ofns'])
      else:
         if elp > 0:
            dist_per_elp = min_max_dist / elp
         else:
            dist_per_elp = 0
   else:
      dist_per_elp = 0

   if len(object['ofns']) > 3 and perc_big >= .75 and len(object['ofns']) < 10:
      moving = "moving"
      meteor_yn = "no"
      obj_class = "car or object"
      bad_items.append("too many big percs")

   if elp > 5 and dist_per_elp < .1 :
      moving = "not moving"
      meteor_yn = "no"
      obj_class = "star"
      bad_items.append("too short and too slow")
   else:
      moving = "moving"
   if min_max_dist > 12 and dist_per_elp < .1:
      moving = "slow moving"
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("too long and too slow")

   #cm
   fc = 0
   cm = 1
   max_cm = 1
   last_fn = None
   for fn in object['ofns']:
      if last_fn is not None:
         if last_fn + 1 == fn or last_fn + 2 == fn:
            cm = cm + 1
            if cm > max_cm :
               max_cm = cm

      fc = fc + 1
      last_fn = fn
   if len(object['ofns']) > 1:
      x_dir_mod,y_dir_mod = meteor_direction(object['oxs'][0], object['oys'][0], object['oxs'][-1], object['oys'][-1])
   else:
      x_dir_mod = 0
      y_dir_mod = 0

   if len(object['ofns'])> 0:
      cm_to_len = max_cm / len(object['ofns'])
   else:
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("0 frames")
   if cm_to_len < .4:
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("cm/len < .4.")

   if len(object['ofns']) >= 300:
      # if cm_to_len is acceptable then skip this.
      if cm_to_len < .6:
         meteor_yn = "no"
         obj_class = "plane"
         bad_items.append("more than 300 frames in event and cm/len < .6.")



   # classify the object

   if max_cm <= 3 and elp > 5 and min_max_dist < 8 and dist_per_elp < .01:
      obj_class = "star"
   if elp > 5 and min_max_dist > 8 and dist_per_elp >= .01 and dist_per_elp < 1:
      obj_class = "plane"
   if elp > 300:
      meteor_yn = "no"
      bad_items.append("more than 300 frames in event.")
   if max_cm < 4:
      neg_perc = intense_neg / max_cm
      if intense_neg / max_cm > .3:
         meteor_yn = "no"
         bad_items.append("too much negative intensity for short event." + str(intense_neg))

   if max_cm > 0:
      neg_perc = intense_neg / max_cm
      if intense_neg / max_cm > .5:
         meteor_yn = "no"
         bad_items.append("too much negative intensity." + str(intense_neg))
   else:
      neg_perc = 0
   if elp < 2:
      meteor_yn = "no"
      bad_items.append("less than 2 frames in event.")
   if perc_big > .75 and len(object['ofns']) < 10:
      meteor_yn = "no"
      bad_items.append("too many big cnts." + str(perc_big))
   if max_cm < 3:
      meteor_yn = "no"
      bad_items.append("less than 2 consecutive motion.")
   if dist_per_elp > 5:
      meteor_yn = "Y"
   if med_int < 5 and med_int != 0:
      meteor_yn = "no"
      obj_class = "bird"
      bad_items.append("low or negative median intensity.")
   if dir_test_perc < .5 and dir_test_perc != 0 and elp > 10:
      #meteor_yn = "no"
      #obj_class = "noise"
      bad_items.append("direction test failed." + str(dir_test_perc))
   if unq_perc < .5:
      meteor_yn = "no"
      obj_class = "star or plane"
      bad_items.append("unique points test failed." + str(unq_perc))

   if max_cm > 0:
      elp_max_cm = elp / max_cm
      if elp / max_cm >3:
         obj_class = "plane"
         meteor_yn = "no"
         bad_items.append("elp to cm to high." + str(elp / max_cm))
   else:
      elp_max_cm = 0
   ang_vel = ((dist_per_elp * deg_multi) * pix_scale) * 25
   ang_dist = ((min_max_dist * deg_multi) * pix_scale)

   if ang_dist < .2:
      meteor_yn = "no"
      bad_items.append("bad angular distance below .2.")
   if ang_vel < .9:
      meteor_yn = "no"
      bad_items.append("bad angular velocity below .9")

   if dir_test_perc < .6 and max_cm > 10:
      meteor_yn = "no"
      obj_class = "star"
      bad_items.append("dir test perc to low for this cm")

   if max_cm < 5 and elp_max_cm > 1.5 and neg_perc > 0:
      meteor_yn = "no"
      obj_class = "plane"
      bad_items.append("low max cm, high neg_perc, high elp_max_cm")

   if ang_vel < 1.5 and elp_max_cm > 2 and cm < 3:
      meteor_yn = "no"
      bad_items.append("short distance, many gaps, low cm")
      obj_class = "plane"


   if elp > 0:
      if min_max_dist * deg_multi < 1 and max_cm <= 3 and cm / elp < .75 :
         meteor_yn = "no"
         bad_items.append("short distance, many gaps, low cm")

   if meteor_yn == "Y" and final == 1:
      if max_cm - elp < -30:
         meteor_yn = "no"
         obj_class = "plane"
         bad_items.append("to many elp frames compared to cm.")


   if len(bad_items) >= 1:
      meteor_yn = "no"
      if obj_class == 'meteor':
         obj_class = "not sure"

   if meteor_yn == "no":
      meteory_yn = "no"
   else:
      meteory_yn = "Y"
      obj_class = "meteor"


   # create meteor 'like' score
   score = 0
   if meteor_yn == "Y":
      avg_line_res = poly_fit(object)
   else:
      avg_line_res = 0

   if avg_line_res > 13:
      meteor_yn = "no"
      obj_class = "noise"
      bad_items.append("bad average line res " + str(avg_line_res))

   if max_cm == elp == len(object['ofns']):
      score = score + 1
   if dir_test_perc == 2:
      score = score + 1
   if max_cm >= 5:
      score = score + 1
   if avg_line_res <= 1:
      score = score + 1
   if ang_vel > 2:
      score = score + 1
   if obj_class == "meteor":
      score = score + 5
   else:
      score = score - 3

   object['report'] = {}

   if meteor_yn == "Y":
      class_rpt = classify_object(object, sd)
      object['report']['classify'] = class_rpt
      object['report']['meteor_yn'] = meteor_yn

      #object['report']['angular_sep_px'] = class_rpt['ang_sep_px']
      #object['report']['angular_vel_px'] = class_rpt['ang_vel_px']
      #object['report']['angular_sep'] = class_rpt['ang_sep_deg']
      #object['report']['angular_vel'] = class_rpt['ang_vel_deg']
      #object['report']['segs'] = class_rpt['segs']
      #object['report']['bad_seg_perc'] = class_rpt['bad_seg_perc']
      #object['report']['neg_int_perc'] = class_rpt['neg_int_perc']
      #object['report']['meteor_yn'] = class_rpt['meteor_yn']
      #object['report']['bad_items'] = class_rpt['bad_items']
   else:
      object['report']['meteor_yn'] = meteor_yn

   object['report']['elp'] = elp
   object['report']['min_max_dist'] = min_max_dist
   object['report']['dist_per_elp'] = dist_per_elp
   object['report']['moving'] = moving
   object['report']['dir_test_perc'] = dir_test_perc
   object['report']['max_cm'] = max_cm
   object['report']['elp_max_cm'] = elp_max_cm
   object['report']['max_fns'] = len(object['ofns'])
   object['report']['neg_perc'] = neg_perc
   object['report']['avg_line_res'] = avg_line_res
   object['report']['obj_class'] = obj_class
   object['report']['bad_items'] = bad_items
   object['report']['x_dir_mod'] = x_dir_mod
   object['report']['y_dir_mod'] = y_dir_mod
   object['report']['score'] = score

   return(object)

def min_cnt_dist(x,y,w,h,tx,ty,tw,th):
   ds = []
   ctx = tx+int(tw/2)
   cty = ty+int(th/2)
   cx = x+int(w/2)
   cy = y+int(h/2)

   dist = calc_dist((x,y), (tx,ty))
   ds.append(dist)
   dist = calc_dist((x,y), (tx+tw,ty+th))
   ds.append(dist)
   dist = calc_dist((x+w,y+h), (tx,ty))
   ds.append(dist)
   dist = calc_dist((x+w,y+h), (tx+tw,ty+th))
   ds.append(dist)
   dist = calc_dist((cx,cy), (ctx,cty))
   ds.append(dist)
   dist = calc_dist((x,y), (ctx,cty))
   ds.append(dist)
   dist = calc_dist((x+w,y), (ctx,cty))
   ds.append(dist)
   dist = calc_dist((x,y+h), (ctx,cty))
   ds.append(dist)
   dist = calc_dist((x+w,y+h), (ctx,cty))
   ds.append(dist)
   return(min(ds))

def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h, intensity=0, hd=0, sd_multi=1, cnt_img=None ):
   print("FIND OBJ:", fn, cnt_x, cnt_y, cnt_w, cnt_h)
   matched = {}
   if hd == 1:
      obj_dist_thresh = 65 
   else:
      obj_dist_thresh = 30 

   #if intensity > 2000:
   #   obj_dist_thresh = obj_dist_thresh * 2.5

   center_x = cnt_x + int(cnt_w/2)
   center_y = cnt_y + int(cnt_h/2)

   found = 0
   max_obj = 0
   closest_objs = []
   not_close_objs = []
   dist_objs = []
   for obj in objects:
      if 'oxs' in objects[obj]:
         ofns = objects[obj]['ofns']
         oxs = objects[obj]['oxs']
         oys = objects[obj]['oys']
         ows = objects[obj]['ows']
         ohs = objects[obj]['ohs']
         if len(oxs) < 2:
            check = len(oxs)
         else:
            check = 2 
         for ii in range(0, check):
            oi = len(oxs) - ii - 1
            #oi = ii
            hm = int(ohs[oi] / 2)
            wm = int(ows[oi] / 2)
            lfn = int(ofns[-1] )
            #dist = calc_obj_dist((cnt_x,cnt_y,cnt_w,cnt_h),(oxs[oi], oys[oi], ows[oi], ohs[oi]))
            t_center_x = oxs[oi] + int(ows[oi]/2) 
            t_center_y = oys[oi] + int(ohs[oi]/2) 
            c_dist = calc_dist((center_x,center_y),(t_center_x, t_center_y))
            dist = min_cnt_dist(cnt_x,cnt_y,cnt_w,cnt_h,oxs[oi],oys[oi],ows[oi],ohs[oi])
            dist_objs.append((obj,dist))
            last_frame_diff = fn - lfn
            if "report" in objects[obj]:
               if objects[obj]['report']['class'] == "meteor" and len(objects[obj]['oxs']) > 3:
                  # only add this new point to the meteor if it is not equal to the last point and if the last_seg and current dist are reasonable.
                  last_x = objects[obj]['oxs'][-1]
                  last_y = objects[obj]['oys'][-1]
                  last_x2 = objects[obj]['oxs'][-2]
                  last_y2 = objects[obj]['oys'][-2]
                  last_seg_dist = calc_dist((last_x,last_y), (last_x2, last_y2))
                  this_seg_dist = calc_dist((last_x,last_y), (cnt_x, cnt_y))
                  abs_diff = abs(last_seg_dist - this_seg_dist)
                  print("THIS/LAST SEG:", obj, this_seg_dist, last_seg_dist, abs_diff)
                  last_fn_diff = fn - objects[obj]['ofns'][-1]
                  if abs_diff > 20 or this_seg_dist > 20 or last_fn_diff > 5:
                     # don't add points to meteors if they are more than 5x farther away than the last seg dist
                  #   cont = input("ABORTED MATCH DUE TO ABS_DIFF." + str( abs_diff) + " " + str( last_seg_dist * 5))
                     continue
                  # if this cnt_x, y is the same as the last one, don't add!
                  if last_x == cnt_x and last_y == cnt_y:
                     continue
               if objects[obj]['report']['class'] == "star":
                  # only match object if dist is within 5 px
                  if dist > 5:
                     continue 

         
            if dist < obj_dist_thresh : #and last_frame_diff < 15:
               #if this is linked to a meteor only associate if the point is further from the start than the last recorded point
               print("CENTER:", center_x, center_y , cnt_x, cnt_y, objects[obj]['oxs'], objects[obj]['oys'])
               #if cnt_x in objects[obj]['oxs'] and cnt_y in objects[obj]['oys']:
               #   print("DUPE PIX")
               #   found = 0
               if len(objects[obj]['oxs']) > 3:
               #if False:
                  last_x = objects[obj]['oxs'][-1]
                  last_y = objects[obj]['oys'][-1]
                  last_x2 = objects[obj]['oxs'][-2]
                  last_y2 = objects[obj]['oys'][-2]
                  last_seg_dist = calc_dist((last_x,last_y), (last_x2, last_y2))
                  this_seg_dist = calc_dist((last_x,last_y), (cnt_x, cnt_y))
                  abs_diff = abs(last_seg_dist - this_seg_dist)
                  print("2nd ABS DIFF IS:", abs_diff, last_seg_dist, this_seg_dist)
                  if abs_diff > 20:
                     found = 0 
                     #found_obj = obj
                     #matched[obj] = 1
                     not_close_objs.append((obj,dist))
                  else:
                     found = 1
                     found_obj = obj
                     matched[obj] = 1
                     closest_objs.append((obj,dist))
               else: 
                  found = 1
                  found_obj = obj
                  matched[obj] = 1
                  closest_objs.append((obj,dist))
            else: 
               not_close_objs.append((obj,dist,last_frame_diff))

      if obj > max_obj:
         max_obj = obj

   if len(closest_objs) >= 1:

      ci = sorted(closest_objs , key=lambda x: (x[1]), reverse=False)
      found =1 
      found_obj = ci[0][0]
   elif (len(not_close_objs) > 0):
      for nc in not_close_objs:
         print("not close" , nc)
      found = 0
   if found == 0:
      dist_objs = sorted(dist_objs, key=lambda x: (x[1]), reverse=False)
    
      obj_id = max_obj + 1
      objects[obj_id] = {}
      objects[obj_id]['obj_id'] = obj_id
      objects[obj_id]['ofns'] = []
      objects[obj_id]['oxs'] = []
      objects[obj_id]['oys'] = []
      objects[obj_id]['ows'] = []
      objects[obj_id]['ohs'] = []
      objects[obj_id]['oint'] = []
      objects[obj_id]['fs_dist'] = []
      objects[obj_id]['segs'] = []
      objects[obj_id]['ofns'].append(fn)
      objects[obj_id]['oxs'].append(cnt_x)
      objects[obj_id]['oys'].append(cnt_y)
      objects[obj_id]['ows'].append(cnt_w)
      objects[obj_id]['ohs'].append(cnt_h)
      objects[obj_id]['oint'].append(intensity)
      objects[obj_id]['fs_dist'].append(0)
      objects[obj_id]['segs'].append(0)
      found_obj = obj_id
   if found == 1:
      #if objects[found_obj]['report']['obj_class'] == "meteor":
      #if True:
      #   # only add if the intensity is positive and the forward motion compared to the last highest FM is greater.
      #   fm_last = calc_dist((objects[found_obj]['oxs'][0],objects[found_obj]['oys'][0]), (objects[found_obj]['oxs'][-1],objects[found_obj]['oys'][-1]))
      #   fm_this = calc_dist((objects[found_obj]['oxs'][0],objects[found_obj]['oys'][0]), (center_x, center_y))
      #   fm = fm_this - fm_last
      #   if intensity > 10 and fm > 0:
      #      objects[found_obj]['ofns'].append(fn)
      #      objects[found_obj]['oxs'].append(center_x)
      #      objects[found_obj]['oys'].append(center_y)
      #      objects[found_obj]['ows'].append(cnt_w)
      #      objects[found_obj]['ohs'].append(cnt_h)
      #      objects[found_obj]['oint'].append(intensity)

      #else:
      if fn not in objects[found_obj]['ofns']:
         cx = cnt_x + int(cnt_w/2)
         cy = cnt_y + int(cnt_h/2)
         if len(objects[found_obj]['oxs']) >= 1:
            fx = objects[found_obj]['oxs'][0] + int(objects[found_obj]['ows'][0]/2)
            fy = objects[found_obj]['oys'][0] + int(objects[found_obj]['ohs'][0]/2)
            lx = objects[found_obj]['oxs'][-1] + int(objects[found_obj]['ows'][-1]/2)
            ly = objects[found_obj]['oys'][-1] + int(objects[found_obj]['ohs'][-1]/2)
            last_fs_dist = calc_dist((fx,fy),(lx,ly))
            fs_dist = calc_dist((fx,fy),(cx,cy))
            this_seg = fs_dist - last_fs_dist
            if len(objects[found_obj]['segs']) > 3:
               med_seg = np.median(objects[found_obj]['segs'])
               
            objects[found_obj]['fs_dist'].append(fs_dist)
            objects[found_obj]['segs'].append(this_seg)
         else:
            objects[found_obj]['fs_dist'].append(0)
            objects[found_obj]['segs'].append(0)


         objects[found_obj]['ofns'].append(fn)
         objects[found_obj]['oxs'].append(cnt_x)
         objects[found_obj]['oys'].append(cnt_y)
         objects[found_obj]['ows'].append(cnt_w)
         objects[found_obj]['ohs'].append(cnt_h)
         objects[found_obj]['oint'].append(intensity)


   return(found_obj, objects)

def msk_fr(masks,frame):
   for msk in masks:
      mx1 = msk[0] 
      my1 = msk[1] 
      mx2 = msk[0] + msk[2]
      my2 = msk[1] + msk[3]
      frame[my1:my2,mx1:mx2] = [0]
   return(frame)

def detect_in_vals(vals_file, masks=None, vals_data=None):

   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(vals_file)

   if masks is None:
      masks = get_masks(cam, json_conf,0)
 
   video_file = vals_file.replace("-vals.json", ".mp4")
   video_file = video_file.replace("data/", "")
   if vals_data is None:
      data = load_json_file(vals_file)
   else:
      data = vals_data
   events = []
   data_x = []
   data_y = []
   cm =0
   last_i = None
   objects = {}
   total_frames = len(data['max_vals'])
   # examine basic values for each frame and find possible meteor detections
   for i in range(0,len(data['max_vals'])):
      x,y = data['pos_vals'][i]
      max_val = data['max_vals'][i]
      if max_val > 10:
         if last_i is not None and  last_i + 1 == i:
            cm += 1
         else:
            cm = 0
         masked = check_pt_in_mask(masks, x, y)
         if masked == 0:
            data_x.append(x)
            data_y.append(y)
            object, objects = find_object(objects, i,x, y, SD_W, SD_H, max_val, 0, 0, None)
      else:
         if cm >= 3:
            e_end = i
            e_start = i - cm
            #e_start -= 5
            #e_end += 5
            event = {}
            event['frames'] = [e_start,e_end]
            event['pos_vals'] = data['pos_vals'][e_start:e_end]
            event['max_vals'] = data['max_vals'][e_start:e_end]
            event['sum_vals'] = data['sum_vals'][e_start:e_end]
            events.append(event)
         cm = 0
      last_i = i

   # remove most eroneous objects
   objects = filter_bad_objects(objects)

   # analyze the objects for a first run meteor detection (strict=0) 
   for id in objects:
      print("FS", objects[id]['fs_dist'])
      print("SEGS:", objects[id]['segs'])
      objects[id] = analyze_object(objects[id], 0,0)
   objects = filter_bad_objects(objects)

   # merge object detections into trim clips
   objects = objects_to_trims(objects, video_file)
   return(events, objects, total_frames)

def buffer_start_end(start,end,buf_size, total_frames):
   start = start - buf_size
   end = end + buf_size
   status = "good"
   if start < 0:
      start = 0
      status = "start_truncated"
   if end >= total_frames:
      end = total_frames
      status = "end_truncated"
   return(start, end, status)

def crop_video(video_file, x, y, w, h, crop_out_file = None): 
   if crop_out_file is None:
      crop_out_file = video_file.replace(".mp4", "-crop.mp4")
   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)

   cmd = "/usr/bin/ffmpeg -i " + video_file + " -filter:v \"" + crop + "\" -y " + crop_out_file + " > /dev/null 2>&1"
   print("CMD:", cmd)
   os.system(cmd)
   return(crop_out_file)

def json_rpt(obj):
   print("")
   for key in obj:
      if key == "report":
         for rk in obj[key]:
            print(rk, obj[key][rk])
      else:
         print(key, obj[key])
   print("")

def get_cal_params(meteor_json_file):  
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(meteor_json_file)
   before_files = []
   after_files = []
   cal_files= get_cal_files(meteor_json_file, cam)
   for cf,td in cal_files:
      (c_datetime, ccam, c_date_str,cy,cm,cd, ch, cmm, cs) = convert_filename_to_date_cam(cf)
      time_diff = f_datetime - c_datetime
      sec_diff= time_diff.total_seconds()
      if sec_diff <= 0:
         after_files.append((cf,sec_diff))
      else:
         before_files.append((cf,sec_diff))

   print("BF:", before_files)
   print("AF:", after_files)

   after_files = sorted(after_files, key=lambda x: (x[1]), reverse=False)[0:5]
   print("Calibs after this meteor.")
   before_data = []
   after_data = []
   if len(after_files) > 0:
      for af in after_files:
         cpf, td = af
         cp = load_json_file(cpf)
         after_data.append((cpf, float(cp['center_az']), float(cp['center_el']), float(cp['position_angle']), float(cp['pixscale']), float(cp['total_res_px'])))

   if len(before_files) > 0:
      before_files = sorted(before_files, key=lambda x: (x[1]), reverse=False)[0:5]
      print("Calibs before this meteor.")
      for af in before_files:
         cpf, td = af
         cp = load_json_file(cpf)
         if "total_res_px" in cp:
            before_data.append((cpf, float(cp['center_az']), float(cp['center_el']), float(cp['position_angle']), float(cp['pixscale']), float(cp['total_res_px'])))
         else:
            print("NO RES?", cpf, cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'])
 
   if len(before_data) > 0:
      azs = [row[1] for row in before_data] 
      els = [row[2] for row in before_data] 
      pos = [row[3] for row in before_data] 
      px = [row[4] for row in before_data] 
      print("AZS:", azs)
   else:
      azs = []
      els = []
      pos = []
      px = []

   if len(azs) > 3:
      before_med_az = np.median(azs)
      before_med_el = np.median(els)
      before_med_pos = np.median(pos)
      before_med_px = np.median(px)
   elif len(az) > 0:
      print("PX:", px)
      before_med_az = np.mean(azs)
      before_med_el = np.mean(els)
      before_med_pos = np.mean(pos)
      before_med_px = np.mean(px)
   else:
      before_med_az = 0
      before_med_el = 0
      before_med_pos = 0
      before_med_px = 0

   azs = [row[1] for row in after_data] 
   els = [row[2] for row in after_data] 
   pos = [row[3] for row in after_data] 
   px = [row[4] for row in after_data] 

   if len(azs) > 3:
      after_med_az = np.median(azs)
      after_med_el = np.median(els)
      after_med_pos = np.median(pos)
      after_med_px = np.median(px)
   elif len(azs) :
      after_med_az = np.mean(azs)
      after_med_el = np.mean(els)
      after_med_pos = np.mean(pos)
      after_med_px = np.mean(px)
   else:
      after_med_az = 0
      after_med_el = 0
      after_med_pos = 0
      after_med_px = 0


   print("BEFORE MED:", before_med_az, before_med_el, before_med_pos, before_med_px)
   print("AFTER MED:", after_med_az, after_med_el, after_med_pos, after_med_px)
   if after_med_az == 0:
      after_med_az = before_med_az
      after_med_el = before_med_el
      after_med_pos = before_med_pos
      after_med_px = before_med_px
   autocal_dir = "/mnt/ams2/meteor_archive/" + STATION_ID + "/CAL/AUTOCAL/" + fy + "/solved/" 
   mcp_file = autocal_dir + "multi_poly-" + STATION_ID + "-" + cam + ".info"
   if cfe(mcp_file) == 1:
      mcp = load_json_file(mcp_file)
      # GET EXTRA STARS?
      before_cp = dict(mcp)
      after_cp = dict(mcp)
   else:
      mcp = None
      before_cp = {}
      after_cp = {}
   print("AFTER MCP")
   before_cp['center_az'] = before_med_az
   before_cp['center_el'] = before_med_el
   before_cp['position_angle'] = before_med_pos
   before_cp['pixscale'] = before_med_px 

   after_cp['center_az'] = after_med_az
   after_cp['center_el'] = after_med_el
   after_cp['position_angle'] = after_med_pos
   after_cp['pixscale'] = after_med_px 
   print("END func")
   return(before_cp, after_cp)
   
def reduce_points(xs, ys, cal_params):
   for i in range(0, len(xs)):
      new_x, new_y, ra ,dec , az, el = XYtoRADec(fd['x'],fd['y'],trim_clip,meteor_obj['cal_params'],json_conf)

 
def reduce_meteor(meteor_json_file):
   mj = load_json_file(meteor_json_file)
   if "cal_params" not in mj:
      cal_params, after_cal_params = get_cal_params(meteor_json_file)
   print(mj['hd_trim'])
   print(mj['hd_video_file'])
   print(mj['sd_video_file'])
   print(mj['sd_stack'])
   print(mj['hd_stack'])
   print("SDO:", mj['sd_objects'])
   print("HDO:", mj['hd_objects'])
   if "best_meteor" not in mj:
      # redect the meteor in the HD clip
      if cfe(mj['hd_trim']) == 1:
         print("DETECT IN HD" )
         best_meteor,hd_stack_img,bad_objs = fireball(mj['hd_trim'], json_conf)
         print("DETECT IN HD:", best_meteor)
         mj['best_meteor'] = best_meteor
         azs, els = reduce_points(xs, ys, cal_params)

def re_detect(date):
   files = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   data_dir = "/mnt/ams2/SD/proc2/" + date + "/data/" 
   for file in files:

      fn,dir= fn_dir(file)
      root = fn.split("-")[0]
      vals_file = data_dir + root + "-vals.json"
      mm_file = data_dir + root + "-maybe-meteors.json"
      cmd = "cd /home/ams/amscams/pythonv2/; ./flex-detect.py dv " + vals_file
      os.system(cmd)
      if cfe(mm_file):
         cmd = "cd /home/ams/amscams/pythonv2/; ./flex-detect.py vm " + mm_file 
         os.system(cmd)

def detect_all(vals_file):
   video_file = vals_file.replace("-vals.json", ".mp4") 
   video_file = video_file.replace("data/", "") 
   try:
      w,h,tf = ffprobe(video_file)
   except:
      print("BAD VIDEO FILE?!", video_file)
      return()
   w = int(w)
   h = int(h)
   hdm_x = 1920 / w 
   hdm_y = 1080 / h

   # GET THE EVENTS AND OBJECTS FROM THE VALS FILE
   events, objects,total_frames, = detect_in_vals(vals_file)
   obj_events = []
   for id in objects:
      obj = objects[id]
      oev = {}
      oev['frames'] = [obj['ofns'][0], obj['ofns'][-1]]
      oev['pos_vals'] = []
      for i in range(0, len(obj['oxs'])):
         x = obj['oxs'][i]
         y = obj['oys'][i]
         oev['pos_vals'].append((x,y))
      obj_events.append(oev)

   print("EVENTS:",  len(events))
   print("OBJECTS:",  len(objects))
   print("EVENTS:",  events)
   print("OBJECTS:",  objects)



   # FOR EACH EVENT MAKE AN SD TRIM FILE AND TRIM CROP FILE
   trim_files, crop_files, crop_boxes,durs = trim_events(vals_file, obj_events, total_frames, w, h, hdm_x, hdm_y)
   print("TRIM FILES:", trim_files) 
   print("CROP FILES:", crop_files) 
   print("CROP BOXES:", crop_boxes) 

   good_meteors = []
   # FOR EACH TRIM FILE RUN VIDEO METEOR DETECTION
   tc = 0
   for trim_file in trim_files:
      crop_file = crop_files[tc]
      crop_x = crop_boxes[tc][0]
      crop_y = crop_boxes[tc][1]
      sd_objects, frames = detect_meteor_in_clip(crop_file, None, 0, crop_x , crop_y , 0)
      mf = 0
      for id in sd_objects:
         sd_objects[id] = analyze_object(sd_objects[id], 0,1)
         if sd_objects[id]['report']['meteor'] == 1:
            mf= 1
            good_meteors.append((trim_file, crop_boxes[tc], sd_objects[id]))
      if mf == 0:
         PIPE_OUT = PIPELINE_DIR + "IN/"
         PIPE_FAILED = PIPELINE_DIR + "FAILED/"
         if cfe(PIPE_FAILED, 1) == 0:
            os.makedirs(PIPE_FAILED)
         #tfn = trim_file.split("/")[-1]
         #tdir = trim_file.replace(tfn, "")
         rpt_file = trim_file.replace(".mp4", "-failed.json")
         failed_data = {}
         failed_data['sd_objects'] = sd_objects
         failed_data['sd_crop_box'] = crop_boxes[tc]
         save_json_file(rpt_file, failed_data)
         twild = trim_file.replace(".mp4", "*")
         cmd = "mv " + twild + " " + PIPE_FAILED
         print(cmd)
         #os.system(cmd)
         exit()
         

      tc += 1

   for gm in good_meteors:
      trim_file, crop_box, obj = gm
      json_rpt(obj)

   if len(good_meteors) == 0:
      print("NO METEORS DETECT")
      return()
   

   # FOR EACH TRIM IF THERE IS A METEOR DETECTION GRAB AND SYNC THE HD FILE
   tc = 0
   for trim_file, crop_boxes, sd_objs in good_meteors:
      hd_trim = find_hd(trim_file,durs[tc])
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(hd_trim, json_conf, 0, 1, [], 0,[])
      sx1,sy1,sx2,sy2 = crop_boxes
      nw = (sx2 - sx1) * 2
      nh = (sy2 - sy1) * 2
      print("NEW W/H:", nw,nh) 

      mx = int(int((sx1 + sx2) * hdm_x) / 2)
      my = int(int((sy1 + sy2) * hdm_y) / 2)

      cx1 = int(mx - nw/2) 
      cy1 = int(my - nh/2) 
      cx2 = int(mx + nw/2) 
      cy2 = int(my + nh/2) 

      cv2.rectangle(frames[0], (mx-5, my-5), (mx+5, my+5), (255,255,255), 1, cv2.LINE_AA)
      cv2.rectangle(frames[0], (cx1, cy1), (cx2, cy2), (100,100,100), 1, cv2.LINE_AA)
      cv2.imshow('pepe', frames[0])
      cv2.waitKey(90)
   
      if hd_trim is not None:
         print("TRIM HD CROP FILE:", hd_trim, cx1,cy1,cx2-cx1, cy2-cy1)
         hd_crop_out_file = crop_video(hd_trim, cx1, cy1, cx2-cx1, cy2-cy1)
      else:
         print("HD TRIM:", hd_trim)
      tc += 1

   # NOW WE SHOULD ALREADY HAVE AN SD METEOR. 
   # LETS TRY TO FIND IT IN THE HD CROP
   # IF WE FAIL, THEN WE WILL JUST USE THE SD METEOR AND UPSCALE THINGS TO WORK
   # ELSE WE WILL USE THE HD DETECT INFO

   for trim_file, crop_box, sd_objs in good_meteors:
      rpt_file = trim_file.replace(".mp4", "-meteor.json")
      md = {}
      md['sd_cropbox'] = crop_box
      md['sd_trim_file'] = trim_file
      md['sd_objs'] = sd_objs
      save_json_file(rpt_file, md)

   

def get_trim_num(file):
   el = file.split("-trim") 
   at = el[1]
   at = at.replace("-SD.mp4", "")
   at = at.replace("-crop", "")
   at = at.replace("-HD.mp4", "")
   at = at.replace(".mp4", "")
   at = at.replace("-", "")
   at = at.replace(".json", "")
   return(at)

def find_hd(sd_trim_file, dur, meteor_start_frame=0):
   PIPE_OUT = PIPELINE_DIR + "IN/"
   if cfe(PIPE_OUT, 1) == 0:
      os.makedirs(PIPE_OUT)
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(sd_trim_file)
   sdfn = sd_trim_file.split("/")[-1]
   sd_trim_num = get_trim_num(sd_trim_file) 
   print("SD FILE TIME:", f_datetime)
   print("SD TRIM NUM:", sd_trim_num)
   extra_trim_sec = int(sd_trim_num) / 25
   print("EXTRA TRIM SECONDS:", sd_trim_num)
   sd_trim_start = f_datetime + datetime.timedelta(seconds=extra_trim_sec)
   if meteor_start_frame > 0:
      mext = (meteor_start_frame / 25) + extra_trim_sec
      meteor_event_start = f_datetime + datetime.timedelta(seconds=mext)

      sd_start_min_before = sd_trim_start + datetime.timedelta(seconds=-60)
      sd_start_min_after = sd_trim_start + datetime.timedelta(seconds=+60)
   else:
      meteor_event_start = sd_trim_start
      mext = extra_trim_sec

   # get the HD files within +/- 1 min of the SD trim start time for this cam
   print("SD TRIM START TIME:", sd_trim_start)
   print("SD METEOR START TIME:", meteor_event_start)
   date_wild = sd_trim_start.strftime("%Y_%m_%d_%H")
   #date_wild_before = sd_start_min_before.strftime("%Y_%m_%d_%H_%M")
   #date_wild_after = sd_start_min_after.strftime("%Y_%m_%d_%H_%M")
   print("CAM:", cam)
   print("DATE WILD:", date_wild)
   hd_wild = "/mnt/ams2/HD/" + date_wild + "*" + cam + ".mp4"
   #hd_wild_before = "/mnt/ams2/HD/" + date_wild_before + "*" + cam + ".mp4"
   #hd_wild_after = "/mnt/ams2/HD/" + date_wild_after + "*" + cam + ".mp4"
   print("HD WILD:", hd_wild)
   hd_matches = glob.glob(hd_wild)

   best_hd_matches = []

   for hd_file in hd_matches:
      (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)
      hd_time_diff = (hd_datetime - sd_trim_start).total_seconds()

      print("SD/HD TIME DIFF:", hd_time_diff)
      if -60 <= hd_time_diff <= 0:
         best_hd_matches.append((hd_file, hd_time_diff))
      #if hd_time_diff > 0:
      #   hd_matches_before = glob.glob(hd_wild_before)

   hd_trim_out = None
   print("BEST HD FILE:", best_hd_matches)
   if len(best_hd_matches) > 0:
      temp = sorted(best_hd_matches, key=lambda x: (x[1]), reverse=True)
      best_hd_matches = [temp[0]]
      print("SORTED BEST HD FILE:", best_hd_matches)

   if len(best_hd_matches) == 1:
      hd_file = best_hd_matches[0][0]

      w,h,frames = ffprobe(hd_file)
      print(w,h,frames)
      hd_time_diff = best_hd_matches[0][1]
      hd_trim_start = (abs(hd_time_diff) * 25) 
      print("HD TRIM START:", hd_trim_start)
      hdfn, dir = fn_dir(hd_file)
      hd_trim_end = hd_trim_start + dur + 100
      print("HD TRIM OUT:", hd_trim_out)
      #if cfe(hd_trim_out) == 0:
      if True:
         print(hd_trim_start, hd_trim_end, hd_file)
         hd_trim_start, hd_trim_end, status = buffer_start_end(hd_trim_start, hd_trim_end, 10, 1499)
         hdfn = hdfn.replace(".mp4", "-trim-" + "{:04d}".format(int(hd_trim_start)) + ".mp4")
         hd_trim_out = PIPE_OUT + hdfn
         trim_min_file(hd_file, hd_trim_out, hd_trim_start, hd_trim_end)
      (hd_datetime, hd_cam, hd_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(hd_file)

   # We should only need the after file if the current file worked but the hd time is at the EOF

   return(hd_trim_out)



def trim_min_file(video_file, trim_out_file, trim_start_num, trim_end_num):
   cmd = """ /usr/bin/ffmpeg -i """ + video_file + """ -vf select="between(n\,""" + str(trim_start_num) + """\,""" + str(trim_end_num) + """),setpts=PTS-STARTPTS" -y """ + trim_out_file + " >/dev/null 2>&1"
   print("CMD:", cmd)
   os.system(cmd)


def trim_events(video_file, events, total_frames, sd_w, sd_h, hdm_x, hdm_y):

   PIPE_OUT = PIPELINE_DIR + "IN/"
   

   if "vals" in video_file:
      video_file = video_file.replace("-vals.json", ".mp4") 
      video_file = video_file.replace("data/", "") 
   vfn = video_file.split("/")[-1]
   sd_min_dir = video_file.replace(vfn, "trim_files/")
   if cfe(PIPE_OUT, 1) == 0:
      os.makedirs(PIPE_OUT)

   #print("TRIM EVENTS")
   trim_files = []
   crop_files = []
   crop_boxes = []
   durations = []
   for ev in events:
      start, end = ev['frames']
      start, end, status = buffer_start_end(start, end, 10, total_frames)
      dur = end - start
      trim_out_file = PIPE_OUT + vfn.replace(".mp4", "-trim-" + str(start) + "-SD.mp4")
      if cfe(trim_out_file) == 0: 
         trim_min_file(video_file, trim_out_file, start, end)
      xs = [i[0] for i in ev['pos_vals']]
      ys = [i[1] for i in ev['pos_vals']]
      (cx1, cy1, cx2, cy2, mx,my) = find_crop_size(min(xs),min(ys),max(xs),max(ys), sd_w, sd_h, hdm_x, hdm_y )
     
      cw = cx2 - cx1 
      ch = cy2 - cy1 
      crop_out_file = trim_out_file.replace(".mp4", "-crop.mp4")
      print("SD CROP BOUNDS:", cx1, cy1, cx2, cy2)
      print("SD CROP SIZE:", cw, ch)
      print("CROP OUT FILE:", crop_out_file)

      if cfe(crop_out_file) == 0: 
         crop_out_file = crop_video(trim_out_file, cx1, cy1, cw, ch)
      print("TRIM :", start, end, video_file)
      print("CROP:", cx1,cy1, cx2,cy2,cw,ch, crop_out_file)

      trim_files.append(trim_out_file)
      crop_files.append(crop_out_file)
      crop_boxes.append((cx1,cy1,cx2,cy2))
      durations.append(dur)

   return(trim_files, crop_files, crop_boxes, durations)
      
     

def trim_meteors_from_min_file(objects):
   # for each object that might be a meteor 
   # trim out the SD clip
   # run video detect on SD clip
   # if it passes on SD
   # find HD file and trim it
   # make an HD crop version
   # run video detect on HD (crop) file
 
   all_clips = {}
   for id in objects:
      # analyze object with strict=0 to confirm meteor
      objects[id] = analyze_object(objects[id], 0,0)
      # If it is a potential meteor split out the SD file
      if objects[id]['report']['non_meteor'] == 0:
         objects[id]['sd_video_file'] = video_file
    
         video_outfile = "/mnt/ams2/tests/" + objects[id]['trim_file'] 
         jpg_outfile = "/mnt/ams2/tests/" + objects[id]['trim_file'] + "-%04d.jpg"
         jpg_outfile = jpg_outfile.replace(".mp4", "")

         start_trim = "{:04d}".format(objects[id]['clip_start_fn'])
         end_trim = objects[id]['clip_start_fn']
         test_outfile = jpg_outfile.replace("%04d", start_trim)

         buf_size = 5
         buf_start, buf_end = buffered_start_end(objects[id]['clip_start_fn'],objects[id]['clip_end_fn'], total_frames, buf_size)

         # dump SD frames
         if cfe(test_outfile) == 0:
            ffmpeg_splice(video_file, buf_start, buf_end, jpg_outfile)
         # dump SD video 
         if cfe(video_outfile) == 0:
            ffmpeg_splice(video_file, buf_start, buf_end, video_outfile)
         objects[id]['sd_trim_file'] = video_outfile

         all_clips[video_outfile] = {}




         
         #obj_report(objects[id])

   # run video meteor detect on the SD video trim
   for video_outfile in all_clips:
      sd_objects, frames = detect_meteor_in_clip(video_outfile, None, fn = 0, crop_x = 0, crop_y = 0, hd_in = 0)
      sd_objects = filter_bad_objects(sd_objects)
      for id in sd_objects:
         # analyze objects with strict=1 to verify meteor
         sd_objects[id] = analyze_object(sd_objects[id], 0, 1)
         sd_objects[id]['sd_video_file'] = video_outfile
         sd_objects[id]['trim_file'] = video_outfile
         obj_report(sd_objects[id])


   return(events,objects)

def objects_to_trims(objects, video_file):
   trim_clips = [] 
   rm_objs = [] 
   oc = 0
   for id in objects:
      merge_clip = 0
      if len(trim_clips) == 0:
         tc = {}
         start = objects[id]['ofns'][0]
         end   = objects[id]['ofns'][-1]
         tc['start'] = start
         tc['end'] = end 
         trim_file = video_file.split("/")[-1]
         trim_file = trim_file.replace(".mp4", "-trim-" + "{:04d}".format(start) + ".mp4")
         objects[id]['trim_file'] = trim_file
         objects[id]['clip_start_fn'] = tc['start']
         objects[id]['clip_end_fn'] = tc['end']
         trim_clips.append(tc)
      else:
         # check if the last trim clip is within 25 frames of this clip. If it is merge this one into the last one
         last_end = trim_clips[oc-1]['end']
         last_start = trim_clips[oc-1]['start']
         start = objects[id]['ofns'][0]
         end = objects[id]['ofns'][-1]


         if tc['start'] - last_end < 25:
            merge_clip = 1
            trim_clips[oc-1]['end']= objects[id]['ofns'][-1]
            objects[id]['trim_file'] = trim_file
            objects[id]['clip_start_fn'] = last_start 
            objects[id]['clip_end_fn'] = end 
            objects[last_obj_id]['clip_end_fn'] = end


            objects[id]['obj_end_fn'] = tc['end']
         else:
            tc = {}
            tc['start'] = objects[id]['ofns'][0]
            tc['end']   = objects[id]['ofns'][-1]
            trim_clips.append(tc)

            trim_file = video_file.split("/")[-1]
            trim_file = trim_file.replace(".mp4", "-trim-" + "{:04d}".format(start) + ".mp4")
            objects[id]['trim_file'] = trim_file
            objects[id]['clip_start_fn'] = tc['start']
            objects[id]['clip_end_fn'] = tc['end']
         
      if merge_clip != 1:  
         oc += 1
      last_obj_id = id
   return(objects)      

def obj_report(object):
   print("")
   if "sd_video_file" in object:
      print("Video File:           :    {:s} ".format(str(object['sd_video_file'])))
   else:
      print("WARNING: no sd_video_file in object.")
   if "trim_file" in object:
      print("Trim File:            :    {:s} ".format(str(object['trim_file'])))
      print("WARNING: no trim_file in object.")
   print("Start                 :    {:s} ".format(str(object['ofns'][0])))
   print("End                   :    {:s} ".format(str(object['ofns'][-1])))
   print("Frames                :    {:s} ".format(str(object['ofns'])))
   print("Xs                    :    {:s} ".format(str(object['oxs'])))
   print("Ys                    :    {:s} ".format(str(object['oys'])))
   print("Intensity             :    {:s} ".format(str(object['oint'])))
   for field in object['report']:
      print("{:18s}    :    {:s} ".format(field, str(object['report'][field])))


#   print("Consecutive Motion    :    {:s} ".format(str(object['report']['cm'])))
#   print("Unique Points         :    {:s} ".format(str(object['report']['unq_points'])))
#   print("Unique Percent        :    {:s} ".format(str(object['report']['unq_perc'])))
#   print("Object PX Length      :    {:s} ".format(str(object['report']['object_px_length'])))
#   print("Object Line Segments  :    {:s} ".format(str(object['report']['line_segments'])))
#   print("Object X Segments     :    {:s} ".format(str(object['report']['x_segs'])))
#   print("Object Ms             :    {:s} ".format(str(object['report']['ms'])))
#   print("Object Bs             :    {:s} ".format(str(object['report']['bs'])))
#   print("Object Non-Meteor     :    {:s} ".format(str(object['report']['non_meteor'])))
#   print("Bad Items             :    {:s} ".format(str(object['report']['bad_items'])))
#object['report']['object_px_length'], object['report']['line_segments'], object['report']['x_segs'], object['report']['ms'], object['report']['bs']

def detect_meteor_in_clip(trim_clip, frames = None, fn = 0, crop_x = 0, crop_y = 0, hd_in = 0 ):
   objects = {}

   past_cnts = []

   print("DETECT METEORS IN VIDEO FILE:", trim_clip)
   if trim_clip is None: 
      return(objects, []) 

   if frames is None :
      print("LOAD FRAMES FAST...")  
      frames,color_frames,subframes,sum_vals,max_vals,pos_vals = load_frames_fast(trim_clip, json_conf, 0, 1, [], 0,[])

   median_frame = cv2.convertScaleAbs(np.median(np.array(frames), axis=0))
   if len(median_frame.shape) == 3:
      median_frame = cv2.cvtColor(median_frame, cv2.COLOR_BGR2GRAY)
   median_frame = cv2.GaussianBlur(median_frame, (7, 7), 0)
   _, threshold = cv2.threshold(median_frame.copy(), 50, 255, cv2.THRESH_BINARY)
   mask_cnts= get_contours_in_image(threshold)


   if len(frames) == 0:
      return(objects, []) 

   if frames[0].shape[1] == 1920 or hd_in == 1:
      hd = 1
      sd_multi = 1
   else:
      hd = 0
      sd_multi = 1920 / frames[0].shape[1]



   if len(frames[0].shape) == 3:
      aframe = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
      aframe = cv2.subtract(aframe, median_frame) 
      #aframe = msk_fr(mask_cnts, aframe)
      image_acc = aframe
   else:
      image_acc = frames[0]
   image_acc = np.float32(image_acc)



   #for i in range(0,len(frames)):
   #   if len(frame.shape) == 3:
   #      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   #   frame = frames[i]
 
#      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
#      alpha = .5
#      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)

   # preload the bg
   for frame in frames:
      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


      frame = np.float32(frame)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      alpha = .5


      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), blur_frame,)
      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)

   fn = 0
   for frame in frames:

      if len(frame.shape) == 3:
         frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      if fn == 0:
         if len(frame.shape) == 3:
            aframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         else:
            aframe = frame.copy()

      #print(frame.shape, median_frame.shape)
      frame = cv2.subtract(frame, median_frame) 

      show_frame = frame.copy()
      frame = np.float32(frame)
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      alpha = .5


      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), blur_frame,)


      hello = cv2.accumulateWeighted(blur_frame, image_acc, alpha)

      show_frame = frame.copy()
      avg_px = np.mean(image_diff)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(image_diff)
      thresh = max_val - 10
      if thresh < 5:
         thresh = 5

      if len(past_cnts) > 0:
         image_diff = msk_fr(past_cnts, image_diff)
         #cv2.imshow("ID", image_diff)
         #cv2.waitKey(30)
      cnts,rects = find_contours_in_frame(image_diff, thresh)
      icnts = []
      if len(cnts) < 5 and fn > 0:
         for (cnt) in cnts:
            px_diff = 0
            x,y,w,h = cnt
            if w > 1 and h > 1:

               past_cnts.append((x,y,w,h))
               intensity,mx,my,cnt_img = compute_intensity(x,y,w,h,frame,aframe)
               cx = int(mx) 
               cy = int(my) 
               cv2.circle(show_frame,(cx+crop_x,cy+crop_y), 10, (255,255,255), 1)
               object, objects = find_object(objects, fn,cx+crop_x, cy+crop_y, w, h, intensity, hd, sd_multi, cnt_img)

               objects[object]['trim_clip'] = trim_clip
               cv2.rectangle(show_frame, (x, y), (x+w, y+h), (255,255,255), 1, cv2.LINE_AA)
               #desc = str(fn) + " " + str(intensity) + " " + str(objects[object]['obj_id']) + " " + str(objects[object]['report']['obj_class']) #+ " " + str(objects[object]['report']['ang_vel'])
               desc = str(fn) + " " + str(intensity) + " " + str(objects[object]['obj_id'])  
               cv2.putText(show_frame, desc,  (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      
      cv2.putText(show_frame, str(fn),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
      show_frame = cv2.convertScaleAbs(show_frame)
      show = 1
      if SHOW == 1:
         cv2.imshow('Detect Meteor In Clip', show_frame)
         cv2.waitKey(30)
      fn += 1



   if SHOW == 1:
      cv2.destroyAllWindows()

   return(objects, frames)   

def get_contours_in_image(frame ):
   cont = [] 
   if len(frame.shape) > 2:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
   cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      if w > 1 or h > 1:
         cont.append((x,y,w,h))
   return(cont)

def find_contours_in_frame(frame, thresh=25 ):
   contours = [] 
   result = []
   _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(threshold.copy(), None , iterations=3)
   threshold = cv2.convertScaleAbs(thresh_obj)
   cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   show_frame = cv2.resize(threshold, (0,0),fx=.5, fy=.5)
   if len(cnts) > 20:
      thresh = thresh +5 
      _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
      #dil
      #thresh_obj = cv2.dilate(threshold.copy(), None , iterations=4)
      #threshold = cv2.convertScaleAbs(thresh_obj)
      cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

   # now of these contours, remove any that are too small or don't have a recognizable blob
   # or have a px_diff that is too small

   rects = []
   recs = []
   if len(cnts) < 250:
      for (i,c) in enumerate(cnts):
         px_diff = 0
         x,y,w,h = cv2.boundingRect(cnts[i])
        

         if w > 1 or h > 1 and (x > 0 and y > 0):

            cnt_frame = frame[y:y+h, x:x+w]
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_frame)
            avg_val = np.mean(cnt_frame)
            #if max_val - avg_val > 5 and (x > 0 and y > 0):
            if (x > 0 and y > 0):
               rects.append([x,y,x+w,y+h])
               contours.append([x,y,w,h])

   #rects = np.array(rects)



   if len(rects) > 2:
      recs, weights = cv2.groupRectangles(rects, 0, .05)
      rc = 0
      for res in recs:
         rc = rc + 1

   #cv2.imshow("pepe", threshold)

   return(contours, recs)

