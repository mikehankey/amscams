import datetime
import scipy.optimize
import html
import time
import json
import numpy as np
import cv2
import cgi
import time
import glob
import os
import cgitb
import sys

from os.path import isfile
from lib.PrintUtils import get_meteor_date
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe
from lib.VideoLib import get_masks, convert_filename_to_date_cam, find_hd_file_new, load_video_frames, find_min_max_dist, ffmpeg_dump_frames
from lib.DetectLib import check_for_motion2, eval_cnt, eval_cnt_better, find_bright_pixels
from lib.MeteorTests import test_objects, meteor_test_elp_frames, meteor_test_cm_gaps
from lib.ImageLib import mask_frame,stack_frames, adjustLevels, upscale_to_hd, median_frames
from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec, define_crop_box
from lib.UtilLib import check_running, calc_dist, angularSeparation, bound_cnt
from lib.Fix_Old_Detection import fix_hd_vid_real_inline
 
  

def update_frame_ajax(json_conf, form):
   
   sd_video_file = form.getvalue("sd_video_file")
   fn = form.getvalue("fn")
   new_x = int(float(form.getvalue("new_x")))
   new_y = int(float(form.getvalue("new_y")))
   
   mrf = sd_video_file.replace(".mp4", "-reduced.json")
   mr = load_json_file(mrf)      

   #Temporary but necessary
   try:
      mr['metframes'][fn]['hd_x'] = int(new_x)
      mr['metframes'][fn]['hd_y'] = int(new_y)
   except Exception: 
      #os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py dm " + sd_video_file + "> /mnt/ams2/tmp/rrr.txt")
      #mrf = sd_video_file.replace(".mp4", "-reduced.json")
      #mr = load_json_file(mrf)   
      #mr['metframes'][fn]['hd_x'] = int(new_x)
      #mr['metframes'][fn]['hd_y'] = int(new_y)
      what = 1

   mr['metframes'][fn]['hd_x'] = int(new_x)
   mr['metframes'][fn]['hd_y'] = int(new_y)
   save_json_file(mrf, mr)

   # this will make new thumbs
   # this will update all values (ra,dec etc) and make new thumbs from new point. 
   resp = {}
   resp['msg'] = "new frame added."
   resp['new_frame'] = mr['metframes'][fn]

   #Twice otherwice it doesn't work
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt")
   #os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt")   

   print(json.dumps(resp))


def add_frame_ajax( json_conf, form):
   hdm_x = 2.7272727272727272
   hdm_y = 1.875

   sd_video_file = form.getvalue("sd_video_file")
   new_fn = form.getvalue("fr") 

   prev_fn = str(int(new_fn) - 1)
   next_fn = str(int(new_fn) + 1)
   
   mrf = sd_video_file.replace(".mp4", "-reduced.json")
   mr = load_json_file(mrf)
   #print(mr['metconf']['sd_fns'])
   first_frame = int(mr['metconf']['sd_fns'][0])
   first_x = int(mr['metconf']['sd_xs'][0])
   metframes = mr['metframes']
   metconf = mr['metconf']
   #print(mr)
   #if new_fn in metframes:
   if str(prev_fn) in metframes:

      # frame exists before make est from prev frame info
      last_x = metframes[prev_fn]['sd_cx']
      last_y = metframes[prev_fn]['sd_cy']
      #est_x = int(last_x + (metconf['x_dir_mod'] * metconf['sd_seg_len']))
      #est_y = int((metconf['sd_m']*est_x)+metconf['sd_b'])
      #est_x = int(est_x * hdm_x)
      #est_y = int(est_y * hdm_y)
      fcc = (int(new_fn) - int(first_frame)) 
      #print("FCC:", fcc, metconf['sd_seg_len'], metconf['sd_acl_poly'])
      est_x = int(first_x) + (metconf['x_dir_mod'] * (metconf['sd_seg_len']*fcc)) + (metconf['sd_acl_poly'] * (fcc**2))
      est_y = (metconf['sd_m']*est_x)+metconf['sd_b']
      #sd_cx = est_x
      #sd_cy = est_y
      sd_cx = last_x
      sd_cy = last_y
      est_x = int(sd_cx *hdm_x)
      est_y = int(sd_cy *hdm_y)

   elif str(next_fn) in metframes:
      # this frame exists before any others so need to add est in reverse. 
      last_x = metframes[next_fn]['sd_cx']
      last_y = metframes[next_fn]['sd_cy']
      #est_x = int(last_x + ((-1*metconf['x_dir_mod']) * metconf['med_seg_len']))
      #est_x = int(last_x + ((-1*metconf['x_dir_mod']) * metconf['sd_seg_len']))
      #est_y = int((metconf['sd_m']*est_x)+metconf['sd_b'])
      #est_x = int(est_x * hdm_x)
      #est_y = int(est_y * hdm_y)

      #print("<HR>", int(last_x), metconf['x_dir_mod'], metconf['sd_seg_len'], metconf['sd_acl_poly'])
      est_x = int(last_x) + (-1*metconf['x_dir_mod'] * (metconf['sd_seg_len']*1)) + (metconf['sd_acl_poly'] * 1)
      est_y = (metconf['sd_m']*est_x)+metconf['sd_b']
      sd_cx = est_x
      sd_cy = est_y
      sd_cx = last_x
      sd_cy = last_y
      est_x = int(sd_cx * hdm_x)
      est_y = int(sd_cy * hdm_y)

   if new_fn not in metframes:
      metframes[new_fn] = {}
      metframes[new_fn]['fn'] = new_fn 
      metframes[new_fn]['hd_x'] = est_x
      metframes[new_fn]['hd_y'] = est_y
      metframes[new_fn]['w'] = 5
      metframes[new_fn]['h'] = 5
      metframes[new_fn]['sd_x'] = sd_cx
      metframes[new_fn]['sd_y'] = sd_cy
      metframes[new_fn]['sd_w'] = 6
      metframes[new_fn]['sd_h'] = 6
      metframes[new_fn]['sd_cx'] = sd_cx
      metframes[new_fn]['sd_cy'] = sd_cy
      metframes[new_fn]['ra'] = 0
      metframes[new_fn]['dec'] = 0
      metframes[new_fn]['az'] = 0
      metframes[new_fn]['el'] = 0
      metframes[new_fn]['max_px'] = 0
      x1,y1,x2,y2 = bound_cnt(est_x,est_y,1920,1080,6)
      frames = load_video_frames(sd_video_file, json_conf)
      ifn = int(new_fn)
      frame = frames[ifn]
      frame = cv2.resize(frame, (1920,1080)) 
      
      cnt_img = frame[y1:y2,x1:x2]
      min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
      hd_x = max_loc[0] + x1  
      hd_y = max_loc[1] + y1 
      #print("MAX:", max_loc)
      metframes[new_fn]['hd_x'] = hd_x
      metframes[new_fn]['hd_y'] = hd_y 
      metframes[new_fn]['est_x'] = est_x
      metframes[new_fn]['est_y'] = est_y 
   else :
      resp = {}
      resp['msg'] = "frame " + str(new_fn)  + " already exists."
      #for fn in metframes:
      #   print(str(fn), "<BR>")
      print(json.dumps(resp))
      exit()
 

   mr['metframes'] = metframes
   save_json_file(mrf, mr)
   print("SAVED HERE ")
   #print(mrf)
   #print("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt")
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt")
   mr = load_json_file(mrf )
   resp = {}
   resp['msg'] = "new frame added."
   resp['newframe'] = mr['metframes'][new_fn] 
   print(json.dumps(resp))
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt")


def remove_dupe_cat_stars(paired_stars):
   used = {}
   new_paired_stars = []
   for data in paired_stars:
      iname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,old_cat_x,old_cat_y,six,siy,cat_dist  = data
      used_key = str(six) + "." + str(siy)
      if used_key not in used:
         new_paired_stars.append(data)
         used[used_key] = 1
   return(new_paired_stars)


def clone_meteor_cal(json_conf, form):
   print("Clone Meteor Cal.")
   file = form.getvalue("file")
   prefix =  file.split("/")[-1][0:30]
   red_file = file.replace("-stacked.png", "-reduced.json") 
   if cfe(red_file) == 1:
      red_data = load_json_file(red_file)
      if "cal_params" in red_data:
         print("Cloning", prefix)
         new_dir = "/mnt/ams2/cal/freecal/" + prefix + "/" 
         os.system("mkdir " + new_dir)
         new_file = new_dir + prefix + "-calparams.json"
         save_json_file(new_file, red_data['cal_params'])


def clone_cal(json_conf, form):
   print("Clone Cal.")
   file = form.getvalue("file")
   prefix =  file.split("/")[-1][0:30]
   red_file = file.replace("-stacked.png", "-reduced.json") 
   if cfe(red_file) == 1:
      red_data = load_json_file(red_file)
      if "cal_params" in red_data:
         print("Cloning", prefix)
         new_dir = "/mnt/ams2/cal/freecal/" + prefix + "/" 
         os.system("mkdir " + new_dir)
         new_file = new_dir + prefix + "-stacked-calparams.json"
         save_json_file(new_file, red_data['cal_params'])
         hd_stack = red_data['hd_video_file']
         hd_stack = hd_stack.replace(".mp4", "-stacked.png") 
         if "SD" in hd_stack:
            hd_stack = hd_stack.replace("SD/proc2/", "meteors/")
            hd_stack = hd_stack.replace("passed/", "")
            #hd_stack = hd_stack.replace(".png", "-stacked.png")
            cal_img_file = new_file.replace("-calparams.json", "-stacked.png")
            if cfe(hd_stack) == 1:
               sd_img = cv2.imread(hd_stack)
               hd_img = cv2.resize(sd_img, (1920,1080)) 
               cv2.imwrite(cal_img_file, hd_img)
         else:
            hd_stack = red_data['hd_video_file']
            hd_stack = hd_stack.replace(".mp4", "-stacked.png") 
            cal_img_file = new_file.replace("-calparams.json", "-stacked.png")
            cmd = "cp " + hd_stack + " " + cal_img_file
            print("<H1>", cmd, "</h1>")
            os.system(cmd)
            
       
         print(hd_stack)
         print("NEW CAL:", new_file)
         cmd = "cd /home/ams/amscams/pythonv2/; ./XYtoRAdecAzEl.py az_grid " + new_file + " >/mnt/ams2/tmp/xy.out"
         os.system(cmd)
         print(cmd)
   else:
      print("No cal params to clone!?")

def sat_cap(json_conf, form):
   print ("Satellite Processing")
   video_file = form.getvalue("input_file")
   stack_file = form.getvalue("stack_file")
   next_stack_file = form.getvalue("next_stack_file")
   merge_needed = form.getvalue("merge_needed")
   if merge_needed is None:
      print("Do you need to merge the file after this one to captre the entire event? ")
      print("<a href=webUI.py?cmd=sat_cap&merge_needed=1&input_file=" + video_file + "&stack_file=" + stack_file + "&next_stack_file=" + next_stack_file + ">Yes</a> / "  )
      print("<a href=webUI.py?cmd=sat_cap&merge_needed=0&input_file=" + video_file + "&stack_file=" + stack_file + "&next_stack_file=" + next_stack_file + ">No</a>")
      print("<P>First File<BR><img src=" + stack_file + "><BR>")
      print("Next File<BR><img src=" + next_stack_file + ">")
      return()
 
   el = video_file.split("/")
   base_dir = el[-1].replace(".mp4", "")

   reduce_dir = "/mnt/ams2/satellites/tmp/" + base_dir  + "/" 

   if cfe(reduce_dir) == 0:
      print("Just starting...")
      if int(merge_needed) == 1:
         vid1 = stack_file.replace("-stacked.png", ".mp4")
         vid2 = next_stack_file.replace("-stacked.png", ".mp4")
         print("need merge ...", vid1, vid2)
         # ffmpeg trim the two files
      else:
         print("no merge needed...", stack_file, next_stack_file)
         # set it up

def man_reduce_canvas(frame_num,thumbs,file,cal_params_file,red_data):
   rand = time.time()
   c = 0 
   jstxt = "<script> var imgFiles = new Array(); \n "
   jstxt = jstxt + " var orig_file = '" + file + "';\n"
   jstxt = jstxt + " var cal_params_file = '" + cal_params_file + "';\n"
   for thumb in thumbs:
      img = thumb.replace("-t", "")
      c = c + 1
      jstxt = jstxt + "imgFiles[" + str(c) + "] = \"" + img + "\";\n" 

   fb = thumbs[0].split("frames")
   frame_base = fb[0]

      #<div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
   jstxt = jstxt + "</script>"
   print(jstxt)
   print("""
      
      <canvas id="cnv" width="960" height="540" style="border:2px solid #000000;"></canvas>
      <div style="clear:both">
      </div>
      <div>manual reduction</div>
      <form>
      <input type=button name=next onclick="javascript:show_frame_image('""" + str(frame_num-1)+ """', '""" + frame_base + """', 'prev','""" + file + "','" + cal_params_file + """')" value="Prev Frame">
      <input type=button name=next onclick="javascript:show_frame_image('""" + str(frame_num+1)+ """', '""" + frame_base + """', 'next','""" + file + "','" + cal_params_file + """')" value="Next Frame">
      </form>
      <div id="info_panel"></div>
   """)
   #extra_html = "<script>var stars = [];\n" 
   extra_html = ""
   #extra_html = "<script src=manreduce.js?" + str(rand) + "></script>"
   extra_html = extra_html + "<script>\n   show_frame_image('" + str(frame_num) + "','" + frame_base + "','prev');\n</script>"

   extra_html = extra_html + """

   <script>
    var grid_by_default = false;
    var my_image = '{MY_IMAGE}';
    var hd_stack_file = '{HD_STACK_FILE}';
    var az_grid_file = '{AZ_GRID_FILE}';
    var stars = [];
   </script>

   <div hidden>
    <img id='half_stack_file' src='{HALF_STACK_FILE}'>
    <img id='az_grid_file' src='{AZ_GRID_FILE}'>
    <img id='meteor_img' src='{METEOR_IMG}'>
   </div>

   """
   half_stack_img= red_data['sd_video_file'].replace(".mp4", "-half-stack.png")

   extra_html = extra_html.replace("{MY_IMAGE}", half_stack_img)
   return(extra_html)

def calc_frame_time(video_file, frame_num):
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(video_file)
   el = video_file.split("-trim")
   min_file = el[0] + ".mp4"
   ttt = el[1].split(".")
   ttt[0] = ttt[0].replace("-stacked", "")
   trim_num = int(ttt[0])
   extra_sec = trim_num / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)
   extra_meteor_sec = frame_num / 25
   meteor_frame_time = start_trim_frame_time + datetime.timedelta(0,extra_meteor_sec)
   meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]



   return(meteor_frame_time,meteor_frame_time_str)


def reduce_point(cal_params_file, meteor_json_file, frame_num, point_data,json_conf):
   if "reduced" in cal_params_file:
      red_data = load_json_file(cal_params_file)
      cal_params = red_data['cal_param']
   
   else:
      cal_params = load_json_file(cal_params_file)
   (cal_date, cam_id, cal_date_str,Y,M,D, H, MM, S) = better_parse_file_date(cal_params_file)
   cal_params = load_json_file(cal_params_file)
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(meteor_json_file)
   (hd_x,hd_y,w,h,mxp) =point_data
   new_x, new_y, ra ,dec , az, el= XYtoRADec(hd_x,hd_y,cal_params_file,cal_params,json_conf)

   (meteor_frame_time,meteor_frame_time_str) = calc_frame_time(meteor_json_file ,frame_num)

   return(ra,dec,az,el,meteor_frame_time_str)


def man_reduce(json_conf,form):
   print("<h2>Manually Reduce</h2>")
   file = form.getvalue('file')
   meteor_json_red_file = file.replace("-stacked.png", "-reduced.json")
   meteor_red = load_json_file(meteor_json_red_file)
   mfd = meteor_red['meteor_frame_data']
   ff = int(mfd[0][1])
   lf = int(mfd[-1][1])
   cal_params_file = form.getvalue('cal_params_file')
   scmd = form.getvalue('scmd')
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(file)

   tmp_dir = "/mnt/ams2/tmp/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + cam_id + "/"
   video_file = file.replace("-stacked.png", ".mp4")
   if scmd is None:
      if cfe(tmp_dir, 1) == 0:
         os.system("mkdir " + tmp_dir)
         ffmpeg_dump_frames(video_file,tmp_dir)
   thumbs = glob.glob(tmp_dir + "*-t.png")
   fc = 0
   if scmd is None:
      for thumb in sorted(thumbs):
         if fc > ff -3 and fc < lf + 3:
            full = thumb.replace("-t", "")
            print("<BR><a href=webUI.py?cmd=man_reduce&scmd=2&file=" + file + "&frame=" + thumb + "&cal_params_file=" + cal_params_file + "><img src=" + full + "></a><BR>")
         else:
            print("<a href=webUI.py?cmd=man_reduce&scmd=2&file=" + file + "&frame=" + thumb + "&cal_params_file=" + cal_params_file + "><img src=" + thumb + " width=100></a>")
         fc = fc + 1 
   if scmd == '2':
      frame = form.getvalue('frame')
      frame = frame.replace("-t", "")
      el = frame.split("/")
      filename = el[-1]
      trash = filename.split("frames")
      frame_num = int(trash[-1].replace(".png", ""))
      next_frame_num = frame_num + 1
      prev_frame_num = frame_num - 1
      frame_num_str = "{0:05d}".format(frame_num)
      prev_frame_num_str = "{0:05d}".format(prev_frame_num)
      next_frame_num_str = "{0:05d}".format(next_frame_num)
      next_frame = frame.replace(frame_num_str, next_frame_num_str)
      prev_frame = frame.replace(frame_num_str, prev_frame_num_str)
      #print("<img src=" + frame + "><br>" + str(frame_num) + " " + frame_num_str)
      #print("<a href=webUI.py?cmd=man_reduce&scmd=2&file=" + file + "&frame=" + prev_frame + "> Prev </a>")
      #print("<a href=webUI.py?cmd=man_reduce&scmd=2&file=" + file + "&frame=" + next_frame + "> Next  </a>")
      extra = man_reduce_canvas(frame_num, thumbs,file,cal_params_file, meteor_red)
      print(extra)
      return(extra)

def test_star(cnt_img, fname=None):
   ch,cw = cnt_img.shape
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
   x,y = max_loc
   
   if fname is not None:
      cv2.imwrite(fname, cnt_img)

   half_width = cw / 2
   half_height = ch / 2
 
   #print(x, half_width, "<HR>")
   #print(y, half_height, "<HR>")
   dx = half_width - x
   dy = half_height - y
   if abs(dx) > 2 or abs(dy) > 2:
      #print(x,y,cw,ch,"Failed bright center test ")
      return(0)
   
   avg_px = np.mean(cnt_img)
   p1 = (x+1,y)
   p2 = (x-1,y)
   p1 = (x,y-1)
   p2 = (x,y-1)
   #print(x,y,"<HR>")
   #print(p1,"<HR>")
   #print(p2,"<HR>")
   #print(p3,"<HR>")
   #print(p4,"<HR>")
   #px_val1 = cnt_img[p1]
   #print(px_val1)
   #print(x,y,cw,ch,"Passed bright center test ")
   return(1)

def find_stars_ajax(json_conf, stack_file, is_ajax = 1):
   stars = []
   #stack_file = form.getvalue("stack_file")
   sd_video_file = stack_file.replace("-stacked.png", ".mp4")
   if cfe(sd_video_file) == 1:
      frames = load_video_frames(sd_video_file,json_conf,0)
      tmp_file, img = stack_frames(frames, stack_file, 3)
   else:
      img = cv2.imread(stack_file, 0)


   #best_thresh = find_best_thresh(med_stack_all, pdif)
   ih, iw = img.shape
   x1 = 0
   x2 = iw
   y1 = 0
   y2 = int(ih / 2)
   half_img = img[y1:y2,x1:x2]
   orig_img = img
   #img = half_img
   avg = np.mean(img)
   best_thresh = avg + 10
   #print("SHAPE:", iw,ih,best_thresh,"<BR>")
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=10)
   rez = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(rez) == 3:
      (_, cnts, xx) =rez 
   else:
      (cnts,rects ) = rez
   cc = 0
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      px_val = int(img[y,x])
      cnt_img = img[y:y+h,x:x+w]
      cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
      max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img.copy())   
      name = "/mnt/ams2/tmp/cnt" + str(cc) + ".png"
      rez = test_star(cnt_img, name)
      x = x + int(w/2)
      y = y + int(h/2)
      if px_diff > 10 and w > 1 and h > 1 and rez == 1 and w < 50 and h < 50:
          #print(x,y,px_diff,"<img src=" + name + "><br>")
        # print(rez, px_diff, w, h, "<HR>")
          stars.append((x,y,int(max_px)))
      cc = cc + 1

   temp = sorted(stars, key=lambda x: x[2], reverse=True)
   stars = temp[0:50]
   
   response = {}
   response['stars'] = stars
   if is_ajax == 1:
      print(json.dumps(response))
   else:
      return(response)



def check_make_half_stack(sd_file,hd_file,meteor_reduced):
   if cfe(sd_file) == 0:
      if "png" in sd_file:
         sd_file = sd_file.replace("png", "jpg")
   if cfe(sd_file) == 0:
      print("SD FILE NOT FOUND.", sd_file)
      exit()
   if cfe(hd_file) == 0:
      print("HD FILE NOT FOUND.", sd_file)
      exit()

   if cfe(hd_file) == 0:
      hd_trim = meteor_reduced['hd_trim']
      #hd_trim.replace(".mp4", "-HD-meteor-stacked.png")

   if "stacked" in sd_file:
      half_stack_file = sd_file.replace("-stacked", "-half-stack")
   else:
      half_stack_file = sd_file.replace("-stacked", "-half-stack")


   if True :
   #if cfe(half_stack_file) == 0:
      if hd_file != 0:
         if cfe(hd_file) == 1:
            img = cv2.imread(hd_file)
            img = cv2.resize(img, (960,540))
            sd_img = cv2.imread(sd_file)
            sd_img = cv2.resize(sd_img, (960,540))
            #exit()
            blend_image = cv2.addWeighted(img, .6, sd_img, .4, 0)
            img = blend_image
         else:
            img = cv2.imread(sd_file)
            img = cv2.resize(img, (960,540))
      else:
         img = cv2.imread(sd_file)
         img = cv2.resize(img, (960,540))
      cv2.imwrite(half_stack_file, img)
  
def make_cal_select(cal_files,video_file,cpf) :

   cal_select = "<SELECT onchange=\"javascript:goto('" + video_file + "', this.options[selectedIndex].value ,'reduce')\" style=\"margin: 5px; padding: 5px\" NAME=cal_param_file>"
   if cal_files is None:
      return("")
   for cal_file, cal_desc, cal_time_diff in cal_files:
      dif_days = abs(cal_time_diff / 86400)
      if int(abs(cal_time_diff)) < 86400:
         hrs = int(cal_time_diff) / 60 / 60 
         dif_days = hrs / 24
      if cpf == cal_file:
         cal_select = cal_select + "<option SELECTED value=" + cal_file + ">" + cal_desc + "(" + str(dif_days)[0:5] + " days diff)</option>" 
      else:
         cal_select = cal_select + "<option value=" + cal_file + ">" + cal_desc + "(" + str(dif_days)[0:5] + " days diff)</option>" 
   cal_select = cal_select + "</SELECT>"
   return(cal_select)


def hist_to_obj(hist):
   object = {}
   object['oid'] = 1
   fc,x,y,w,h,mx,my = hist[0]

   object['fc'] = fc
   object['x'] = x
   object['y'] = y
   object['w'] = w
   object['h'] = h
   object['history'] = []
   for fc,x,y,w,h,mx,my in hist:
      object['history'].append([fc,x,y,w,h,mx,my])
   return(object)

def bound_xy(x,y,iw,ih,sz):
   if x-sz < 0:
      x1 = 0
   else:
      x1 = x - sz
   if y-sz < 0:
      y1 = 0
   else:
      y1 = y - sz
   if x+sz > iw-1:
      x2 = iw -1
   else:
      x2 = x + sz 
   if y+sz > ih-1:
      y2 = ih
   else:
      y2 = y + sz 


   return(x1,y1,x2,y2)

def find_mask_bp(image):
   done = 0
   masks = []
   wc = 0
   ih,iw = image.shape
   while done == 0 and wc < 100:
      max_px, avg_px, px_diff,max_loc = eval_cnt(image.copy())
      mx,my = max_loc 
      mx = mx + 5 
      my = my + 5 
      max_loc = (mx,my)
      if px_diff > 10:
         x,y = max_loc

         masks.append((x,y))
         x1,y1,x2,y2 = bound_xy(x,y,iw,ih,3)
         image[y1:y2,x1:x2] = 0
         cv2.imshow('pepe', image)
         cv2.waitKey(0)
      else:
         done = 1
      wc = wc + 1
   return(masks,image)
      

def track_bright_objects(frames, sd_video_file, cam_id, meteor_object, json_conf, show = 0):

   objects = []
   object = []
   shp = frames[0].shape
   ih,iw  = shp[0], shp[1]
   (max_x,max_y,min_x,min_y) = find_min_max_dist(meteor_object['history'])
   min_y = min_y - 25
   min_x = min_x - 25
   max_y = max_y + 25
   max_x = max_x + 25
   if max_y >= ih - 1:
      max_y = ih - 1  
   if max_x > iw - 1:
      max_x = iw - 1
   if min_y < 0:
      min_y = 0
   if min_x < 0:
      min_x = 0

   fc = 0
   for frame in frames:
      roi_frame = frame[min_y:max_y,min_x:max_x]

      max_px, avg_px, px_diff,max_loc = eval_cnt(roi_frame)
      if px_diff > 15:
         x,y = max_loc
         rx = x + 5
         ry = y + 5
         x = x + min_x + 5
         y = y + min_y + 5
         w = 10
         h = 10
         mx = 0
         my = 0
         if show == 1:
            print(px_diff)
         object.append((fc,x,y,w,h,mx,my))
         if show == 1:
            cv2.rectangle(roi_frame, (rx-5, ry-5), (rx+5, ry+5), (128, 128, 128), 1)
            cv2.imshow('pepe', roi_frame)
            cv2.waitKey(0)
      fc = fc + 1
   print("LEN B", len(object))
   object = remove_obj_dupes(object)
   print("LEN A", len(object))
   object = hist_to_obj(object)
   objects.append(object)
   return(objects)

