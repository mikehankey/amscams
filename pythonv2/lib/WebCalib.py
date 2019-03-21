import datetime
import time
import json
import numpy as np
import cv2
import cgi
import time
import glob
import os
from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe
from lib.VideoLib import get_masks, convert_filename_to_date_cam, find_hd_file_new, load_video_frames, find_min_max_dist, ffmpeg_dump_frames
from lib.DetectLib import check_for_motion2, eval_cnt, find_bright_pixels

from lib.MeteorTests import test_objects
from lib.ImageLib import mask_frame,stack_frames, adjustLevels, upscale_to_hd, median_frames

from lib.CalibLib import radec_to_azel, clean_star_bg, get_catalog_stars, find_close_stars, XYtoRADec, HMS2deg, AzEltoRADec
from lib.UtilLib import check_running, calc_dist, angularSeparation, bound_cnt


def man_reduce_canvas(frame_num,thumbs,file,cal_params_file):
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
   extra_html = "<script src=../js/manreduce.js?" + str(rand) + "></script>"
   extra_html = extra_html + "<script>\n   show_frame_image('" + str(frame_num) + "','" + frame_base + "','prev');\n</script>"
   return(extra_html)

def calc_frame_time(video_file, frame_num):

   return(frame_time)

def reduce_point(cal_params_file, meteor_json_file, frame_num, point_data,json_conf):
   cal_params = load_json_file(cal_params_file)
   (cal_date, cam_id, cal_date_str,Y,M,D, H, MM, S) = better_parse_file_date(cal_params_file)
   cal_params = load_json_file(cal_params_file)
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(meteor_json_file)
   (hd_x,hd_y,w,h,mxp) =point_data
   new_x, new_y, ra ,dec , az, el= XYtoRADec(hd_x,hd_y,cal_params_file,cal_params,json_conf)


   return(ra,dec,az,el)


def man_reduce(json_conf,form):
   print("<h2>Manually Reduce</h2>")
   file = form.getvalue('file')
   cal_params_file = form.getvalue('cal_params_file')
   scmd = form.getvalue('scmd')
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(file)

   tmp_dir = "/mnt/ams2/tmp/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + cam_id + "/"
   video_file = file.replace("-stacked.png", ".mp4")
   if scmd is None:
      if cfe(tmp_dir, 1) == 0:
         print("MAKE:", tmp_dir)
         os.system("mkdir " + tmp_dir)
      ffmpeg_dump_frames(video_file,tmp_dir)
   thumbs = glob.glob(tmp_dir + "*-t.png")
   if scmd is None:
      for thumb in sorted(thumbs):
         print("<a href=webUI.py?cmd=man_reduce&scmd=2&file=" + file + "&frame=" + thumb + "&cal_params_file=" + cal_params_file + "><img src=" + thumb + "></a>")
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
      extra = man_reduce_canvas(frame_num, thumbs,file,cal_params_file)
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
   best_thresh = avg + 15
   #print("SHAPE:", iw,ih,best_thresh,"<BR>")
   _, star_bg = cv2.threshold(img, best_thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.dilate(star_bg, None , iterations=4)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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



def check_make_half_stack(sd_file,hd_file):
   half_stack_file = sd_file.replace("-stacked", "-half-stack")
   if cfe(half_stack_file) == 0:
      if hd_file != 0:
         if cfe(hd_file) == 1:
            img = cv2.imread(hd_file)
            img = cv2.resize(img, (0,0),fx=.5, fy=.5)
         else:
            img = cv2.imread(sd_file)
            img = cv2.resize(img, (960,540))
      else:
         img = cv2.imread(sd_file)
         img = cv2.resize(img, (960,540))
      cv2.imwrite(half_stack_file, img)
  
def make_cal_select(cal_files,video_file,cpf) :
   cal_select = "<SELECT onchange=\"javascript:goto('" + video_file + "', this.options[selectedIndex].value ,'reduce')\" style=\"margin: 5px; padding: 5px\" NAME=cal_param_file>"
   for cal_file, cal_desc, cal_time_diff in cal_files:
      dif_days = cal_time_diff / 86400
      if int(abs(cal_time_diff)) < 86400:
         hrs = int(cal_time_diff) / 60 / 60 
         dif_days = hrs * 24
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
      print(wc, px_diff, max_loc)
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
   meteor_reduced['cal_params']['az_center'] = cal_params['center_az']
   meteor_reduced['cal_params']['el_center'] = cal_params['center_el']
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
 
   cx1 = x - 5 
   cy1 = y - 5 
   cx2 = x + 5 
   cy2 = y + 5 

   frame_img = cv2.imread(frame_file,0)
   cnt_img = frame_img[cy1:cy2,cx1:cx2]
   max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img)
   w = 5
   h = 5




   meteor_json_file = orig_file.replace("-stacked.mp4", ".json")
   hd_x = (x + int(max_loc[0])) * 2
   hd_y = (y + int(max_loc[1])) * 2
   point_data = (hd_x,hd_y,5,5,int(max_px))
   (ra,dec,az,el) = reduce_point(cal_params_file, meteor_json_file, frame_num, point_data,json_conf)

   response['frame_num'] = 0
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
   man_json[frame_num] = [frame_time,frame_num,x,y,w,h,int(max_px),ra,dec,az,el]
   response['manual_frame_data'] = man_json

   save_json_file(man_json_file, man_json)

   save_manual_reduction(meteor_json_file,cal_params_file,json_conf)

   print(json.dumps(response))


