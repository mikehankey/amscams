#!/usr/bin/python3

import glob
import cv2
from detectlib import *
import sys
import datetime
import json
from caliblib import find_best_thresh

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']

from caliblib import find_non_cloudy_times, summarize_weather, save_json_file, load_json_file
#   weather = find_non_cloudy_times(cal_date, cam_num)

def direction(hist):
   fx,fy = hist[0][1],hist[0][2]
   lx,ly = hist[-1][1],hist[-1][2]
   if fx < lx:
     x_dir = 1
     x_dir_txt = "right"
   else:
     x_dir = -1
     x_dir_txt = "left"
   if fy < ly:
     y_dir = 1
     y_dir_txt = "down"
   else:
     y_dir = -1
     y_dir_txt = "up"
   return(x_dir,y_dir,x_dir_txt,y_dir_txt)

def calc_angle(pointA, pointB):
  changeInX = pointB[0] - pointA[0]
  changeInY = pointB[1] - pointA[1]
  ang = math.degrees(math.atan2(changeInY,changeInX)) #remove degrees if you want your answer in radians
  if ang < 0 :
     ang = ang + 360
  return(ang)

def min_max_hist(hist):
   points = []
   sizes = []
   for fn,x,y,w,h,mx,my in hist:
      size  = w * h
      sizes.append(size)
      point = x+mx,y+my
      points.append(point)

   max_x = max(map(lambda x: x[0], points))
   max_y = max(map(lambda x: x[1], points))
   min_x = min(map(lambda x: x[0], points))
   min_y = min(map(lambda x: x[1], points))
   minmax_dist = calc_dist((min_x,min_y),(max_x,max_y))
   minmax_ang = calc_angle((min_x,min_y),(max_x,max_y))
   return(min_x, min_y, max_x, max_y, minmax_dist, minmax_ang)


def obj_box(hist,img_w,img_h):
   sizes= []
   points= []
   for fn,x,y,w,h,mx,my in hist:
      size  = w * h
      sizes.append(size)
      point = x+mx,y+my
      points.append(point)

   max_x = max(map(lambda x: x[0], points))
   max_y = max(map(lambda x: x[1], points))
   min_x = min(map(lambda x: x[0], points))
   min_y = min(map(lambda x: x[1], points))

   ow = max_x - min_x
   oh = max_y - min_y
   ow = ow + (ow * 1.2)
   oh = oh + (oh * 1.2)
   if oh > ow:
      ow = oh
   else:
      oh = ow
   cx = (min_x + max_x) / 2
   cy = (min_y + max_y) / 2



   min_x = int(cx - (ow / 2 ))
   min_y = int(cy - (oh / 2 ))
   max_x = int(cx + (ow /2))
   max_y = int(cy + (oh /2))

   if min_x < 0:
      min_x = 0
   if min_y < 0:
      min_y = 0
   return(min_x,min_y,max_x,max_y)

