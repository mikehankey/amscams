import math
import numpy as np

def gap_test(fns):
   total_gaps = 0
   gap_events = 0
   total_fns = len(fns)
   fn_dur = fns[-1] - fns[0]
   for i in range(0, len(fns)):
      fn = fns[i]
      if i > 0 and last_fn is not None:
         gap = fn - last_fn - 1
         if gap > 1:
            print("FN GAP:", fn, last_fn, gap)
            total_gaps += gap
            gap_events += 1
      last_fn = fn

   print("GAP TEST RESULTS:")
   print("Total FNS:", total_fns)
   print("FN Dur:", fn_dur)
   print("Total Gaps:", total_gaps)
   print("Gap Events:", gap_events)
   gap_test_info = {}
   gap_test_info['total_fns'] = total_fns
   gap_test_info['fn_dur'] = fn_dur
   gap_test_info['total_gaps'] = total_gaps
   gap_test_info['gap_events'] = gap_events
   if gap_events > 5 or total_gaps > 10:
      return(0, gap_test_info)
   else:
      return(1, gap_test_info)

def analyze_intensity(ints):
   pos_vals = []
   neg_vals = []
   for int_val in ints:
      if int_val > 0:
         pos_vals.append(int_val)
      else:
         neg_vals.append(int_val)


   if len(neg_vals) > 0:
      pos_neg_perc = len(pos_vals) / (len(pos_vals) + len(neg_vals))
   else:
      pos_neg_perc = 1
   if len(pos_vals) == 0:
      return(0, 1, [])


   max_int = max(pos_vals)
   min_int = min(pos_vals)
   max_times = max_int / min_int
   perc_val = []
   for int_val in pos_vals:
      if max_int > 0:
         mxt = int_val / max_int
      else:
         mxt = 0
      perc_val.append(mxt)
   return(max_times, pos_neg_perc, perc_val)

def meteor_dir_test(fxs,fys):
   fx = fxs[0]
   fy = fys[0]
   lx = fxs[-1]
   ly = fys[-1]
   fdir_x = lx - fx 
   fdir_y = ly - fy

   if fdir_x < 0:
      fx_dir_mod = 1
   else:
      fx_dir_mod = -1
   if fdir_y < 0:
      fy_dir_mod = 1
   else:
      fy_dir_mod = -1


   match = 0
   nomatch = 0


   for i in range(0,len(fxs)):
      x = fxs[i]
      y = fys[i]
      dir_x = x - fx 
      dir_y = y - fy
      if dir_x <= 0:
         x_dir_mod = 1
      else:
         x_dir_mod = -1
      if dir_y < 0:
         y_dir_mod = 1
      else:
         y_dir_mod = -1

      if x_dir_mod == fx_dir_mod or dir_x <= 1:
         match = match + 1
      else:
         nomatch = nomatch + 1

      if y_dir_mod == fy_dir_mod or dir_y <= 1:
         match = match + 1
      else:
         nomatch = nomatch + 1

 
   if len(fxs) > 0: 
      perc = match / (len(fxs)*2)
   else:
      perc = 1
   return(perc)

def meteor_dir(fx,fy,lx,ly):
   # positive x means right to left (leading edge = lowest x value)
   # negative x means left to right (leading edge = greatest x value)
   # positive y means top to down (leading edge = greatest y value)
   # negative y means down to top (leading edge = lowest y value)
   dir_x = lx - fx 
   dir_y = ly - fy
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1
   return(x_dir_mod, y_dir_mod)


def one_dir_test(object):
   last_x = None
   last_x_dir_mod = None
   first_x = object['oxs'][0]
   first_y = object['oys'][0]
   xerrs = 0
   yerrs = 0
   for i in range(0,len(object['oxs'])):
      fn = object['ofns'][i]
      x = object['oxs'][i]
      y = object['oys'][i]
      if last_x is not None:
         dir_x = first_x - x 
         dir_y = first_y - y
         if dir_x < 0:
            x_dir_mod = 1
         else:
            x_dir_mod = -1
         if dir_y < 0:
            y_dir_mod = 1
         else:
            y_dir_mod = -1
         if last_x_dir_mod is not None:
            if x_dir_mod != last_x_dir_mod:
               xerrs = xerrs + 1
            if y_dir_mod != last_y_dir_mod:
               yerrs = yerrs + 1

         last_x_dir_mod = x_dir_mod
         last_y_dir_mod = y_dir_mod
      last_x = x 
      last_y = y
   dir_mod_errs = xerrs + yerrs
   dir_mod_err_perc = dir_mod_errs / len(object['oxs'])
   if dir_mod_errs == 0:
      return(1)
   if dir_mod_err_perc > .2:
      return(0)
   else:
      return(1)