def reduce_meteor_ajax(json_conf,meteor_json_file, cal_params_file, show = 0):
   if show == 1:
      cv2.namedWindow('pepe')
   hdm_x = 2.7272727272727272
   hdm_y = 1.875
   mj = load_json_file(meteor_json_file)
   man_reduce_file = meteor_json_file.replace(".json", "-manual.json")

   meteor_obj = get_meteor_object(mj)
   start_clip = meteor_obj['history'][0][0]
   end_clip = meteor_obj['history'][-1][0]
   start_clip = start_clip - 25
   if start_clip < 0:
      start_clip = 0
   end_clip = end_clip + 50

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

   el = mj['sd_video_file'].split("-trim")
   min_file = el[0] + ".mp4"
   ttt = el[1].split(".")
   trim_num = int(ttt[0])
   extra_sec = trim_num / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)
   sd_stack_file = sd_video_file.replace(".mp4", "-stacked.png")

   meteor_json = load_json_file(meteor_json_file)
   sd_video_file = meteor_json['sd_video_file']
   (crop_max_x,crop_max_y,crop_min_x,crop_min_y) = find_min_max_dist(meteor_obj['history'])
   crop = (crop_min_x,crop_min_y,crop_max_x,crop_max_y)
   #crop_min_x = 0
   #crop_min_y = 0
   frames,ofx,ofy = load_video_frames(sd_video_file,json_conf,0,0,crop)
   crop_min_x = ofx
   crop_min_y = ofy
   if end_clip > len(frames) -1 :
      end_clip = len(frames) - 1
   #frames = frames[start_clip:end_clip]
   objects = {}

   #objects = track_bright_objects(frames, sd_video_file, cam_id, meteor_obj, json_conf, show)
   objects = check_for_motion2(frames, sd_video_file,cam_id, json_conf,show)

   # do track brightest object here instead of check_for_motion2? 

   
   if len(objects) > 0:
      objects,meteor_found = test_objects(objects,frames)
   else:
      objects = []
      meteor_found = 0
   meteor_obj = get_meteor_object(objects)

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
         max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img)
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
         cv2.circle(reduce_img, (half_hd_x,half_hd_y), int(w/2.5), (255,128,128), 1)
         meteor_frame_data.append((meteor_frame_time_str,fn,int(hd_x),int(hd_y),int(w),int(h),int(max_px),float(round(ra,2)),float(round(dec,2)),float(round(az,2)),float(round(el,2))))
 
         tdesc = str(fc) + " - " + str(az)[0:6] + "/" + str(el)[0:5]
         cv2.putText(reduce_img, str(tdesc),  (int(half_hd_x) + 16,int(half_hd_y+pad-y_adj)), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1) 
         fc = fc + 1
      last_dist = dist_from_first
   cv2.imwrite(reduce_img_file, reduce_img)
   rand = time.time()

   response = {}
   response['status'] = 1
   response['message'] = "reduce complete"
   response['debug'] = "none"
   response['sd_meteor_frame_data'] = meteor_frame_data
   response['reduce_img_file'] = reduce_img_file
   vf_type = "SD"
   fin_sd_stack = fin_sd_video_file.replace(".mp4", ".png")
   fin_hd_stack = fin_hd_video_file.replace(".mp4", ".png")
   fin_reduced_video = fin_sd_video_file.replace(".mp4", "-reduced.mp4")
   fin_reduced_stack = fin_sd_video_file.replace(".mp4", "-reduced.png")
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
   meteor_reduced['start_az'] = int(start_az)
   meteor_reduced['start_el'] = int(start_el)
   meteor_reduced['end_az'] = int(end_az)
   meteor_reduced['end_el'] = int(end_el)
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
   meteor_reduced['cal_params']['az_center'] = cal_params['center_az']
   meteor_reduced['cal_params']['el_center'] = cal_params['center_el']
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

   print(json.dumps(response))
  