def plot_object(objects, video_file):
   el = video_file.split("/")
   fn = el[-1]
   base_dir = video_file.replace(fn, "")
   stack_file = fn.replace(".mp4", "-stacked.png")
   stack_file = base_dir + "/images/" + stack_file
   obj_stack_file = stack_file.replace("-stacked.png", "-obj_stacked.png")
   print("ST", stack_file)
   image = cv2.imread(stack_file)
   ih,iw,xx = image.shape
   for object in objects:

      if 'meteor_found' in object:
         bmin_x,bmin_y,bmax_x,bmax_y = object['box']
   
         cv2.putText(image, "[" + str(object['oid']) + "] Meteor " ,  (int(bmin_x+8),int(bmin_y+15)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)

         for hist in object['history']:
            fn,x,y,w,h,mx,my = hist
            cox = x + mx
            coy = y + my
            cv2.circle(image, (int(cox),int(coy)), 1, (0,255,0), 1)

         cv2.rectangle(image, (bmin_x, bmin_y), (bmax_x, bmax_y), (255,255,255), 2) 
      else:
         print("OBJECT", object['oid'])
         bmin_x,bmin_y,bmax_x,bmax_y = obj_box(object['history'],iw,ih)
         cv2.rectangle(image, (bmin_x, bmin_y), (bmax_x, bmax_y), (123,0,0), 2) 
         #for hist in object['history']:
         #   fn,x,y,w,h,mx,my = hist
         #   cv2.rectangle(image, (x, y), (x+w, y+h), (255,100,100), 1) 
                


   #cv2.imshow('pepe', image)
   #cv2.imwrite(obj_stack_file, image)
   #cv2.waitKey(30)


def save_meteor(meteor_video_file, object):
   print("SAVE METEOR")
   el =meteor_video_file.split("/") 
   fn = el[-1]
   base_dir = meteor_video_file.replace(fn, "")

   dd = fn.split("_")
   YY = dd[0]
   MM = dd[1]
   DD = dd[2]
  
   meteor_base_dir = "/mnt/ams2/SD/proc2/meteors/"
   meteor_day_dir = "/mnt/ams2/SD/proc2/meteors/" + YY + "_" + MM + "_" + DD + "/"

   if cfe(meteor_base_dir,1) == 0:
      print("METEOR BASE DIR DOESNT EXIST:", meteor_base_dir)
      os.system("mkdir " + meteor_base_dir)
   if cfe(meteor_day_dir,1) == 0:
      os.system("mkdir " + meteor_day_dir)

   # for SD stuff
   # copy trim video files (normal trim and meteor trim) 

   sdv_wild = meteor_video_file.replace(".mp4", "*.mp4") 
   img_wild = fn.replace(".mp4", "*.png") 
   img_wild = base_dir + "/images/" + img_wild

   cmd = "cp " + sdv_wild + " " + meteor_day_dir 
   print(cmd)
   os.system(cmd)

   cmd = "cp " + img_wild + " " + meteor_day_dir 
   print(cmd)
   os.system(cmd)



   # stack pic and stack-obj pics
   # meteor data.txt files ( or object.json)
   # for HD stuff
   # HD TRIM clip
   # HD TRIM CROP
   # HD meteor.json reduction file


   return(meteor_day_dir) 
   



def scan_trim_file(trim_file, show = 0):

   el = trim_file.split("/")
   base_trim_file = el[-1]
   base_dir = trim_file.replace(base_trim_file, "")
   meteor_video_file = trim_file.replace(".mp4", "-meteor.mp4")
   base_file = base_trim_file.replace(".mp4", "")
   
   meteor_file = base_dir + "/data/" + base_file + "-meteor.txt"
   objfail_file = base_dir + "/data/" + base_file + "-objfail.txt"
   
   trim_stack_file = base_dir + "/images/" + base_file + "-stacked.png"
   trim_stack_meteor_file = base_dir + "/images/" + base_file + "-meteor-stacked.png"

   data_wildcard = base_dir + "/data/" + base_file + "*"
   vid_wildcard = base_dir + "/" + base_file + "*meteor*"

   print ("FILE:", trim_file)
   done_already = check_if_done(trim_file)
   if done_already == 1:
      if sys.argv[1] != "sf":
         print ("SKIP! Already done.")
         return()
      else:
         print ("SKIP! Already done.")
         #return()

   cmd = "rm " + data_wildcard
   print(cmd)
   os.system(cmd)
   cmd = "rm " + vid_wildcard
   print(cmd)
   os.system(cmd)
   cmd = "rm " + trim_stack_file 
   print(cmd)
   os.system(cmd)
   cmd = "rm " + trim_stack_meteor_file
   print(cmd)
   os.system(cmd)


   frames = load_video_frames(trim_file)

   height, width = frames[0].shape

   #max_cons_motion, frame_data, moving_objects, trim_stack = check_for_motion2(frames, trim_file, show)
   objects = check_for_motion2(frames, trim_file)
   print("Stacking...")
   cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
   os.system(cmd)
   stacked_frame = cv2.imread(trim_stack_file)  

   print("DOne Stacking...")
   meteor_objects = []
   meteor_found = 0
   print("OBJECTS:", len(objects))
   for object in objects:
      status, reason, obj_data = test_object2(object)
      #print("TRIM FILE TESTS:", trim_file)
      print("Object Test Result: ", object['oid'], status, reason)
      print("Object:", object)
      if status == 1:
         print("OBJ MIKE: ", object)
         min_x,min_y,max_x,max_y = obj_data['min_max_xy']
         ow = max_x - min_x
         oh = max_y - min_y
         ow = ow + (ow * 1.2)
         oh = oh + (oh * 1.2)
         if oh > ow:
            ow = oh
         else:
            oh = ow
         cx = (min_x + max_x) / 2
         cy = (min_y + max_y) / 2
         bmin_x = int(cx - (ow / 2 ))
         bmin_y = int(cy - (oh / 2 ))
         bmax_x = int(cx + (ow /2))
         bmax_y = int(cy + (oh /2))

         #print("OBJ_DATA:", obj_data['min_max_xy'])
         oid = object['oid']
         cv2.putText(stacked_frame, str(oid),  (int(cx+5),int(cy+5)), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
         cv2.circle(stacked_frame, (int(cx),int(cy)), 1, (255), 1)
         cv2.rectangle(stacked_frame, (bmin_x, bmin_y), (bmax_x, bmax_y), (255,255,255), 2) 
         if bmin_x < 0:
           bmin_x = 0
         if bmin_y < 0:
           bmin_y = 0
         box = (bmin_x,bmin_y,bmax_x,bmax_y)
         box_str = str(bmin_x) + "," + str(bmin_y) + "," + str(bmax_x) + "," + str(bmax_y) 
         object['box'] = box
         object['meteor_found'] = 1
         for hist in object['history']:
            fn,x,y,w,h,mx,my = hist
            cox = x + mx
            coy = y + my
            cv2.circle(stacked_frame, (int(cox),int(coy)), 1, (0,255,0), 1)
         meteor_objects.append(object)
         print(object)
         hist = object['history']
         start= hist[0][0] 
         end= hist[-1][0]
         elp_time = (end - start) / 25
         if elp_time < 3:
            elp_time = 3 
         if 3 < elp_time < 4:
            elp_time = 4
         if 4 < elp_time < 5:
            elp_time = 5

         if start - 100 > 0: 
            trim_adj = start - 100 

         if start - 25 > 0: 
            trim_adj = start - 25
         else:
            trim_adj = 0
         elp_time = elp_time + 4
         # METEOR FOUND!

         trim_meteor(trim_file, start, end)
         cmd = "./stack-stack.py stack_vid " + meteor_video_file + " mv"
         print(cmd)
         os.system(cmd)

         meteor_day_dir = save_meteor(meteor_video_file, object)
         cv2.rectangle(stacked_frame, (bmin_x, bmin_y), (bmax_x, bmax_y), (255,255,255), 2) 
         #cv2.imshow('pepe', stacked_frame)
         #cv2.waitKey(10)

         cmd = "./doHD.py " + meteor_video_file + " " + str(elp_time) + " " + str(box_str) + " " + str(trim_adj) + " " + meteor_day_dir
         print("DOHD:", cmd)
         meteor_found = 1
         os.system(cmd)


   #meteor_objects = merge_meteor_objects(meteor_objects) 

   if meteor_found >= 1:
      print ("METEOR", meteor_file)
      meteor_plot = plot_object(meteor_objects, meteor_video_file)
      mt = open(meteor_file, "w")
      mt.write(str(objects))
      mt.close()

      #print("OBJ:", object)
      #print("START: ", object['first']) 
      #print("END: ", object['last']) 
      #trim_meteor(trim_file, object['first'][0], object['last'][0])

   else:
      print ("NO METEOR", objfail_file)
      
      meteor_plot = plot_object(objects, trim_file)
      mt = open(objfail_file, "w")
      mt.write(str(objects))
      mt.close()




   return()

   stacked_image_np = np.asarray(trim_stack)
   found_objects, moving_objects = object_report(trim_file, frame_data)

   stacked_image = draw_obj_image(stacked_image_np, moving_objects,trim_file, stacked_image_np)

   #if sys.argv[1] == 'sf':
      #cv2.namedWindow('pepe')
      #cv2.imshow('pepe', stacked_image)
      #cv2.waitKey(30)
   passed,all_objects = test_objects(moving_objects, trim_file, stacked_image_np)

   meteor_found = 0
   meteor_objects = []
   for object in all_objects:
      #print("OID:", object['oid'])
      #print("METEOR YN:", object['meteor_yn'])
      if object['meteor_yn'] == 1:
         print("START: ", object['first']) 
         print("END: ", object['last']) 
         trim_meteor(trim_file, object['first'][0], object['last'][0])
         meteor_found = 1
         meteor_objects.append(object)


   cmd = "./stack-stack.py stack_vid " + trim_file + " mv"
   os.system(cmd)
   print("STACK", cmd)

   #for object in meteor_objects:
   #   check_final_stack(trim_stack,object)

   meteor_found = 0

   for object in meteor_objects:
      if object['meteor_yn'] == 1:
         for key in object:
            print(key,object[key])
         box = str(object['box'])
         elp_time = object['elp_time'] + 1
         box = box.replace(" ", "")
         box = box.replace("[", "")
         box = box.replace("]", "")
         cmd = "./doHD.py " + meteor_video_file + " " + str(elp_time) + " " + str(box_str)
         print("DOHD:", cmd)
         os.system(cmd)
         meteor_found = 1

def reduce_hd_crop(trim_file, hd_crop, show = 0):
   if show == 1:
      cv2.namedWindow('pepe')

   objects = []
   bp_objects = []
   print("REDUCE FILE:", trim_file, hd_crop)
   frames = load_video_frames(hd_crop)
   ih,iw = frames[0].shape 

   image_acc = np.empty(np.shape(frames[0]))
   crop_stack_file = hd_crop.replace(".mp4", "-stacked.png")

   crop_stack = cv2.imread(crop_stack_file)

   el = trim_file.split("/")
   fn = el[-1]
   sd_trim_file_name = fn

   nel = trim_file.split("-trim")
   xxx = nel[-1]
   yyy = xxx.split("-")
   trim_num = int(yyy[0])
   print("XXX:", xxx)
   print("TRIM FILE:", trim_file)
   print("TRIM NUM:", trim_num)

   dd = fn.split("_")
   YY = dd[0]
   MM = dd[1]
   DD = dd[2]
   HH = dd[3]
   MN = dd[4]
   SS = dd[5]
   EX = dd[6]

   f_date_str = YY + "-" + MM + "-" + DD + " " + HH + ":" + MN + ":" + SS
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")

   meteor_base_dir = "/mnt/ams2/SD/proc2/meteors/"
   meteor_day_dir = "/mnt/ams2/SD/proc2/meteors/" + YY + "_" + MM + "_" + DD + "/"

  

   meteor_json_file = meteor_day_dir + sd_trim_file_name + ".json"
   meteor_json_file = meteor_json_file.replace(".mp4", "")

   meteor_json = load_json_file(meteor_json_file)
   meteor_json['trim_file'] =  meteor_day_dir + sd_trim_file_name
   meteor_json['trim_stack'] = meteor_day_dir + sd_trim_file_name.replace(".mp4", "-stacked.png")
   meteor_json['trim_stack_obj'] = meteor_day_dir + sd_trim_file_name.replace(".mp4", "-obj_stacked.png")
   meteor_json['hd_crop'] = hd_crop
   hd_trim = hd_crop.replace("-crop", "")
   meteor_json['hd_trim'] = hd_trim
   meteor_json['hd_trim_stack'] = hd_trim.replace(".mp4", "-stacked.png")
   meteor_json['hd_crop_stack'] = hd_crop.replace(".mp4", "-stacked.png")



   extra_sec = int(trim_num) / 25
   #print("FDATE Time:", f_datetime)
   #print("Extra:", extra_sec)
   start_frame_time = f_datetime + datetime.timedelta(0,extra_sec)

   start_frame_num = trim_num

   #cv2.namedWindow('pepe')
   frame_height, frame_width = frames[0].shape
   fc = 0

   last_frame = None
   frame_data = []

   med_frames = median_frames(frames)
   masked_pixels = []
   thresh = np.mean(med_frames) 
   thresh = find_best_thresh(med_frames[0], thresh+ 5)
   _, threshold = cv2.threshold(med_frames.copy(), thresh, 255, cv2.THRESH_BINARY)
   thresh_obj = cv2.convertScaleAbs(threshold)
   (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   for (i,c) in enumerate(cnts):
      x,y,w,h = cv2.boundingRect(cnts[i])
      cv2.rectangle(med_frames, (x, y), (x+w, y+h), (255,255,255), 1) 
      x = int(x + (w/2))
      y = int(y + (h/2))
      masked_pixels.append((x,y))

   if show == 1:
      cv2.imshow("pepe", med_frames)
      cv2.waitKey(10)

   thresh = np.mean(frames[0]) + 15
   next_thresh = thresh + 10

   for frame in frames:
      frame = adjustLevels(frame, 10,1,254)
      frame = cv2.convertScaleAbs(frame)
      if show == 1:
         cv2.imshow('pepe', frame) 
         cv2.waitKey(10)
      #print(frame.shape)
      frame = mask_frame(frame, masked_pixels,5)
      extra_sec = (start_frame_num + fc) /  25
      frame_time = f_datetime + datetime.timedelta(0,extra_sec)
    

      #BP Threshold      
      frame = cv2.GaussianBlur(frame, (7, 7), 0)
      _, threshold = cv2.threshold(frame.copy(), thresh, 255, cv2.THRESH_BINARY)
      threshold = cv2.convertScaleAbs(threshold)
      (_, bp_cnts, xx) = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      #if show == 1:
      #   cv2.imshow('pepe', threshold) 
      #   cv2.waitKey(10)

      alpha = .33
      #hello = cv2.accumulateWeighted(frame, image_acc, alpha)
      hello = cv2.accumulateWeighted(threshold, image_acc, alpha)


      # IMG DIFF THRESHOLD
      image_diff = cv2.absdiff(image_acc.astype(frame.dtype), threshold,)
      _, threshold = cv2.threshold(image_diff.copy(), next_thresh, 255, cv2.THRESH_BINARY)
      thresh_obj = cv2.convertScaleAbs(threshold)
      (_, cnts, xx) = cv2.findContours(thresh_obj.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

      #cv2.imshow('pepe', image_diff)
      #cv2.waitKey(10)
      if len(bp_cnts) >  0:
         for (i,c) in enumerate(bp_cnts):
            x,y,w,h = cv2.boundingRect(bp_cnts[i])
            y2 = y + h
            x2 = x + w
            mx = int(x + (w/2))
            my = int(y + (w/2))
            cnt_img = frame[y:y2,x:x2]
            max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img)
            bp_object, bp_objects = id_object(bp_cnts[i], bp_objects,fc, (mx,my), 1)
            #cv2.circle(thresh_obj, (int(mx),int(my)), 1, (0,0,0), 1)




      if len(cnts) >  0:
         for (i,c) in enumerate(cnts):
            x,y,w,h = cv2.boundingRect(cnts[i])
            if w > 1 and h > 1:
               y2 = y + h
               x2 = x + w
               mx = int(x + (w/2))
               my = int(y + (w/2))
               cnt_img = frame[y:y2,x:x2]
               max_px, avg_px, px_diff,max_loc = eval_cnt(cnt_img)
               object, objects = id_object(cnts[i], objects,fc, (mx,my), 1)

               cv2.putText(thresh_obj, str(object['oid']), (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
               #cv2.rectangle(thresh_obj, (x, y), (x2, y2), (255,255,255), 1) 
               cv2.circle(thresh_obj, (int(mx),int(my)), 1, (0,0,0), 1)


      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      cv2.putText(thresh_obj, str(fc), (5,ih-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)

      cv2.putText(thresh_obj, str(frame_time_str), (25,ih-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
      #cv2.imshow('pepe', thresh_obj)
      #cv2.waitKey(10)
      fc = fc + 1
      last_frame = frame

   meteor_objects = []

   noise_objs = []

   for object in objects:
      tests_passed = 1
      min_x,min_y,max_x,max_y,minmax_dist,minmax_ang = min_max_hist(object['history'])
      object['box'] = [min_x,min_y,max_x,max_y]
      oid = object['oid']
      status, reason = meteor_test_distance(object)
      print("\n\nTEST OBJECT:",oid)
      print("-----------------------------")
      if status == 0:
         tests_passed = 0 
         print("DIST TEST FAILED", object['oid'], reason)
      else:
         print("DIST TEST PASSED", object['oid'], reason)



      status, reason = meteor_test_hist_len(object)
      if status == 0:
         tests_passed = 0 
         print("HIST LEN TEST FAILED", object['oid'], reason)
      else:
         print("HIST LEN PASSED", object['oid'], reason)

      if tests_passed == 1:
         print(object)
         if object['history'] is not None:
            status, reason = meteor_test_noise(object['history'])

            
            if status == 0:
               tests_passed = 0
               noise_objs.append(object)
      
      if tests_passed == 1:

         status, reason = meteor_test_dupe_px(object)
         if status == 0:
            tests_passed = 0 
            print("DUPE TEST FAILED", object['oid'], reason)
         else:
            print("DUPE TEST PASSED", object['oid'], reason)


      if tests_passed == 1:
         match_perc = meteor_test_fit_line(object)
         if float(match_perc) < .5:
            tests_passed = 0 
         else:
            print("FIT TEST PASSED", object['oid'], match_perc)

      if tests_passed == 1:
         status, reason = meteor_test_peaks(object)
         print("PEAKS:", status, reason)
         if status == 0:
            print("PEAK TEST FAILED", object['oid'], reason)
            tests_passed = 0 
         else:
            print("PEAK TEST PASSED", object['oid'], reason)


      if tests_passed == 1:
         meteor_objects.append(object)
         print("\nMETEOR TESTS PASSED FOR:",oid)
         print("-----------------------------\n\n")
      else:
         print("\nMETEOR TESTS FAILED FOR :",oid)
         print("-----------------------------\n\n")

   if len(meteor_objects) == 1:
      object = meteor_objects[0]
      clog = open("crop_log.txt", "a")
      clog.write("passed" +  trim_file + " " + hd_crop + "\n")
      clog.close()

      print(object)
      x_dir,y_dir,x_dir_txt,y_dir_txt = direction(object['history'])
      print(x_dir,y_dir,x_dir_txt,y_dir_txt)

      print("CROP STACK FILE:", crop_stack_file)
  
      meteor_json['frames'] = {}
 
      for hs in object['history']:
         fn,x,y,w,h,mx,my = hs
         extra_sec = (start_frame_num + fn) /  25
         frame_time = f_datetime + datetime.timedelta(0,extra_sec)
         cx,cy = moving_cnt(hs,x_dir,y_dir)
         #cv2.rectangle(crop_stack, (x, y), (x+w, y+w), (255,255,255), 1) 
         cv2.circle(crop_stack, (int(cx),int(cy)), 1, (255,0,0), 1)
         meteor_json['frames'][fn] = {}
         meteor_json['frames'][fn]['frame_time'] = str(frame_time)
         meteor_json['frames'][fn]['xywh'] = [x,y,w,h] 
         meteor_json['frames'][fn]['mxmy'] = [mx,my] 
         meteor_json['frames'][fn]['cxcy'] = [cx,cy] 

      cv2.putText(crop_stack, "METEOR!", (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,0,255), 1)
      #meteor_json['box'] = object['box']
      print("BOXBOX:", object['box'])
      hd_stack_img = cv2.imread(meteor_json['hd_trim_stack'], 0)
      #hd_stack_img, bbox = bigger_box([min_x,min_y,max_x,max_y], meteor_json['hd_trim_stack'], hd_stack_img)
      meteor_json['noise_objs'] = noise_objs


   else:
      clog = open("crop_log.txt", "a")
      clog.write("failed" +  trim_file + " " + hd_crop + "\n")
      clog.close()
      cv2.putText(crop_stack, "FAILED.", (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (0,0,255), 1)
      print("Meteor failed cropping test. :(", len(meteor_objects))
      for obj in meteor_objects:
         print(obj)
      exit()

   print("BP OBJ", len(bp_objects))
   #for object in bp_objects:
   #   for hs in object['history']:
   #      fn,x,y,w,h,mx,my = hs
   #      cv2.circle(crop_stack, (int(x),int(y)), 5, (255,255,0), 1)

   for object in meteor_objects:
      for hs in object['history']:
         fn,x,y,w,h,mx,my = hs
         cv2.circle(crop_stack, (int(x),int(y)), 10, (255,255,0), 1)
         cv2.putText(crop_stack, str(object['oid']), (x,y), cv2.FONT_HERSHEY_SIMPLEX, .4, (255,255,255), 1)
   print("METEOR JSON:", meteor_json)
   print("METEOR JSON FILE:", meteor_json_file)


   save_json_file(meteor_json_file, meteor_json)
   cmd = "./cal-meteor.py " + meteor_json_file
   print(cmd)
   os.system(cmd)
   #cv2.imshow('pepe', crop_stack)
   #cv2.waitKey(10)

def moving_cnt(hs,x_dir,y_dir):
   fn,x,y,w,h,mx,my = hs
   if x_dir == 1 and y_dir == 1:
      x = x 
      y = y 
   if x_dir == -1 and y_dir == 1:
      x = x + w
      y = y 
   if x_dir == 1 and y_dir == -1:
      x = x 
      y = y 
   if x_dir == -1 and y_dir == -1:
      x = x + w
      y = y + h



   return(x,y)


def merge_meteor_objects(meteor_objects):
   print(meteor_objects)

def scan_dir(dir):
   files = glob.glob(dir + "/*trim*.mp4")
   for file in files:
     if "meteor" not in file:
        print(file)
        scan_trim_file(file) 

cmd = sys.argv[1]
if cmd == 'reduce' or cmd == 'reduce_hd_crop':
   if len(sys.argv) == 4:
      show = sys.argv[3]
   else: 
      show = 0
   trim_file = sys.argv[2]
   hd_crop_file = sys.argv[3]
   reduce_hd_crop(trim_file, hd_crop_file, show)

if cmd == 'sf':
   trim_file = sys.argv[2]
   if len(sys.argv) == 4:
      show = sys.argv[3]
   else: 
      show = 0
   trim_file = trim_file.replace("-meteor.mp4", ".mp4")
   scan_trim_file(trim_file, show)
if cmd == 'scan_dir':
   sdir = sys.argv[2]
   scan_dir(sdir)