def big_cnt_test(object,hd=0):
   sizes = []
   big = 0
   sz_thresh = 20
   if hd == 1:
      sz_thresh = 40

   for i in range(0, len(object['ofns'])):
      w = object['ows'][i]
      h = object['ohs'][i]
      if w > sz_thresh:
         big += 1
      if h > sz_thresh:
         big += 1
      sizes.append(w)
      sizes.append(h)
   tot = len(sizes)
   if len(sizes) > 0:
      perc_big = big / len(sizes)
   return(perc_big)

def obj_cm(ofns):
   #cm
   fc = 0
   cm = 1
   max_cm = 1
   last_fn = None
   for fn in ofns:
      if last_fn is not None:
         if int(last_fn) + 1 == int(fn) or int(last_fn) + 2 == int(fn):
            cm = cm + 1
            if cm > max_cm :
               max_cm = cm

      fc = fc + 1
      last_fn = fn
   return(max_cm)


def filter_bad_objects(objects):
   bad_objs = []
   for id in objects:
     obj = objects[id]
     if "report" in obj:
        if obj['report']['non_meteor'] == 1:
           bad_objs.append(id)

     elif len(obj['ofns']) < 2 :
        bad_objs.append(id)

   for id in bad_objs:
      del(objects[id])
   return(objects)
        


def check_pt_in_mask(masks, px,py):
   for m in masks:
      x1,y1,w,h = m.split(",")
      x1 = int(x1)
      y1 = int(y1)
      w = int(w)
      h = int(h)
      x2 = x1 + w
      y2 = y1 + h
      if x1 <= px <= x2 and y1 <= py <= y2:
         return(1)
   return(0)


def unq_points(object):
   points = {}
   tot = 0
   unq_tot = 0
   for i in range(0, len(object['oxs'])):
      x = object['oxs'][i]
      y = object['oys'][i]
      key = str(x) + "." + str(y)
      if key not in points: 
         points[key] = 1
         unq_tot += 1
     
      tot = tot + 1

   perc = unq_tot / tot
   return(perc, unq_tot)


def calc_line_segments(xobj):
   dist_from_start = []
   line_segs = []
   x_segs = []
   ms = []
   bs = []
   fx, fy = xobj['oxs'][0],xobj['oys'][0]

   # find distance from start point for each frame
   # turn that into seg_dist for each frame

   for i in range(0, len(xobj['ofns'])):
      tx = xobj['oxs'][i]
      ty = xobj['oys'][i]
      dist = calc_dist((fx,fy),(tx,ty))
      dist_from_start.append(dist)
      if i > 0 and i < len(xobj['ofns']) and len(xobj['ofns']) > 2:
         tm,tb = best_fit_slope_and_intercept([fx,tx],[fy,ty])
         seg_len = dist_from_start[i] - dist_from_start[i-1]
         line_segs.append(seg_len)
         x_segs.append(xobj['oxs'][i-1] - tx)
         ms.append(tm)
         bs.append(tb)

      else:
         x_segs.append(0)
         line_segs.append(0)
         ms.append(0)
         bs.append(0)

   #xobj['dist_from_start'] = dist_from_start
   #xobj['line_segs'] = line_segs
   #xobj['x_segs'] = x_segs
   #xobj['ms'] = ms 
   #xobj['bs'] = bs



   return(dist_from_start, line_segs, x_segs, ms, bs)


def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist

def find_angle(p1,p2):
   myrad = math.atan2(p1[1]-p2[1],p1[0]-p2[0])
   mydeg = math.degrees(myrad)
   return(mydeg)

def find_slope(p1,p2):
   (x1,y1) = p1
   (x2,y2) = p2
   top = y2 - y1
   bottom = x2 - y2
   if bottom != 0:
      slope = top / bottom
   else:
      slope = 0
   return(slope)