def get_meteor_object(meteor_json):
   if 'sd_objects' in meteor_json:
      objects = meteor_json['sd_objects']
   else:
      objects = meteor_json

   for object in objects:
      if object['meteor'] == 1:
         return(object)
   if len(objects) > 0:
      return(objects[0])
   else:
      return(None)

def make_frame_table(meteor_reduced):
   stab,sr,sc,et,er,ec = div_table_vars()
   frame_javascript = "<script>"
   frame_table = stab
   frame_table = frame_table + sr + sc + "FN" +ec + sc + "Frame Time" + ec + sc + "X/Y - W/H " + ec + sc + "Max PX" +ec + sc + "RA/DEC" + ec + sc + "AZ/EL" + ec + er 
   lc = 0
   start_y = meteor_reduced['meteor_frame_data'][0][3]
   for frame_data in meteor_reduced['meteor_frame_data'] :
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      hd_x = int(hd_x/2)
      hd_y = int(hd_y/2)
      text_y = str(hd_y)
      text_y = (start_y/2) - (lc * 12)

      az_desc = "\"" + str(lc) + " -  " + str(az) + " / " + str(el)  + "\""
      frame_table = frame_table + sr + sc + str(fn) +ec + sc + frame_time + ec + sc + str(hd_x) + "/" + str(hd_y) + " - " + str(w) + "/" + str(h) + ec + sc + str(max_px) +ec + sc + str(ra) + "/" + str(dec) + ec + sc +  str(az) + "/" + str(el)  + ec +er

      frame_javascript = frame_javascript + """
                 var rad = 6;

                 var meteor_rect = new fabric.Circle({

                     radius: rad, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(255,255,255,.5)', left: """ + str(hd_x-5) + """, top: """ + str(hd_y-5) + """,
                     selectable: false
                 });
                 canvas.add(meteor_rect);
      """        
      frame_javascript = frame_javascript + """ 
                 var text_p = new fabric.Text(""" + az_desc + """, {
                    fontFamily: 'Arial',
                    fontSize: 10,
                    left: """ + str(hd_x) + """ +25,
                    top: """ + str(text_y) + """ +25
                 });
                 text_p.setColor('rgba(255,255,255,.75)')
                 canvas.add(text_p)


      """
      lc = lc + 1
   frame_javascript = frame_javascript + "</script>"
   frame_table = frame_table + et
   return(frame_table, frame_javascript)