def remove_obj_dupes(object):
   counter = {}
   unique_px = []
   for fn,x,y,w,h,mx,my in object:
      key = str(x) + "," + str(y)
      if key in counter:
         counter[key] = counter[key] + 1
      else:
         counter[key] = 1
   for fn,x,y,w,h,mx,my in object:
      key = str(x) + "," + str(y)
      if counter[key] <= 3:
         unique_px.append((fn,x,y,w,h,mx,my))
   return(unique_px)

def get_manual_points(json_conf, form):
   response = {}
   response['status'] = 1
   response['message'] = "get points"
   print(json.dumps(response))
   frame_file = form.getvalue("frame_file")
   crp = frame_file.split("frames")
   frame_num = int(crp[-1].replace(".png", ""))
   orig_file = form.getvalue("orig_file")

   man_json_file = orig_file.replace("-stacked.png", "-manual.json")
   if cfe(man_json_file) == 0:
      man_json = {}
   else:
      man_json = load_json_file(man_json_file)
   
   response['manual_frame_data'] = man_json


def save_manual_reduction(meteor_json_file,cal_params_file,json_conf):
   meteor_json_file = meteor_json_file.replace("-stacked.png", ".json")
   man_file = meteor_json_file.replace(".json", "-manual.json")
   mj = load_json_file(meteor_json_file)

   man_json = load_json_file(man_file) 
   meteor_frame_data = []
   for key in man_json:

      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = man_json[key]
      hd_x = int(hd_x) * 2
      hd_y = int(hd_y) * 2
      meteor_frame_data.append((frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el))
   meteor_frame_data = sorted(meteor_frame_data, key=lambda x: x[1], reverse=False)


   first_frame_data = meteor_frame_data[0]
   last_frame_data = meteor_frame_data[-1]

   (start_frame_time,start_frame,sx,sy,sw,sh,smp,sra,sdec,saz,sel) = first_frame_data
   (end_frame_time,end_frame,ex,ey,ew,eh,emp,era,edec,eaz,eel) = last_frame_data

   (cal_date, cam_id, cal_date_str,Y,M,D, H, MM, S) = better_parse_file_date(cal_params_file)
   cal_params = load_json_file(cal_params_file)
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(meteor_json_file)

   start_clip_time_str = str(f_datetime)
   sd_video_file = mj['sd_video_file']
   hd_video_file = mj['hd_trim']
   meteor_dir = "/mnt/ams2/meteors/" + Y + "_" + M + "_" + D + "/"
   el = sd_video_file.split("/")
   fn = el[-1]
   fin_sd_video_file = meteor_dir + fn

   if hd_video_file != 0 and hd_video_file != None:
      el = hd_video_file.split("/")
      fn = el[-1] 
      fin_hd_video_file = meteor_dir + fn
   else:
      fin_hd_video_file = sd_video_file

   max_max_px= 0
   elp_dur = (end_frame - start_frame) / 25

   vf_type = "SD"
   fin_sd_stack = fin_sd_video_file.replace(".mp4", ".png")
   fin_hd_stack = fin_hd_video_file.replace(".mp4", ".png")
   fin_reduced_video = fin_sd_video_file.replace(".mp4", "-reduced.mp4")
   fin_reduced_stack = fin_sd_video_file.replace(".mp4", "-reduced.png")


   response = {}
   response['status'] = 1
   response['message'] = "Reduction Saved"
   meteor_reduced = {}
   meteor_reduced['api_key'] = json_conf['site']['api_key']
   meteor_reduced['station_name'] = json_conf['site']['ams_id']
   meteor_reduced['device_name'] = cam_id
   meteor_reduced['sd_video_file'] = fin_sd_video_file
   meteor_reduced['hd_video_file'] = fin_hd_video_file
   meteor_reduced['sd_stack'] = fin_sd_stack
   meteor_reduced['hd_stack'] = fin_hd_stack
   meteor_reduced['reduced_stack'] = fin_reduced_stack
   meteor_reduced['reduced_video'] = fin_reduced_video
   meteor_reduced['vf_type'] = vf_type
   meteor_reduced['event_start_time'] = start_frame_time 
   meteor_reduced['event_duration'] = float(elp_dur)
   meteor_reduced['peak_magnitude'] = int(max_max_px)
   meteor_reduced['start_az'] = saz 
   meteor_reduced['start_el'] = sel
   meteor_reduced['end_az'] = eaz
   meteor_reduced['end_el'] = eel
   meteor_reduced['start_ra'] = sra
   meteor_reduced['start_dec'] = sdec
   meteor_reduced['end_ra'] = era
   meteor_reduced['end_dec'] = edec 
   meteor_reduced['meteor_frame_data'] = meteor_frame_data
   meteor_reduced['cal_params_file'] = cal_params_file
   meteor_reduced['cal_params'] = {}
   meteor_reduced['cal_params']['site_lat'] = json_conf['site']['device_lat']
   meteor_reduced['cal_params']['site_lng'] = json_conf['site']['device_lng']
   meteor_reduced['cal_params']['site_alt'] = json_conf['site']['device_alt']
   meteor_reduced['cal_params']['ra_center'] = cal_params['ra_center']
   meteor_reduced['cal_params']['dec_center'] = cal_params['dec_center']
   meteor_reduced['cal_params']['center_az'] = cal_params['center_az']
   meteor_reduced['cal_params']['center_el'] = cal_params['center_el']
   meteor_reduced['cal_params']['position_angle'] = cal_params['position_angle']
   meteor_reduced['cal_params']['cal_date'] = cal_date_str
   meteor_reduced['cal_params']['x_poly'] = cal_params['x_poly']
   meteor_reduced['cal_params']['y_poly'] = cal_params['y_poly']
   meteor_reduced['cal_params']['x_poly_fwd'] = cal_params['x_poly_fwd']
   meteor_reduced['cal_params']['y_poly_fwd'] = cal_params['y_poly_fwd']
   meteor_reduced['cal_params']['x_res_err'] = cal_params['x_fun']
   meteor_reduced['cal_params']['y_res_err'] = cal_params['y_fun']
   meteor_reduced['cal_params']['x_fwd_res_err'] = cal_params['x_fun_fwd']
   meteor_reduced['cal_params']['y_fwd_res_err'] = cal_params['y_fun_fwd']
   meteor_reduce_file = meteor_json_file.replace(".json", "-reduced.json")
   save_json_file(meteor_reduce_file, meteor_reduced)

def del_frame(json_conf, form):
   fn = form.getvalue("fn")
   meteor_file = form.getvalue("meteor_json_file")
   meteor_file = meteor_file.replace(".json", "-reduced.json")
   meteor_json = load_json_file(meteor_file)
   new_frame_data = []
   for data in meteor_json['meteor_frame_data']:
      tfn = data[1]
      if str(fn) == str(tfn):
         skip = 1
      else:
         new_frame_data.append(data)
   meteor_json['meteor_frame_data'] = new_frame_data
   if "metframes" in meteor_json:
      if fn in meteor_json['metframes']:
         meteor_json['metframes'].pop(fn)
   response = {}
   response['message'] = 'frame deleted'
   response['frame_data'] = new_frame_data
   save_json_file(meteor_file, meteor_json)
   print(json.dumps(response))

def del_manual_points(json_conf, form):
   response = {}
   response['status'] = 1
   response['message'] = "delete point"

   frame_num = form.getvalue("frame_num")
   orig_file = form.getvalue("orig_file")

   man_json_file = orig_file.replace("-stacked.png", "-manual.json")
   if cfe(man_json_file) == 0:
      man_json = {}
   else:
      man_json = load_json_file(man_json_file)
   man_json.pop(frame_num)

   save_json_file(man_json_file, man_json)
   response['manual_frame_data'] = man_json

   print(json.dumps(response))

def pin_point(json_conf, form):
   response = {}
   response['status'] = 1
   response['message'] = "pin point"
   
   frame_file = form.getvalue("frame_file")
   crp = frame_file.split("frames")
   frame_num = int(crp[-1].replace(".png", ""))
   orig_file = form.getvalue("orig_file")
   cal_params_file = form.getvalue("cal_params_file")

   man_json_file = orig_file.replace("-stacked.png", "-manual.json")
   if cfe(man_json_file) == 0:
      man_json = {}
   else:
      man_json = load_json_file(man_json_file)

   #el = frame_file.split("/")
   #base_dir = el[-2]

   x = int(form.getvalue("x"))
   y = int(form.getvalue("y"))
 
   cx1 = x - 10 
   cy1 = y - 10 
   cx2 = x + 10 
   cy2 = y + 10 

   frame_img = cv2.imread(frame_file,0)
   cnt_img = frame_img[cy1:cy2,cx1:cx2]
   max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img)
   w = 5
   h = 5




   meteor_json_file = orig_file.replace("-stacked.mp4", ".json")
   hd_x = (x + int(max_loc[0]) - 10) * 2
   hd_y = (y + int(max_loc[1]) - 10) * 2
   point_data = (hd_x,hd_y,5,5,int(max_px))
   (ra,dec,az,el,frame_time_str) = reduce_point(cal_params_file, meteor_json_file, frame_num, point_data,json_conf)

   response['frame_num'] = 0
   response['pp_ft'] = frame_time_str
   response['pp_x'] = x
   response['pp_y'] = y
   response['pp_w'] = 5
   response['pp_h'] = 5
   response['pp_mx'] = int(max_loc[0]) 
   response['pp_my'] = int(max_loc[1]) 
   response['pp_max_px'] = int(max_px)
   response['pp_ra'] = ra
   response['pp_dec'] = dec
   response['pp_az'] = az
   response['pp_el'] = el

   frame_time = "na"
   man_json[frame_num] = [frame_time_str,frame_num,x,y,w,h,int(max_px),ra,dec,az,el]
   response['manual_frame_data'] = man_json

   save_json_file(man_json_file, man_json)

   save_manual_reduction(meteor_json_file,cal_params_file,json_conf)

   print(json.dumps(response))


def custom_fit(json_conf,form):
   cal_params_file = form.getvalue("cal_params_file")
   cmd1 = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + cal_params_file + " 0 > /mnt/ams2/tmp/autoCal.txt "
   os.system(cmd1)
   cmd2 = "cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + cal_params_file + " 0 > /mnt/ams2/tmp/autoCal.txt &"
   #print(cmd)
   os.system(cmd2)

   response = {}
   response['msg'] = "custom fit process started"
   #response['debug'] = cmd
   print(json.dumps(response))

def make_meteor_cnt_composite_images(json_conf, mfd, sd_video_file):
   cmp_images = {}
   frames = load_video_frames(sd_video_file, json_conf)
   cnt_max_w = 0
   cnt_max_h = 0
   for frame_data in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      if w > cnt_max_w:
         cnt_max_w = w
      if h > cnt_max_h:
         cnt_max_h = h 

   cnt_w = int(cnt_max_w / 2)
   cnt_h = int(cnt_max_h / 2)
   #if cnt_w < 50 and cnt_h < 50:
   #   cnt_w = 50 
   #   cnt_h = 50 
   #if cnt_w < 40 and cnt_h < 40:
   #   cnt_w = 40 
   #   cnt_h = 40 
   if cnt_w < 25 and cnt_h < 25:
      cnt_w = 25
      cnt_h = 25
   else:
      cnt_w = 50 
      cnt_h = 50
   #print(cnt_w,cnt_h)
   for frame_data in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      x1,y1,x2,y2 = bound_xy(hd_x,hd_y,1920,1080,cnt_w)
      #x1 = hd_x - cnt_w
      #x2 = hd_x + cnt_w
      #y1 = hd_y - cnt_h
      #y2 = hd_y + cnt_h
      img = frames[fn]
      hd_img = cv2.resize(img, (1920,1080))
      #cv2.rectangle(hd_img, (x1, y1), (x2, y2), (128, 128, 128), 1)
      cnt_img = hd_img[y1:y2,x1:x2]
      cmp_images[fn] = cnt_img 
   return(cmp_images)