def calc_obj_dist(obj1, obj2):
   x1,y1,w1,h1 = obj1
   x2,y2,w2,h2 = obj2
   pts1 = []
   pts2 = []
   pts1.append((x1,y1))
   pts1.append((x1+w1,y1))
   pts1.append((x1,y1+h1))
   pts1.append((x1+w1,y1+h1))
   pts1.append((x1+int(w1/2),y1+int(h1/2)))

   pts2.append((x2,y2))
   pts2.append((x2+w2,y2))
   pts2.append((x2,y2+h2))
   pts2.append((x2+w2,y2+h2))
   pts2.append((x2+int(w2/2),y2+int(h2/2)))
   all_dist = []
   for a,b in pts1:
      for d,e in pts2:

         dist = calc_dist((a,b),(d,e))
         all_dist.append(dist)

   min_dist = min(all_dist)
   return(min_dist) 

def meteor_direction(fx,fy,lx,ly):
   # positive x means right to left (leading edge = lowest x value)
   # negative x means left to right (leading edge = greatest x value)
   # positive y means top to down (leading edge = greatest y value)
   # negative y means down to top (leading edge = lowest y value)
   dir_x = lx - fx 
   dir_y = ly - fy
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1
   return(x_dir_mod, y_dir_mod)

def best_fit_slope_and_intercept(xs,ys):
    xs = np.array(xs, dtype=np.float64)
    ys = np.array(ys, dtype=np.float64)
    if len(xs) < 3:
       return(0,0)
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

    b = np.mean(ys) - m*np.mean(xs)
    if math.isnan(m) is True:
       m = 1
       b = 1

    return m, b

def meteor_direction_test(fxs,fys):
   fx = fxs[0]
   fy = fys[0]
   lx = fxs[-1]
   ly = fys[-1]
   fdir_x = lx - fx 
   fdir_y = ly - fy

   if fdir_x < 0:
      fx_dir_mod = 1
   else:
      fx_dir_mod = -1
   if fdir_y < 0:
      fy_dir_mod = 1
   else:
      fy_dir_mod = -1


   match = 0
   nomatch = 0

   for i in range(0,len(fxs)):
      x = fxs[i]
      y = fys[i]
      dir_x = x - fx 
      dir_y = y - fy
      if dir_x < 0:
         x_dir_mod = 1
      else:
         x_dir_mod = -1
      if dir_y < 0:
         y_dir_mod = 1
      else:
         y_dir_mod = -1

      if x_dir_mod == fx_dir_mod :
         match = match + 1
      else:
         nomatch = nomatch + 1

      if y_dir_mod == fy_dir_mod :
         match = match + 1
      else:
         nomatch = nomatch + 1

 
   if len(fxs) > 0: 
      perc = match / len(fxs)
   else:
      perc = 0
   return(perc)

def arc_seconds_to_degrees(arc_seconds):
   # 1 arc second this many degrees
   min_deg_conv = 0.00027777777
   return(arc_seconds * min_deg_conv)

def ang_dist_vel(xs=[], ys=[],azs=[],els=[], pixscale=155):
   #px_dist = calc_dist((x[-1],y[-1]), (x[0],y[0]))

   #angular_separation = np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2)
   #angular_separation_px = np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2) / float(fns[-1] - fns[0])
   #angular_velocity_px = angular_separation_px * 25

   #angular_separation_deg = (angular_separation * px_scale) / 3600

   # Convert to deg/sec
   #scale = (config.fov_h/float(config.height) + config.fov_w/float(config.width))/2.0



   # Formula for finding ang_dist and vel from px
   if len(xs) > 0:
      px_dist = calc_dist((min(xs),min(ys)), (max(xs), max(ys)))
      ang_dist = px_dist * pixscale
      ang_dist = arc_seconds_to_degrees(ang_dist)
      # to find angular velocity per second in degrees 
      ang_vel = ang_dist / (len(xs) / 25)
   # Formula for finding ang_dist and vel from az,el 
   #if len(azs) > 0:
   return(ang_dist, ang_vel)
       
def angularSeparation(ra1, dec1, ra2, dec2):
    """ Calculates the angle between two points on a sphere. 
    
    Arguments:
        dec1: [float] Declination 1 (radians).
        ra1: [float] Right ascension 1 (radians).
        dec2: [float] Declination 2 (radians).
        ra2: [float] Right ascension 2 (radians).
    Return:
        [float] Angle between two coordinates (radians).
    """

    return np.arccos(np.sin(dec1)*np.sin(dec2) + np.cos(dec1)*np.cos(dec2)*np.cos(ra2 - ra1))
