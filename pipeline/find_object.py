import math
import numpy as np
def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h, intensity=0, hd=0, sd_multi=1, cnt_img=None , obj_tdist = None):
   #print("FIND OBJ:", fn, cnt_x, cnt_y, cnt_w, cnt_h)
   matched = {}
   if hd == 1:
      obj_dist_thresh = 80
   else:
      obj_dist_thresh = 30
   if obj_tdist is not None:
      obj_dist_thresh = obj_tdist

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
                  #print("THIS/LAST SEG:", obj, this_seg_dist, last_seg_dist, abs_diff)
                  last_fn_diff = fn - objects[obj]['ofns'][-1]
                  if abs_diff > 20 or this_seg_dist > 20 or last_fn_diff > 7:
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


            #print("DIFF:", dist, obj_dist_thresh)
            if dist < obj_dist_thresh : #and last_frame_diff < 15:
               #if this is linked to a meteor only associate if the point is further from the start than the last recorded point
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
                  #print("ABS DIFF:", abs_diff)
                  if abs_diff > obj_dist_thresh:
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
      #for nc in not_close_objs:
      #   print("not close" , nc)
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
      #print("FS", objects[id]['fs_dist'])
      #print("SEGS:", objects[id]['segs'])
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

def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist

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