def reduce_meteor(json_conf,form):

   form_cal_params_file = form.getvalue("cal_params_file")

   hdm_x = 2.7272727272727272
   hdm_y = 1.875
   video_file = form.getvalue("video_file")
   meteor_json_file = video_file.replace(".mp4", ".json") 
   meteor_reduced_file = meteor_json_file.replace(".json", "-reduced.json")
   if cfe(meteor_reduced_file) == 1:
      meteor_reduced = load_json_file(meteor_reduced_file)
      frame_table, frame_javascript = make_frame_table(meteor_reduced)
      reduced = 1
   else:
      frame_table = ""
      reduced = 0
   mj = load_json_file(meteor_json_file)
   meteor_obj = get_meteor_object(mj)


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
         mj['hd_crop_file_stack'] = mj['hd_crop_file'].replace(".mp4", "-stacked.png")
         mj['hd_trim_stack'] = mj['hd_trim'].replace(".mp4", "-stacked.png")
      else:
         mj['hd_file'] = 0
         mj['hd_trim'] = 0
         mj['hd_crop_file'] = 0
         mj['hd_crop_file_stack'] = 0
         mj['hd_trim_stack'] = 0
      mj['sd_stack'] = mj['sd_video_file'].replace(".mp4", "-stacked.png")
     
      mj['half_stack'] = mj['sd_stack'].replace("-stacked.png", "-half-stack.png")
   sd_video_file = mj['sd_video_file']
   sd_stack = mj['sd_stack']
   
   check_make_half_stack(mj['sd_stack'], mj['hd_trim_stack'])
   half_stack_file = mj['half_stack']
   hd_stack_file = mj['hd_trim_stack']
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
   
      mj['cal_params_file']  = cal_params_file
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

   print("<h1>Reduce Meteor</h1>")


   extra_js = "<script>var stars = []</script>"


   #bottom_html = "<script>window.onload = show_image('" + half_stack_file + "','" + az_grid_file + "',1,1);"
   bottom_html = "<script>"
   bottom_html = bottom_html + "function play_video(src_url) { $('#ex1').modal(); $('#v1').attr(\"src\", src_url);} </script>"

   if reduced == 1:
      bottom_html = bottom_html + frame_javascript


   js_html = """

   <script>
      var my_image = '""" + half_stack_file + """'
      var hd_stack_file = '""" + hd_stack_file + """'
      var az_grid_file = '""" + az_grid_file + """'
      var stars = []
   </script>


   """.format(hd_stack_file)
   canvas_html = """
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
      <div style="float:left">
      <div>
<span style="padding: 5px"> Calibration File</span><br>
   """ + cal_select + """</div>
<span style="padding: 5px"> <b>Meteor Info</b></span><br>
<span style="padding: 5px"> Start Clip Time: """ + start_clip_time_str + """</span><br>
<span style="padding: 5px"> Trim Start Frame Num: """ + str(trim_num) + """ </span><br>
<span style="padding: 5px"> Meteor Start/End Frame: """ + str(meteor_start_frame) + "/" + str(meteor_end_frame) + """ </span><br>
<span style="padding: 5px"> Meteor Start Time: """ + str(start_meteor_frame_time_str) + """</span><br>
<span style="padding: 5px"> Duration: """ + str(elp_dur) + "seconds / " + str(elp_frames) + """ frames</span><br>
      """
   canvas_html = canvas_html + """


<span style="padding: 5px"> <B>SD Reduction Values</B></span><br>

<span style="padding: 5px"> Start X/Y: """ + str(start_x) + "/" + str(start_y) + """</span><br>
<span style="padding: 5px"> End X/Y: """ + str(end_x) + "/" + str(end_y) + """</span><br>
<span style="padding: 5px"> Start RA/DEC: """ + str(start_ra)[0:5] + "/" + str(start_dec)[0:5] + """</span><br>
<span style="padding: 5px"> End RA/DEC: """ + str(end_ra)[0:5] + "/" + str(end_dec)[0:5] + """</span><br>
<span style="padding: 5px"> Start AZ/EL: """ + str(start_az)[0:5] + "/" + str(start_el)[0:5] + """</span><br>
<span style="padding: 5px"> End AZ/EL: """ + str(end_az)[0:5] + "/" + str(end_el)[0:5] + """</span><br>
<span style="padding: 5px"> <a target='_blank' href=\"webUI.py?cmd=man_reduce&file=""" + mj['sd_stack']+ "&cal_params_file=" + cal_params_file +  """\">Manualy Reduce</a></span><br>

<span style="padding: 5px"> <B>Media Files</B></span><br>
<span style="padding: 5px"> <a target='_blank' href=javascript:play_video('""" + mj['sd_video_file']+ """')>SD Video</a></span><br>


<span style="padding: 5px"> <a target='_blank' href=\"javascript:show_image('""" + mj['sd_stack']+ """',1.3636,.9375)\">SD Image</a></span><br>
   """
   if mj['hd_trim'] != 0 and mj['hd_trim'] != None:
      canvas_html = canvas_html + """
<span style="padding: 5px"> <a target='_blank' href=javascript:play_video('""" + mj['hd_trim']+ """')>HD Video</a></span><br>
<span style="padding: 5px"> <a target='_blank' href= """ + mj['hd_trim_stack']+ """>HD Image</a></span><br>
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
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="Show Catalog Stars" onclick="javascript:show_cat_stars('""" + hd_stack_file + "','" + cal_params_file + """', 'nopick')">
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="  Reduce Meteor " onclick="javascript:reduce_meteor_ajax('""" + meteor_json_file + "','" + cal_params_file + """')">
         <input style="width: 200; margin: 5px; padding: 5px" type=button id="button1" value="  Fit Stars " onclick="javascript:custom_fit('""" + meteor_json_file + "','" + cal_params_file + """')">
      </div>


      <div style="clear: both"></div>

      <div style="float:left" id=info_panel>Info</div>
      <div style="clear: both"></div>
      <div style="float:left" id=info_panel><a href="javascript:show_hide_div('adv_func')">Advanced Functions</a> - 

<a href="javascript:show_hide_div('problems')">Fix Problems</a></div>
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
      <div style="" id=star_list>""" + frame_table + """</div>
      </div>
   """
   #print(stack_file)

   print(canvas_html)
   print(js_html)
   print(extra_js)

   print("<img id='half_stack_file' style='display: none' src='" + half_stack_file + "'> <br>")
   print("<img id='az_grid_file' style='display: none' src='" + az_grid_file + "'> <br>")
   print("<img id='meteor_img' style='display: none' src='" + half_stack_file + "'> <br>")

   return(bottom_html)