def save_reduction(meteor_json_file, metconf, metframes):

   meteor_reduced = {}

   meteor_reduced['api_key'] = json_conf['site']['api_key']
   meteor_reduced['station_name'] = json_conf['site']['ams_id']
   meteor_reduced['device_name'] = cam_id
   meteor_reduced['sd_video_file'] = fin_sd_video_file
   meteor_reduced['hd_video_file'] = fin_hd_video_file
   meteor_reduced['sd_stack'] = fin_sd_stack
   meteor_reduced['hd_stack'] = fin_hd_stack
   meteor_reduced['reduced_stack'] = fin_reduced_stack
   meteor_reduced['reduced_video'] = fin_reduced_video
   meteor_reduced['vf_type'] = vf_type
   meteor_reduced['event_start_time'] = event_start_time
   meteor_reduced['event_duration'] = float(elp_dur)
   meteor_reduced['peak_magnitude'] = int(max_max_px)
   meteor_reduced['start_az'] = start_az
   meteor_reduced['start_el'] = start_el
   meteor_reduced['end_az'] = end_az

   meteor_reduced['end_el'] = end_el
   meteor_reduced['start_ra'] = start_ra
   meteor_reduced['start_dec'] = start_dec
   meteor_reduced['end_ra'] = end_ra
   meteor_reduced['end_dec'] = end_dec
   meteor_reduced['meteor_frame_data'] = meteor_frame_data
   meteor_reduced['cal_params_file'] = cal_params_file
   meteor_reduced['cal_params'] = {}
   meteor_reduced['cal_params']['site_lat'] = json_conf['site']['device_lat']
   meteor_reduced['cal_params']['site_lng'] = json_conf['site']['device_lng']
   meteor_reduced['cal_params']['site_alt'] = json_conf['site']['device_alt']
   meteor_reduced['cal_params']['ra_center'] = cal_params['ra_center']
   meteor_reduced['cal_params']['dec_center'] = cal_params['dec_center']
   meteor_reduced['cal_params']['center_az'] = cal_params['center_az']
   meteor_reduced['cal_params']['center_el'] = cal_params['center_el']
   meteor_reduced['cal_params']['position_angle'] = cal_params['position_angle']
   meteor_reduced['cal_params']['pixscale'] = cal_params['pixscale']
   meteor_reduced['cal_params']['imagew'] = cal_params['imagew']
   meteor_reduced['cal_params']['imageh'] = cal_params['imageh']
   meteor_reduced['cal_params']['cal_date'] = cal_date_str
   meteor_reduced['cal_params']['x_poly'] = cal_params['x_poly']
   meteor_reduced['cal_params']['y_poly'] = cal_params['y_poly']
   meteor_reduced['cal_params']['x_poly_fwd'] = cal_params['x_poly_fwd']
   meteor_reduced['cal_params']['y_poly_fwd'] = cal_params['y_poly_fwd']


   (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_reduced['meteor_frame_data'])
   meteor_reduced['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y)

   if 'x_fun' in cal_params:
      meteor_reduced['cal_params']['x_res_err'] = cal_params['x_fun']
      meteor_reduced['cal_params']['y_res_err'] = cal_params['y_fun']
      meteor_reduced['cal_params']['x_fwd_res_err'] = cal_params['x_fun_fwd']
      meteor_reduced['cal_params']['y_fwd_res_err'] = cal_params['y_fun_fwd']
   meteor_reduce_file = meteor_json_file.replace(".json", "-reduced.json")

   (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_reduced['meteor_frame_data'])
   meteor_reduced['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y)

   save_json_file(meteor_reduce_file, meteor_reduced)
   return(metconf,metframes)

def best_fit_slope_and_intercept(xs,ys):
    xs = np.array(xs, dtype=np.float64)
    ys = np.array(ys, dtype=np.float64)
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

    b = np.mean(ys) - m*np.mean(xs)

    return m, b



def better_reduce(json_conf,meteor_json_file,show=0):

   #if "-reduced" not in meteor_json_file:
   #   meteor_json_file = meteor_json_file.replace(".json", "-reduced.json")
   #   meteor_json_file = meteor_json_file.replace(".mp4", "-reduced.json")
   if show == 1:
      cv2.namedWindow('pepe')
   hdm_x = 2.7272727272727272
   hdm_y = 1.875
   print(meteor_json_file)
   mj = load_json_file(meteor_json_file)
   sd_video_file = mj['sd_video_file']
   frames = load_video_frames(sd_video_file,json_conf, 0, 1, [],1)
   skip_detect = 0
   if "updated_obj" in mj:
      skip_detect = 1
   if skip_detect == 0:
      objects = detect_meteor(json_conf, frames, meteor_json_file,mj,show=0)
      print("New objects")
   else:
      objects = mj['updated_obj']
      print("Loaded objects")
   detect_meteor_step2(json_conf, objects, frames, meteor_json_file,mj,show=0)



def detect_meteor(json_conf, frames, meteor_json_file,mj,show=0):

   fc = 0
   image_acc = None
   last_crop_img = None
   last_crops = []
   first_frame = frames[0]
   first_frame = cv2.resize(first_frame, (int(1920),int(1080)))

   image_acc = first_frame
   image_acc = cv2.cvtColor(image_acc, cv2.COLOR_BGR2GRAY)
   image_acc = cv2.GaussianBlur(image_acc, (5, 5), 0)
   cv2.convertScaleAbs(image_acc, image_acc, 1, 1)

   avg_px = np.mean(first_frame)
   max_px = np.max(first_frame)
   min_px = np.min(first_frame)
   px_diff = max_px - avg_px
   min_min_px = max_px - int(px_diff /2)
   
   pos_cnts = []

   # block out bright stars first
   fc = 0
   smasks = []
   last_wf = None
   med_frames = []
   thresh_frames = []
   alpha = .5
   image_acc = None
   diff_frames = []
   for frame in frames:
      work_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      #work_frame = cv2.resize(work_frame, (int(1920),int(1080)))
      if last_wf is not None:
         last_wf = cv2.GaussianBlur(last_wf, (7, 7), 0)
         if image_acc is None:
            image_acc = frames[-1] 
            image_acc = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            image_acc = cv2.GaussianBlur(image_acc, (7, 7), 0)
         image_diff = cv2.absdiff(last_wf.astype(work_frame.dtype), work_frame,)
         image_acc = np.float32(image_acc)
         hello = cv2.accumulateWeighted(image_diff, image_acc, alpha)

         avg_px = np.mean(first_frame)
         max_px = np.max(first_frame)
         min_px = np.min(first_frame)
         px_diff = max_px - avg_px
         thresh_for_diff = max_px - int(px_diff /4)
         thresh_for_diff = 3 
         _, first_thresh = cv2.threshold(image_diff.copy(), thresh_for_diff, 255, cv2.THRESH_BINARY)
         tmp_img = np.uint8(first_thresh.copy())
         cnt_res = cv2.findContours(tmp_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         #show_img = cv2.resize(first_thresh, (0,0),fx=.5, fy=.5)
         #show_img = cv2.resize(image_acc, (0,0),fx=.5, fy=.5)
         show_img = cv2.resize(image_diff, (0,0),fx=.5, fy=.5)
         diff_frames.append(image_diff)
         #cv2.imshow('pepe', show_img)
         #cv2.waitKey(1)

         if len(cnt_res) == 3:
            (_, cnts, xx) = cnt_res
         elif len(cnt_res) == 2:
            (cnts, xx) = cnt_res
         if len(cnts) > 0:
            this_pos_cnts = []
            for (i,c) in enumerate(cnts):
               tx,ty,tw,th = cv2.boundingRect(cnts[i])
               smasks.append((tx,ty,tw,th))
         med_frames.append(np.uint8(first_thresh))
         #if fc > 50:
         #   break
      last_wf = work_frame
      fc = fc + 1

   med_frame = median_frames(med_frames[0:10])

   blur_med = cv2.GaussianBlur(med_frame, (7, 7), 0)
   med_frame = blur_med
   blur_med = cv2.dilate(blur_med, None , iterations=10)
   blur_frame = cv2.GaussianBlur(last_wf, (7, 7), 0)

   _, med_thresh= cv2.threshold(blur_med.copy(), 2, 255, cv2.THRESH_BINARY)
   cnt_res = cv2.findContours(tmp_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   show_img = cv2.resize(first_thresh, (0,0),fx=.5, fy=.5)

   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   smasks = []
   test_frame = last_wf 
   if len(cnts) > 0:
      this_pos_cnts = []
      for (i,c) in enumerate(cnts):
         tx,ty,tw,th = cv2.boundingRect(cnts[i])
         smasks.append((tx,ty,tw,th))
         #test_frame[ty:ty+th,tx:tx+tw] = 0

   show_f = cv2.subtract(test_frame, med_frame)

   clean_frames = []
   clean_sm_frames = []
   med_frame = cv2.dilate(med_frame, None , iterations=10)
   blur_med= cv2.GaussianBlur(med_frame, (11, 11), 0)
   for frame in med_frames:

      blur_frame = cv2.GaussianBlur(frame, (11, 11), 0)
      temp = cv2.subtract(blur_frame, blur_med)
      for pnt in smasks:
         (px,py,pw,ph) = pnt
         cpx = px + int(pw/2)
         cpy = py + int(ph/2)
         sz2 = int(pw * ph / 4)
         if pw < 10 and ph < 10:
            temp[cpy-sz2:cpy+sz2,cpx-sz2:cpx+sz2] = 0
      clean_frames.append(temp)
      temp_sm = cv2.resize(temp, (int(704),int(576)))
      clean_sm_frames.append(temp_sm)
      #cv2.imshow('pepe', temp)
      #cv2.waitKey(0)
   (f_datetime, cam_id, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(mj['sd_video_file'])
   show = 0
   objects = check_for_motion2(diff_frames, mj['sd_video_file'],cam_id, json_conf,show)
   save_json_file(meteor_json_file, mj)

   return(objects)

def detect_meteor_step2(json_conf, objects, frames, meteor_json_file,mj,show=0):

   mj['updated_obj'] = objects
   sd_video_file = mj['sd_video_file']
   print(meteor_json_file)
   show = 1
   meteor_found = 0
   pos_met = []
   for object in objects:  
      bad = 0
      status = ""
      hist = object['history']
      if len(object['history']) < 2:
         bad = 1 
         status =  status + "history too short: " + str(len(object['history']))
      else:
         hist,metframes,metconf = clean_hist(hist)
         object['history'] = hist

      # ELP Frames test
      elp_frames = meteor_test_elp_frames(object)
      cm,gaps,gap_events,cm_hist_len_ratio = meteor_test_cm_gaps(object)
      if (elp_frames) > 1:
         cm_elp_ratio = cm / elp_frames
      else:
         cm_elp_ratio = 0

      if cm_elp_ratio < .5:
         bad = 1
         status =  status + "cm_elp_ratio too low: " + str(cm_elp_ratio)


      if bad == 0:
         print("METEOR FOUND:", cm, elp_frames, cm_elp_ratio, object)
         object['status'] = "meteor found"
         object['meteor'] = 1
         meteor_found = 1   
         pos_met.append(object)
      else:
         object['status'] = "NOT FOUND:" + status
         object['meteor'] = 0
      print(object['oid'], object['status'], object['history'])


   if len(pos_met) >1:
      # more than one meteor!
      print("more than one met")
      for met in pos_met:
         print(met)
      exit()
   elif len(pos_met) == 1:
      print("Just one met")
      meteor_obj = pos_met[0]
      meteor_found = 1
      
      hist,metframes,metconf = clean_hist(meteor_obj['history'])
   else:
      print("NO MET FOUND!")
      exit()

   print("MO:", meteor_obj)

   hdm_x = 2.7272727272727272
   hdm_y = 1.875


   fx = None

   hd_xs = []
   hd_ys = []
   hd_fcs = []
   for fc in metframes:
      hd_xs.append( metframes[fc]['orig_hd_x'] )
      hd_ys.append( metframes[fc]['orig_hd_y'])
      hd_fcs.append( fc) 

   m,b = best_fit_slope_and_intercept(hd_xs,hd_ys)

   metconf['hd_m'] = m
   metconf['hd_b'] = b
   metconf['hd_first_x'] = hd_xs[0]
   metconf['hd_first_y'] = hd_ys[0]
   metconf['hd_first_fc'] = hd_fcs[0]
   metconf['hd_last_x'] = hd_xs[-1]
   metconf['hd_last_y'] = hd_ys[-1]
   metconf['hd_last_fc'] = hd_fcs[-1]
   metconf['hd_total_dist'] = calc_dist((metconf['hd_first_x'],metconf['hd_first_y']),(metconf['hd_last_x'],metconf['hd_last_y']))
   metconf['hd_avg_seg_len'] = metconf['hd_total_dist'] / (hd_fcs[-1]- hd_fcs[0])


   hd_xs = []
   hd_ys = []
   
   acl_poly = np.zeros(shape=(2,), dtype=np.float64)
   acl_poly[0] = np.float64(metconf['hd_avg_seg_len'])
   acl_poly[1] = np.float64(0.001)
   #acl_poly[2] = np.float64(metconf['x_dir_mod'] )


   if meteor_found == 1:
      print("FOUND?", meteor_found)
      print("METFRAMES:", metframes)
      for fn in metframes:
         print(fn,metframes[fn])   
      if "acl_poly" in metconf:
         if type(metconf['acl_poly']) != float:
            acl_poly = metconf['acl_poly']
            acl_poly[0] = np.float64(acl_poly[0])
            acl_poly[1] = np.float64(acl_poly[1])
            if len(acl_poly) > 2:
               acl_poly = np.zeros(shape=(2,), dtype=np.float64)
               acl_poly[0] = np.float64(metconf['hd_avg_seg_len'])
               acl_poly[1] = np.float64(0.001)


      avg_res,metframes = reduce_meteor_acl(acl_poly, metconf,metframes,frames,4,1,show)

      mj['metconf'] = metconf
      mj['metframes'] = metframes
      save_json_file(meteor_json_file,mj)

      if "metframes" not in mj:
         res = scipy.optimize.minimize(reduce_meteor_acl, acl_poly, args=( metconf, metframes,frames,7,0,show), method='Nelder-Mead')
         print("SCI PI DONE:", res)
         acl_poly = res['x']
         x_fun = res['fun']
         avg_res = reduce_meteor_acl(acl_poly, metconf,metframes,frames,4,1,show)
         #print(acl_poly, x_fun)
         metconf['acl_poly'] = acl_poly.tolist()
         metconf['acl_fun'] = x_fun 
         metconf['acl_res'] = avg_res 
         avg_res,metframes = reduce_meteor_acl(acl_poly, metconf,metframes,frames,4,1,show)
         mj['metconf'] = metconf
         mj['metframes'] = metframes
         #print("final point res:", avg_res)
         save_json_file(meteor_json_file,mj)
         #print("saved:", meteor_json_file)
      else:
         if "acl_res" in mj['metconf']:
            avg_res = mj['metconf']['acl_res'] 
         else:
            avg_res = 0
         print("already solved with error of:", avg_res)
         mc = 0
         first_frame = cv2.resize(frames[0], (int(1920),int(1080)))
         for mf in metframes:
            #print("MF:", mf, metframes[mf].keys())
            if mc == 0:
               print("MF:", mf )
            else:
               start_set = metframes[mf]['start_dist'] / mc
               print("MF:", mf, metframes[mf]['start_dist'], start_set, metframes[mf]['last_dist'], metframes[mf]['hd_res_dist'], metframes[mf]['cnt_box'])
               frame = frames[mf]
               frame = cv2.resize(frame, (int(1920),int(1080)))
               x1,y1,x2,y2 = metframes[mf]['cnt_box']
               x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
 
               cnt_img = frame[y1:y2,x1:x2]

               first_frame_cnt = first_frame[y1:y2,x1:x2]
               print(cnt_img.shape, first_frame_cnt.shape)
               flux_image = cv2.subtract(cnt_img, first_frame_cnt)
               flux = np.sum(flux_image)
               flux_size = flux_image.shape[0],flux_image.shape[1]
               #cv2.imshow('pepe', flux_image)
               #cv2.waitKey(1)
               metframes[mf]['flux'] = int(flux)
               metframes[mf]['flux_size'] = flux_size
               show_cnt_img = frame[y1:y2,x1:x2]
               Gcnt_img = cv2.cvtColor(cnt_img, cv2.COLOR_BGR2GRAY)
               min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(Gcnt_img)
               best_thresh = max_val - 10
               _, cnt_img_thresh = cv2.threshold(Gcnt_img, best_thresh, 255, cv2.THRESH_BINARY)
               cnt_img_thresh_dil = cv2.dilate(cnt_img_thresh, None , iterations=10)
               cnt_res = cv2.findContours(cnt_img_thresh_dil.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
               if len(cnt_res) == 3:
                  (_, cnts, xx) = cnt_res
               elif len(cnt_res) == 2:
                  (cnts, xx) = cnt_res

               txs = []
               tys = []
               for (i,c) in enumerate(cnts):
                 tx,ty,tw,th = cv2.boundingRect(cnts[i])
                 cv2.rectangle(show_cnt_img, (tx, ty), (tx+tw, ty+th), (255 ,9, 9), 1)
                 txs.append(tx+int(tw/2))
                 tys.append(ty+int(th/2))
               atx = np.mean(txs)
               aty = np.mean(tys)
               metframes[mf]['hd_bp_x'] = int(x1 + max_loc[0] )
               metframes[mf]['hd_bp_y'] = int(y1 + max_loc[1])
               metframes[mf]['hd_blob_x'] = int(atx) + x1
               metframes[mf]['hd_blob_y'] = int(aty) + y1
               cv2.circle(show_cnt_img, (int(atx),int(aty)), int(10), (0,255,0), 1)

               #cv2.circle(show_cnt_img, (int(max_loc[0]),int(max_loc[1])), int(10), (128,182,255), 1)
               #cv2.imshow('pepe', show_cnt_img)
               cv2.waitKey(30)
    
            mc = mc + 1
         mc = 0

         #exit()
         for mf in metframes:
               best_xs = []
               best_ys = []
               #print("MF ORIG:", mf, int(metframes[mf]['orig_hd_x']), int(metframes[mf]['orig_hd_y']))
               #best_xs.append(np.float64(metframes[mf]['orig_hd_x']))
               #best_ys.append(np.float64(metframes[mf]['orig_hd_y']))
               if "hd_bp_x" in metframes[mf]:
                  print("MF BP:", mf, metframes[mf]['hd_bp_x'], metframes[mf]['hd_bp_y'])
                  best_xs.append(np.float64(metframes[mf]['hd_bp_x']))
                  best_ys.append(np.float64(metframes[mf]['hd_bp_y']))
               else:
                  metframes[mf]['hd_bp_x'] = 0 
                  metframes[mf]['hd_bp_y'] = 0

               if "hd_blob_x" in metframes[mf]:
                  print("MF BLOB:", mf, metframes[mf]['hd_blob_x'], metframes[mf]['hd_blob_y'])
                  best_xs.append(np.float64(metframes[mf]['hd_blob_x']))
                  best_ys.append(np.float64(metframes[mf]['hd_blob_y']))
               else:
                  metframes[mf]['hd_blob_x'] = 0 
                  metframes[mf]['hd_blob_y'] = 0
               if "hd_est_x" in metframes[mf]:
                  print("MF EST:", mf, metframes[mf]['hd_est_x'], metframes[mf]['hd_est_y'])
                  best_xs.append(np.float64(metframes[mf]['hd_est_x']))
                  best_ys.append(np.float64(metframes[mf]['hd_est_y']))
               else:
                  metframes[mf]['hd_est_x'] = int(metframes[mf]['orig_hd_x'])
                  metframes[mf]['hd_est_y'] = int(metframes[mf]['orig_hd_y'])
               frame = frames[mf]
               frame = cv2.resize(frame, (int(1920),int(1080)))
               work_frame = frame.copy()
               print("MF:", mf)
    
               best_x = np.median(best_xs)
               best_y = np.median(best_ys)
               std_x = int(np.std(best_xs))
               std_y = int(np.std(best_ys))
               print("MF STD X,Y / BEST x,y:", std_x, std_y, "/", best_x, best_y)
               print("BEST XS:", best_xs)
               print("BEST YS:", best_ys)

               #best_x = std_x
               #best_y = std_y

               x1,y1,x2,y2 = bound_xy(best_x,best_y,1920,1080,24)
               #x1,y1,x2,y2 = bound_xy(metframes[mf]['hd_est_x'],metframes[mf]['hd_est_y'],1920,1080,24)
               x1,y1,x2,y2 = int(x1),int(y1),int(x2),int(y2)
               small_cnt  = work_frame[y1:y2,x1:x2]

               #ox1,oy1,ox2,oy2 = bound_xy(metframes[mf]['orig_hd_x'],metframes[mf]['orig_hd_y'],1920,1080,24)
               ox1,oy1,ox2,oy2 = bound_xy(metframes[mf]['hd_est_x'],metframes[mf]['hd_est_y'],1920,1080,24)
               #ox1,oy1,ox2,oy2 = bound_xy(metframes[mf]['hd_bp_x'],metframes[mf]['hd_bp_y'],1920,1080,24)
               ox1,oy1,ox2,oy2 = int(ox1),int(oy1),int(ox2),int(oy2)

               orig_small_cnt  = work_frame[oy1:oy2,ox1:ox2].copy()
               cv2.circle(small_cnt, (int(24), int(24)), int(15), (255,255,255), 1)
               cv2.circle(orig_small_cnt, (int(24), int(24)), int(15), (255,255,255), 1)
              
               #print("DEBUG:", x1,y1,x2,y2)
               #print("DEBUG:", ox1,oy1,ox2,oy2)

               metframes[mf]['hd_best_x'] = best_x
               metframes[mf]['hd_best_y'] = best_y
               cv2.circle(frame, (int(metframes[mf]['hd_best_x']), int(metframes[mf]['hd_best_y'])), int(15), (255,0,255), 2)
               cv2.circle(frame, (int(metframes[mf]['orig_hd_x']), int(metframes[mf]['orig_hd_y'])), int(10), (0,0,255), 1)
               if mc > 0:
                  cv2.circle(frame, (int(metframes[mf]['hd_bp_x']), int(metframes[mf]['hd_bp_y'])), int(10), (0,255,255), 1)
                  cv2.circle(frame, (int(metframes[mf]['hd_blob_x']), int(metframes[mf]['hd_blob_y'])), int(10), (0,255,0), 1)
                  cv2.circle(frame, (int(metframes[mf]['hd_est_x']), int(metframes[mf]['hd_est_y'])), int(10), (255,0,0), 1)
               show_frame = cv2.resize(frame, (int(960),int(540)))
               if orig_small_cnt.shape[0] == 48 and orig_small_cnt.shape[1] == 48:
                  show_frame[5:53,800:848] = orig_small_cnt 
               if small_cnt.shape[0] == 48 and small_cnt.shape[1] == 48:
                  show_frame[5:53,900:948] = small_cnt 
               #cv2.imshow('pepe', show_frame)
               #cv2.waitKey(30)
               mc = mc + 1

      hd_xs = []
      hd_ys = []
      hd_fcs = []
      for fc in metframes:
         if "best_x" in metframes[fc]:
            hd_xs.append( metframes[fc]['best_y'] )
            hd_ys.append( metframes[fc]['best_x'])
         #elif "hd_est_x" in metframes[fc]:
         #   hd_xs.append( metframes[fc]['hd_est_x'] )
         #   hd_ys.append( metframes[fc]['hd_est_y'])
         else:
            hd_xs.append( metframes[fc]['orig_hd_x'] )
            hd_ys.append( metframes[fc]['orig_hd_y'])
         hd_fcs.append( fc)

      m,b = best_fit_slope_and_intercept(hd_xs,hd_ys)

      metconf['hd_m'] = m
      metconf['hd_b'] = b
      metconf['hd_first_x'] = hd_xs[0]
      metconf['hd_first_y'] = hd_ys[0]
      metconf['hd_first_fc'] = hd_fcs[0]
      metconf['hd_last_x'] = hd_xs[-1]
      metconf['hd_last_y'] = hd_ys[-1]
      metconf['hd_last_fc'] = hd_fcs[-1]
      metconf['hd_total_dist'] = calc_dist((metconf['hd_first_x'],metconf['hd_first_y']),(metconf['hd_last_x'],metconf['hd_last_y']))
      metconf['hd_avg_seg_len'] = metconf['hd_total_dist'] / (hd_fcs[-1]- hd_fcs[0])

      print("TOTAL DIST: ", metconf['hd_total_dist'])
      print("AVG SEG LEN: ", metconf['hd_avg_seg_len'])
      acl_poly = np.zeros(shape=(2,), dtype=np.float64)
      acl_poly[0] = np.float64(metconf['hd_avg_seg_len'])
      acl_poly[1] = np.float64(-0.001) 
      if "acl_poly" in metconf:
         if type(metconf['acl_poly']) != float:
            acl_poly = metconf['acl_poly']
            acl_poly[0] = np.float64(acl_poly[0])
            acl_poly[1] = np.float64(acl_poly[1])

      print("ACL POLY BEFORE LAST RUN:", acl_poly)
      res = scipy.optimize.minimize(reduce_meteor_acl, acl_poly, args=( metconf, metframes,frames,7,0,show), method='Nelder-Mead')
      print("NEW RES:", res)
      save_json_file(meteor_json_file,mj)
      print("SCI PI DONE:", res)
      acl_poly = res['x']
      x_fun = res['fun']
      avg_res = reduce_meteor_acl(acl_poly, metconf,metframes,frames,4,1,show)
      print(acl_poly, x_fun)
      metconf['acl_poly'] = acl_poly.tolist()
      metconf['acl_fun'] = x_fun
      metconf['acl_res'] = avg_res
      avg_res,metframes = reduce_meteor_acl(acl_poly, metconf,metframes,frames,4,1,show)
      mj['metconf'] = metconf
      mj['metframes'] = metframes
      print("final point res:", avg_res)
      save_json_file(meteor_json_file,mj)
      print("saved:", meteor_json_file)


   exit()



   if meteor_found == 1:
      fc = 0
      for frame in frames:
         if fc in metframes: 
            hd_x = metframes[fc]['orig_hd_x'] 
            hd_y = metframes[fc]['orig_hd_y']
            hd_xs.append( metframes[fc]['orig_hd_x'] )
            hd_ys.append( metframes[fc]['orig_hd_y'])
            if fx is None:
               fx = hd_x
               fy = hd_y
               ffn = fc 
            orig_est_x = metframes[fc]['orig_est_x'] * hdm_x 
            orig_est_y = metframes[fc]['orig_est_y'] * hdm_y
            if len(hd_xs) > 10:
               sxs = hd_xs[-10:]
               sys = hd_ys[-10:]
               print(sxs)
               print(sys)
               lf_m,lf_b = best_fit_slope_and_intercept(sxs,sys)
               metframes[fc]['lf_m'] = m
               metframes[fc]['lf_b'] = b
               m = lf_m
               b = lf_b
 
            elp_fs = fc - ffn 
            extra_acl = metconf['acl_poly'] *elp_fs**2
            #print("INFO:", fc, elp_fs, m, b, metconf['hd_avg_seg_len'], metconf['hd_avg_seg_len']*elp_fs, extra_acl ) 
            hd_est_x = int((fx + (metconf['x_dir_mod'] * (metconf['hd_avg_seg_len']*elp_fs)) + extra_acl ))
            hd_est_y = int((m*hd_est_x)+b)
         
            print("HD X,Y:", hd_x,hd_y, orig_est_x, orig_est_y)
            frame = cv2.resize(frame, (int(1920),int(1080)))
            cv2.circle(frame, (int(hd_x),int(hd_y)), int(10), (255,255,255), 1)
            cv2.circle(frame, (int(orig_est_x),int(orig_est_y)), int(2), (255,9,10), 2)
            cv2.circle(frame, (int(hd_est_x),int(hd_est_y)), int(2), (255,254,10), 2)
         show_frame = cv2.resize(frame, (int(960),int(540)))
         cv2.imshow('pepe', show_frame)
         cv2.waitKey(0)
         fc = fc + 1

   else:
      for object in objects:  
         if object['meteor'] == 1:
            print("METEOR FOUND:", object)
         else:
            print("NOT FOUND:", object)


   # end first run
   exit()

   #x1,y1,x2,y2= mj['crop_box']
   fc = 0
   for frame in frames:
      this_pos_cnts = ()
      color_frame = frame.copy()
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      frame = cv2.resize(frame, (int(1920),int(1080)))
      reduce_img  = cv2.resize(frame, (int(1920),int(1080)))

      temp = cv2.subtract(reduce_img , med_frame)
      reduce_img = temp
      frame = temp

      crop_img = reduce_img[y1:y2,x1:x2]
      crh,crw = crop_img.shape

      cv2.rectangle(frame, (x1, y1), (x2, y2), (128, 128, 128), 1)


      tdesc = str(fc) 

      crop_blur = cv2.GaussianBlur(crop_img, (7, 7), 0)

      alpha = .1

      # good
      #image_diff = cv2.absdiff(image_acc.astype(crop_img.dtype), crop_blur,)





      for pnt in smasks:
         (px,py,pw,ph) = pnt
         cpx = px + int(pw/2)
         cpy = py + int(ph/2)
         sz2 = int(pw * ph / 4)
         if pw < 10 and ph < 10:
            print("not today")
            #frame[cpy-sz2:cpy+sz2,cpx-sz2:cpx+sz2] = 0
            #image_acc[cpy-sz2:cpy+sz2,cpx-sz2:cpx+sz2] = 0
            #color_frame[cpy-sz2:cpy+sz2,cpx-sz2:cpx+sz2] = 0,0,0
         else:
            sz2 = 10
            #frame[cpy-sz2:cpy+sz2,cpx-sz2:cpx+sz2] = 0
            #image_acc[cpy-sz2:cpy+sz2,cpx-sz2:cpx+sz2] = 0
            #color_frame[cpy-sz2:cpy+sz2,cpx-sz2:cpx+sz2] = 0,0,0


      half_frame = cv2.resize(frame, (int(960),int(540)))
      if fc > 0:
         alpha = .5
         image_diff = np.float32(image_diff)
         image_acc = np.float32(image_acc)
         hello = cv2.accumulateWeighted(image_diff, image_acc, alpha)

      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), frame,)
      _, diff_thresh = cv2.threshold(image_diff.copy(), min_min_px, 255, cv2.THRESH_BINARY)
      #cv2.imshow('pepe', image_diff)
      #cv2.waitKey(0)
      #cv2.imshow('pepe', diff_thresh)
      #cv2.waitKey(0)


      _, diff_thresh = cv2.threshold(image_diff.copy(), 5, 255, cv2.THRESH_BINARY)

      #cv2.rectangle(half_frame, (dmx1, dmy1), (dmx2, dmy2), (128, 128, 128), 1)
      #thresh_obj = cv2.dilate(diff_thresh, None , iterations=10)
      cnt_diff_thresh = np.uint8(diff_thresh)

      cnt_diff_thresh_crop = cnt_diff_thresh[y1:y2,x1:x2]
      image_diff_crop = image_diff[y1:y2,x1:x2]
      cnt_res = cv2.findContours(cnt_diff_thresh_crop.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      image_diff_crop = image_diff[y1:y2,x1:x2]
      diff_thresh_crop = diff_thresh[y1:y2,x1:x2]
      crh,crw = diff_thresh_crop.shape

      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      print("CNTS:", fc, len(cnts))
      if len(cnts) > 0:
         this_pos_cnts = []
         # below is for the small window...
         #x,y,w,h,sz = 0,0,0,0,0
         for (i,c) in enumerate(cnts):
            tx,ty,tw,th = cv2.boundingRect(cnts[i])
            size = tw * th
            this_pos_cnts.append((tx,ty,tw,th,tw*th))
         if tw > 1 and th > 1:
            if len(this_pos_cnts) > 1:
               # more than 1 cnt, find best one. 
               temp = sorted(this_pos_cnts, key=lambda x: x[4], reverse=True)
               # biggest_cnt 
               x,y,w,h,sz = temp[0]
               for a,b,c,d,e in temp:
                  print("MANY CNTS:", fc, a,b,c,d,e)
            else:
               print("ONLY ONE CNT!")
               x,y,w,h,sz = this_pos_cnts[0]
            pos_cnts.append((x,y,w,h))
            cv2.rectangle(diff_thresh_crop, (int(x), int(y)), (int((x+w)), int((y+h))), (128, 128, 128), 1)
            cv2.rectangle(image_diff, (int(x), int(y)), (int((x+w)), int((y+h))), (128, 128, 128), 1)
            cnt_found = 1
         else:
            print("TOO SMALL", w,h)  
            x,y,w,h,sz = 0,0,0,0,0
            cnt_found = 0 
         



          

      crh,crw = diff_thresh_crop.shape
      mx1 = 5
      mx2 = 5 + int(crw)
      my1 = 5 
      my2 = 5 + int(crh)

      if fc in metframes:
         tdesc = tdesc + " " + metframes[fc]['frame_time']

      # fix if image is too big 
      
      cv2.putText(half_frame, str(tdesc),  (10, 530), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
      if fc in metframes:
         tdesc = "Frame: " + str(fc)
         hd_x = metframes[fc]['hd_x']
         hd_y = metframes[fc]['hd_y']
         #cv2.putText(half_frame, str(tdesc),  (int(mx1-5) ,int(my1-5)), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1) 
         cv2.circle(half_frame, (int(hd_x/2),int(hd_y/2)), int(10), (128,128,128), 1)

      #cv2.rectangle(half_frame, (mx1, my1), (mx2, my2), (128, 128, 128), 1)
      crop_img = image_diff[y1:y2,x1:x2]
      crh,crw = crop_img.shape
      print("RESIZE???", crw, crh)
      if crh >= 400 or crw >= 400:
         show_crop_img = cv2.resize(crop_img, (0,0),fx=.7, fy=.7)
         show_image_acc = cv2.resize(image_acc, (0,0),fx=.7, fy=.7)
         crh,crw = show_crop_img.shape
      else:
         show_crop_img = crop_img
         show_image_acc = image_acc 


      if len(this_pos_cnts) > 0 and cnt_found == 1:
         
         cnt_desc = str(x) + "," + str(y) + " " + str(w) + "," + str(h)
         cv2.putText(half_frame, str(cnt_desc),  (mx1+2, my2+20), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1) 
         sm_x1 = int(x+(w/2)) - 24
         sm_y1 = int(y+(h/2)) - 24
         sm_x2 = int(x+(w/2)) + 24
         sm_y2 = int(y+(h/2)) + 24
         hd_cnt_x = sm_x1 + 24 + x1
         hd_cnt_y = sm_y1 + 24 + y1
         #small_cnt = crop_img[sm_y1:sm_y2,sm_x1:sm_x2]
         small_cnt = image_diff_crop[sm_y1:sm_y2,sm_x1:sm_x2]
         if fc not in metframes:
            metframes[fc] = {}

         metframes[fc]['small_cnt'] = [sm_y1+y1,sm_y2+y1,sm_x1+x1,sm_x2+x1]
         min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(small_cnt)
         sc_bp_x = max_loc[0] - 12
         sc_bp_y = max_loc[1] - 12
         small_cnt2 = image_diff_crop[sm_y1+sc_bp_y:sm_y2+sc_bp_y,sm_x1+sc_bp_x:sm_x2+sc_bp_x]
         cv2.circle(small_cnt, (sc_bp_x+12,sc_bp_y+12), int(10), (255,128,128), 1)
         bp_x = sm_x1+sc_bp_x+x1 +12
         bp_y = sm_y1+sc_bp_y+y1 +12
         cv2.circle(half_frame, (int(bp_x/2),int(bp_y/2)), int(5), (255,255,255), 1)
         print("X1,Y1:", x1,y1) 
         print("HD CNT_X", int(hd_cnt_x/2),int(hd_cnt_y/2))
         cv2.circle(half_frame, (int(hd_cnt_x/2),int(hd_cnt_y/2)), int(10), (255,255,255), 2)
         metframes[fc]['blob_x'] = hd_cnt_x
         metframes[fc]['blob_y'] = hd_cnt_y
         metframes[fc]['bp_x'] = bp_x
         metframes[fc]['bp_y'] = bp_y
         smch,smcw = small_cnt.shape 
         if smch == 48 and smcw == 48:
            half_frame[5:53,900:948] = small_cnt 
      else:
         print("Problem...")
         # no cnt found.... if event is not over, we should create a new point from the estimate here.
         # or at least create and empty frame so we can fill it in later


      crh,crw = image_diff_crop.shape
      print("what is crop shape = ", crh,crw)
      if crh >= 400 or crw >= 400:
         #print("MIKE: ", crw, crh)
         show_diff = cv2.resize(image_diff_crop, (0,0),fx=.7, fy=.7)
         show_diff_thresh = cv2.resize(diff_thresh_crop, (0,0),fx=.7, fy=.7)
         show_image_diff_crop = cv2.resize(image_diff_crop, (0,0),fx=.5, fy=.5)
      else:
         show_diff_thresh = diff_thresh_crop
         show_image_diff_crop = image_diff_crop
      crh,crw = show_image_diff_crop.shape
      mx1 = 5
      mx2 = 5 + int(crw)
      my1 = 5 
      my2 = 5 + int(crh)
      print("orig crop shape: ", image_diff_crop.shape)
      print("canvas shape = ", my2-my1,mx2-mx1)
      print("crop shape: ", show_image_diff_crop.shape)
      print("mx,my: ", mx1,mx2,my1,my2)


      half_frame[my1:my2,mx1:mx2] = show_image_diff_crop


      cv2.rectangle(half_frame, (int(mx1), int(my1)), (int(mx2), int(my2)), (128, 128, 128), 1)

      if show == 1 and fc  < last_fn + 5:
         cv2.imshow('pepe', half_frame)
         cv2.waitKey(0)
         #cv2.waitKey(60)
      last_crop_img = crop_img
      last_crops.append(last_crop_img)
      fc = fc + 1


   # 2nd Pass 
   fc = 0
   
   for frame in frames:
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      color_frame = frame.copy()
      color_frame = cv2.resize(color_frame, (int(1920),int(1080)))
      cv2.rectangle(color_frame, (x1, y1), (x2, y2), (128, 128, 128), 1)
      frame = cv2.resize(frame, (int(1920),int(1080)))

      if fc in metframes:
         if 'small_cnt' in metframes[fc]:
            sm_y1,sm_y2,sm_x1,sm_x2 = metframes[fc]['small_cnt'] 
            cv2.rectangle(color_frame, (int(sm_x1), int(sm_y1)), (int(sm_x2), int(sm_y2)), (128, 128, 128), 1)


      half_frame = cv2.resize(color_frame, (int(960),int(540)))
      cv2.imshow('pepe', half_frame)
      cv2.waitKey(30)
      fc = fc + 1

def reduce_meteor_acl(acl_poly, metconf,metframes,frames,thresh=4,mode=0,show=0):
   print("POLYLEN:", len(acl_poly))
   hd_xs = []
   hd_ys = []
   ffn = None
   fx = None
   m = metconf['hd_m']
   b = metconf['hd_b']
   avg_res_dist = 0
   total_res_dist = 0
   res_dist = 0
   over = 0
   hd_est_x = None
   total_met_frames = len(metframes)
   if True:
      fc = 0
      total_res_dist = 0
      for frame in frames:
         if fc in metframes:
            over = 0
            hd_x = metframes[fc]['orig_hd_x']
            hd_y = metframes[fc]['orig_hd_y']
            if "hd_best_x" in metframes[fc]:
               hd_x = metframes[fc]['hd_best_x']
               hd_y = metframes[fc]['hd_best_y']
               print("USE BEST X", hd_x,hd_y)
            hd_xs.append( hd_x)
            hd_ys.append( hd_y)
            if fx is None:
               fx = hd_x
               fy = hd_y
               ffn = fc
            if len(hd_xs) > 10:
               sxs = hd_xs[-10:]
               sys = hd_ys[-10:]
               lf_m,lf_b = best_fit_slope_and_intercept(sxs,sys)
               metframes[fc]['lf_m'] = m
               metframes[fc]['lf_b'] = b
               m = lf_m
               b = lf_b
            if len(hd_xs) > 20:
               sxs = hd_xs[-20:]
               sys = hd_ys[-20:]
               lf_m,lf_b = best_fit_slope_and_intercept(sxs,sys)
               metframes[fc]['lf_m'] = m
               metframes[fc]['lf_b'] = b
               m = lf_m
               b = lf_b

            elp_fs = fc - ffn
            extra_acl = acl_poly[1] *elp_fs**2
            if ffn == fc:
               hd_est_x = fx 
               hd_est_y = fy
            else:
               hd_est_x = int((fx + (metconf['x_dir_mod'] * (acl_poly[0]*elp_fs)) + extra_acl ))
               hd_est_y = int((m*hd_est_x)+b)

            #cw = x2 - x1
            #ch = y2 - y1
            if hd_x != 0 and hd_y != 0:
               res_dist = calc_dist((hd_x,hd_y),(hd_est_x,hd_est_y))
            else:
               res_dist = 0
            metframes[fc]['hd_est_x'] = hd_est_x
            metframes[fc]['hd_est_y'] = hd_est_y
            metframes[fc]['hd_res_dist'] = res_dist 
            if fc + 3 <= len(metframes):
               total_res_dist = total_res_dist + res_dist
            frame = cv2.resize(frame, (int(1920),int(1080)))
            
            #gf = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            x1,y1,x2,y2 = bound_xy(hd_x,hd_y,1920,1080,50)
            y1,y2,x1,x2 = int(y1),int(y2),int(x1),int(x2)
            #cw = x2 - x1
            #ch = y2 - y1
            crop_img = frame[y1:y2,x1:x2]
            metframes[fc]['cnt_box'] = [x1,y1,x2,y2]


            cv2.circle(frame, (int(hd_x),int(hd_y)), int(10), (255,255,255), 1)
            if "hd_blob_x" in metframes[fc]:
               cv2.circle(frame, (int(metframes[fc]['hd_blob_x']),int(metframes[fc]['hd_blob_y'])), int(8), (0,255,0), 1)
            if "hd_bp_x" in metframes[fc]:
               cv2.circle(frame, (int(metframes[fc]['hd_bp_x']),int(metframes[fc]['hd_bp_y'])), int(5), (0,255,255), 1)
            if "orig_hd_x" in metframes[fc]:
               cv2.circle(frame, (int(metframes[fc]['orig_hd_x']),int(metframes[fc]['orig_hd_x'])), int(10), (128,128,128), 1)
         
            cv2.circle(frame, (int(hd_est_x),int(hd_est_y)), int(2), (255,0,0), 2)
            show_frame = cv2.resize(frame, (int(960),int(540)))
            ch,cw,cl = crop_img.shape
            #crop_img = cv2.resize(crop_img, (int(100),int(100)))
            show_frame[5:5+ch,5:5+cw] = crop_img
            if len(hd_xs) > 0:
               avg_res_dist = total_res_dist / len(hd_xs)
            tdesc = "RES: " + str(res_dist)[0:6] + "AVG RES: " + str(avg_res_dist)[0:6]
            cv2.putText(show_frame, str(tdesc),  (int(5) ,int(25+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
            tdesc = "AVG RES: " + str(avg_res_dist)[0:6]
            cv2.putText(show_frame, str(tdesc),  (int(5) ,int(50+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
            tdesc = "FC : " + str(fc)[0:6]
            cv2.putText(show_frame, str(tdesc),  (int(5) ,int(75+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
            tdesc = "EST XY : " + str(hd_est_x)[0:6] + "," + str(hd_est_y)[0:6]
            cv2.putText(show_frame, str(tdesc),  (int(5) ,int(100+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
            tdesc = "POLY : " + str(acl_poly[0])[0:6] + "," + str(acl_poly[1])[0:6] 
            cv2.putText(show_frame, str(tdesc),  (int(5) ,int(125+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
            tdesc = "ELPS: " + str(elp_fs)
            cv2.putText(show_frame, str(tdesc),  (int(5) ,int(150+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
            tdesc = "BOX: " + str(x1)+"," + str(y1) + "/" + str(x2) + "," + str(y2)
            cv2.putText(show_frame, str(tdesc),  (int(5) ,int(180+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
         else:
            # missing frame if things started?
            elp_fs = 0
            over = over + 1
            if fx is not None and over < 7:
               frame = cv2.resize(frame, (int(1920),int(1080)))
               elp_fs = fc - ffn
               #hd_est_x = int((fx + (acl_poly[2] * (acl_poly[0]*elp_fs)) + extra_acl ))
               hd_est_x = int((fx + (metconf['x_dir_mod'] * (acl_poly[0]*elp_fs)) + extra_acl ))
               hd_est_y = int((m*hd_est_x)+b)
               x1,y1,x2,y2 = bound_xy(hd_est_x,hd_est_y,1920,1080,50)
               cw = x2 - x1
               ch = y2 - y1
               crop_img = frame[y1:y2,x1:x2]

               cv2.circle(frame, (int(hd_est_x),int(hd_est_y)), int(10), (0,0,255), )
               res = 0
               if fc in metframes:
                  metframes[fc]['hd_est_x'] = hd_est_x
                  metframes[fc]['hd_est_y'] = hd_est_y
                  metframes[fc]['hd_res_dist'] = 0
                  metframes[fc]['cnt_box'] = [x1,y1,x2,y2]

               show_frame = cv2.resize(frame, (int(960),int(540)))
               ch = int(ch)
               cw = int(cw)
               ich,icw,cl = crop_img.shape 
               if ich == 100 and icw == 100:
                  print(ich,icw)
                  show_frame[5:5+ch,5:5+cw] = crop_img
               if len(hd_xs) > 0:
                  avg_res_dist = total_res_dist / len(hd_xs)
               tdesc = "RES: " + str(res_dist)[0:6] + "AVG RES: " + str(avg_res_dist)[0:6]
               cv2.putText(show_frame, str(tdesc),  (int(5) ,int(25+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
               tdesc = "AVG RES: " + str(avg_res_dist)[0:6]
               cv2.putText(show_frame, str(tdesc),  (int(5) ,int(50+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
               tdesc = "FC : " + str(fc)[0:6]
               cv2.putText(show_frame, str(tdesc),  (int(5) ,int(75+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
               tdesc = "EST XY : " + str(hd_est_x)[0:6] + "," + str(hd_est_y)[0:6]
               cv2.putText(show_frame, str(tdesc),  (int(5) ,int(100+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
               tdesc = "POLY : " + str(acl_poly[0])[0:6] + "," + str(acl_poly[1])[0:6] 
               cv2.putText(show_frame, str(tdesc),  (int(5) ,int(125+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 
               tdesc = "ELPS: " + str(elp_fs)
               cv2.putText(show_frame, str(tdesc),  (int(5) ,int(150+ch)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1) 

         if hd_est_x is not None :
               cv2.circle(frame, (int(hd_est_x),int(hd_est_y)), int(10), (255,0,0), 1)

         #if fx is not None:
            #if fc % 1 == 0:
               #cv2.imshow('pepe', show_frame)
               #cv2.waitKey(30)
        
         fc = fc + 1
   if len(hd_xs) -3 > 0:
     avg_res_dist = total_res_dist / len(hd_xs) -3
   if mode == 1:
      return(avg_res_dist,metframes)
   else:
      return(avg_res_dist)



def clean_hist(history, metframes = None, metconf = None):

   if metconf is None:
      metconf = {}
   hdm_x = 2.7272727272727272
   hdm_y = 1.875

   metconf['first_x'] = history[0][1] + int(history[0][5]/2)
   metconf['first_y'] = history[0][2] + int(history[0][6]/2)
   metconf['first_fc'] = history[0][0]
   metconf['last_x'] = history[-1][1] + int(history[-1][5]/2)
   metconf['last_y'] = history[-1][2] + int(history[-1][6]/2)
   metconf['last_fc'] = history[-1][0]
   metconf['total_dist'] = calc_dist((metconf['first_x'],metconf['first_y']),(metconf['last_x'],metconf['last_y']))
   metconf['avg_seg_len'] = metconf['total_dist'] / len(history)
   #print("AVG:SEG LEN:", total_dist, len(history), avg_seg_len)
   xs = []
   ys = []
   for fc,x,y,w,h,mx,my in history:
      xs.append(x)
      ys.append(y)

   m,b = best_fit_slope_and_intercept(xs,ys)
   metconf['xs'] = xs
   metconf['ys'] = ys
   metconf['m'] = m
   metconf['b'] = b
   metconf['acl_poly'] = .37

   metconf['dir_x'] = metconf['first_x'] - metconf['last_x']
   metconf['dir_y'] = metconf['first_y'] - metconf['last_y']
   if metconf['dir_x'] < 0:
      metconf['x_dir_mod'] = 1
   else:
      metconf['x_dir_mod'] = -1
   if metconf['dir_y'] < 0:
      metconf['y_dir_mod'] = 1
   else:
      metconf['y_dir_mod'] = -1


   # check for and remove a single trailing last frame if it exists
   last_fn_gap = history[-1][0] -  history[-2][0] 
   #print("GAP:", history[-1][0], history[-2][0], last_fn_gap)
   last_fn = len(history) -1 
   if last_fn_gap > 2:
      print("BAD GAP DEL HIST:!", last_fn)
      history.pop(last_fn)

   # check the distance between frames and remove bad frames towards the end if they exist
   over = 0
   hc = 0
   bad_fr = {}
   if metframes is None:
      metframes = {}
   fcc = 0
   acl_poly = 0
   last_x = None 


   for fc,x,y,w,h,mx,my in history:
      #print("EST:", first_x, x_dir_mod, avg_seg_len, fcc, acl_poly, fcc)
      est_x = int((metconf['first_x'] + metconf['x_dir_mod'] * (metconf['avg_seg_len']*fcc)) + metconf['acl_poly'] * fcc)
      est_y = int((m*est_x)+b)

      if fc not in metframes:
         hd_x = (x + mx ) * hdm_x
         hd_y = (y + my ) * hdm_y
         metframes[fc] = {}
         metframes[fc]['orig_x'] = x
         metframes[fc]['orig_y'] = y
         metframes[fc]['orig_w'] = w
         metframes[fc]['orig_h'] = h
         metframes[fc]['orig_mx'] = mx
         metframes[fc]['orig_my'] = my
         metframes[fc]['orig_est_x'] = est_x
         metframes[fc]['orig_est_y'] = est_y
         metframes[fc]['orig_hd_x'] = hd_x
         metframes[fc]['orig_hd_y'] = hd_y

      dist = 0

      gap = 0
      nx = x + (w) + mx
      ny = y + (h) + my
      if last_x is not None:
         dist = calc_dist((nx,ny),(last_x,last_y))
         start_dist = calc_dist((metconf['first_x'],metconf['first_y']),(nx,ny))
         gap = fc - last_fc
         metframes[fc]['start_dist'] = start_dist 
         metframes[fc]['last_dist'] = dist 
         metframes[fc]['gap'] = gap
         #print("LAST DIST/Gap:", fc, dist, gap)
         # frames till end? 
         frames_till_end = history[-1][0] - fc
         #print("FRAMES TILL END?", frames_till_end)
         if frames_till_end <= 3 and dist == 0 and gap > 3:
            # this event is DEF over and this is a ghost frame
            over = 1
            metframes[fc]['over'] = 1
      #print("FRAME:", hc, fc, nx, ny, dist, gap, over)
      last_x = nx
      last_y = ny
      last_fc = fc
      hc = hc + 1
      fcc = fcc + 1


   for fc in metframes:
      if over in metframes: 
         print("DEL:", fc, hc)
         bad_fr[fc] = 1
         del metframes[fc]

   new_hist = []
   for fc,x,y,w,h,mx,my in history:
      if fc not in bad_fr:
         new_hist.append((fc,x,y,w,h,mx,my))


   xs = []
   ys = []
   for fc,x,y,w,h,mx,my in new_hist:
      xs.append(x)
      ys.append(y)

   m,b = best_fit_slope_and_intercept(xs,ys)
   metconf['xs'] = xs
   metconf['ys'] = ys
   metconf['m'] = m
   metconf['b'] = b
   metconf['acl_poly'] = .2

   metconf['dir_x'] = metconf['first_x'] - metconf['last_x']
   metconf['dir_y'] = metconf['first_y'] - metconf['last_y']
   if metconf['dir_x'] < 0:
      metconf['x_dir_mod'] = 1
   else:
      metconf['x_dir_mod'] = -1
   if metconf['dir_y'] < 0:
      metconf['y_dir_mod'] = 1
   else:
      metconf['y_dir_mod'] = -1


   return(new_hist,metframes,metconf)
 


def reduce_meteor_ajax(json_conf,meteor_json_file, cal_params_file, show = 0):

   if show == 1:
      cv2.namedWindow('pepe')
   custom_fit = 0
   hdm_x = 2.7272727272727272
   hdm_y = 1.875
   #print(meteor_json_file)
   mj = load_json_file(meteor_json_file)
   red_file = meteor_json_file.replace(".json", "-reduced.json") 
   if cfe(red_file) == 1:
      mjr = load_json_file(red_file)
   
      if "cal_params" in mjr:
         cal_params = mjr['cal_params']
         custom_fit = 1

   sd_video_file = mj['sd_video_file']
   sd_stack_file = sd_video_file.replace(".mp4", "-stacked.png")
   man_reduce_file = meteor_json_file.replace(".json", "-manual.json")
   failed_file = meteor_json_file.replace(".json", "-rfailed.txt")

   meteor_obj = get_meteor_object(mj)
   if meteor_obj is None: 
      os.system("touch " + failed_file)

   start_clip = meteor_obj['history'][0][0]
   end_clip = meteor_obj['history'][-1][0]
   start_clip = start_clip - 25
   if start_clip < 0:
      start_clip = 0
   end_clip = end_clip + 50

   (cal_date, cam_id, cal_date_str,Y,M,D, H, MM, S) = better_parse_file_date(cal_params_file)
   if "reduced" in cal_params_file :
      if cfe(cal_params_file) == 1:
         red_data  = load_json_file(cal_params_file) 
         cal_params = red_data['cal_params']
      else:
         if custom_fit == 0:
            cal_params_files = get_active_cal_file(sd_stack_file)
            cal_params_file = cal_params_files[0][0]
            cal_params = load_json_file(cal_params_file) 
   else:
      if custom_fit == 0:
         cal_params = load_json_file(cal_params_file) 


   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(meteor_json_file)

   start_clip_time_str = str(f_datetime)
   hd_video_file = mj['hd_trim']
   meteor_dir = "/mnt/ams2/meteors/" + Y + "_" + M + "_" + D + "/" 
   el = sd_video_file.split("/")
   fn = el[-1] 
   fin_sd_video_file = meteor_dir + fn

   if hd_video_file != 0 and hd_video_file != None:
      el = hd_video_file.split("/")
      fn = el[-1] 
      fin_hd_video_file = meteor_dir + fn
   else:
      fin_hd_video_file = sd_video_file

   el = mj['sd_video_file'].split("-trim")
   min_file = el[0] + ".mp4"
   ttt = el[1].split(".")
   trim_num = int(ttt[0])
   extra_sec = trim_num / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)


   if cfe(failed_file) == 1:
      print('{"error":"This reduction was already tried and failed: '+ failed_file +'","status":0}')
      sys.exit(0)
    

   #cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py cfit " + cal_params_file + " 0 > /mnt/ams2/tmp/autoCal.txt "
   #print(cmd)
   #os.system(cmd)


   meteor_json = load_json_file(meteor_json_file)
   sd_video_file = meteor_json['sd_video_file']
   (crop_max_x,crop_max_y,crop_min_x,crop_min_y) = find_min_max_dist(meteor_obj['history'])
   crop = (crop_min_x,crop_min_y,crop_max_x,crop_max_y)
   #crop_min_x = 0
   #crop_min_y = 0
   if cfe(sd_video_file) == 0:
      sd_video_file = sd_video_file.replace("SD/proc2/", "meteors/")
      sd_video_file = sd_video_file.replace("/passed/", "/")

   frames,ofx,ofy = load_video_frames(sd_video_file,json_conf,0,0,crop)
   
   frs = load_video_frames(sd_video_file,json_conf,2)
   ih, iw = frs[0].shape[:2]
   hdm_x = 1920 / iw
   hdm_y = 1080 / ih



   crop_min_x = ofx
   crop_min_y = ofy
   if end_clip > len(frames) -1 :
      end_clip = len(frames) - 1
   #frames = frames[start_clip:end_clip]
   objects = {}
   #objects = track_bright_objects(frames, sd_video_file, cam_id, meteor_obj, json_conf, show)
   objects = check_for_motion2(frames, sd_video_file,cam_id, json_conf,show)
   if len(objects) == 0:
      os.system("touch " + failed_file)
      return()
      

   # do track brightest object here instead of check_for_motion2? 

   
   if len(objects) > 0:
      objects,meteor_found = test_objects(objects,frames)
   else:
      objects = []
      meteor_found = 0
   meteor_obj = get_meteor_object(objects)
   if len(meteor_obj) == 0:
      os.system("touch " + failed_file)
      return()

   if cfe(sd_stack_file) == 0:
      sd_stack_file = sd_stack_file.replace("SD/proc2/", "meteors/")
      sd_stack_file = sd_stack_file.replace("/passed/", "/")
   reduce_img = cv2.imread(sd_stack_file)

   reduce_img  = cv2.resize(reduce_img, (int(1920/2),int(1080/2)))
   reduce_img_file = sd_stack_file.replace("-stacked.png", "-reduced.png")



   if len(meteor_obj['history']) > 0:
      fx = meteor_obj['history'][0][1]
      fy = meteor_obj['history'][0][2]
      lx = meteor_obj['history'][-1][1]
      ly = meteor_obj['history'][-1][2]
   else: 
      fx = 0
      fy = 0
      lx = 0
      ly = 0

   
   sfn = meteor_obj['history'][0][0]
   lfn = meteor_obj['history'][-1][0]

   elp_frames = lfn - sfn 
   elp_dur = elp_frames / 25

   # direction?
   ex = lx - fx
   if ex < 0:
      left_right = "left"
   else:
      left_right = "right"
   ey = ly - fy
   if ey < 0:
      up_down = "up"
   else:
      up_down = "down"



   fc = 0
   last_dist = 0 
   meteor_frame_data = []
   padding = len(meteor_obj['history']) * 5
   tot_f = len(meteor_obj['history'])
   max_max_px = 0
   ih,iw = frames[0].shape

   end_el = None
   end_az = None
   start_el = None
   start_az = None

   for fn,x,y,w,h,mx,my in meteor_obj['history']:
      #if fc == 0:
      #   fy = int((fy + my) * hdm_y / 2)
       
      pad = int(padding / (fc+1))
      if up_down == "up":
         pad = -10
         y_adj = int((pad * tot_f) / 2)
      else:
         pad = 10
         y_adj = int((pad * tot_f) / 2)
      pad = pad * fc
      #cv2.rectangle(reduce_img, (x, y), (x+ w, y+w), (128, 128, 128), 1)
      dist_from_first = calc_dist((fx,fy),(x+mx,y+my))
      if dist_from_first > last_dist or fc == 0: 
         x2 = x + w
         y2 = y + h
         cnt_img = frames[fn][y:y2,x:x2]
         #max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img)
         max_px, avg_px, px_diff,max_loc = eval_cnt_better(cnt_img)
         if max_px > max_max_px:
            max_max_px = max_px
 
         extra_meteor_sec = fn / 25
         meteor_frame_time = start_trim_frame_time + datetime.timedelta(0,extra_meteor_sec)
         meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         if fc == 0: 
            event_start_time = meteor_frame_time_str

         x = x + mx + crop_min_x
         y = y + my + crop_min_y
         hd_x = int((x) * hdm_x)
         hd_y = int((y) * hdm_y)
         half_hd_x = int(hd_x / 2)
         half_hd_y = int(hd_y / 2)
         new_x, new_y, ra ,dec , az, el= XYtoRADec(hd_x,hd_y,cal_params_file,cal_params,json_conf)
         if fc == 0:
            start_az = az
            start_el = el
            start_ra = ra
            start_dec = dec
         else:
            end_az = az
            end_el = el
            end_ra = ra
            end_dec = dec
         cv2.circle(reduce_img, (half_hd_x,half_hd_y), int(10), (255,128,128), 1)
         meteor_frame_data.append((meteor_frame_time_str,fn,int(hd_x),int(hd_y),int(w),int(h),int(max_px),float(round(ra,2)),float(round(dec,2)),float(round(az,2)),float(round(el,2))))
 
         tdesc = str(fc) + " - " + str(az)[0:6] + "/" + str(el)[0:5]
         cv2.putText(reduce_img, str(tdesc),  (int(half_hd_x) + 16,int(half_hd_y+pad-y_adj)), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1) 
         fc = fc + 1
      last_dist = dist_from_first
   cv2.imwrite(reduce_img_file, reduce_img)
   rand = time.time()

   if end_az is None and start_az is not None:
      end_az = start_az
      end_el = start_el
      end_ra = start_ra
      end_dec = start_dec

   response = {}
   response['status'] = 1
   response['message'] = "reduce complete"
   response['debug'] = "none"
   response['sd_meteor_frame_data'] = meteor_frame_data
   response['reduce_img_file'] = reduce_img_file
   vf_type = "SD"
   fin_sd_stack = fin_sd_video_file.replace(".mp4", ".png")
   fin_hd_stack = fin_hd_video_file.replace(".mp4", ".png")
   if "stacked-stacked" in fin_hd_stack:
      fin_hd_stack = fin_hd_stack.replace("-stacked-stacked", "-stacked")
   fin_reduced_video = fin_sd_video_file.replace(".mp4", "-reduced.mp4")
   fin_reduced_stack = fin_sd_video_file.replace(".mp4", "-reduced.png")

   if custom_fit == 1:
      meteor_reduced = mjr
   else:
      meteor_reduced = {}
  
   meteor_reduced['api_key'] = json_conf['site']['api_key']
   meteor_reduced['station_name'] = json_conf['site']['ams_id']
   meteor_reduced['device_name'] = cam_id
   meteor_reduced['sd_video_file'] = fin_sd_video_file
   meteor_reduced['hd_video_file'] = fin_hd_video_file
   meteor_reduced['sd_stack'] = fin_sd_stack
   meteor_reduced['hd_stack'] = fin_hd_stack
   meteor_reduced['reduced_stack'] = fin_reduced_stack
   meteor_reduced['reduced_video'] = fin_reduced_video
   meteor_reduced['vf_type'] = vf_type
   meteor_reduced['event_start_time'] = event_start_time
   meteor_reduced['event_duration'] = float(elp_dur)
   meteor_reduced['peak_magnitude'] = int(max_max_px)
   meteor_reduced['start_az'] = start_az
   meteor_reduced['start_el'] = start_el
   meteor_reduced['end_az'] = end_az

   meteor_reduced['end_el'] = end_el
   meteor_reduced['start_ra'] = start_ra
   meteor_reduced['start_dec'] = start_dec
   meteor_reduced['end_ra'] = end_ra
   meteor_reduced['end_dec'] = end_dec
   meteor_reduced['meteor_frame_data'] = meteor_frame_data
   meteor_reduced['cal_params_file'] = cal_params_file
   if "cal_params" not in meteor_reduced:
      meteor_reduced['cal_params'] = {}
   meteor_reduced['cal_params']['site_lat'] = json_conf['site']['device_lat']
   meteor_reduced['cal_params']['site_lng'] = json_conf['site']['device_lng']
   meteor_reduced['cal_params']['site_alt'] = json_conf['site']['device_alt']
   meteor_reduced['cal_params']['ra_center'] = cal_params['ra_center']
   meteor_reduced['cal_params']['dec_center'] = cal_params['dec_center']
   meteor_reduced['cal_params']['center_az'] = cal_params['center_az']
   meteor_reduced['cal_params']['center_el'] = cal_params['center_el']
   meteor_reduced['cal_params']['position_angle'] = cal_params['position_angle']
   meteor_reduced['cal_params']['pixscale'] = cal_params['pixscale']
   meteor_reduced['cal_params']['imagew'] = cal_params['imagew']
   meteor_reduced['cal_params']['imageh'] = cal_params['imageh']
   meteor_reduced['cal_params']['cal_date'] = cal_date_str
   meteor_reduced['cal_params']['x_poly'] = cal_params['x_poly']
   meteor_reduced['cal_params']['y_poly'] = cal_params['y_poly']
   meteor_reduced['cal_params']['x_poly_fwd'] = cal_params['x_poly_fwd']
   meteor_reduced['cal_params']['y_poly_fwd'] = cal_params['y_poly_fwd']

   
   (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_reduced['meteor_frame_data'])
   meteor_reduced['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y)

   if 'x_fun' in cal_params:
      meteor_reduced['cal_params']['x_res_err'] = cal_params['x_fun']
      meteor_reduced['cal_params']['y_res_err'] = cal_params['y_fun']
      meteor_reduced['cal_params']['x_fwd_res_err'] = cal_params['x_fun_fwd']
      meteor_reduced['cal_params']['y_fwd_res_err'] = cal_params['y_fun_fwd']
   meteor_reduce_file = meteor_json_file.replace(".json", "-reduced.json")

   (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_reduced['meteor_frame_data'])
   meteor_reduced['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y) 

   save_json_file(meteor_reduce_file, meteor_reduced) 


   cmp_imgs = make_meteor_cnt_composite_images(json_conf, meteor_frame_data, sd_video_file)
   prefix = sd_video_file.replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")
   response['prefix'] = prefix
   for fn in cmp_imgs:
      cv2.imwrite(prefix  + str(fn) + ".png", cmp_imgs[fn])    

   
   mfd_file = meteor_json_file.replace(".json", "-reduced.json")
   #print("cd /home/ams/amscams/pythonv2/; ./reducer3.py mfd " + mfd_file + " > /dev/null")
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py mfd " + mfd_file + " > /dev/null")
   os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mfd_file + "> /dev/null")

   print(json.dumps(response))
  
def get_meteor_object(meteor_json):
   if 'sd_objects' in meteor_json:
      objects = meteor_json['sd_objects']
   else:
      objects = meteor_json

   for object in objects:
      if "meteor" in object: 
         if object['meteor'] == 1:
            return(object)
   if len(objects) > 0:
      return(objects[0])
   else:
      return(None)

def make_frame_table(meteor_reduced,meteor_json_file):
   astro_res_err = 0
   cat_image_stars = []
   total_stars = 0
   if "cal_params" in meteor_reduced:
      if "astro_res_err" in meteor_reduced['cal_params']:
         astro_res_err = meteor_reduced['cal_params']['astro_res_err']
      if "cat_image_stars" in meteor_reduced['cal_params']:
         cat_image_stars = meteor_reduced['cal_params']['cat_image_stars']
         total_stars = len(cat_image_stars)


   prefix = meteor_reduced['sd_video_file'].replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")

   video_file = meteor_reduced['sd_video_file']
   hd_stack_file = meteor_reduced['hd_stack']
   cal_params_file = ""
   res_desc = "Residual Star Error: " + str(astro_res_err)[0:5]
   star_desc = "Total Stars: " + str(total_stars)
   stab,sr,sc,et,er,ec = div_table_vars()
   if "crop_box" in meteor_reduced:

      (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_reduced['meteor_frame_data'])
      meteor_reduced['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y) 
      #(box_min_x,box_min_y,box_max_x,box_max_y) = meteor_reduced['crop_box']
      box_width = int((box_max_x - box_min_x) / 2)
      box_height = int((box_max_y - box_min_y) / 2)
   else: 
     box_min_x =0 
     box_min_y =0 
     box_width=0 
     box_height=0 
   box_min_x = int(box_min_x/2)
   box_min_y = int(box_min_y/2)



   frame_javascript = """ <script> 

      function init_info() {

         var site_id = '"""  + meteor_reduced['station_name'].upper() + """'
         var cam_id = '"""  + meteor_reduced['device_name'] + """'
         var start_time = '"""  + meteor_reduced['event_start_time'] + """'
         var duration = '"""  + str(meteor_reduced['event_duration']) + """'
         var start_az = '"""  + str(meteor_reduced['start_az']) + """'
         var start_el = '"""  + str(meteor_reduced['start_el']) + """'
         var end_az = '"""  + str(meteor_reduced['end_az']) + """'
         var end_el = '"""  + str(meteor_reduced['end_el']) + """'

         var text_cam_id = new fabric.Text("Cam ID: " + site_id + "-" + cam_id, {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 495 
         });
         text_cam_id.setColor('rgba(255,255,255,.75)')
         canvas.add(text_cam_id)

         var text_cam_id = new fabric.Text("Start Time: " + start_time + " (" + duration + " seconds)", {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 510
         });
         text_cam_id.setColor('rgba(255,255,255,.75)')
         canvas.add(text_cam_id)

         var text_cam_id = new fabric.Text("Start AZ/EL : " + Math.round(start_az * 100) / 100 + "/" + Math.round(start_el* 100) / 100 + " End AZ/EL: " + Math.round(end_az * 100) / 100 + "/" + Math.round(end_el * 100) / 100 , {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 525
         });
         text_cam_id.setColor('rgba(255,255,255,.75)')
         canvas.add(text_cam_id)

      }

      window.onload = function () {
         init_info()
         show_cat_image_stars_ajax ('""" + video_file + """') 

         var text_p = new fabric.Text('""" + res_desc + """', {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 5 
         });
         text_p.setColor('rgba(255,255,255,.75)')
         //canvas.add(text_p)

         var text_p = new fabric.Text('""" + star_desc + """', {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 20 
         });
         text_p.setColor('rgba(255,255,255,.75)')
         //canvas.add(text_p)

         var roi_rect = new fabric.Rect({
            fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,230,230,.2)',  left: """ + str(box_min_x) + """, top: """ + str(box_min_y) + """, 
            width: """ + str(box_width) + """,
            height: """ + str(box_height) + """ ,
            selectable: false
         });
         canvas.add(roi_rect);

      }
   """
   frame_table = stab
   frame_table = frame_table + sr + sc + "IMG" + ec + sc + "FN" +ec + sc + "Frame Time" + ec + sc + "X/Y - W/H " + ec + sc + "Max PX" +ec + sc + "RA/DEC" + ec + sc + "AZ/EL" + ec + sc + "DEL " + ec + er 
   lc = 0
   start_y = meteor_reduced['meteor_frame_data'][0][3]

   #for cstar in meteor_reduced['cal_params']['cat_image_stars']:
   #   (iname,mag,ra,dec,tmp1,tmp2,px_dist,new_cat_x,new_cat_y,tmp3,tmp4,new_cat_x,new_cat_y,ix,iy,px_dist) = cstar



   for frame_data in meteor_reduced['meteor_frame_data'] :
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      hd_x = int(hd_x/2)
      hd_y = int(hd_y/2)
      text_y = str(hd_y)
      text_y = (start_y/2) - (lc * 12)
      fr_id = "fr_row" + str(fn)
      cmp_img_url = prefix  + str(fn) + ".png"
      cmp_img = "<img src=" + cmp_img_url + ">"

      az_desc = "\"" + str(lc) + " -  " + str(az) + " / " + str(el)  + "\""
      del_frame_link = "<a href=\"javascript:del_frame('" + str(fn) + "','" + meteor_json_file +"')\">X</a> "

      sr_id = "<div class=\"divTableRow\" id=\"" + fr_id + "\">"
      frame_table = frame_table + sr_id + sc + cmp_img + ec + sc  + str(fn) +ec + sc + str(frame_time) + ec + sc + str(hd_x) + "/" + str(hd_y) + " - " + str(w) + "/" + str(h) + ec + sc + str(max_px) +ec + sc + str(ra) + "/" + str(dec) + ec + sc +  str(az) + "/" + str(el)  + ec + sc + del_frame_link + ec + er

      frame_javascript = frame_javascript + """
                 var rad = 5;
                 var meteor_rect = new fabric.Rect({
                    fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,100,200,.3)',  left: """ + str(hd_x-5) + """, top: """ + str(hd_y-5) + """, 
                    width: 10,
                    height: 10 ,
                    selectable: false
                 });
                 canvas.add(meteor_rect);
/*
                 var meteor_rect = new fabric.Circle({

                     radius: rad, fill: 'rgba(255,255,0,0)', strokeWidth: 1, stroke: 'rgba(255,255,255,.5)', left: """ + str(hd_x-5) + """, top: """ + str(hd_y-5) + """,
                     selectable: false
                 });
                 canvas.add(meteor_rect);
*/
      """        
      frame_javascript = frame_javascript + """ 
/*
                 var text_p = new fabric.Text(""" + az_desc + """, {
                    fontFamily: 'Arial',
                    fontSize: 10,
                    left: """ + str(hd_x) + """ +25,
                    top: """ + str(text_y) + """ +25
                 });
                 text_p.setColor('rgba(255,255,255,.75)')
                 canvas.add(text_p)
*/

      """
      lc = lc + 1
   frame_javascript = frame_javascript + "</script>"
   frame_table = frame_table + et
   return(frame_table, frame_javascript)

def update_hd_cal_ajax(json_conf, form):
   cfile = form.getvalue('cfile') 
   cal_file = cfile.replace("-stacked.png", "-calparams.json")
   cal_params = load_json_file(cal_file)
   cal_params['cat_image_stars'] = remove_dupe_cat_stars(cal_params['cat_image_stars'])
   resp = {}
   resp['cat_image_stars'] = cal_params['cat_image_stars']
   resp['total_stars'] = len(cal_params['cat_image_stars'])
   resp['total_res_px'] = cal_params['total_res_px']
   resp['total_res_deg'] = cal_params['total_res_deg']

   print(json.dumps(resp))

def update_red_info_ajax(json_conf, form):

   # need reduction points / metframe_data
   # crop_box
   # ares err 
   # text values 
   # star list 
   total_res_deg = 0 
   total_res_px = 0 
   max_res_deg = 0 
   max_res_px = 0 
   


   video_file = form.getvalue('video_file') 
   meteor_json_file = video_file.replace(".mp4", ".json")
   meteor_red_file = meteor_json_file.replace(".json", "-reduced.json")
   rsp = {}



   if cfe(meteor_red_file) == 1:
      mr = load_json_file(meteor_red_file)
      if "cal_params" in mr:
 
         if "cat_image_stars" in mr['cal_params']:
            rsp['cat_image_stars'] = mr['cal_params']['cat_image_stars'] 
            sc = 0
            for star in mr['cal_params']['cat_image_stars']:
               (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) = star
               max_res_deg = float(max_res_deg) + float(match_dist)
               max_res_px = float(max_res_px) + float(cat_dist )
               sc = sc + 1
            if "total_res_px" in mr['cal_params']:
               rsp['total_res_px'] = mr['cal_params']['total_res_px']
               rsp['total_res_deg'] = mr['cal_params']['total_res_deg']

            elif len( mr['cal_params']['cat_image_stars']) > 0:
               rsp['total_res_px'] = max_res_px/ sc
               rsp['total_res_deg'] = (max_res_deg / sc) 
               mr['total_res_px'] = max_res_px / sc
               mr['total_res_deg'] = (max_res_deg  / sc ) 


         else:
            #os.system("cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + meteor_json_file + " >/mnt/ams2/tmp/aci.txt")
            mr = load_json_file(meteor_red_file)
            if "cal_params" in mr:
               if "cat_image_stars" in mr['cal_params']:
                  rsp['cat_image_stars'] = mr['cal_params']['cat_image_stars'] 

         new_mfd = []
         if "meteor_frame_data" in mr: 
            temp = sorted(mr['meteor_frame_data'], key=lambda x: int(x[1]), reverse=False)
            for frame_data in temp:      
               frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
               if len(str(ra)) > 6:
                  ra = str(ra)[0:6]
               if len(str(dec)) > 6:
                  dec = str(dec)[0:6]
               if len(str(az)) > 6:
                  az = str(az)[0:6]
               if len(str(el)) > 6:
                  el = str(el)[0:6]
               new_mfd.append((frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el)) 

            rsp['meteor_frame_data'] = new_mfd
            (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(mr['meteor_frame_data'])
            rsp['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y)
            mr['crop_box'] = rsp['crop_box']
      rsp['status'] = 1
   else: 
      rsp['status'] = 0
         

   print(json.dumps(rsp))
   

def reduce_meteor_js(meteor_reduced):
   video_file = meteor_reduced['sd_video_file']
   hd_stack_file = meteor_reduced['hd_stack']
   cal_params_file = ""
   if "cal_params" in meteor_reduced:
      if "total_res_deg" in meteor_reduced['cal_params']:
         res_deg = meteor_reduced['cal_params']['total_res_deg']
         res_px = meteor_reduced['cal_params']['total_res_px']
      else:
         res_deg = "9999"
         res_px = "9999"
      if "cat_image_stars" in meteor_reduced['cal_params']:
         cat_image_stars = meteor_reduced['cal_params']['cat_image_stars']
      else:
         cat_image_stars = []
   else:
      res_deg = "9999"
      res_px = "9999"
      cat_image_stars = [] 
   star_desc = "Registered Stars: " + str(len(cat_image_stars))
   res_desc = "Residual Star Error: " + str(res_deg)[0:5] + "deg" + " " + str(res_px) + " px"


   (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_reduced['meteor_frame_data'])
   meteor_reduced['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y) 
   box_width = int((box_max_x - box_min_x) / 2)
   box_height = int((box_max_y - box_min_y) / 2)
   meteor_js = """ <script>

      function init_info() {

         var site_id = '"""  + meteor_reduced['station_name'].upper() + """'
         var cam_id = '"""  + meteor_reduced['device_name'] + """'
         var start_time = '"""  + meteor_reduced['event_start_time'] + """'
         var duration = '"""  + str(meteor_reduced['event_duration']) + """'
         var start_az = '"""  + str(meteor_reduced['start_az']) + """'
         var start_el = '"""  + str(meteor_reduced['start_el']) + """'
         var end_az = '"""  + str(meteor_reduced['end_az']) + """'
         var end_el = '"""  + str(meteor_reduced['end_el']) + """'

         var text_cam_id = new fabric.Text("Cam ID: " + site_id + "-" + cam_id, {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 495
         });
         text_cam_id.setColor('rgba(255,255,255,.75)')
         canvas.add(text_cam_id)

         var text_cam_id = new fabric.Text("Start Time: " + start_time + " (" + duration + " seconds)", {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 510
         });
         text_cam_id.setColor('rgba(255,255,255,.75)')
         canvas.add(text_cam_id)

         var text_cam_id = new fabric.Text("Start AZ/EL : " + Math.round(start_az * 100) / 100 + "/" + Math.round(start_el* 100) / 100 + " End AZ/EL: " + Math.round(end_az * 100) / 100 + "/" + Math.round(end_el * 100) / 100 , {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 525
         });
         text_cam_id.setColor('rgba(255,255,255,.75)')
         canvas.add(text_cam_id)

      }

      window.onload = function () {
         init_info()
         show_cat_stars('""" + video_file + "','" + hd_stack_file + "','" + cal_params_file + """', 'first_load')

         var text_p = new fabric.Text('""" + res_desc + """', {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 5
         });
         text_p.setColor('rgba(255,255,255,.75)')
         //canvas.add(text_p)

         var text_p = new fabric.Text('""" + star_desc + """', {
            fontFamily: 'Arial',
            fontSize: 10,
            left: 5 ,
            top: 20
         });
         text_p.setColor('rgba(255,255,255,.75)')
         //canvas.add(text_p)

         var roi_rect = new fabric.Rect({
            fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(230,230,230,.2)',  left: """ + str(box_min_x) + """, top: """ + str(box_min_y) + """,
            width: """ + str(box_width) + """,
            height: """ + str(box_height) + """ ,
            selectable: false
         });
         canvas.add(roi_rect);

      }
   """

   return(meteor_js)


def reduce_meteor_new(json_conf,form):

   #cgitb.enable()
      
   fp = open("/home/ams/amscams/pythonv2/templates/reducePage.html")
   template = ""
   for line in fp :
      template = template + line

   form_cal_params_file = form.getvalue("cal_params_file")
   hdm_x = 2.7272727272727272
   hdm_y = 1.875
   video_file = form.getvalue("video_file")
 
   # Try to build the corresponding JSID
   jsid = video_file.split("/")[-1]
   jsid = jsid.replace("_", "")
   jsid = jsid.replace(".mp4", "")
   template = template.replace("{JSID}", jsid) 

   meteor_json_file = video_file.replace(".mp4", ".json") 
   meteor_reduced_file = meteor_json_file.replace(".json", "-reduced.json")
   template = template.replace("{VIDEO_FILE}", video_file)
 
   ms_data = None
   if cfe(meteor_reduced_file) == 1:
      meteor_reduced = load_json_file(meteor_reduced_file)
      reduced = 1
      if "crop_box" not in meteor_reduced:
         (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_reduced['meteor_frame_data'])
         meteor_reduced['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y)
      frame_table, frame_javascript = make_frame_table(meteor_reduced,meteor_json_file)

   else:
      frame_table = ""
      reduced = 0
   mj = load_json_file(meteor_json_file)
   meteor_obj = get_meteor_object(mj)
   ms_desc = ""
   if "hd_trim" in mj:
      if mj['hd_trim'] != 0:
         hd_trim = mj['hd_trim']
      else:
         hd_trim = 0




   if reduced == 1:
      if "cal_params" in meteor_reduced:
         if "cat_image_stars" in meteor_reduced['cal_params']:
            cat_image_stars = meteor_reduced['cal_params']['cat_image_stars']
            total_stars = len(cat_image_stars)
      if "multi_station" in meteor_reduced:
         ms_data= meteor_reduced['multi_station']
         if cfe("/home/ams/amscams/conf/sync_urls.json") == 1:
            sync_urls = load_json_file("/home/ams/amscams/conf/sync_urls.json")
            for st in ms_data['obs']:
               #ms_link = sync_urls['sync_urls'][st] + "/pycgi/webUI.py?cmd=reduce&video_file=" + ms_data['obs'][st]['sd_video_file'].replace(".json", ".mp4")
               ms_link = ""
               ms_desc = ms_desc + "<a href=" + ms_link + ">" + st + "</a><BR>"
         template = template.replace("{MULTI_STATION}", ms_desc)

    
#      mj = meteor_reduced
#      mr = mj
   else:
      ms_data = None
      cal_files = get_active_cal_file(mj['sd_video_file'])
      #for cal_file in cal_files:
      #   print(cal_file, "<BR>")
      if cal_files is not None:
         cal_params_file = cal_files[0][0]
      else:
         cal_params_file = None
      #print("Meteor not reduced yet...using...", cal_params_file)
      #exit()
   if "/mnt/ams2/meteors" not in mj['sd_video_file']:
      el = mj['sd_video_file'].split("/")
      sd_fn = el[-1]
      day_dir = el[-3]
      mj['sd_video_file'] = mj['sd_video_file'].replace("/mnt/ams2/SD/proc2", "/mnt/ams2/meteors")
      mj['sd_video_file'] = mj['sd_video_file'].replace("/passed", "")
      if mj['hd_file'] != 0 and mj['hd_file'] != None:
         mj['hd_file'] = mj['hd_file'].replace("/mnt/ams2/HD", "/mnt/ams2/meteors/" + day_dir)
         mj['hd_trim'] = mj['hd_trim'].replace("/mnt/ams2/HD", "/mnt/ams2/meteors/" + day_dir)
         mj['hd_crop_file'] = mj['hd_crop_file'].replace("/mnt/ams2/HD", "/mnt/ams2/meteors/" + day_dir)
         mj['hd_crop_file_stack'] = mj['hd_crop_file'].replace(".mp4", "-stacked.jpg")
         mj['hd_trim_stack'] = mj['hd_trim'].replace(".mp4", "-stacked.jpg")
      else:
         mj['hd_file'] = 0
         mj['hd_trim'] = 0
         mj['hd_crop_file'] = 0
         mj['hd_crop_file_stack'] = 0
         mj['hd_trim_stack'] = 0
      mj['sd_stack'] = mj['sd_video_file'].replace(".mp4", "-stacked.jpg")


   if cfe(meteor_reduced_file) == 1:
      if "ams_event_id" in meteor_reduced:
         link = "/mnt/ams2/events/" + meteor_reduced['ams_event_id'] + "/"
         solution = "<dt class=\"col-6\"><a href=" + link + ">" + meteor_reduced['ams_event_id'] + "</dt><dd class=\"col-6\">Monte Carlo</dd>";
      else:
         solution = ""

   plots_html = ""
   traj_html = ""
   orb_html = ""
   if cfe(meteor_reduced_file) == 1:
      if "ams_event_id" in meteor_reduced:
         template = template.replace("{SOLUTIONS}", solution)
         sol_dir = link + "monte_carlo/"
         sol_files = glob.glob(sol_dir + "*")
         for sf in sorted(sol_files):
            if "png" in sf and "track" not in sf and "orbit" not in sf:
               plots_html = plots_html + "<figure ><img width=400 src=" + sf + "></figure>" 
            if "png" in sf and "track" in sf :
               traj_html = traj_html + "<figure ><img width=400 src=" + sf + "></figure>" 
            if "png" in sf and "orbit" in sf :
               orb_html = orb_html + "<figure ><img width=400 src=" + sf + "></figure>" 

   template = template.replace("{%PLOTS_TABLE%}", plots_html)
   template = template.replace("{%TRAJECTORY_TABLE%}", traj_html)
   template = template.replace("{%ORBIT_TABLE%}", orb_html)

   if "stacked" in mj['sd_stack']:
      if "png" in mj['sd_stack']:
         mj['half_stack'] = mj['sd_stack'].replace("-stacked.png", "-half-stack.png")
      else:
         mj['half_stack'] = mj['sd_stack'].replace("-stacked.jpg", "-half-stack.jpg")

   sd_video_file = mj['sd_video_file']
   sd_stack = mj['sd_stack']
   if "stacked" not in mj['sd_stack']:
      mj['sd_stack'] = mj['sd_stack'].replace(".jpg", "-stacked.jpg")
      mj['hd_stack'] = mj['hd_stack'].replace(".jpg", "-stacked.jpg")




   if "hd_stack" not in mj and mj['hd_trim'] != 0: 
      mj['hd_stack'] = mj['hd_trim'].replace(".mp4", "-stacked.jpg")
   else:
      mj['hd_stack'] = sd_stack.replace(".jpg", "-HD-meteor.jpg")
      #exit()
      if cfe(mj['hd_stack']) == 0:
         tmp = cv2.imread(sd_stack)
         hd_stack_img = cv2.resize(tmp, (1920,1080))
         cv2.imwrite(mj['hd_stack'], hd_stack_img)
   if mj['hd_trim'] == 0 :
      mj['hd_trim'] = mj['sd_video_file'] 
      hd_trim = mj['sd_video_file']

   check_make_half_stack(mj['sd_stack'], mj['hd_stack'], mj)
   mj['half_stack'] = mj['half_stack'].replace("-stacked", "")
   half_stack_file = mj['half_stack']
   hd_stack_file = mj['hd_stack']


   if cfe(hd_stack_file) == 0:
      stack_img = cv2.imread(sd_stack)
      hd_stack_file = sd_stack.replace("-stacked.png", "-HD-stacked.jpg")
      hd_stack_img = cv2.resize(stack_img, (1920,1080))
   hd_stack = hd_stack_file

   if "cal_params_file" not in mj:
      if hd_stack_file == 0:
         cal_files = get_active_cal_file(sd_stack)
      else:
         cal_files = get_active_cal_file(hd_stack_file)
      if cal_files is not None:
         cal_params_file = cal_files[0][0]
      if form_cal_params_file is not None:
         cal_params_file = form_cal_params_file

      cal_select = make_cal_select(cal_files,sd_video_file,cal_params_file)

      mj['cal_params_file']  = cal_params_file
      if cal_params_file is not None:
         az_grid_file = cal_params_file.replace("-calparams.json", "-azgrid-half.jpg")
   else:
      cal_params_file = mj['cal_params_file']
      az_grid_file = cal_params_file.replace("-calparams.json", "-azgrid-half.jpg")
  
   # find new? 
   if cal_params_file is not None:
      if cfe(cal_params_file) == 1: 
         cal_params = load_json_file(cal_params_file)

   if reduced == 1: 
      meteor_js = reduce_meteor_js(meteor_reduced)
   else:
      meteor_js = ""


   if reduced == 1:
      template = template.replace("{EVENT_START_TIME}", meteor_reduced['event_start_time'])
      template = template.replace("{EVENT_DURATION}", str(meteor_reduced['event_duration']))
      template = template.replace("{EVENT_MAGNITUDE}", str(meteor_reduced['peak_magnitude']))
      if "solution" in meteor_reduced:
         template = template.replace("{EVENT_OBS_TOTAL}", meteor_reduced['solution']['obs_total'])
      else:
         template = template.replace("{EVENT_OBS_TOTAL}", "1 Station 1 Cam")

   else:
      template = template.replace("{EVENT_START_TIME}", "<i>pending reduction</i>")
      template = template.replace("{EVENT_DURATION}", "<i>pending reduction</i>")
      template = template.replace("{EVENT_MAGNITUDE}", "<i>pending reduction</i>")

   if "stacked-stacked" in hd_stack:
      hd_stack = hd_stack.replace("-stacked-stacked", "-stacked")


   if reduced == 1:
      sd_video_file = meteor_reduced['sd_video_file']
      hd_video_file = meteor_reduced['hd_video_file']
      if "stacked" not in meteor_reduced['sd_stack']:
         sd_stack = meteor_reduced['sd_stack'].replace(".jpg", "-stacked.jpg")
      if "stacked" not in meteor_reduced['hd_stack']:
         hd_stack = meteor_reduced['hd_stack'].replace(".jpg", "-stacked.jpg")
      template = template.replace("{SD_VIDEO}", sd_video_file)
      template = template.replace("{HD_VIDEO}", str(hd_video_file))
      template = template.replace("{SD_STACK}", sd_stack)
      template = template.replace("{HD_STACK}", hd_stack)
   else:
      hd_video_file = mj['hd_trim']
   if cal_params_file is not None:
      template = template.replace("{CAL_PARAMS_FILE}", cal_params_file)
   

   # We test if an important file is missing
   errors = ""
   if(cfe(hd_trim)==0):
 

      if(cfe(hd_video_file)):

         # We automatically fix the issue
         fix_hd_vid_real_inline(hd_video_file,video_file,meteor_json_file) 
         #errors += "<p>HD TRIM - <b><a href='" +  hd_trim + "'> " +  hd_trim + "</a></b> as defined in the JSON is missing. <br> Do you want to replace it with: <a href='" +  hd_video_file + "'><b> " +  hd_video_file + "</b></a>?<br><a href='/pycgi/webUI.py?cmd=fix_hd_vid&json_file="+meteor_json_file+"&hd_video_file="+hd_video_file+"&cur_video_file="+video_file+"' class='btn btn-primary mt-2'>FIX THIS</a></p>"
      else:
         #print("<br>===> FAILED")
         errors += "<p>HD TRIM - <b><a href='" +  hd_trim + "'> " +  hd_trim + "</a></b> as defined in the JSON is missing.</p>"
         errors += "<p>HD TRIM - <b><a href='" +  hd_video_file + "'> " +  hd_video_file + "</a></b> as guessed by the program is missing too.</p>"

   if(cfe(video_file)==0):
      errors += "<p>SD VIDEO - <b><a href='" +  video_file + "'> " +  video_file + "</a></b> as defined in the JSON is missing.</p>"
   
   if(cfe(meteor_json_file)==0):
      errors += "<p>JSON FILE - <b><a href='" +  meteor_json_file + "'> " +  meteor_json_file + "</a></b> as defined in the JSON is missing.</p>"

   if(errors!=''):
      print("<div id='main_container' class='container mt-4 lg-l pt-4'><div class='alert alert-danger'>"+errors+"</div></div>")
      
   # MIKE
   if "archive_file" not in mj:
      move_to_archive_link = "<a class='btn btn-primary d-block' href='/pycgi/webUI.py?cmd=move_to_archive&video_file=" + hd_trim + "&sd_video=" + video_file + "&json_file=" + meteor_json_file + "'>Move to Archive</a>"
      template = template.replace("{ARCHIVE_LINK}", move_to_archive_link)
   else:
      archive_file = mj['archive_file']
      view_arc_link_and_back = "<a class='btn btn-primary d-block mb-2' href='/pycgi/webUI.py?cmd=reduce2&video_file=" + archive_file + "'>View Archived Meteor</a>"
      view_arc_link_and_back += "<a class='btn btn-primary d-block' href='/pycgi/webUI.py?cmd=move_to_archive&video_file=" + hd_trim + "&sd_video=" + video_file + "&json_file=" + meteor_json_file + "'>Replace Archived Meteor</a> "
      template = template.replace("{ARCHIVE_LINK}", view_arc_link_and_back)

   jsid = video_file.split("/")[-1]
   jsid = jsid.replace("_", "")
   jsid = jsid.replace(".mp4", "")

   template = template.replace("{JSID}", jsid)


   template = template.replace("{HD_STACK}", hd_stack)
   template = template.replace("{SD_STACK}", sd_stack)
   template = template.replace("{SD_VIDEO}", sd_video_file)
   template = template.replace("{HD_VIDEO}", str(hd_video_file))
   template = template.replace("{METEOR_JSON_FILE}", meteor_json_file)
   template = template.replace("{METEOR_JSON}", meteor_json_file)
   template = template.replace("{event_start_time}", meteor_json_file)
   template = template.replace("{HALF_STACK}", half_stack_file)

   if cal_params_file is not None:
      template = template.replace("{SELECTED_CAL_PARAMS_FILE}", cal_params_file)

   #Name of the option in the <select>
   if cal_params_file is not None:
      template = template.replace("{SELECTED_CAL_PARAMS_FILE_NAME}", get_meteor_date(cal_params_file))

   prefix = sd_video_file.replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")

   # STARS TABLE

   stars_table = """ <table class="table table-dark table-striped table-hover td-al-m"><thead>
         <tr>
            <th>Name</th><th>mag</th><th>Cat RA/Dec</th><th>Res &deg;</th><th>Res. Pixels</th>
         </tr>
      </thead>
      <tbody>
   """
   if reduced == 1:
      if "cal_params" in meteor_reduced:
         if "cat_image_stars" in meteor_reduced['cal_params']:
            for star in meteor_reduced['cal_params']['cat_image_stars']:
               (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) = star
               good_name =  dcname.encode("ascii","xmlcharrefreplace")

               good_name = str(good_name).replace("b'", "")
               good_name = str(good_name).replace("'", "")
               enc_name = good_name 

               ra_dec = str(ra) + "/" + str(dec)
               stars_table = stars_table + """ 
               <tr>
                  <td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td><td>{:s}</td>
               </tr>
               """.format(str(enc_name), str(mag), str(ra_dec), str(match_dist), str(cat_dist))

            stars_table  + stars_table + "</tbody> </table>"
         else:
            fin_a_cal = 1
   if reduced == 0:
      meteor_reduced = {}
      meteor_reduced['meteor_frame_data'] = []
   stars_table = stars_table + "</tbody></table>";
   # RED TABLE
   # <button id="fix_frames" class="btn btn-primary btn-sm btn-tb-spec">Update/Fix Frames</button>
   # Thumb	#	Time	X/Y - W/H	Max PX	RA/DEC	AZ/EL
   table_top = """
   <table class="table table-dark table-striped table-hover td-al-m mb-2 pr-5" >
      <thead>
         <tr>
            <th></th><th></th><th>#</th><th>Time</th><th>RA/DEC</th><th>AZ/EL</th><th>X/Y</th><th>w/h</th><th>Max px</th><th colspan="4"></th>
         </tr>
      </thead>
   """
   table_bottom = """
   <tbody></tbody>
   </table>
   """

   red_table = table_top 
   for frame_data in meteor_reduced['meteor_frame_data']:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      row_id = "tr" + str(fn)
      xy_wh = str(hd_x) + "," + str(hd_y) + " " + str(w) + "," + str(h)
      az_el = str(az) + "/" + str(el) 
      ra_dec = str(ra) + "/" + str(dec) 


      fr_id = "fr_row" + str(fn)
      cmp_img_url = prefix  + str(fn) + ".jpg"
      cmp_img = "<img alt=\"" + str(fn) + "\" width=\"50\" height=\"50\" src=" + cmp_img_url + " class=\"img-fluid select_meteor\">"

      del_frame_link = "javascript:del_frame('" + str(fn) + "','" + meteor_json_file +"')"


      red_table2 = red_table + """
      <tr id="fr_{:s}">
        <td>{:s}</td>
        <td>{:s}</td>
        <td>{:s}</td>
        <td>{:s}</td>
        <td>{:s}</td>
        <td>{:s}</td>
        <td>{:s}</td>
        <td><a class="btn btn-danger btn-sm delete_frame"><i class="icon-delete"></i></a></td>
        <td><a class="btn btn-success btn-sm select_meteor"><i class="icon-target"></i></a></td>
      </tr>
   """.format(str(fn), str(cmp_img ), str(fn), str(frame_time),str(xy_wh), str(max_px),str(ra_dec),str(az_el))
   red_table = red_table + table_bottom 
   frame_javascript = ""

   template = template.replace("{%RED_TABLE%}", red_table)
   template = template.replace("{%STAR_TABLE%}", stars_table)
 
   light_curve_file = sd_video_file.replace('.mp4','-lightcurve.jpg')
   if(isfile(light_curve_file)):
      template = template.replace("{%LIGHT_CURVE%}", '<a class="d-block nop text-center img-link-n" href="'+light_curve_file+'"><img  src="'+light_curve_file+'" class="mt-2 img-fluid"></a>')
   else:
      template = template.replace("{%LIGHT_CURVE%}", "<div class='alert error mt-4'>Light Curve file not found</div>")

   
   #template = template.replace("{%RED_TABLE%}", "")
   #template = template.replace("{%STAR_TABLE%}", "")
   cal_params_file = ""
   #template = template.replace("{%CAL_PARAMS_OPTIONS%}", cal_params_options)
   template = template.replace("{%SELECTED_CAL_PARAMS_FILE%}", cal_params_file)

   print(template)
   # canvas image
   # side info
   # stars info table
   # frame data table
   # other stuff
   #half_stack_file = ""
   az_grid_file = ""

   if reduced == 1:
      #bottom_html = bottom_html + frame_javascript
      ejs = frame_javascript
   else:
      ejs = ""


   rand = str(time.time())
   js_html = ejs + """
   <script>
       var grid_by_default = false;
       var my_image = '""" + half_stack_file + """'
       var hd_stack_file = '""" + hd_stack_file + """'
       var az_grid_file = '""" + az_grid_file + """'
       var meteor_json_file = '""" + meteor_json_file + """'
       var main_vid = '""" + sd_video_file + """'
       var stars = [];
     </script>
   """

   if(meteor_reduced_file is not None):
      js_html += "<script>var json_reduced = '" + meteor_reduced_file + "'</script>"

   return(js_html)

def reduce_meteor(json_conf,form):
   form_cal_params_file = form.getvalue("cal_params_file")
   hdm_x = 2.7272727272727272
   hdm_y = 1.875
   video_file = form.getvalue("video_file")
   meteor_json_file = video_file.replace(".mp4", ".json") 
   meteor_reduced_file = meteor_json_file.replace(".json", "-reduced.json")




   if cfe(meteor_reduced_file) == 1:
      meteor_reduced = load_json_file(meteor_reduced_file)
      reduced = 1
      if "crop_box" not in meteor_reduced:
         (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_reduced['meteor_frame_data'])
         meteor_reduced['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y)
      frame_table, frame_javascript = make_frame_table(meteor_reduced,meteor_json_file)

   else:
      frame_table = ""
      reduced = 0
   mj = load_json_file(meteor_json_file)
   meteor_obj = get_meteor_object(mj)
   if reduced == 1:
      if "cal_params" in meteor_reduced:
         if "astro_res_err" in meteor_reduced['cal_params']:
            astro_res_error = meteor_reduced['cal_params']['astro_res_err']
         if "cat_image_stars" in meteor_reduced['cal_params']:
            cat_image_stars = meteor_reduced['cal_params']['cat_image_stars']
            total_stars = len(cat_image_stars)

   mr = meteor_reduced
   if "/mnt/ams2/meteors" not in mr['sd_video_file']:
      el = mr['sd_video_file'].split("/")
      sd_fn = el[-1]
      day_dir = el[-3]
      mr['sd_video_file'] = mr['sd_video_file'].replace("/mnt/ams2/SD/proc2", "/mnt/ams2/meteors")
      mr['sd_video_file'] = mr['sd_video_file'].replace("/passed", "")
      if mr['hd_file'] != 0 and mr['hd_file'] != None:
         mr['hd_file'] = mr['hd_file'].replace("/mnt/ams2/HD", "/mnt/ams2/meteors/" + day_dir)
         mr['hd_trim'] = mr['hd_trim'].replace("/mnt/ams2/HD", "/mnt/ams2/meteors/" + day_dir)
         mr['hd_crop_file'] = mr['hd_crop_file'].replace("/mnt/ams2/HD", "/mnt/ams2/meteors/" + day_dir)
         mr['hd_crop_file_stack'] = mr['hd_crop_file'].replace(".mp4", "-stacked.jpg")
         mr['hd_trim_stack'] = mr['hd_trim'].replace(".mp4", "-stacked.jpg")
      else:
         mr['hd_file'] = 0
         mr['hd_trim'] = 0
         mr['hd_crop_file'] = 0
         mr['hd_crop_file_stack'] = 0
         mr['hd_trim_stack'] = 0
      mr['sd_stack'] = mj['sd_video_file'].replace(".mp4", "-stacked.jpg")
     
      mr['half_stack'] = mj['sd_stack'].replace("-stacked.jpg", "-half-stack.jpg")
   sd_video_file = mr['sd_video_file']
   sd_stack = mr['sd_stack']

   mr['sd_stack'] = sd_stack.replace(".png", "-stacked.png")
   mr['hd_stack'] = sd_stack.replace(".png", "-stacked.png")

   print(mr['sd_stack'], mr['hd_stack'])  
 
   check_make_half_stack(mr['sd_stack'], mr['hd_stack'], mr)
   hd_stack_file = mr['hd_stack']
   half_stack_file = hd_stack_file.replace("-stacked","half-stacked")
   if hd_stack_file == 0:
      stack_img = cv2.imread(sd_stack)
      hd_stack_file = sd_stack.replace("-stacked.png", "-HD-stacked.png")
      hd_stack_img = cv2.resize(stack_img, (1920,1080))
     


   meteor_start_frame = meteor_obj['history'][0][0]
   meteor_end_frame = meteor_obj['history'][-1][0]
   elp_frames = meteor_end_frame - meteor_start_frame -1 
   elp_dur = elp_frames / 25
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(meteor_json_file)
   start_clip_time_str = str(f_datetime)
   el = sd_video_file.split("-trim")
   min_file = el[0] + ".mp4"
   ttt = el[1].split(".")
   trim_num = int(ttt[0])
   extra_sec = trim_num / 25 
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)

   extra_meteor_sec = meteor_start_frame / 25
   start_meteor_frame_time = start_trim_frame_time + datetime.timedelta(0,extra_meteor_sec)
   start_meteor_frame_time_str = start_meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
   
   start_x = int((meteor_obj['history'][0][1] + (meteor_obj['history'][0][5])) * hdm_x)/2
   start_y = int((meteor_obj['history'][0][2] + (meteor_obj['history'][0][6])) * hdm_y)/2

   end_x = int((meteor_obj['history'][-1][1] + (meteor_obj['history'][-1][5])/2) * hdm_x)/2
   end_y = int((meteor_obj['history'][-1][2] + (meteor_obj['history'][-1][6])/2) * hdm_y)/2



   if "cal_params_file" not in mj:
      if hd_stack_file == 0:
         cal_files = get_active_cal_file(sd_stack)
      else:
         cal_files = get_active_cal_file(hd_stack_file)
      cal_params_file = cal_files[0][0]
      if form_cal_params_file is not None:
         cal_params_file = form_cal_params_file

      cal_select = make_cal_select(cal_files,sd_video_file,cal_params_file)
   
      #mj['cal_params_file']  = cal_params_file
      az_grid_file = cal_params_file.replace("-calparams.json", "-azgrid-half.png")
   else:
      cal_params_file = mj['cal_params_file'] 
      az_grid_file = cal_params_file.replace("-calparams.json", "-azgrid-half.png")
   cal_params = load_json_file(cal_params_file)
   if reduced == 0:
      new_x, new_y, start_ra ,start_dec , start_az, start_el= XYtoRADec(start_x*2,start_y*2,cal_params_file,cal_params,json_conf)
      new_x, new_y, end_ra ,end_dec , end_az, end_el= XYtoRADec(end_x*2,end_y*2,cal_params_file,cal_params,json_conf)
   else:
      start_ra = meteor_reduced['meteor_frame_data'][0][7]
      start_dec = meteor_reduced['meteor_frame_data'][0][8]
      end_ra = meteor_reduced['meteor_frame_data'][-1][7]
      end_dec = meteor_reduced['meteor_frame_data'][-1][8]
      start_az = meteor_reduced['meteor_frame_data'][0][9]
      start_el = meteor_reduced['meteor_frame_data'][0][10]
      end_az = meteor_reduced['meteor_frame_data'][-1][9]
      end_el = meteor_reduced['meteor_frame_data'][-1][10]

   #print("<h1>Reduce Meteor</h1>")


   extra_js = "<script>var stars = []</script>"


   #bottom_html = "<script>window.onload = show_image('" + half_stack_file + "','" + az_grid_file + "',1,1);"
   bottom_html = "<script>"
   bottom_html = bottom_html + "function play_video(src_url) { $('#ex1').modal(); $('#v1').attr(\"src\", src_url);} </script>"

   if reduced == 1:
      #bottom_html = bottom_html + frame_javascript
      ejs = frame_javascript
   else:
      ejs = ""

   js_html = ejs + """
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
      <img id='""" + half_stack_file + """' id='my_image'>
     </div> """

   meteor_reduced['half_stack'] = half_stack_file
   mj = mr

#   """.format(hd_stack_file)

   canvas_html = """
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
      <div style="float:left">
      <div>
<!--
<div id="loading" >
  <p><img src="loading.gif" /> Please Wait</p>
</div>
-->
<span style="padding: 5px"> Calibration File</span><br>
   """ + cal_select + """</div>
<!--
<span style="padding: 5px"> <b>Meteor Info</b></span><br>
<span style="padding: 5px"> Start Clip Time: """ + start_clip_time_str + """</span><br>
<span style="padding: 5px"> Trim Start Frame Num: """ + str(trim_num) + """ </span><br>
<span style="padding: 5px"> Meteor Start/End Frame: """ + str(meteor_start_frame) + "/" + str(meteor_end_frame) + """ </span><br>
<span style="padding: 5px"> Meteor Start Time: """ + str(start_meteor_frame_time_str) + """</span><br>
<span style="padding: 5px"> Duration: """ + str(elp_dur) + "seconds / " + str(elp_frames) + """ frames</span><br>
-->
      """
   canvas_html = canvas_html + """

<!--
<span style="padding: 5px"> <B>SD Reduction Values</B></span><br>

<span style="padding: 5px"> Start X/Y: """ + str(start_x) + "/" + str(start_y) + """</span><br>
<span style="padding: 5px"> End X/Y: """ + str(end_x) + "/" + str(end_y) + """</span><br>
<span style="padding: 5px"> Start RA/DEC: """ + str(start_ra)[0:5] + "/" + str(start_dec)[0:5] + """</span><br>
<span style="padding: 5px"> End RA/DEC: """ + str(end_ra)[0:5] + "/" + str(end_dec)[0:5] + """</span><br>
<span style="padding: 5px"> Start AZ/EL: """ + str(start_az)[0:5] + "/" + str(start_el)[0:5] + """</span><br>
<span style="padding: 5px"> End AZ/EL: """ + str(end_az)[0:5] + "/" + str(end_el)[0:5] + """</span><br>
<span style="padding: 5px"> <a target='_blank' href=\"webUI.py?cmd=man_reduce&file=""" + mj['sd_stack']+ "&cal_params_file=" + cal_params_file +  """\">Manually Reduce</a></span><br>
<span style="padding: 5px"> <a target='_blank' href=\"webUI.py?cmd=clone_cal&file=""" + mj['sd_stack']+ "&cal_params_file=" + cal_params_file +  """\">Clone Cal</a></span><br>
-->
<span style="padding: 5px"> <B>Media Files</B></span><br>
<span style="padding: 5px"> <a target='_blank' href=javascript:play_video('""" + mj['sd_video_file']+ """')>SD Video</a></span><br>


<span style="padding: 5px"> <a target='_blank' href=\"javascript:show_image('""" + mr['sd_stack']+ """',1.3636,.9375)\">SD Image</a></span><br>
   """
   if mj['hd_stack'] != 0 and mj['hd_stack'] != None:
      canvas_html = canvas_html + """
<span style="padding: 5px"> <a target='_blank' href=javascript:play_video('""" + mj['hd_stack']+ """')>HD Video</a></span><br>
<span style="padding: 5px"> <a target='_blank' href= """ + mj['hd_stack']+ """>HD Image</a></span><br>
<span style="padding: 5px"> <a target='_blank' href= """ + mj['half_stack']+ """>Half Stack Image</a></span><br>
      
      """

   canvas_html = canvas_html + """
      </div>
      <div style="clear: both"></div>
   """

   canvas_html = canvas_html + """
      <div>
      <div style="float: left; position: relative; height: 50px; width: 50px" id="myresult" class="img-zoom-result"> </div>

      <div style="float: left" id=action_buttons>
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="  Show Image    " onclick="javascript:show_meteor_image('""" + half_stack_file + """')">
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="  Show AZ Grid  " onclick="javascript:show_az_grid('""" + half_stack_file + "','" + az_grid_file + """')">
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="Show Catalog Stars" onclick="javascript:show_cat_stars('""" + video_file + "','" + hd_stack_file + "','" + cal_params_file + """', 'nopick')">
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="  Reduce Meteor " onclick="javascript:reduce_meteor_ajax('""" + meteor_json_file + "','" + cal_params_file + """')">
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="  Minimize FOV Vars  " onclick="javascript:custom_fit('""" + meteor_json_file + "','" + hd_stack_file + "','" + cal_params_file + """')">
      </div>


      <div style="clear: both"></div>

      <div style="float:left" id=info_panel>Info</div>
      <div style="clear: both"></div>
      <div style="float:left" id=info_panel>
<!--
<a href="javascript:show_hide_div('adv_func')">Advanced Functions</a> - 
<a href="javascript:show_hide_div('problems')">Fix Problems</a></div>
-->
</div>

      <div style="float:left; display: none;" id=adv_func>
<br>
      <li><a href="javascript:show_hide_div('adv_func')">Calibrate This Image</a> 
      <li><a href="javascript:show_hide_div('adv_func')">Re-Fit This Image</a>
      <li><a href="javascript:show_hide_div('adv_func')">Re-stack SD</a>
      <li><a href="javascript:show_hide_div('adv_func')">Re-stack HD</a>
      <li><a href="javascript:show_hide_div('adv_func')">Re-Trim SD</a>
      <li><a href="javascript:show_hide_div('adv_func')">Re-Trim HD</a>
      <li><a href="javascript:show_hide_div('adv_func')">Make HD Reduce Video </a>
      <li><a href="javascript:show_hide_div('adv_func')">Make SD Reduce Video </a>
      <li><a href="javascript:show_hide_div('adv_func')">Submit To AMS</a>
      <li><a href="javascript:show_hide_div('adv_func')">Check For Other Observations</a>
      <li><a href="javascript:show_hide_div('adv_func')">Remaster Video</a>
      </div>
      <div style="float:left; display: none;" id=problems>
<br>
<input type="checkbox">HD trim is bad<br>
<input type="checkbox">Meteor Missing Points<br>
<input type="checkbox">Meteor Mis-identified<br>
<input type="checkbox">Meteor Not Identified<br>
<form>

</form>

</a></div>
  
      <div style="clear: both"></div>
      <div style="" id=meteor_frame_list>""" + frame_table + """</div>
      <div style="" id=star_list>""" +  """</div>
      </div>
   """
   #print(stack_file)

   extra_js = extra_js + """

<script src="./dist/js/amscam.min.js?a"></script>
<script src="./src/js/mikes/freecal-ajax.js?a"></script>
<script src="./src/js/plugins/fabric.js?a"></script>
<script src="./src/js/mikes/freecal-canvas.js?a"></script>


   """ 
   print(canvas_html)
   print(js_html)
   print(extra_js)

   print("<img id='half_stack_file' style='display: none' src='" + half_stack_file + "'> <br>")
   print("<img id='az_grid_file' style='display: none' src='" + az_grid_file + "'> <br>")
   print("<img id='meteor_img' style='display: none' src='" + half_stack_file + "'> <br>")

  


   return(bottom_html)


def get_active_cal_file(input_file):
   #print("INPUT FILE", input_file) 
   if "png" in input_file:
      input_file = input_file.replace(".png", ".mp4")
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)

   # find all cal files from his cam for the same night
   matches = find_matching_cal_files(cam_id, f_datetime)
   #print("MATCHED:", matches)
   if len(matches) > 0: 
      return(matches)
   else:
      return(None)

def find_matching_cal_files(cam_id, capture_date):
   matches = []
   all_files = glob.glob("/mnt/ams2/cal/freecal/*")
   for file in all_files:
      if cam_id in file :
         el = file.split("/")
         fn = el[-1]
         cal_p_file = file  + "/" + fn + "-stacked-calparams.json"
         if cfe(cal_p_file) == 1:
            matches.append(cal_p_file)
         else:
            cal_p_file = file  + "/" + fn + "-calparams.json"
         if cfe(cal_p_file) == 1:
            matches.append(cal_p_file)
  
   td_sorted_matches = [] 

   for match in matches:
      (t_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(match)
      tdiff = abs((capture_date-t_datetime).total_seconds())
      td_sorted_matches.append((match,f_date_str,tdiff))
   temp = sorted(td_sorted_matches, key=lambda x: x[2], reverse=False)
   return(temp)


def save_add_stars_to_fit_pool(json_conf,form):
   hd_stack_file = form.getvalue("hd_stack_file")
   half_stack_file = hd_stack_file.replace("-stacked.png", "-half-stack.png")
   #/mnt/ams2/HD/2019_02_17_09_43_36_000_010002-stacked-calparams.json
   cal_params_file = hd_stack_file.replace(".png", "-calparams.json")
   cmd1 = "cp " + hd_stack_file + " /mnt/ams2/cal/fit_pool/"
   cmd2 = "cp " + half_stack_file + " /mnt/ams2/cal/fit_pool/"
   cmd3 = "cp " + cal_params_file + " /mnt/ams2/cal/fit_pool/"
   os.system(cmd1)
   os.system(cmd2)
   os.system(cmd3)
   status = "success" 
   message = "Stars saved to the fit pool." 
   message = cmd1 + " " + cmd2 + " " + cmd3
   debug = ""
   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "message": """ + "\"" + message + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """
   print(response)

def pin_point_stars(image, points):   
   star_points = []
   for x,y in points:
      x,y = int(x),int(y)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      cnt_img = image[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      try:
         max_pnt,max_val,min_val = cnt_max_px(cnt_img)
         mx,my = max_pnt
         mx = mx - 15
         my = my - 15
         x = x + mx
         y = y + my
         star_points.append((x,y))
      except:
         missed_star = 1
   return(star_points)


def add_stars_to_fit_pool(json_conf,form):
   input_file = form.getvalue("input_file")
   cal_files = get_active_cal_file(input_file)
   cal_params_file = cal_files[0][0]
   cal_hd_stack_file = cal_params_file.replace("-calparams.json", ".png")
   #print(cal_params_file, "<BR>")
   #print(cal_hd_stack_file, "<BR>")
   hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(input_file, 250, 10, 0)
   if hd_file is None:
      print("No HD file found. This feature requires HD files. Try doing this on a more recent day. HD files are kept for 3 days total.") 
      sd_stack_file = input_file.replace(".mp4", "-stacked.png")
      el = sd_stack_file.split("/")
      fn = el[-1]
      dir = sd_stack_file.replace(fn, "")
      sd_stack_file = dir + "images/" + fn

      print(sd_stack_file)
      sd_img = cv2.imread(sd_stack_file, 0)
      hd_stack_img = cv2.resize(sd_img, (1920,1080))
      half_stack_img = cv2.resize(sd_img, (960,540))
      half_stack_file = sd_stack_file.replace("-stacked.png", "-half-stack.png")
      hd_stack_file = sd_stack_file
      cv2.imwrite(half_stack_file, half_stack_img)
      cv2.imwrite(hd_stack_file, hd_stack_img)
      this_cal_params_file = hd_stack_file.replace(".png", "-calparams.json")
      if cfe(this_cal_params_file) == 1:
         this_cal_params = load_json_file(this_cal_params_file)
      else:
         this_cal_params = []

 
   else:
      frames = load_video_frames(hd_file, json_conf, 25)
      hd_stack_file = hd_file.replace(".mp4", "-stacked.png")

      this_cal_params_file = hd_stack_file.replace(".png", "-calparams.json")
      if cfe(this_cal_params_file) == 1:
         this_cal_params = load_json_file(this_cal_params_file)
      else:
         this_cal_params = []

      tmp_file, stack_img = stack_frames(frames, hd_stack_file, 0)
      hd_stack_file = tmp_file
      half_stack_file = tmp_file.replace("-stacked.png", "-half-stack.png")
      half_stack_img = cv2.resize(stack_img, (0,0),fx=.5, fy=.5)
      cv2.imwrite(half_stack_file, half_stack_img)

      #print("<img src=" + half_stack_file + ">", half_stack_file)


   print("<h1>Add Stars To Fit Pool</h1>")
   if cfe(cal_params_file) == 1:
      cal_params = load_json_file(cal_params_file)
      if "user_stars" in this_cal_params:
         user_stars = this_cal_params['user_stars']
      else:
         user_stars = []
      extra_js = """
         <script>
         """
      extra_js = extra_js + "var stars = ["

      c = 0
      for temp in user_stars:
         sx,sy = temp
         #sx,sy = int(sx),int(sy)
         if c > 0:
            extra_js = extra_js + ","
         extra_js=extra_js+ "[" + str(sx) + "," +str(sy) +"]"
         c = c + 1
      extra_js = extra_js + "]"
      extra_js = extra_js + """
         </script>
   """
   else:
      extra_js = "<script>var stars = []</script>"



   js_html = """

   <script>
      var my_image = '""" + half_stack_file + """';
      var hd_stack_file = '""" + hd_stack_file + """';
      var stars = [];
   </script>


   """.format(hd_stack_file)
   canvas_html = """
      <p>An HD source file was not found for this time period. No worries, we can still calibrate from an SD image, but first we need to pick the stars so we can upscale the image. Select as many stars as possible from the image below and then click the "Upscale To HD" button.</p>
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
      <div style="float:left"><div style="position: relative; height: 50px; width: 50px" id="myresult" class="img-zoom-result"> </div></div>
      <div style="clear: both"></div>
   """

   canvas_html = canvas_html + """
      <div style="float:left" id=info_panel>Info: </div>

      <div style="clear: both"></div>

      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="Show Catalog Stars" onclick="javascript:show_cat_stars('""" + hd_stack_file + "','" + cal_params_file + """', 'pick')">
         <input type=button id="button1" value="Add Stars To Fit Pool" onclick="javascript:add_to_fit_pool('""" + hd_stack_file + """')">
      </div>
      <div id=star_list>star_list: </div>
       <BR><BR>
   """
   #print(stack_file)

   print(canvas_html)
   print(js_html)
   print(extra_js)


def delete_cal(json_conf, form):
   hd_stack_file = form.getvalue("hd_stack_file")
   if cfe(hd_stack_file) == 1 and "-stacked.png" in hd_stack_file:
      el = hd_stack_file.split("/")
      job = el[-2]
      if len(job) < 10:
         status = "error"
         debug = "bad file"
      else:
         job_dir = "/mnt/ams2/cal/freecal/" + job 
         cmd = "rm -rf " + job_dir 
         os.system(cmd)
         status = "deleted"
         debug = cmd
   else:
      status = "error"
      debug = "stack file not found"
   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """
   print(response)

def fit_field(json_conf, form):

   hd_stack_file = form.getvalue("hd_stack_file")
   cal_params_file = hd_stack_file.replace(".png", "-calparams.json")
   cal_params = load_json_file(cal_params_file)
   override = form.getvalue("override")

   status = "" 
   debug = "" 
   if "x_fun" in cal_params:
      status = "done"
      x_fun = cal_params['x_fun']
      y_fun = cal_params['y_fun']
      x_fun_fwd = cal_params['x_fun_fwd']
      y_fun_fwd = cal_params['y_fun_fwd']
   running = check_running("fitPairs.py")
   if running == 1:
      status = "running" 
      message = "Fit process is running"
   elif status ==  "done" and override is None:
      message = "The fit proceedure has completed with residual error of {:f}/{:f} x/y pixels and {:f}/{:f} x/y degrees".format(x_fun,y_fun,x_fun_fwd,y_fun_fwd);
      # todo/future check if it already ran and give user option to re-run or
      # cancel. 
   else:
      cmd = "cd /home/ams/amscams/pythonv2/; ./fitPairs.py " + cal_params_file + "> /dev/null & 2>&1" 
      os.system(cmd)
      debug = cmd
      status = "started"
      message = "Fit process started"

   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "debug": """ + "\"" + debug + "\"," + """ 
      "message": """ + "\"" + message+ "\"" + """ 
   }
   """
   print(response)


def check_solve_status(json_conf,form):
   hd_stack_file = form.getvalue("hd_stack_file")

   debug = "DEBUG: "
   if "-stacked.png" in hd_stack_file:
      # CASE 1
      debug = debug + "case=1;"
      solved_file = hd_stack_file.replace(".png", ".solved")
      grid_file = solved_file.replace(".solved", "-grid.png")
      obj_file = solved_file.replace(".solved", "-objs.png")

   
   #solved_file = grid_file

 

   #print(solved_file)
   running = check_running("solve-field")
   status = ""
   if cfe(obj_file) == 0:
      status = "new"
   if running > 0:
      status = "running"
   elif running == 0 and cfe(solved_file) == 1:
      status = "success" 
   elif running == 0 and cfe(obj_file) == 0:
      status = "new"
   elif running == 0 and cfe(solved_file) == 0:
      status = "failed"
   #status = solved_file 
   debug = debug + " hd_stack_file=" + hd_stack_file + ";" + "solved_file=" + solved_file + ";" + "status=" + status
   
   if cfe(grid_file) == 1:
      tmp_img = cv2.imread(grid_file)
      tmp_img_tn = cv2.resize(tmp_img, (0,0),fx=.5, fy=.5)
      grid_file_half = grid_file.replace(".png", "-half.png")
      cv2.imwrite(grid_file_half, tmp_img_tn)
   else:
      grid_file_half = ""

   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "grid_file": """ + "\"" + grid_file_half + "\"," + """ 
      "solved_file": """ + "\"" + solved_file + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """

   print(response)



def solve_field(json_conf, form):

   hd_stack_file = form.getvalue("hd_stack_file")
   fn,tdir = get_hd_filenames(hd_stack_file)
   plate_file = hd_stack_file.replace("-stacked.png", "-stacked.jpg")

   ff_plate_file = plate_file.replace("-stacked-an.png", "-stacked-4f.jpg")


   running = check_running("solve-field")
   status = ""
   if running > 0:
      status = "running"
   else:
      cmd = "cd /home/ams/amscams/pythonv2; ./plateSolve.py " + plate_file + " > /mnt/ams2/tmp/plt.txt 2>&1 &"
      #print(cmd)
      #exit()
      os.system(cmd)

   #plate_solve("/mnt/ams2/cal/tmp/" + new_fn, json_conf)
   status = "running" + ff_plate_file
   debug = "DEBUG: hd_stack_file" + hd_stack_file + "; cmd =" + cmd + "; status = " + status
   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """
   print(response)


def cnt_max_px(cnt_img):
   cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)

   return(max_loc, min_val, max_val)

def make_plate_from_points(json_conf, form):
   hd_stack_file = form.getvalue("hd_stack_file")
   hd_stack_img = cv2.imread(hd_stack_file,0)
   shp = hd_stack_img.shape
   ih,iw = shp[0],shp[1]
   sd = 0
   if iw < 1920:
      sd = 1
   
   hdm_x = 2.7272
   hdm_y = 1.875
  
   plate_img = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_file_an = hd_stack_file.replace(".png", "-an.png")
   half_stack_file_an = hd_stack_file.replace("-stacked.png", "-half-stack-an.png")
   #print(half_stack_file_an)
   pin = form.getvalue("points")
   points = []
   temps = pin.split("|")
   for temp in temps:
      if len(temp) > 0:
         (x,y) = temp.split(",")
         x,y = int(float(x)),int(float(y))
         x,y = int(x)+5,int(y)+5
         x,y = x*2,y*2
         points.append((x,y))
   plate_image_4f = np.zeros((ih,iw),dtype=np.uint8)
   hd_stack_img = cv2.imread(hd_stack_file,0);
   hd_stack_img_an = hd_stack_img.copy()
   star_points = []
   for x,y in points:
      x,y = int(x),int(y)
      #cv2.circle(hd_stack_img_an, (int(x),int(y)), 5, (128,128,128), 1)
      y1 = y - 15
      y2 = y + 15
      x1 = x - 15
      x2 = x + 15
      x1,y1,x2,y2= bound_cnt(x,y,iw,ih,15)
      cnt_img = hd_stack_img[y1:y2,x1:x2]
      ch,cw = cnt_img.shape
      max_pnt,max_val,min_val = cnt_max_px(cnt_img) 
      mx,my = max_pnt 
      mx = mx - 15
      my = my - 15
      cy1 = y + my - 15
      cy2 = y + my +15
      cx1 = x + mx -15
      cx2 = x + mx +15
      cx1,cy1,cx2,cy2= bound_cnt(x+mx,y+my,iw,ih)
      if ch > 0 and cw > 0:
         cnt_img = hd_stack_img[cy1:cy2,cx1:cx2]
         bgavg = np.mean(cnt_img)
         cnt_img = clean_star_bg(cnt_img, bgavg + 3)

      #cv2.rectangle(hd_stack_img_an, (x1,y1), (x2,y2), (90, 90, 90), 1)
         cv2.rectangle(hd_stack_img_an, (x+mx-5-15, y+my-5-15), (x+mx+5-15, y+my+5-15), (128, 128, 128), 1)
         cv2.rectangle(hd_stack_img_an, (x+mx-15-15, y+my-15-15), (x+mx+15-15, y+my+15-15), (128, 128, 128), 1)
         star_points.append([x+mx,y+my])
         if abs(cy1- (ih/2)) <= (ih/2)*.8 and abs(cx1- (iw/2)) <= (iw/2)*.8:
            plate_image_4f[cy1:cy2,cx1:cx2] = cnt_img 
            plate_img[cy1:cy2,cx1:cx2] = cnt_img
         else:
            plate_image_4f[cy1:cy2,cx1:cx2] = cnt_img 

   points_json = {}
   points_json['user_stars'] = star_points
   if sd == 1:
      temp_stars = []
      for x,y in star_points:
         x = x * hdm_x
         y = y * hdm_y
         temp.appen((x,y))
      points_json['user_stars'] = temp
      star_points = temp
   points_file = hd_stack_file.replace("-stacked.png", "-user-stars.json")
   save_json_file(points_file,points_json)

   #cv2.imwrite(hd_stack_file_an, hd_stack_img_an)
   ff_file = hd_stack_file_an.replace("-an.png", "-4f.jpg")
   cal_file = hd_stack_file_an.replace("-an.png", ".jpg")
   #print("FF:", ff_file)
   if iw != 1920 and ih != 1080:
      plate_img = cv2.resize(plate_img, (1920,1080))
      plate_image_4f = cv2.resize(plate_image_4f, (1920,1080))
      hd_stack_img_an = cv2.resize(hd_stack_img_an, (1920,1080))
   
   half_stack_img_an = cv2.resize(hd_stack_img_an, (0,0),fx=.5, fy=.5)
   half_stack_plate = cv2.resize(plate_img, (0,0),fx=.5, fy=.5)

   cv2.imwrite(cal_file, plate_img)
   cv2.imwrite(hd_stack_file_an, plate_img)
   cv2.imwrite(ff_file, plate_image_4f)
   #cv2.imwrite(half_stack_file_an, half_stack_img_an)
   cv2.imwrite(half_stack_file_an, half_stack_plate)


   response = """
   {
      "hd_stack_file_an": """ + "\"" + hd_stack_file_an + "\"," + """ 
      "half_stack_file_an": """ + "\"" + half_stack_file_an + "\"," + """
      "stars": """ + "" + str(star_points) + "" + """ 
   }
   """
   print(response)

def get_sd_filenames(sd_video_file):
   el = sd_video_file.split("/")
   fn = el[-1]
   tdir = sd_video_file.replace(fn, "")
   sd_img_dir = tdir + "images/"
   sd_stack = sd_img_dir + fn.replace(".mp4", "-stacked.png")
   return(sd_stack)

def get_hd_filenames(hd_video_file):
   el = hd_video_file.split("/")
   fn = el[-1]
   tdir = hd_video_file.replace(fn, "")
   return(fn,tdir)

def better_parse_file_date(input_file):
   el = input_file.split("/")
   fn = el[-1]
   ddd = fn.split("_")
   Y = ddd[0]
   M = ddd[1]
   D = ddd[2]
   H = ddd[3]
   MM = ddd[4]
   S = ddd[5]
   MS = ddd[6]
   CAM = ddd[7]
   extra = CAM.split("-")
   cam_id = extra[0]
   cam_id = cam_id.replace(".mp4", "")
   f_date_str = Y + "-" + M + "-" + D + " " + H + ":" + MM + ":" + S
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S)

def upscale_2HD(json_conf,form):
   hdm_x = 2.7272
   hdm_y = 1.875
   hd_stack_file = form.getvalue("hd_stack_file")
   half_stack_file = hd_stack_file.replace("-stacked.png", "-half-stack.png")
   points = form.getvalue("points")
   star_points = []
   temps = points.split("|")
   for temp in temps:
      if len(temp) > 0:
         (x,y) = temp.split(",")
         x,y = int(float(x)),int(float(y))
         x,y = int(x)+5,int(y)+5
         x,y = x,y
         star_points.append((x,y))
   points = star_points
   star_points = []

   for temp in points:
      if len(temp) > 0:
         (x,y) = temp
         x,y = int(float(x)),int(float(y))
         #x,y = int(x)+5,int(y)+5
         x,y = x*hdm_x,y*hdm_y
         star_points.append((x,y))

   user_stars = {}
   user_stars['user_stars'] = star_points

   stack_img = cv2.imread(half_stack_file,0)

   hd_image,plate_image,plate_image_4f,star_points = upscale_to_hd(stack_img, points)
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(hd_stack_file)
   base_dir = "/mnt/ams2/cal/freecal/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   base_file = Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   if cfe(base_dir, 1) != 1:
      os.system("mkdir " + base_dir)
   stack_file = base_dir + "/" + base_file + "-stacked.png"
   orig_file = base_dir + "/" + base_file + "-orig.png"
   half_stack_file = base_dir + "/" + base_file + "-half-stack.png"
   plate_file = base_dir + "/" + base_file + ".jpg"
   plate_file_4f = base_dir + "/" + base_file + "-4f.jpg"

   user_star_file = stack_file.replace("-stacked.png", "-user-stars.json")
   save_json_file(user_star_file, user_stars)

   cv2.imwrite(plate_file, plate_image)
   cv2.imwrite(plate_file_4f, plate_image_4f)
   cv2.imwrite(stack_file, hd_image)
   half_stack_img = cv2.resize(hd_image, (960, 540))

   cv2.imwrite(half_stack_file, half_stack_img)
   status = "ok" 
   debug = ""
   response = """
   {
      "status": """ + "\"" + status + "\"," + """ 
      "hd_stack_file": """ + "\"" + stack_file + "\"," + """ 
      "debug": """ + "\"" + debug + "\"" + """ 
   }
   """
   print(response)

def choose_file(json_conf,form):
   input_file = form.getvalue("input_file")
   hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(input_file, 250, 10, 0)   
   if hd_file is None:
      sd_pic_stars(json_conf,form)
   else:
      #<a href=webUI.py?cmd=free_cal&input_file=" + hd_file + "></a>
      print('<div id="main_container" class="container-fluid h-100 mt-4 lg-l">')
      print("<div id='overlay' class='animated'><div class='row h-100 text-center'><div class='col-sm-12 my-auto'><div class='card card-block' style='background:transparent'><iframe style='zoom: 1.8;border:0;margin: 0 auto;' src='./dist/img/anim_logo.svg' width='140' height='90'></iframe><h3>HD File found. Stacking frames. Please wait...</h3></div></div></div></div>")
      print('</div>')
      print("<script>window.location.href='webUI.py?cmd=free_cal&input_file=" + hd_file + "';</script>")




def sd_pic_stars(json_conf,form):

   
   input_file = form.getvalue("input_file")
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)
   base_dir = "/mnt/ams2/cal/freecal/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   base_file = Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   if cfe(base_dir, 1) != 1:
      os.system("mkdir " + base_dir)
   stack_file = base_dir + "/" + base_file + "-stacked.png"
   half_stack_file = base_dir + "/" + base_file + "-half-stack.png"
   orig_file = base_dir + "/" + base_file + "-orig.png"

   if "mp4" in input_file:
      frames = load_video_frames(input_file, json_conf, 1000)
      tmp_file, stack_img = stack_frames(frames, input_file, 1)
      half_stack_img = stack_img 
      shp = half_stack_img.shape
      sh,sw = shp[0], shp[1]
      stack_img = cv2.resize(stack_img, (sw*2, sh*2))
      #half_stack_file = input_file.replace(".mp4", "-half-stack.png") 
      #stack_file = input_file.replace(".mp4", "-stacked.png") 
      #print(stack_file,half_stack_file)
      #stack_img = cv2.resize(stack_img, (1920, 1080))
      #half_stack_img = cv2.resize(stack_img, (960, 540))
      cv2.imwrite(stack_file, stack_img)
      cv2.imwrite(half_stack_file, half_stack_img)
   else:
      stack_file = input_file
      stack_img = cv2.imread(input_file)

   print("<h1>Calibrate SD Image Step #1 - Pick Stars - "+ get_meteor_date(stack_file) +"</h1>")

   js_html = """
   <script>
      var my_image = '""" + half_stack_file + """'
      var hd_stack_file = '""" + stack_file + """'
      var stars = []
   </script>
   """.format(stack_file)

   canvas_html = '<div class="container-fluid"><div class="alert alert-info mt-4 mb-4">An HD source file was not found for this time period. No worries, we can still calibrate from an SD image, but first we need to pick the stars so we can upscale the image.<br/><b>Select as many stars as possible from the image below and then click the "Upscale To HD" button.</b></div></div>'
   
   canvas_html = canvas_html +  '<div id="main_container" class="container-fluid d-flex h-100 mt-4 position-relative">'
   canvas_html = canvas_html +  '<div class="h-100 flex-fixed-canvas"><div class="canvas-container"><canvas id="c" width="960" height="785"></canvas></div></div>' 

   #Right Col
   canvas_html = canvas_html + "<div class='flex-fixed-r-canvas h-100'>"
   canvas_html = canvas_html + """<div class="canvas_zoom_holder mb-3">
                              <div id="canvas_zoom_target"><img alt="" src="./dist/img/target.svg"/></div>
                              <div id="canvas_pointer_info"></div>
                              <div id="canvas_zoom"></div>
                              </div>"""


   canvas_html = canvas_html + """<div class="box">
                <h2>Info</h2>
                <dl class="row mb-0">
                    <dt class="col-6">Start Time</dt>   <dd class="col-6">"""+ get_meteor_date(half_stack_file) +"""</dd>
                </dl> 
            </div>"""

   canvas_html = canvas_html +"<div class='box'><h2 class='mb-4'>Actions</h2>"
   canvas_html = canvas_html +"<a class='btn btn-primary mx-auto d-block mb-2' id='auto_detect_stars'>Auto Star Detect</a>"
   canvas_html = canvas_html +"<a class='btn btn-primary mx-auto d-block mb-2' id='upscale_to_HD'>Upscale to HD</a>"
   canvas_html = canvas_html +"</div>"

   canvas_html = canvas_html +"</div></div>"
   
   canvas_html = canvas_html + """
      
      <div style="float:left"><div style="position: relative; height: 50px; width: 50px" id="myresult" class="img-zoom-result"> </div></div>
      <div id=info_panel>Info: </div>
      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input type=button id="button1" value="Find Stars" onclick="javascript:find_stars('""" + stack_file + """')">
         <input type=button id="button1" value="Upscale To HD" onclick="javascript:upscale_HD('""" + stack_file + """')">
      </div>
      <div id=star_list>star_list: </div>
       <BR><BR>
   """
   #print(stack_file)

   print(canvas_html)
   print(js_html)


def auto_cal(json_conf,form):
   print("<h2>Auto Calibration</h2>")
   input_file = form.getvalue("input_file")
   cal_params_file = input_file.replace(".png", "-calparams.json")
   az_grid = input_file.replace(".png", "-azgrid-half.png")
   if cfe(cal_params_file) == 1:
      cal_params = load_json_file(cal_params_file)
   else:
      print("can't find cal file", cal_params_file)
   print("<img src=" + az_grid + "><BR>");
   print(cal_params_file + "<BR>")
   el = cal_params_file.split("/")
   fn = el[-1]
   day = fn[0:10]
   wild = fn[24:30]

   all_stars_file = "/mnt/ams2/cal/autocal/hdimages/" + day + "/" + day + "-allstars.json"
   print(all_stars_file,"<BR>")
   allstars = load_json_file(all_stars_file)

   image_dir = "/mnt/ams2/cal/autocal/hdimages/" + day + "/*" + wild + "*-hd-stacked.png" 
   images = glob.glob(image_dir)
   for image in images:
      el = image.split("/")
      fn = el[-1]
      key_image = image.replace("cal/autocal/hdimages/", "SD/proc2//")
      key_image = key_image.replace(fn, "images/" + fn)
      solved_file = image.replace(".png", ".solved")
      print("<img width=960 height=530 src=" + image + "><BR>" + key_image + " ")
      if cfe(solved_file) == 1:
         print("solved<br>")
      else:
         print("solve failed<br>")
      if key_image in allstars:
         for star in allstars[key_image]:
            name = star[0]
            #dcname = str(name.decode("utf-8"))
            #dbname = dcname.encode("utf-8")
            test = name.encode("ascii",'xmlcharrefreplace')
            print(test.decode('ascii') )
          
         print("<BR>")


def free_cal(json_conf,form):

   fp = open("/home/ams/amscams/pythonv2/templates/freeCalibrationPage.html")
   template = ""
   for line in fp :
      template = template + line

   input_file = form.getvalue("input_file")
   # if no input file is specified ask for one. 
   if cfe(input_file) == 0:
      print("input file was not found .")
      #auto_cal(json_conf,form)
      return()
   if input_file is None :
      print("To start the calibration process, goto the <a href=webUI.py>minute-by-minute view</a> for a stary night, click a thumb with nice stars and then click the 'Calibrate Star Field' button.<BR><BR> ")

      print("Or you can enter the path and filename to the image or video you want to calibrate:")
      print("<form>")
      print("<input type=hidden name=cmd value=free_cal>")
      print("<input type=text size=50 name=input_file value=\"\">")
      print("<input type=submit value=\"Continue\">")
      print("</form>")
      return()

   # test the input file, stack if video, check size and re-size, make half-stack, copy to work dir
   fn, dir = fn_dir(input_file)
   cfs = glob.glob(dir + "/" + "*calparams.json")
   if len(cfs) >= 1:
      cp_file = cfs[0]
   else:
      print("NO CP:!", input_file)
      exit()
  
   #print("IN FILE:", input_file)
   #print("CP FILE:", cp_file)
   if cfe(cp_file) == 0:
      cp_file = cp_file.replace("-calparams.json", "-stacked-calparams.json")
      if cfe(cp_file) == 0:
         cp_file = cp_file.replace("-calparams.json", "-stacked-calparams.json")

   if cfe(cp_file) == 1:
      cp = load_json_file(cp_file)
   else:
      print("NO CP:", cp_file)
      exit()

   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)
   if ".png" in cam_id:
      cam_id = cam_id.replace(".png", "")

   base_dir = "/mnt/ams2/cal/freecal/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   base_file = Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   if cfe(base_dir, 1) != 1:
      os.system("mkdir " + base_dir)

   #video or image
   if "mp4" in input_file:
      stack_file = input_file.replace(".mp4", "-stacked.png")
      el = input_file.split("/")
      dr  = el[-1].replace(".mp4", "")
      sfn = el[-1].replace(".mp4", "-stacked.png")
      stack_file = "/mnt/ams2/cal/freecal/" + dr + "/" + sfn 
      if cfe(stack_file) == 0:
         sfn = el[-1].replace(".mp4", ".png")
         stack_file = "/mnt/ams2/cal/freecal/" + dr + "/" + sfn 



      if cfe(stack_file) == 0:
         frames = load_video_frames(input_file, json_conf, 100)
         stack_file, stack_img = stack_frames(frames, input_file, 1)
         input_file = input_file.replace(".mp4", ".png") 
      else:
         input_file = input_file.replace(".mp4", ".png") 
         stack_img = cv2.imread(stack_file,0)
   else:
      stack_file = input_file
      stack_img = cv2.imread(input_file)

   sfs = stack_img.shape
   sh,sw = sfs[0],sfs[1]

   if sw != 1920:
      #stack_img = adjustLevels(stack_img, 5,.98,255)
      half_stack_img = stack_img 
      stack_img = cv2.resize(stack_img, (sw*2, sh*2))
      sfs = stack_img.shape
      sh,sw = sfs[0],sfs[1]
   else:
      half_stack_img = cv2.resize(stack_img, (0,0),fx=.5, fy=.5)

   iw = int(sw/2)
   ih = int(sh/2)

   half_stack_file = base_dir + "/" + base_file + "-half-stack.png"
   #stack_file = base_dir + "/" + base_file + "-stacked.png"


   cv2.imwrite(half_stack_file, half_stack_img)
   #cv2.imwrite(stack_file, stack_img)

   cfs = glob.glob(dir + "/" + "*azgrid-half.png")
   print("AZ:", dir + "/" + "*azgrid-half.png")
   if len(cfs) > 0:
      az_grid_file = cfs[0]
      az_grid_blend = az_grid_file.replace(".png", "-blend.png")
   else:
      az_grid_file = "none"
      az_grid_blend = "none"

   user_stars_file = cp_file.replace("-calparams.json", "-user-stars.json" )

   if cfe(user_stars_file) == 1:
      user_stars = load_json_file(user_stars_file)
      extra_js = """
         <script>
         """
      extra_js = extra_js + "var stars = ["

      c = 0
      for sdata in user_stars['user_stars']:
         if len(sdata) == 2:
            sx,sy = sdata
         elif len(sdata) == 3:
            sx,sy,sf = sdata
         else:
            print("BAD:", sdata)
            exit()
         if c > 0:
            extra_js = extra_js + ","
         extra_js=extra_js+ "[" + str(sx) + "," +str(sy) +"]" 
         c = c + 1
      extra_js = extra_js + "]"
      extra_js = extra_js + """
         </script>
   """
   else:
      extra_js = "<script>var stars = []</script>"



   #get Meteor Date as title
   template = template.replace("{%METEOR_DATE%}", get_meteor_date(stack_file))
   template = template.replace("{%AZ%}", str(cp['center_az'])[0:5])
   template = template.replace("{%EL%}", str(cp['center_el'])[0:5])
   template = template.replace("{%POS%}", str(cp['position_angle'])[0:5])
   template = template.replace("{%PX%}", str(cp['pixscale'])[0:5])
   template = template.replace("{%TSTARS%}", str(len(cp['cat_image_stars'])))
   template = template.replace("{%RES_PX%}", str(cp['total_res_px'])[0:5])
   template = template.replace("{%RES_DEG%}", str(cp['total_res_deg'])[0:5])


   js_html = """
   <script>
      var my_image = '""" + half_stack_file + """'
      var half_stack_file = '""" + half_stack_file + """'
      var az_grid_file = '""" + az_grid_file + """'
      var grid_by_default = false
      var hd_stack_file = '""" + stack_file + """'
   </script>
   """.format(stack_file)


   #canvas_html = """
   #   <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
   #   <div style="clear: both"></div>
   #       <div style="float:left; border: 1px #000000 solid;"><div style="position: relative; height: 50px; width: 50px; " id="myresult" class="img-zoom-result"> </div> </div>

   #"""
   canvas_html = ""
   canvas_html = canvas_html + """
      <div>
      <div style="float:left; padding: 10px;" id=action_buttons>
      </div>
      <div style="clear: both"></div>
      </div>
      <div style="float:left" id=info_panel>Info: </div>
      <div style="clear: both"></div>
       <BR><BR>
   """
   #print(stack_file)
      #<div id=star_panel> Stars: </div>
      #<div id=star_list>star_list: </div>

   list_of_buttons = '<a class="btn btn-primary d-block" onclick="javascript:show_image(\''+half_stack_file+'\',1,1)">Show Image</a>'
   list_of_buttons += '<a class="btn btn-primary d-block mt-2" onclick="javascript:find_stars(\''+stack_file+'\')">Find Stars</a>'
   #list_of_buttons += '<a class="btn btn-primary d-block mt-2" onclick="javascript:make_plate(\''+stack_file+'\')">Make Plate</a>'
   #list_of_buttons += '<a class="btn btn-primary d-block mt-2" onclick="javascript:solve_field(\''+stack_file+'\')">Solve Field</a>'
   list_of_buttons += '<a class="btn btn-primary d-block mt-2" onclick="javascript:show_cat_stars(\''+stack_file+'\',\'\',\'pick\')">Show Catalog Stars</a>'
   #list_of_buttons += '<a class="btn btn-primary d-block mt-2" onclick="javascript:fit_field(\''+stack_file+'\')">Fit Field</a>'
   list_of_buttons += '<a class="btn btn-primary d-block mt-2" onclick="javascript:az_grid(\''+az_grid_blend+'\')">AZ Grid</a>'
   list_of_buttons += '<a class="btn btn-danger d-block mt-4"  onclick="javascript:delete_cal(\''+stack_file+'\')">Delete Calibration</a>'
 
   template = template.replace("{%ALL_BUTTONS%}", list_of_buttons)

   #print(list_of_buttons)

   print(template)
   print(canvas_html)

   extra_js = extra_js + """ """
  
 

   print(js_html)
   print(extra_js)


def default_cal_params(cal_params,json_conf):
   if 'fov_poly' not in cal_params:
      fov_poly = [0,0]
      cal_params['fov_poly'] = fov_poly
   if 'pos_poly' not in cal_params:
      pos_poly = [0]
      cal_params['pos_poly'] = pos_poly
   if 'x_poly' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64) 
      cal_params['x_poly'] = x_poly.tolist()
   if 'y_poly' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64) 
      cal_params['y_poly'] = x_poly.tolist()
   if 'x_poly_fwd' not in cal_params:
      x_poly = np.zeros(shape=(15,), dtype=np.float64) 
      cal_params['x_poly_fwd'] = x_poly.tolist()
   if 'y_poly_fwd' not in cal_params:
      y_poly = np.zeros(shape=(15,), dtype=np.float64) 
      cal_params['y_poly_fwd'] = x_poly.tolist()

   return(cal_params)

def remove_dupe_cat_stars(cat_image_stars):
   new_data = []
   dupe_cat = {}
   dupe_img = {}
   for star in cat_image_stars: 
      (dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist) = star
      ikey = str(six) + "." + str(siy)
      ckey = str(new_cat_x) + "." + str(new_cat_y)
      if ikey not in dupe_img and ckey not in dupe_cat:
         new_data.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))
         dupe_cat[ckey] = 1
         dupe_img[ikey] = 1
 
   return(new_data)


def show_cat_stars(json_conf,form):
   child = 0
   cal_params = None
   hd_stack_file = form.getvalue("hd_stack_file")
   points = form.getvalue("points")
   type = form.getvalue("type")
   points = form.getvalue("points")
   video_file = form.getvalue("video_file")
   if cfe(hd_stack_file) == 0:
      sd_stack_file = video_file.replace(".mp4", "-stacked.png")
      sd_img = cv2.imread(sd_stack_file)
      hd_stack_img = cv2.resize(sd_img, (1920,1080))
      cv2.imwrite(hd_stack_file, hd_stack_img)
   # check if this meteor file has been custom fit and if it has use that info.
   meteor_red_file = video_file.replace(".mp4", "-reduced.json")

   # check if there are zero stars selected and zero in cat_img
   if cfe(meteor_red_file) == 1 and "reduced" in meteor_red_file:
      meteor_red = load_json_file(meteor_red_file)
      if points is None :
         mvf = meteor_red_file.replace("-reduced.json", ".mp4")
         cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mvf + " > /mnt/ams2/tmp/trs.txt"
         #print(cmd)
         os.system(cmd)

   meteor_mode = 0
   if cfe(meteor_red_file) == 1 and "reduced" in meteor_red_file:
      meteor_red = load_json_file(meteor_red_file)
      if "cal_params" in meteor_red:
         cal_params = meteor_red['cal_params']
         meteor_mode = 1
         cal_params_file = ""
         if "cat_image_stars" not in cal_params:
            mp4 = meteor_red_file.replace("-reduced.json", ".mp4")
            #os.system("cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + mp4)
            meteor_red = load_json_file(meteor_red_file)

         if "cat_image_stars" in cal_params:

            clean_close_stars = remove_dupe_cat_stars(cal_params['cat_image_stars'])
            cal_params['close_stars']  = clean_close_stars
            #cal_params['user_stars']  = cal_params['user_stars']
            
            #user_stars = cal_params['user_stars']
            user_stars = []
            used = {}
            for cstar in cal_params['cat_image_stars']:
               (iname,mag,ra,dec,tmp1,tmp2,px_dist,est_cat_x,est_cat_y,tmp3,tmp4,new_cat_x,new_cat_y,ix,iy,px_dist) = cstar
               key = str(ix) + "." + str(iy)
               here_now = 1
               if px_dist < 15:
                  for x,y in user_stars:
                     dst = calc_dist((x,y),(ix,iy))
                     if dst < 15:
                        here_now = 1
                  if here_now == 0:
                     user_stars.append((ix,iy))
            cal_params['user_stars']  = user_stars

            if "crop_box" in meteor_red:
               cal_params['crop_box']  = meteor_red['crop_box'] 
            if type == "first_load" or points is None:
               # this didn't work out the way we wanted it do. can delete
               if "cat_image_stars" not in cal_params:
                  video_json_file = video_file.replace(".mp4", ".json")
                  cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + video_json_file + " > /mnt/ams2/tmp/trs.txt"
                  os.system(cmd)
               elif len(cal_params['cat_image_stars']) == 0:
                  video_json_file = video_file.replace(".mp4", ".json")
                  cmd = "cd /home/ams/amscams/pythonv2/; ./autoCal.py imgstars " + video_json_file + " > /mnt/ams2/tmp/trs.txt"
                  #os.system(cmd)

            
               print(json.dumps(cal_params))
               exit()
         (box_min_x,box_min_y,box_max_x,box_max_y) = define_crop_box(meteor_red['meteor_frame_data'])
         meteor_red['crop_box'] = (box_min_x,box_min_y,box_max_x,box_max_y) 

   if meteor_mode == 0:
      cal_params_file_orig = hd_stack_file.replace(".png", "-calparams.json")
      cpfo = cfe(cal_params_file_orig)

      user_stars = {}
      cal_params_file = form.getvalue("cal_params_file")

      if cal_params_file is None and cpfo == 0:
         cal_params_files = get_active_cal_file(hd_stack_file)
         cal_params_file = cal_params_files[0][0]
      elif cal_params_file is not None:
         cal_params_file = cal_params_file
      else:
         cal_params_file = cal_params_file_orig

   star_points = []
   if cfe(hd_stack_file) == 0:
      bad_hd = 1      
      print("BAD HD LINK! Try to fix...")

   #print("RED FILE:", meteor_red_file)
   user_points = {}
   if points is None:
      points = ""
      star_json = find_stars_ajax(json_conf, hd_stack_file, 0)
      
      #for x,y,mp in star_json['stars'][0:20]:
      #   star_points.append((x,y))
   else:
      temps = points.split("|")
      for temp in temps:
         if len(temp) > 0:
            (x,y) = temp.split(",")
            x,y = int(float(x)),int(float(y))
            x,y = int(x)+5,int(y)+5
            x,y = x*2,y*2
            if x >0 and y > 0 and x<1920 and y< 1080:


               star_points.append((x,y))
   points = star_points
   hd_stack_img = cv2.imread(hd_stack_file,0)
   points = pin_point_stars(hd_stack_img, points)

   for x,y in points:
      pk = str(x) + '.' + str(y)
      user_points[pk] = 1

   if meteor_mode == 0:
      user_stars['user_stars'] = points 
   else:
      cal_params['user_stars'] = points 
      user_stars = {}
      user_stars['user_stars'] = points 

   if meteor_mode == 0:
      if cfe(cal_params_file_orig) == 1:
         #print("CAL PARAMS:", cal_params_file_orig)
         cal_params = load_json_file(cal_params_file_orig)
      else:
         #print("CAL PARAMS:", cal_params_file)
         cal_params = load_json_file(cal_params_file)
   
   if meteor_mode == 1: 
      if 'crop_box' not in meteor_red:
         cal_params['crop_box'] = (0,0,0,0)
      else: 
         cal_params['crop_box'] = meteor_red['crop_box']
   else:
         if "crop_box" not in cal_params:
            cal_params['crop_box'] = (0,0,0,0)


   #else:
   #   user_star_file = hd_stack_file.replace("-stacked.png", "-user-stars.json")
   #   user_stars = load_json_file(user_star_file)
   #solved_file = cal_params_file.replace("-calparams.json", ".solved")
   #cal_params = load_json_file(cal_params_file)
   cal_params = default_cal_params(cal_params,json_conf)

   if 'parent' in cal_params:
      child = 1
   else:
      child = 0 
   #print("<HR>RA/DEC:", cal_params_file, child, cal_params['ra_center'], cal_params['dec_center'])
   if meteor_mode == 0:
      el1 = cal_params_file.split("/")
      el2 = hd_stack_file.split("/")
      temp1 = el1[-1]
      temp2 = el2[-1]
      temp1 = temp1[0:20]
      temp2 = temp2[0:20]
      if temp1 != temp2:
         child = 1
   else:
      child = 1

   #print("<HR>RA/DEC:", child, cal_params['ra_center'], cal_params['dec_center'])
   #print(cal_params['center_az'], cfe(solved_file))
   if child == 1:
      #update center/ra dec
      if "center_az" in cal_params :
         center_az = cal_params['center_az']
         center_el = cal_params['center_el']

         rah,dech = AzEltoRADec(center_az,center_el,hd_stack_file,cal_params,json_conf)
         rah = str(rah).replace(":", " ")
         dech = str(dech).replace(":", " ")
         ra_center,dec_center = HMS2deg(str(rah),str(dech))
      else:
         ra_center = cal_params['ra_center']
         dec_center = cal_params['dec_center']
      #print("RA/DEC ADJ:", ra_center, dec_center, "<HR>")
      #print("RA/DEC ORIG:", cal_params['ra_center'], cal_params['dec_center'], "<HR>")
      #print("CENTER AZ/EL:", center_az, center_el, "<HR>")
      cal_params['ra_center'] = ra_center
      cal_params['dec_center'] = dec_center

   #print("<HR>RA/DEC:", cal_params['ra_center'], cal_params['dec_center'])
   #print("<HR>", cal_params_file, "<HR>")
   if "imagew" not in cal_params:
      cal_params['imagew'] = 1920
      cal_params['imageh'] = 1080
   cat_stars = get_catalog_stars([], [], cal_params,"x",cal_params['x_poly'],cal_params['y_poly'],min=0)
   my_cat_stars = []
   my_close_stars = []


   for name,mag,ra,dec,new_cat_x,new_cat_y in cat_stars :
      dcname = str(name.decode("utf-8"))
      dbname = dcname.encode("utf-8")
      my_cat_stars.append((dcname,mag,ra,dec,new_cat_x,new_cat_y))
   #cal_params['cat_stars'] = my_cat_stars
   #cal_params['user_stars'] = user_stars
   total_match_dist = 0
   total_cat_dist = 0 
   total_matches = 0
   for ix,iy in user_stars['user_stars']:
   #   print(ix,iy)
      close_stars = find_close_stars((ix,iy), cat_stars) 
      for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist in close_stars:
         dcname = str(name.decode("utf-8"))
         dbname = dcname.encode("utf-8")
         if meteor_mode == 0:
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,cal_params_file,cal_params,json_conf)
         else:
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,video_file,cal_params,json_conf)
         match_dist = abs(angularSeparation(ra,dec,img_ra,img_dec))
         ipk = str(six) + "." + str(siy)
         if ipk in user_points.keys() :
            my_close_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))
         else:
            print(ipk,"not found<BR>", user_points.keys(), "<BR>")
         total_match_dist = total_match_dist + match_dist
         total_cat_dist = total_cat_dist + cat_dist
         total_matches = total_matches + 1


      #print(close_stars,"<BR>")
   #   print(close_stars, "<BR>")
   clean_close_stars = remove_dupe_cat_stars(my_close_stars)
   cal_params['close_stars'] = clean_close_stars 
   cal_params['cat_image_stars'] = clean_close_stars 
   #out = str(cal_params)
   #out = out.replace("'", "\"")
   #out = out.replace("(b", "(")
   this_cal_params_file = hd_stack_file.replace(".png", "-calparams.json")
   if meteor_mode == 0:
      cal_params['parent_cal'] = cal_params_file
   
   if total_matches > 0 :
      cal_params['total_res_deg'] = total_match_dist / total_matches
      cal_params['total_res_px'] = total_cat_dist / total_matches
   else:
      cal_params['total_res_deg'] = 9999
      cal_params['total_res_px'] = 9999
   cal_params['cal_params_file'] = this_cal_params_file
   cal_params['user_stars'] = user_stars['user_stars']

   # need to remove from cat stars any stars that are not on the users list. and then add them to a banned list for the file so they don't come back. 
   #print("NEED TO SAVE.")
   #if meteor_mode == 0:
   #   save_json_file(this_cal_params_file, cal_params) 
   if meteor_mode == 1:
      meteor_red['cal_params'] = cal_params
      meteor_red['manual_update'] = 1 
      save_json_file(meteor_red_file, meteor_red) 
   if meteor_mode == 0:
      meteor_red_file = meteor_red_file.replace(".png", "-calparams.json") 
      if type == 'hd_cal_detail':
         meteor_red_file = meteor_red_file.replace("reduced", "calparams")
      cal_params['manual_update'] = 1 
      save_json_file(meteor_red_file, cal_params) 
   print(json.dumps(cal_params))

def calibrate_pic(json_conf,form):
   hdm_x = 2.7272
   hdm_y = 1.875
   sd_video_file = form.getvalue("sd_video_file")
   hd_file = None
   override = form.getvalue("override") 


   if override is not None:
      if "mp4" in override:
         sd_video_file = override
         print("OVERRIDE VIDEO", sd_video_file)
         override = None

   if sd_video_file is None and override is None:
      print("enter the path and filename to the image or video you want to calibrate:")
      print("<form>")
      print("<input type=hidden name=cmd value=calibrate_pic>")
      print("<input type=text size=50 name=override value=\"\">")
      print("<input type=submit value=\"Continue\">")
      print("</form>")
      return()


   if override is None or override == "":
      print("looking for HD file.")
      sd_stack_file = get_sd_filenames(sd_video_file)
      stack_img = cv2.imread(sd_stack_file,0)
      ih,iw = stack_img.shape
      hd_file, hd_trim,time_diff_sec, dur = find_hd_file_new(sd_video_file, 250, 10, 0)   
      print(hd_file, hd_trim)
   if hd_file is None and override is None:
      print("NO HD FILE FOUND. Using SD image instead.")
      # no HD file exists..
 
      hd_stack_img = cv2.resize(stack_img, (1920,1080))
      half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
      sd_stack_file = sd_stack_file.replace("_000_", "_007_")
      half_stack_file = sd_stack_file.replace("-stacked.png", "half-stack.png")
      hd_stack_file = sd_stack_file.replace("-stacked.png", "-stacked.png")
      override = hd_stack_file 
      cv2.imwrite(half_stack_file, half_stack_img)
      cv2.imwrite(hd_stack_file, hd_stack_img)

   if override is None or override == "":
      #print(hd_file,"<BR>")
      hd_stack_file = hd_file.replace(".mp4", "-stacked.png")
      half_stack_file = hd_file.replace(".mp4", "-half-stack.png")
      if cfe(hd_stack_file) == 0: 
         frames = load_video_frames(hd_file, json_conf, 20)
         hd_stack_file, hd_stack_img = stack_frames(frames, hd_file)
         half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
         cv2.imwrite(half_stack_file, half_stack_img)
         ih,iw = half_stack_img.shape
         #print("HD FILE Exists :", half_stack_file) 
      else:
         half_stack_img = cv2.imread(half_stack_file,0)
         ih,iw = half_stack_img.shape

   if override is not None:
      sd_stack_file = override
      stack_img = cv2.imread(sd_stack_file,0)

      hd_stack_img = cv2.resize(stack_img, (1920,1080))
      half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
      sd_stack_file = sd_stack_file.replace("_000_", "_007_")
      if "stacked" in sd_stack_file:
         half_stack_file = sd_stack_file.replace("-stacked.png", "-half-stack.png")
         hd_stack_file = sd_stack_file.replace("-stacked.png", "-stacked.png")
      if "jpg" in sd_stack_file:
         half_stack_file = sd_stack_file.replace(".jpg", "half-stack.jpg")
         hd_stack_file = sd_stack_file 
      override = hd_stack_file 
      print("HALF:", half_stack_file)
      cv2.imwrite(half_stack_file, half_stack_img)
      cv2.imwrite(hd_stack_file, hd_stack_img)

      print(hd_stack_file)
      #hd_stack_img = cv2.imread(hd_stack_file, 0)



      #half_stack_file = hd_stack_file.replace("-stacked.png", "-half-stack.png")
      #half_stack_img = cv2.resize(hd_stack_img, (0,0),fx=.5, fy=.5)
      #cv2.imwrite(half_stack_file, half_stack_img)



      ih,iw = half_stack_img.shape

   canvas_js = """
      <script>

      var hd_stack_file = '""" + hd_stack_file + """'
      var waiting = false

      function sleep (time) {
         return new Promise((resolve) => setTimeout(resolve, time));
      }

      function solve_field(hd_stack_file) {
         check_solve_status(1)
      }

      function send_ajax_solve() { 
         ajax_url = "/pycgi/webUI.py?cmd=solve_field&hd_stack_file=" + hd_stack_file 
         alert(ajax_url)
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            alert(json_resp['debug'])
            sleep(5000).then(() => {
               alert("time to wake up!")
               check_solve_status(0)
            });
         });
      }

      function check_solve_status(then_run) {
         ajax_url = "/pycgi/webUI.py?cmd=check_solve_status&hd_stack_file=" + hd_stack_file 
         alert(ajax_url)
         waiting = true
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            waiting = false
            alert(json_resp['debug']) 
            if (json_resp['status'] == 'failed' && then_run == 1) {
               send_ajax_solve()
            }
            if (json_resp['status'] == 'running' && then_run == 0) {
               alert("still running")
            }
            if (json_resp['status'] == 'success' && then_run == 0) {
               alert("solved")
            }
            if (json_resp['status'] == 'success' && then_run == 1) {
               grid_img = json_resp['grid_file']
               canvas.setBackgroundImage(grid_img, canvas.renderAll.bind(canvas));
               alert("GRID IMAGE:" + grid_img)
               alert(json_resp['debug'])
            }
            if (json_resp['status'] == 'failed' && then_run == 0) {
               alert(json_resp['solved_file'])
               alert("failed")
            }
         });
      }

      function make_plate(img_url) {
         var point_str = ""
         for (i in user_stars) {
            point_str = point_str + user_stars[i].toString()  + "|"
         }

         var point_str = ""
 
         var objects = canvas.getObjects('circle')
         for (let i in objects) {
            x = objects[i].left
            y = objects[i].top
            point_str = point_str + x.toString() + "," + y.toString() + "|"
         }

         ajax_url = "/pycgi/webUI.py?cmd=make_plate_from_points&hd_stack_file=" + hd_stack_file + "&points=" + point_str 
         alert(ajax_url)
 
         $.get(ajax_url, function(data) {
            $(".result").html(data);
            var json_resp = $.parseJSON(data);
            alert(json_resp['half_stack_file_an']) 
            var new_img = json_resp['half_stack_file_an'] + "?r=" + Math.random().toString()
            var stars = json_resp['stars'];

            for (let s in stars) {
              
              cx = stars[s][0] - 11 
              cy = stars[s][1] - 11
              var circle = new fabric.Circle({
                 radius: 5, fill: 'rgba(255,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
                 selectable: false
              });
              canvas.add(circle);

            }            

            alert(stars)
            canvas.setBackgroundImage(new_img, canvas.renderAll.bind(canvas));
            // remove existing objects & replace with pin pointed stars
            for (let i in objects) {
               canvas.remove(objects[i]);
            }


            //alert(json_resp.error)
            //alert(data)
         });


      }


      var canvas = new fabric.Canvas('c', {
         hoverCursor: 'default', 
         selection: true 
      });
      var my_image = " """ + half_stack_file + """"
      var user_stars = []

      canvas.setBackgroundImage(my_image, canvas.renderAll.bind(canvas));

      canvas.on('mouse:move', function(e) {
         var pointer = canvas.getPointer(event.e);
         x_val = pointer.x | 0;
         y_val = pointer.y | 0;
         cx = 2
         cy = 2
         document.getElementById('info_panel').innerHTML = x_val.toString() + " , " + y_val.toString()
         myresult = document.getElementById('myresult')
         myresult.style.backgroundImage = "url('" + hd_stack_file + "')";
         myresult.style.backgroundPosition = "-" + ((x_val*cx)-75) + "px -" + ((y_val * cy)-75)  + "px" 
      });

      canvas.on('mouse:down', function(e) {
         var pointer = canvas.getPointer(event.e);
         x_val = pointer.x | 0;
         y_val = pointer.y | 0;
         user_stars.push([x_val,y_val])

         var circle = new fabric.Circle({
            radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: x_val-5, top: y_val-5,
            selectable: false
         });

         var objFound = false
         var clickPoint = new fabric.Point(x_val,y_val);

         //canvas.forEachObject(function (obj) {
         var objects = canvas.getObjects('circle')
         for (let i in objects) {
            if (!objFound && objects[i].containsPoint(clickPoint)) {
               objFound = true
               canvas.remove(objects[i]);
            }
         }
         if (objFound == false) {
            canvas.add(circle);
         }


         document.getElementById('info_panel').innerHTML = "star added"
         document.getElementById('star_panel').innerHTML = "Total Stars: " + user_stars.length;
      });

      </script>
   """


   canvas_html = """
      <div style="float:left"><canvas id="c" width="{:d}" height="{:d} style="border:2px solid #000000;"></canvas></div><div style="float:left"><div style="position: relative; height: 150px; width: 150px" id="myresult" class="img-zoom-result"> </div></div><div style="clear: both"></div>
   """.format(iw,ih)

   canvas_html = canvas_html + """ 
      <div id=info_panel>Info: </div>
      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input type=button id="button1" value="Make Plate" onclick="javascript:make_plate('""" + hd_stack_file + """')"> 
         <input type=button id="button1" value="Find Stars"> 
         <input type=button id="button1" value="Solve Field" onclick="javascript:solve_field('""" + hd_stack_file + """')"> 
         <input type=button id="button1" value="Fit Field" onclick="javascript:fit_field('""" + hd_stack_file + """')"> 
      </div>
       <BR><BR>
   """

   print(canvas_html)
   print(canvas_js)

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


def fn_dir(file):
   fn = file.split("/")[-1]
   dir = file.replace(fn, "")
   return(fn, dir)

