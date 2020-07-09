import datetime
import numpy as np


from lib.CalibLibv2 import distort_xy_new, AzEltoRADec, HMS2deg
from lib.UtilLib import best_fit_slope_and_intercept, calc_dist

import glob
import cv2
import os
#import time
from lib.UtilLib import convert_filename_to_date_cam, bound_cnt
from lib.FileIO import load_json_file, save_json_file, cfe
from lib.ImageLib import find_min_max_dist,bigger_box, mask_frame
#Add text, logo, etc.. to a frame

 


def add_radiant(ra,dec,image,json_file,json_data,json_conf):
   cp = json_data['cal_params']

   rah,dech = AzEltoRADec(cp['center_az'],cp['center_el'],json_file,cp,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center= HMS2deg(str(rah),str(dech))

   #perseids radiant
   #ra= 46
   #dec= 58
   F_scale = 3600/float(cp['pixscale'])

   new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,ra_center, dec_center, cp['x_poly'], cp['y_poly'], 1920, 1080, cp['position_angle'],F_scale)

   xy_text_mod = 0
   x_text_mod = 0
   if new_cat_x < 0 :
      edge_x = 20
   elif new_cat_x > 1910 :
      edge_x = 1910
      x_text_mod = -60
      xy_text_mod = -20
   else:
      edge_x = int(new_cat_x)

   new_cat_x, new_cat_y = int(new_cat_x), int(new_cat_y)

   y_text_mod = 0
   if new_cat_x <= 10 or new_cat_y <= 10 or new_cat_x > 1900 or new_cat_y > 1070:
      center_x = int(1920 / 2)
      center_y = int(1080 / 2)
      # radiant is off screen find the slope to it from the center
      tm,tb = best_fit_slope_and_intercept((center_x,new_cat_x),(center_y,new_cat_y))
      edge_y = (tm*edge_x)+tb
      edge_y, edge_x = int(edge_y), int(edge_x)
      print("EDGE:", edge_x, edge_y)
      if edge_y < 0:
         edge_y = 10
         y_text_mod = 20
      elif edge_y > 1060:
         edge_y = 1060
         y_text_mod = -20
      else:
         edge_y = int(edge_y)

      #cv2.line(image, (center_x,center_y), (edge_x,edge_y), (128,128,128), 1)
      cv2.circle(image,(edge_x,edge_y), 25 , (128,128,128), 1)
      cv2.putText(image, "Perseid Radiant",  (edge_x+x_text_mod, edge_y+y_text_mod+xy_text_mod), cv2.FONT_HERSHEY_SIMPLEX, .5, (145, 145, 145), 1)
      new_cat_x = edge_x
      new_cat_y = edge_y
      print("EDGE:", edge_x, edge_y)
   else:
      print("ACCEPTED IT")
      cv2.circle(image,(new_cat_x,new_cat_y), 25 , (128,128,128), 1)
      cv2.putText(image, "Perseid Radiant",  (new_cat_x, new_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .5, (145, 145, 145), 1)


   print("RAD XY:", new_cat_x, new_cat_y)
   return(image, new_cat_x, new_cat_y)



def add_radiant_old(ra,dec,image,json_file, json_data,json_conf):

   json_data = load_json_file(json_file)

   cp = json_data['cal_params']

   rah,dech = AzEltoRADec(cp['center_az'],cp['center_el'],json_file,cp,json_conf)
   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")
   ra_center,dec_center= HMS2deg(str(rah),str(dech))


   F_scale = 3600/float(cp['pixscale'])

   new_cat_x, new_cat_y = distort_xy_new (0,0,ra,dec,ra_center, dec_center, cp['x_poly'], cp['y_poly'], 1920, 1080, cp['position_angle'],F_scale)
   print("RAD:", new_cat_x, new_cat_y)
   text_pos = int(new_cat_x - 60) , int(new_cat_y + 35)
   cv2.putText(image, "Perseid Radiant",  (text_pos), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)

   new_cat_x, new_cat_y = int(new_cat_x), int(new_cat_y)
   cv2.circle(image,(new_cat_x,new_cat_y), 25, (128,128,128), 1)











   return(image)


def add_overlay(background, overlay, x, y):

    background_width = background.shape[1]
    background_height = background.shape[0]

    if x >= background_width or y >= background_height:
        return background

    h, w = overlay.shape[0], overlay.shape[1]

    if x + w > background_width:
        w = background_width - x
        overlay = overlay[:, :w]

    if y + h > background_height:
        h = background_height - y
        overlay = overlay[:h]

    if overlay.shape[2] < 4:
        overlay = np.concatenate(
            [
                overlay,
                np.ones((overlay.shape[0], overlay.shape[1], 1), dtype = overlay.dtype) * 255
            ],
            axis = 2,
        )

    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0

    background[y:y+h, x:x+w] = (1.0 - mask) * background[y:y+h, x:x+w] + mask * overlay_image

    return background





def make_crop_box(meteor_data, iw, ih):

   segs = []
   mxs = meteor_data['metconf']['mxs']
   mys = meteor_data['metconf']['mys']
   gxs = []
   gys = []
   last_x = None
   for i in range(0,len(mxs)-1):
      if last_x is not None:
         last_seg_dist = calc_dist((mxs[i], mys[i]), (last_x, last_y))
         segs.append(last_seg_dist)
      last_x = mxs[i]
      last_y = mys[i]

   med_seg_dist = np.median(segs) 
   last_x = None
   last_seg_dist = 0
   for i in range(0,len(mxs)-1):
      if last_x is not None:
         last_seg_dist = calc_dist((mxs[i], mys[i]), (last_x, last_y))
      if last_seg_dist < med_seg_dist * 2:
         gxs.append(mxs[i])
         gys.append(mys[i])
      last_x = mxs[i]
      last_y = mys[i]

   if len(gxs) > 0:
      min_x = min(gxs) - 20
      max_x = max(gxs) + 20
      min_y = min(gys) - 20
      max_y = max(gys) + 20
   else:
      min_x = min(mxs) - 20
      max_x = max(mxs) + 20
      min_y = min(mys) - 20
      max_y = max(mys) + 20

   cx = int((min_x + max_x) / 2)
   cy = int((min_y + max_y) / 2)

   if min_x < 0:
      min_x = 0
   if min_y < 0:
      min_y = 0
   if max_x > 1919:
      max_x = 1919
   if max_y > 1080:
      max_y = 1080 


   return(min_x,min_y,max_x,max_y)

def remaster(video_file, json_conf):

   #ams_watermark = "../dist/img/ams_logo_vid_anim/1280x720/AMS30.png" 
   ams_watermark = "../dist/img/ams_logo_vid_anim/1920x1080/AMS30.png" 
   if "logo_file" in json_conf['site']:
      logo_file = json_conf['site']['logo_file']
      logo_pos = json_conf['site']['logo_pos']
   else:
      logo_file = None


   #watermark_image = cv2.imread('../dist/img/ams_logo_vid_anim/1920x1080/AMS30.png', cv2.IMREAD_UNCHANGED)

   watermark_image = cv2.imread(ams_watermark, cv2.IMREAD_UNCHANGED)
   if logo_file is not None:
      logo_image = cv2.imread(logo_file, cv2.IMREAD_UNCHANGED)

   print(watermark_image.shape)
   marked_video_file = video_file.replace(".mp4", "-pub.mp4")

   (wH, wW) = watermark_image.shape[:2]
   (B, G, R, A) = cv2.split(watermark_image)
   #B = cv2.bitwise_and(B, B, mask=A)
   #G = cv2.bitwise_and(G, G, mask=A)
   #R = cv2.bitwise_and(R, R, mask=A)
   watermark = cv2.merge([B, G, R, A])

   frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)
   json_file = video_file.replace(".mp4", ".json")
   meteor_data = load_json_file(json_file)
   start_buff = int(meteor_data['start_buff'])
   start_sec = (start_buff / 25) * -1 
   el = video_file.split("_")
   station = el[-2]   
   cam = el[-3]   
   (hd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)
   ih, iw = frames[0].shape[:2]

 
   start_frame_time = hd_datetime + datetime.timedelta(0,start_sec)
   start_frame_str = hd_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

   cx1, cy1, cx2, cy2 = make_crop_box(meteor_data, iw, ih)
   print("CROP BOX:", cx1, cy1, cx2, cy2)
   fc = 0
   new_frames = []
   for frame in frames:
      frame_sec = fc / 25
      frame_time = start_frame_time + datetime.timedelta(0,frame_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      hd_img = frame
      color = 150 - fc * 3
      if color > 50:
         cv2.rectangle(hd_img, (cx1, cy1), (cx2, cy2), (color,color,color), 1)

      camID = station + "-" +sd_cam 

      extra_text = json_conf['site']['operator_name'] + " " + json_conf['site']['obs_name'] + " " + json_conf['site']['operator_city'] + "," + json_conf['site']['operator_state'] 

 
      #hd_img = cv2.resize(frame, (1280,720))
      #print("WATER:", watermark_image.shape)
      hd_img = add_overlay(hd_img, watermark_image, 10, 10)


      if logo_file is not None:
         hd_img = add_overlay(hd_img, logo_image, logo_pos, 10)

      new_frame = hd_img

      #perseids radiant
      ra = 46
      dec = 59

      new_frame, rad_x, rad_y = add_radiant(ra,dec,new_frame,json_file, meteor_data,json_conf)
     

 

      path = "/home/ams/tmpvids/"
      ih, iw = hd_img.shape[:2]

      text_pos = (5,ih-10)
      date_pos = (iw-620,ih-10)

      print("TEXT POS:", text_pos)

      cv2.putText(hd_img, extra_text,  (text_pos), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
      station_id = json_conf['site']['ams_id'] + "-" + sd_cam
      station_id = station_id.upper()
      cv2.putText(hd_img, station_id + " " + frame_time_str + " UTC",  (date_pos), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
      new_frames.append(new_frame)

      #cv2.imshow('pepe', new_frame)
      #cv2.waitKey(10)
      fc = fc + 1

   make_movie_from_frames(new_frames, [0,len(new_frames) - 1], marked_video_file, 1)


def make_movie_from_frames(frames, fns, outfile , remaster = 0):
 
   ofn = outfile.split("/")[-1]

   #TMP_DIR = "/mnt/ams2/tmpvids/" + ofn + "/"
   TMP_DIR = "/home/ams/tmpvids/" + ofn + "/"
   if cfe(TMP_DIR, 1) == 0:
      os.system("mkdir " + TMP_DIR )
   else:
      os.system("rm " + TMP_DIR + "*")

   first_frame = 0
   last_frame = len(fns)
   start_buff = 0
   end_buff = 0

   first_frame = fns[0]
   last_frame = fns[-1]

   cc = 0
   print("MM Start Trim Fn:", first_frame)
   print("MM Last Trim Fn:", last_frame)
   print("MM Total frames :", len(frames))

   for frame in frames:
      filename = TMP_DIR + '{0:06d}'.format(cc) + ".png"
      if first_frame <= cc <= last_frame:
         print(cc, first_frame, last_frame )
         cv2.imwrite(filename, frame)
      cc = cc + 1

   if remaster == 1:
      cmd = """/usr/bin/ffmpeg -y -framerate 25 -pattern_type glob -i '""" + TMP_DIR + """*.png' \
        -c:v libx264 -r 25 -vf scale='1920x1080' -pix_fmt yuv420p """ + outfile 
   else:
      cmd = """/usr/bin/ffmpeg -y -framerate 25 -pattern_type glob -i '""" + TMP_DIR + """*.png' \
        -c:v libx264 -r 25 -pix_fmt yuv420p """ + outfile 
   print(cmd)
   os.system(cmd)


   
   os.system("rm -rf " + TMP_DIR )
   print("rm -rf " + TMP_DIR )
   return(start_buff, end_buff)
   

def find_hd_frame(fn, hd_x, hd_y, x1,y1,x2,y2,hd_frames):
   crops = []
   max_hd_val = 0
   best_hd_frame = 0
   cc = 0
   best_cc = 0
   for frame in hd_frames:
      gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      crop_frame = gray_frame[y1:y2,x1:x2]
      max_val = gray_frame[hd_y,hd_x]
      if max_val > max_hd_val:
         max_hd_val = max_val
         best_hd_frame = cc 
         best_cc = cc
      cc = cc + 1
      crops.append(crop_frame)
   #cv2.imshow('pepe', crops[best_cc])
   #cv2.waitKey(0)
   return(best_hd_frame)

def sync_hd_frames(sd_video_file, json_conf):
   print("sync hd frames")
   red_file = sd_video_file.replace(".mp4", "-reduced.json")
   red_data = load_json_file(red_file)
   hd_video_file = red_data['hd_video_file']
   hd_frames = load_video_frames(hd_video_file, json_conf, limit=0, mask=1,crop=(),color=1)
   sd_frames = load_video_frames(sd_video_file, json_conf, limit=0, mask=1,crop=(),color=1)

   metframes = red_data['metframes']
   first_sd_frame = None
   first_hd_frame = None
   hd_fns = []
   sd_fns = []

   for fn in metframes:
      if first_sd_frame is None:
         first_sd_fram = fn
      x1 = metframes[fn]['x1']
      x2 = metframes[fn]['x2']
      y1 = metframes[fn]['y1']
      y2 = metframes[fn]['y2']
      hd_x = metframes[fn]['hd_x']
      hd_y = metframes[fn]['hd_y']
      hd_fn = find_hd_frame(fn, hd_x, hd_y, x1,y1,x2,y2,hd_frames)
      sd_fns.append(int(fn))
      hd_fns.append(int(hd_fn))
      print(fn, metframes[fn]['hd_x'], metframes[fn]['hd_y'])

   if len(sd_fns) == len(hd_fns):
      # buffer the frames with 10 frames on either side if we can.
      hd_archive_movie = sd_video_file.replace(".mp4", "-archiveHD.mp4")
      sd_archive_movie = sd_video_file.replace(".mp4", "-archiveSD.mp4")
      hd_start_buff, hd_end_buff = make_movie_from_frames(hd_frames, hd_fns, hd_archive_movie)
      sd_start_buff, sd_end_buff = make_movie_from_frames(sd_frames, sd_fns, sd_archive_movie)
      red_data['metconf']['archive_sd_pre_roll'] = sd_start_buff
      red_data['metconf']['archive_sd_post_roll'] = sd_end_buff
      red_data['metconf']['archive_hd_pre_roll'] = hd_start_buff
      red_data['metconf']['archive_hd_post_roll'] = hd_end_buff
      red_data['metconf']['hd_sync'] = 1 
      print("Perfect HD/SD frame match up!")       
      print("SD FRAMES:", sd_fns)
      print("HD FRAMES:", hd_fns)
      print("Archive HD Movie:", hd_archive_movie)
      print("Archive SD Movie:", sd_archive_movie)
      save_json_file(red_file, red_data)

def doHD(sd_video_file, json_conf):
   sd_w = 704
   sd_h = 576
   hd_w = 1920
   hd_h = 1080

   hdm_x = 2.7272
   hdm_y = 1.875

   # All steps to find and reduce HD file and save in archive and cloud
   # find HD file
   # trim HD file
   # handle EOF exceptions
   # crop HD file
   # make stacks for Crop,crop obj, HD & HD obj
   # make meteor json file with HD reduction and meteor info
   # if HD reduction fails, note this in the JSON file
   # preserve original objects json in new json file
   # copy all meteor files to the meteor archive
   # upload to VMA

   json_file = sd_video_file.replace(".mp4", ".json")
   objects = load_json_file(json_file)
   for object in objects:
      if object['meteor'] == 1:
   

         el = sd_video_file.split("-trim")
         min_file = el[0] + ".mp4"
         ttt = el[1].split(".")
         o_trim_num = ttt[0]
         trim_num = int(ttt[0])
  
         start_frame = object['history'][0][0]
         end_frame = object['history'][-1][0]
         frame_dur = end_frame - start_frame  

         start_sec = (start_frame / 25) 
         frame_dur_sec = (frame_dur / 25) + 3

         #print("SF:", start_frame, end_frame, frame_dur) 

         if start_sec - 1 < 0:
            start_sec = 0
         else:
            start_sec = start_sec - 1

         if frame_dur_sec + start_sec + 1 >= 59:
            frame_dur_sec = 59 - start_sec
         else:
            frame_dur_sec = frame_dur_sec + 1
         if frame_dur_sec < 5:
            frame_dur_sec = 5

         if frame_dur > 180:
            frame_dur_sec = frame_dur_sec +  4
         #print("SS:", start_sec, frame_dur_sec) 
         frame_dur_sec = frame_dur_sec + 3
         #print(min_file,start_sec,frame_dur_sec)
         hd_file, hd_trim,trim_time_offset, trim_dur = find_hd_file_new(min_file, o_trim_num, frame_dur_sec)

         #print("HD:", hd_file, hd_trim)
         if hd_file == None or hd_file == 0:
            return(None,None,None,None,None,None)
         (max_x,max_y,min_x,min_y) = find_min_max_dist(object['history'])
         (min_x,min_y,max_x,max_y) = bigger_box(min_x,min_y,max_x,max_y,sd_w,sd_h,25)
         hd_min_x = min_x * hdm_x
         hd_max_x = max_x * hdm_x
         hd_min_y = min_y * hdm_y
         hd_max_y = max_y * hdm_y

         sd_box= (min_x,min_y,max_x,max_y)
         hd_box= (hd_min_x,hd_min_y,hd_max_x,hd_max_y)
         crop_out_file = crop_hd(hd_trim,hd_box)
         print("HD TRIM:", hd_trim)
         return(hd_file,hd_trim,crop_out_file,hd_box,trim_time_offset, trim_dur)
   return(0,0,0,0,0,0)

def archive_meteor (sd_video_file,hd_file,hd_trim,crop_out_file,hd_box,hd_objects,json_conf):
   print(archive_meteor)

def crop_hd(hd_file,box_str):
   #x,y,mx,my = box_str.split(",")
   x,y,mx,my = box_str

   #hd_mx = 1
   #hd_my = 1
   #x = float(x) * hd_mx
   #y = float(y) * hd_my
   #mx = float(mx) * hd_mx
   #my = float(my) * hd_my

   w = float(mx) - float(x)
   h = float(my) - float(y)

   x = int(x)
   y = int(y)
   w = int(w)
   h = int(h)

   print("XY: ",x,y,mx,my,w,h)

   crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)
   print("CROP: ", crop)
   crop_out_file = hd_file.replace(".mp4", "-crop.mp4")
   cmd = "/usr/bin/ffmpeg -i " + hd_file + " -filter:v \"" + crop + "\" " + crop_out_file + " >/dev/null 2>&1"
   cmd = "/usr/bin/ffmpeg -i " + hd_file + " -filter:v \"" + crop + "\" -y " + crop_out_file 
   print(cmd)
   os.system(cmd)
   return(crop_out_file)


def check_hd_motion(frames, trim_file):

   height, width = frames[0].shape

   max_cons_motion, frame_data, moving_objects, trim_stack = check_for_motion(frames, trim_file)
   stacked_image_np = np.asarray(trim_stack)
   found_objects, moving_objects = object_report(trim_file, frame_data)

   stacked_image = draw_obj_image(stacked_image_np, moving_objects,trim_file, stacked_image_np)

   cv2.namedWindow('pepe')
   cv2.imshow('pepe', stacked_image)
   cv2.waitKey(5)

   passed,all_objects = test_objects(moving_objects, trim_file, stacked_image_np)
   max_x = 0
   max_y = 0
   min_x = frames[0].shape[1]
   min_y = frames[0].shape[0]
   for object in all_objects:
      if(object['meteor_yn'] == 1):
         box = object['box']
         w = box[2] - box[0] + 25
         h = box[3] - box[1] + 25
         x = box[0]
         y = box[1]

         cx = x + (w/2)
         cy = y + (h/2)

         w = w * 2
         h = h * 2
         if w > h:
            h = w
         else:
            w = h

         x = cx - (w/2)
         y = cy - (h/2)
    
         crop = "crop=" + str(w) + ":" + str(h) + ":" + str(x) + ":" + str(y)

         if crop_on == 1:
            min_x,min_y,max_x,max_y = box
            w = max_x - min_x
            h = max_y - min_y
            crop_out_file = trim_file.replace(".mp4", "-crop.mp4")
            scaled_out_file = trim_file.replace(".mp4", "-scaled.mp4")
            pip_out_file = trim_file.replace(".mp4", "-pip.mp4")
            cmd = "ffmpeg -i " + trim_file + " -filter:v \"" + crop + "\" " + crop_out_file+ " >/dev/null 2>&1"
            os.system(cmd)

            cmd = "ffmpeg -i " + trim_file + " -s 720x480 -c:a copy " + scaled_out_file
            os.system(cmd)

            cmd = "/usr/bin/ffmpeg -i " + scaled_out_file + " -i " + crop_out_file + " -filter_complex \"[1]scale=iw/1:ih/1 [pip];[0][pip] overlay=main_w-overlay_w-10:main_h-overlay_h-10\" -profile:v main -level 3.1 -b:v 440k -ar 44100 -ab 128k -s 1920x1080 -vcodec h264 -acodec libfaac " + pip_out_file + " >/dev/null 2>&1"
            os.system(cmd)





def find_hd_file_new(sd_file, trim_num, dur = 5, trim_on =1):
   o_trim_num = trim_num
   trim_num = int(trim_num)
   print("FIND HD FILE NEW FOR :", sd_file)

   (sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(sd_file)
   if trim_num > 1400:
      hd_file, hd_trim = eof_processing(sd_file, trim_num, dur)
      time_diff_sec = int(trim_num / 25)
      if hd_file != 0:
         return(hd_file, hd_trim, time_diff_sec, dur)
   offset = int(trim_num) / 25
   meteor_datetime = sd_datetime + datetime.timedelta(seconds=offset)
   hd_glob = "/mnt/ams2/HD/" + sd_y + "_" + sd_m + "_" + sd_d + "_*" + sd_cam + "*.mp4"
   hd_files = sorted(glob.glob(hd_glob))
   for hd_file in hd_files:
      el = hd_file.split("_")
      print("HD FILE:", hd_file)
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file and "trim" not in hd_file:
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds()
         if 0 < time_diff_sec < 60:
            time_diff_sec = time_diff_sec - 3
            dur = int(dur) + 1 + 3
            if trim_num == 0:
               trim_num = 1
            if time_diff_sec < 0:
               time_diff_sec = 0
            if trim_on == 1:
               print("TRIMTRIMTIRM")
               hd_trim = ffmpeg_trim(hd_file, str(time_diff_sec), str(dur), "-trim-" + str(trim_num) + "-HD-meteor")
            else:
               print("NOOOOOOOOOOOOOOOOOOOOOO TRIMMMMMMMMMMMMMMM")
               hd_trim = None
            return(hd_file, hd_trim, time_diff_sec, dur)
   # No HD file was found. Trim out the SD Clip and then upscale it.
   print("NO HD FOUND!")

   time_diff_sec = int(trim_num / 25)
   dur = int(dur) + 1 + 3
   print("UPSCALE FROM SD!", time_diff_sec, dur)
   time_diff_sec = time_diff_sec - 1
   if "passed" in sd_file:
      sd_trim = ffmpeg_trim(sd_file, str(time_diff_sec), str(dur), "-trim" + str(o_trim_num) + "")
   else:
      sd_trim = ffmpeg_trim(sd_file, str(time_diff_sec), str(dur), "-trim-" + str(trim_num) + "-SD-meteor")
   hd_trim = upscale_sd_to_hd(sd_trim)
   if "-SD-meteor-HD-meteor" in hd_trim:
      orig_hd_trim = hd_trim
      hd_trim = hd_trim.replace("-SD-meteor", "")
      hdf = hd_trim.split("/")[-1]
      os.system("mv " + orig_hd_trim + " /mnt/ams2/HD/" + hdf)
      print("HD F: mv " + orig_hd_trim + " /mnt/ams2/HD/" + hdf)
      hd_trim = "/mnt/ams2/HD/" + hdf
 
   return(sd_file,hd_trim,str(0),str(dur))

def upscale_sd_to_hd(video_file):
   new_video_file = video_file.replace(".mp4", "-HD-meteor.mp4")
   if cfe(new_video_file) == 0:
      cmd = "/usr/bin/ffmpeg -i " + video_file + " -vf scale=1920:1080 " + new_video_file
      os.system(cmd)
   return(new_video_file)


def eof_processing(sd_file, trim_num, dur):
   merge_files = []
   sd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s = convert_filename_to_date_cam(sd_file)
   offset = int(trim_num) / 25
   print("TRIM SEC OFFSET: ", offset)
   meteor_datetime = sd_datetime + datetime.timedelta(seconds=offset)
   print("METEOR DATETIME:", meteor_datetime)
   #hd_glob = "/mnt/ams2/HD/" + sd_date + "_*" + sd_cam + "*"
   hd_glob = "/mnt/ams2/HD/" + sd_y + "_" + sd_m + "_" + sd_d + "_*" + sd_cam + "*"
   print("HD GLOB:", hd_glob)
   hd_files = sorted(glob.glob(hd_glob))
   print("HD FILES:", hd_files)
   for hd_file in hd_files:
      el = hd_file.split("_")
      print ("EOF HD FILE", hd_file)
      if len(el) == 8 and "meteor" not in hd_file and "crop" not in hd_file and "-HD-" not in hd_file:
         hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)
         time_diff = meteor_datetime - hd_datetime
         time_diff_sec = time_diff.total_seconds()
         print("HD FOUND ", meteor_datetime, hd_datetime, time_diff_sec,hd_file) 
         if -90 < time_diff_sec < 90:
            print("TIME:", time_diff_sec, hd_file)
            merge_files.append(hd_file)
   # take the last 5 seconds of file 1
   # take the first 5 seconds of file 2
   # merge them together to make file 3
   print("MERGE FILES:", merge_files)
   if len(merge_files) == 0:
      return(0,0)

   hd_trim1 = ffmpeg_trim(merge_files[0], str(55), str(5), "-temp-" + str(trim_num) + "-HD-meteor")
   hd_trim2 = ffmpeg_trim(merge_files[1], str(0), str(5), "-temp-" + str(trim_num) + "-HD-meteor")
   # cat them together

   print("TRIM FILES:", hd_trim1, hd_trim2)

   #hd_datetime, sd_cam, sd_date, sd_h, sd_m, sd_s = convert_filename_to_date_cam(merge_files[0])
   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(merge_files[0])
   new_clip_datetime = hd_datetime + datetime.timedelta(seconds=55)
   new_hd_outfile = "/mnt/ams2/HD/" + new_clip_datetime.strftime("%Y_%m_%d_%H_%M_%S" + "_" + "000" + "_" + sd_cam + ".mp4")
   print("HD TRIM1,2,NEW:", hd_trim1, hd_trim2, new_hd_outfile)
   ffmpeg_cat(hd_trim1, hd_trim2, new_hd_outfile)
   hd_trim = new_hd_outfile.replace(".mp4", "-trim-0-HD-trim.mp4")
   cmd = "cp " + new_hd_outfile + " " + hd_trim
   os.system(cmd)

   return(new_hd_outfile, hd_trim)


def ffmpeg_cat (file1, file2, outfile):
   cat_file = "/tmp/cat_files.txt"
   fp = open(cat_file, "w")
   fp.write("file '" + file1 + "'\n")
   fp.write("file '" + file2 + "'\n")
   fp.close()
   cmd = "/usr/bin/ffmpeg -y -f concat -safe 0 -i " + cat_file + " -c copy " + outfile + " >/dev/null 2>&1"
   print(cmd)
   os.system(cmd)



def ffmpeg_trim (filename, trim_start_sec, dur_sec, out_file_suffix):

   outfile = filename.replace(".mp4", out_file_suffix + ".mp4")
   cmd = "/usr/bin/ffmpeg -i " + filename + " -y -ss 00:00:" + str(trim_start_sec) + " -t 00:00:" + str(dur_sec) + " -c copy " + outfile+ " >/dev/null 2>&1"
   print (cmd)
   os.system(cmd)
   return(outfile)

def trim_event(event):
   low_start = 0
   high_end = 0
   start_frame = int(event[0][0])
   end_frame = int(event[-1][0])
   if low_start == 0:
      low_start = start_frame
   if start_frame < low_start:
      low_start = start_frame
   if end_frame > high_end:
      high_end = end_frame

   start_frame = int(low_start)
   end_frame = int(high_end)
   frame_elp = int(end_frame) - int(start_frame)
   start_sec = int(start_frame / 25) - 3
   if start_sec <= 0:
      start_sec = 0
   dur = int(frame_elp / 25) + 3 + 3
   if dur >= 60:
      dur = 59
   if dur < 2:
      dur = 3 

   pad_start = '{:04d}'.format(start_frame)
   outfile = ffmpeg_trim(mp4_file, start_sec, dur, "-trim" + str(pad_start))


def get_masks(this_cams_id, json_conf, hd = 0):
   #hdm_x = 2.7272
   #hdm_y = 1.875
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         if hd == 1:
            masks = cameras[camera]['hd_masks']
         else:
            masks = cameras[camera]['masks']
         for key in masks:
            mask_el = masks[key].split(',')
            (mx, my, mw, mh) = mask_el
            masks[key] = str(mx) + "," + str(my) + "," + str(mw) + "," + str(mh)
            my_masks.append((masks[key]))
   print("MASKS:", my_masks)
   return(my_masks)


def load_video_frames(trim_file, json_conf, limit=0, mask=0,crop=(),color=0, skip=None,resize=None):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   cap = cv2.VideoCapture(trim_file)
   masks = None 

   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      #print(frame_count)
      if frame is None:
         if frame_count <= 5 :
            cap.release()
            return(frames)
         else:
            go = 0
      else:
         if limit != 0 and frame_count > limit:
            cap.release()
            return(frames)
         if len(frame.shape) == 3 and color == 0:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

         if mask == 1 and frame is not None:
            if frame.shape[0] == 1080:
               hd = 1
            else:
               hd = 0
            masks = get_masks(cam, json_conf,hd)
            frame = mask_frame(frame, [], masks, 5)

         if len(crop) == 4:
            ih,iw = frame.shape
            x1,y1,x2,y2 = crop
            x1 = x1 - 25
            y1 = y1 - 25
            x2 = x2 + 25
            y2 = y2 + 25
            if x1 < 0:
               x1 = 0 
            if y1 < 0:
               y1 = 0 
            if x1 > iw -1:
               x1 = iw -1 
            if y1 > ih -1:
               y1 = ih -1 
            #print("MIKE:", x1,y2,x2,y2)
            crop_frame = frame[y1:y2,x1:x2]
            frame = crop_frame
         if skip is None:
            frames.append(frame)
         else:
            if frame_count % skip == 0:
               if resize is None:
                  frames.append(frame)
               else:
                  frame = cv2.resize(frame, (resize[0],resize[1]))
                  frames.append(frame)

         frame_count = frame_count + 1
   cap.release()
   if len(crop) == 4:
      return(frames,x1,y1)
   else:
      return(frames)

def ffmpeg_dump_frames(video_file, out_dir):
   jpg_out = out_dir + "frames%05d.png"
   #"960" height="540"
   syscmd = "/usr/bin/ffmpeg -i " + video_file + " " + jpg_out
   #print(syscmd)
    
   os.system(syscmd)