def get_active_cal_file(input_file):
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)

   # find all cal files from his cam for the same night
   matches = find_matching_cal_files(cam_id, f_datetime)
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
  
   td_sorted_matches = [] 

   for match in matches:
      (t_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(match)
      tdiff = (capture_date-t_datetime).total_seconds()   
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
      max_pnt,max_val,min_val = cnt_max_px(cnt_img)
      mx,my = max_pnt
      mx = mx - 15
      my = my - 15
      x = x + mx
      y = y + my
      star_points.append((x,y))
   return(star_points)


def add_stars_to_fit_pool(json_conf,form):
   input_file = form.getvalue("input_file")
   cal_files = get_active_cal_file(input_file)
   cal_params_file = cal_files[0][0]
   cal_hd_stack_file = cal_params_file.replace("-calparams.json", ".png")
   print(cal_params_file, "<BR>")
   print(cal_hd_stack_file, "<BR>")
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
      var my_image = '""" + half_stack_file + """'
      var hd_stack_file = '""" + hd_stack_file + """'
      var stars = []
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
      # exit()
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
   #print(hd_stack_file)
   hd_stack_img = cv2.imread(hd_stack_file,0)
   #print(hd_stack_img)
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
      print("<a href=webUI.py?cmd=free_cal&input_file=" + hd_file + "></a>HD File found. Stacking frames. Please wait... </a>") 
      print("<script>window.location.href='webUI.py?cmd=free_cal&input_file=" + hd_file + "';</script>")

def sd_pic_stars(json_conf,form):
   print("<h1>Calibrate SD Image Step #1 - Pick Stars</h1>")
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
      print(stack_file,half_stack_file)
      #stack_img = cv2.resize(stack_img, (1920, 1080))
      #half_stack_img = cv2.resize(stack_img, (960, 540))
      cv2.imwrite(stack_file, stack_img)
      cv2.imwrite(half_stack_file, half_stack_img)
   else:
      stack_file = input_file
      stack_img = cv2.imread(input_file)


   js_html = """

   <script>
      var my_image = '""" + half_stack_file + """'
      var hd_stack_file = '""" + stack_file + """'
      var stars = []
   </script>


   """.format(stack_file)
   canvas_html = """
      <p>An HD source file was not found for this time period. No worries, we can still calibrate from an SD image, but first we need to pick the stars so we can upscale the image. Select as many stars as possible from the image below and then click the "Upscale To HD" button.</p>
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
      <div style="float:left"><div style="position: relative; height: 50px; width: 50px" id="myresult" class="img-zoom-result"> </div></div>
      <div style="clear: both"></div>
   """

   canvas_html = canvas_html + """
      <div id=info_panel>Info: </div>
      <div id=star_panel>Stars: </div>
      <div id=action_buttons>
         <input type=button id="button1" value="Find Stars" onclick="javascript:find_stars('""" + stack_file + """')">
         <input type=button id="button1" value="Upscale To HD" onclick="javascript:upscale_HD('""" + stack_file + """')">
      </div>
      <div id=star_list>star_list: </div>
       <BR><BR>
   """
   print(stack_file)

   print(canvas_html)
   print(js_html)



def free_cal(json_conf,form):
   input_file = form.getvalue("input_file")
   # if no input file is specified ask for one. 
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

   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(input_file)
   base_dir = "/mnt/ams2/cal/freecal/" + Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   base_file = Y + "_" + M + "_" + D + "_" + H + "_" + MM + "_" + S + "_" + "000" + "_" + cam_id
   if cfe(base_dir, 1) != 1:
      os.system("mkdir " + base_dir)

   #video or image
   if "mp4" in input_file:
      frames = load_video_frames(input_file, json_conf, 1499)
      stack_file, stack_img = stack_frames(frames, input_file, 1)
      input_file = input_file.replace(".mp4", ".png") 
   else:
      stack_file = input_file
      stack_img = cv2.imread(input_file)

   sfs = stack_img.shape
   sh,sw = sfs[0],sfs[1]


   if sw != 1920:
      #print(input_file, sh,sw)
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
   stack_file = base_dir + "/" + base_file + "-stacked.png"


   cv2.imwrite(half_stack_file, half_stack_img)
   cv2.imwrite(stack_file, stack_img)


   user_stars_file = stack_file.replace("-stacked.png", "-user-stars.json")
   az_grid_file = stack_file.replace(".png", "-azgrid-half.png")
   az_grid_blend = stack_file.replace(".png", "-azgrid-half-blend.png")


   if cfe(user_stars_file) == 1:
      user_stars = load_json_file(user_stars_file)
      extra_js = """
         <script>
         """
      extra_js = extra_js + "var stars = ["

      c = 0
      for sx,sy in user_stars['user_stars']:
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
      var my_image = '""" + half_stack_file + """'
      var hd_stack_file = '""" + stack_file + """'
   </script>
   """.format(stack_file)
   canvas_html = """
      <div style="float:left"><canvas id="c" width="960" height="540" style="border:2px solid #000000;"></canvas></div>
      <div style="clear: both"></div>
   """

   canvas_html = canvas_html + """
      <div>
      <div style="float:left; border: 1px #000000 solid;"><div style="position: relative; height: 50px; width: 50px; " id="myresult" class="img-zoom-result"> </div> </div>

      <div style="float:left; padding: 10px;" id=action_buttons>
         <input type=button id="button1" value="Show Image" onclick="javascript:show_image('""" + half_stack_file + """',1,1)">
         <input type=button id="button1" value="Find Stars" onclick="javascript:find_stars('""" + stack_file + """')">
         <input type=button id="button1" value="Make Plate" onclick="javascript:make_plate('""" + stack_file + """')">
         <input type=button id="button1" value="Solve Field" onclick="javascript:solve_field('""" + stack_file + """')">
         <input type=button id="button1" value="Show Catalog Stars" onclick="javascript:show_cat_stars('""" + stack_file + "','" + "" + """', 'pick')">
         <input type=button id="button1" value="Fit Field" onclick="javascript:fit_field('""" + stack_file + """')">
         <input type=button id="button1" value="AZ Grid" onclick="javascript:az_grid('""" + az_grid_blend + """')">
         <input type=button id="button1" value="Delete Calibration" onclick="javascript:delete_cal('""" + stack_file + """')">
      </div>
      <div style="clear: both"></div>
      </div>
      <div style="float:left" id=info_panel>Info: </div>
      <div style="clear: both"></div>
      <div id=star_panel> Stars: </div>
      <div id=star_list>star_list: </div>
       <BR><BR>
   """
   print(stack_file)

   print(canvas_html)
   print(extra_js)
   print(js_html)
   #print("<script src=\"/js/freecal-canvas.js\"></script>")
   #print("<script src=\"/js/freecal-ajax.js\"></script>")



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


def show_cat_stars(json_conf,form):
   child = 0
   hd_stack_file = form.getvalue("hd_stack_file")
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

   points = form.getvalue("points")
   star_points = []
   if points is None:
      points = ""
      star_json = find_stars_ajax(json_conf, hd_stack_file, 0)
      
      for x,y,mp in star_json['stars'][0:20]:
         star_points.append((x,y))
   else:
      temps = points.split("|")
      for temp in temps:
         if len(temp) > 0:
            (x,y) = temp.split(",")
            x,y = int(float(x)),int(float(y))
            x,y = int(x)+5,int(y)+5
            x,y = x*2,y*2
            star_points.append((x,y))
   points = star_points
   hd_stack_img = cv2.imread(hd_stack_file,0)
   points = pin_point_stars(hd_stack_img, points)
   user_stars['user_stars'] = points 

   if cfe(cal_params_file_orig) == 1:
      cal_params = load_json_file(cal_params_file_orig)
   else:
      cal_params = load_json_file(cal_params_file)
    
   #else:
   #   user_star_file = hd_stack_file.replace("-stacked.png", "-user-stars.json")
   #   user_stars = load_json_file(user_star_file)
   solved_file = cal_params_file.replace("-calparams.json", ".solved")
   #cal_params = load_json_file(cal_params_file)
   cal_params = default_cal_params(cal_params,json_conf)

   if 'parent' in cal_params:
      child = 1
   else:
      child = 0 
   #print("<HR>RA/DEC:", cal_params_file, child, cal_params['ra_center'], cal_params['dec_center'])
   el1 = cal_params_file.split("/")
   el2 = hd_stack_file.split("/")
   temp1 = el1[-1]
   temp2 = el2[-1]
   temp1 = temp1[0:20]
   temp2 = temp2[0:20]
   if temp1 != temp2:
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

   cat_stars = get_catalog_stars(cal_params['fov_poly'], cal_params['pos_poly'], cal_params,"x",cal_params['x_poly'],cal_params['y_poly'],min=0)
   my_cat_stars = []
   my_close_stars = []


   for name,mag,ra,dec,new_cat_x,new_cat_y in cat_stars :
      dcname = str(name.decode("utf-8"))
      dbname = dcname.encode("utf-8")
      my_cat_stars.append((dcname,mag,ra,dec,new_cat_x,new_cat_y))
   cal_params['cat_stars'] = my_cat_stars
   cal_params['user_stars'] = user_stars['user_stars']
   total_match_dist = 0
   total_cat_dist = 0 
   total_matches = 0
   for ix,iy in user_stars['user_stars']:
   #   print(ix,iy)
      close_stars = find_close_stars((ix,iy), cat_stars) 
      for name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist in close_stars:
         dcname = str(name.decode("utf-8"))
         dbname = dcname.encode("utf-8")
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(ix,iy,cal_params_file,cal_params,json_conf)
         match_dist = abs(angularSeparation(ra,dec,img_ra,img_dec))
         my_close_stars.append((dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist))
         total_match_dist = total_match_dist + match_dist
         total_cat_dist = total_cat_dist + cat_dist
         total_matches = total_matches + 1


      #print(close_stars,"<BR>")
   #   print(close_stars, "<BR>")

   cal_params['close_stars'] = my_close_stars
   #out = str(cal_params)
   #out = out.replace("'", "\"")
   #out = out.replace("(b", "(")
   this_cal_params_file = hd_stack_file.replace(".png", "-calparams.json")
   cal_params['parent_cal'] = cal_params_file
   cal_params['total_res_deg'] = total_match_dist / total_matches
   cal_params['total_res_px'] = total_cat_dist / total_matches
   cal_params['cal_params_file'] = this_cal_params_file
   save_json_file(this_cal_params_file, cal_params) 
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
                 radius: 5, fill: 'rgba(0,0,0,0)', strokeWidth: 1, stroke: 'rgba(100,200,200,.5)', left: cx/2, top: cy/2,
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

