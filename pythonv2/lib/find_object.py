from lib.UtilLib import calc_dist
def find_object(objects, fn, cnt_x, cnt_y, cnt_w, cnt_h, intensity=0, hd=0, sd_multi=1, cnt_img=None ,classify=1):
   print("*** FIND OBJ START")
   matched = {}
   if hd == 1:
      obj_dist_thresh = 75
   else:
      obj_dist_thresh = 35

   center_x = cnt_x + int(cnt_w/2)
   center_y = cnt_y + int(cnt_h/2)

   found = 0
   max_obj = 0
   closest_objs = []
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
            print("CDIST/MDIST", c_dist, dist)
            dist_objs.append((obj,dist))
            last_frame_diff = fn - lfn

            if dist < obj_dist_thresh and last_frame_diff < 10:
               #if this is linked to a meteor only associate if the point is further from the start than the last recorded point
               found = 1
               found_obj = obj
               #if obj not in matched:
               closest_objs.append((obj,dist))
               matched[obj] = 1

      if obj > max_obj:
         max_obj = obj


   if len(closest_objs) > 1:
      print("FIND: MORE THAN ONE MATCH!")

      ci = sorted(closest_objs , key=lambda x: (x[1]), reverse=False)
      print(ci)
      found =1
      found_obj = ci[0][0]
      #c = input("Continue")
      #exit()

   if found == 0:
      dist_objs = sorted(dist_objs, key=lambda x: (x[1]), reverse=False)
      print("FIND: * * * * * * * OBJECT NOT FOUND. MAKE NEW ONE.", dist_objs)
      print(" * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * ")

      obj_id = max_obj + 1
      #if obj_id > 10:
      #   cc = input("cont")
      #if obj_id > 20:
      #   c = input("Continue")
      objects[obj_id] = {}
      objects[obj_id]['obj_id'] = obj_id
      objects[obj_id]['ofns'] = []
      objects[obj_id]['oxs'] = []
      objects[obj_id]['oys'] = []
      objects[obj_id]['ows'] = []
      objects[obj_id]['ohs'] = []
      objects[obj_id]['oint'] = []
      objects[obj_id]['ofns'].append(fn)
      objects[obj_id]['oxs'].append(cnt_x)
      objects[obj_id]['oys'].append(cnt_y)
      objects[obj_id]['ows'].append(cnt_w)
      objects[obj_id]['ohs'].append(cnt_h)
      objects[obj_id]['oint'].append(intensity)
      found_obj = obj_id
      print("FIND NEW OBJ:", found_obj)
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
         objects[found_obj]['ofns'].append(fn)
         objects[found_obj]['oxs'].append(cnt_x)
         objects[found_obj]['oys'].append(cnt_y)
         objects[found_obj]['ows'].append(cnt_w)
         objects[found_obj]['ohs'].append(cnt_h)
         objects[found_obj]['oint'].append(intensity)
         print("FIND: OBJ FOUND:", found_obj)


   #objects[found_obj] = analyze_object_old(objects[found_obj], hd, sd_multi, 1)
   #if objects[found_obj]['report']['meteor_yn'] == 'Y':
   #   max_int = max(objects[found_obj]['oint'])
   #   if max_int > 25000:
   #      objects[found_obj]['report']['obj_class'] = "fireball"
   print("*** FIND OBJ END")

   return(found_obj, objects)


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
   print("DISTS:", sorted(ds))
   return(min(ds))


