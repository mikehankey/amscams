from scipy import signal
import cv2
import numpy as np
from lib.UtilLib import calc_dist
import math

def best_fit_slope_and_intercept(xs,ys):
    xs = np.array(xs, dtype=np.float64)
    ys = np.array(ys, dtype=np.float64)
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

    b = np.mean(ys) - m*np.mean(xs)

    return m, b

def max_xy(x,y,w,h,max_x,max_y,min_x,min_y,mute_wh=0):
   # ignore w,h
   if mute_wh == 1:
      w = 0
      h = 0

   if x + w > max_x:
      max_x = x + w
   if y + h > max_y:
      max_y = y + h
   if x < min_x:
      min_x = x
   if y < min_y:
      min_y = y
   return(max_x,max_y,min_x,min_y)


def find_min_max_dist(hist,mute_wh=0):
   max_x = 0
   max_y = 0
   min_x = 10000
   min_y = 10000
   for hs in hist:
      if len(hs) == 7:
         fn,x,y,w,h,mx,my = hs
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hs
      max_x, max_y,min_x,min_y = max_xy(x,y,w,h,max_x,max_y,min_x,min_y,mute_wh)

   return(max_x,max_y,min_x,min_y)

def test_score(test_results):
   score = 0
   for test, result, desc in test_results:
      score = score + result
   return(score)

def validate_objects(objects,frames ):
   meteor_found = 0
   new_objects = []
   for object in objects:
      status, intensity,px_diffs,avg_vals,hist = intensity_test(object, frames)
      if status == 0: 
         object['meteor'] = status
      if object['meteor'] == 1:
         meteor_found = 1
      object['intensity'] = intensity
      object['px_diffs'] = px_diffs 
      object['avg_vals'] = avg_vals 
      object['test_results'].append(("intensity", status, np.mean(intensity)))

      new_objects.append(object)
   return(new_objects, meteor_found)

def intensity_test(object, frames):
   intensity = []
   px_diffs = []
   avg_vals = []
   new_hist = []
   for hist in object['history']:
      if len(hist) == 7:
         fn,x,y,w,h,mx,my = hist
      if len(hist) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hist
      crop = frames[fn][y:y+h,x:x+w]
      crop_bg = frames[0][y:y+h,x:x+w]
      avg_crop = np.mean(crop)
      avg_bg = np.mean(crop_bg)
      min_val, max_val, min_loc, (bmx,bmy)= cv2.minMaxLoc(crop)
      px_diff = max_val - avg_crop 
      obj_val = int(np.sum(crop)) 
      bg_val  = np.sum(crop_bg)
      intensity.append(obj_val-bg_val)
      px_diffs.append(px_diff)
      avg_vals.append(avg_crop)
      new_hist.append(hist)

   avg_int = int(np.mean(intensity))
   if avg_int < 10:
      status = 0
   else:
      status = 1
   return(status, intensity, px_diffs, avg_vals,hist)

   

def test_objects(objects,frames):
   total_frames = len(frames)
   meteor_found = 0
   meteors = 0
   new_objects = []
   total_objects = len(objects)
   for object in objects:
      status, test_results = test_object(object, total_frames)

      object['total_frames'] = total_frames
      object['meteor'] = status
      object['test_results'] = test_results
      score = test_score(test_results)
      object['first_last'] = [object['history'][0][0],object['history'][-1][0]]
      object['score'] = score
      new_objects.append(object)
      if status == 1:
         meteors = meteors + 1
         meteor_found = 1
   # over-riding noise test
   #if meteors > 1:
   #   if len(new_objects) > 20:
   #      failed_objects = []
   #      for object in objects:
            #object['meteor'] = 0
   #         object['test_results'].append(('Clip Noise', 0,'Too much noise.'))
   #         failed_objects.append(object)
         #meteor_found = 0
   #      new_objects = failed_objects

   # over-ridding big cnts test (for cars etc)
   if meteors >= 1:
      failed_objects = []
      big_cnts = 0
      for object in objects:
         for test in object['test_results']:
            if "Big CNT" in test:
               tname, tstatus,tdesc = test
               xx,yy = tdesc.split(",")
               stuff = yy.split(" ")
               if stuff[1] != "":
                  big_cnt = int(stuff[1])
                  big_cnts = big_cnts + big_cnt
      if big_cnts > 200 and total_objects > 20:
         for object in objects:
            object['meteor'] = 0
            object['test_results'].append(('Big CNTs', 0,'Too many big CNTs:' + str(big_cnts)))
            failed_objects.append(object)
         new_objects = failed_objects 
         meteor_found = 0

   # BG / Intensity test / px diff
   
     
   sorted_objects = sorted(new_objects, key = lambda i: i['score'], reverse=True) 

   return(sorted_objects, meteor_found)

def test_object(object, total_frames):
   status = 1
   results = []
   first_frame = object['history'][0][0]
   last_frame = object['history'][-1][0]
   # Dist test
   dist = meteor_test_distance(object) 
   if float(dist) <= 5:
      results.append(('Distance', 0, dist))
      status = 0
   else:
      results.append(('Distance', 1, dist))

   # Trailer Test
   trailer_test, desc = meteor_test_trailer(object,total_frames)
   if trailer_test == 0:
      status = 0
   results.append(('Trailer', trailer_test, desc))

   # Hist Len test
   hist_test,desc = meteor_test_hist_len(object) 
   results.append(('Hist Len', hist_test, desc))
   if hist_test == 0:
      status = 0

   # ELP Frames test
   elp_frames = meteor_test_elp_frames(object) 
   results.append(('Elp Frames', 1, elp_frames))

   (perc_pass,avg_avl,avl_segs) = meteor_test_direction(object)
   avl_test = 1
   if perc_pass < .5 and avg_avl > .9: 
      avl_test = 0
      status = 0
   desc = "{}/f ratio AVL test {} {}".format(perc_pass,avg_avl,str(avl_segs))
   results.append(('AVL', avl_test, desc))

   # BIG contour test
   big,big_perc = meteor_test_big(object) 
   big_test = 1
   if big_perc > .9:
      big_test = 0
      status = 0
   desc = "{:f} big/frame , {:d} big contours ".format(big_perc,big)
   results.append(('Big CNT', big_test, desc))
   if elp_frames > 100 and big == 0:
      results.append(('Length Size', 0, "Too long an event for for size."))
      status = 0

   # CM / GAPS
   cm_gap_test = 1
   cm,gaps,gap_events,cm_hist_len_ratio = meteor_test_cm_gaps(object)

   if int(gaps) > 10:
      status = 0
      cm_gap_test = 0

   if cm < 3:
      cm_gap_test = 0
      status = 0
   if cm_hist_len_ratio < .5 and gap_events > 1: 
      cm_gap_test = 0
      status = 0
   if gaps > 10 and gap_events > 1 and cm_hist_len_ratio < .5: 
      cm_gap_test = 0
      status = 0
   if first_frame > 10 and gap_events >= 1 and gaps > 10 and cm_hist_len_ratio < .5:
      cm_gap_test = 0
      status = 0
   
   if big >= cm:   
      status = 0
      desc = "More big cnts ({:d}) than cm ({:d})".format(big,cm)
      results.append(('Big/CM', 0, desc))

   desc = "{:d} cons motion, {:d} gap frames {:d} gap events {:2.2f} cm/hist".format(cm,gaps,gap_events,cm_hist_len_ratio) 
   if gaps >= cm and gap_events > 1:
      cm_gap_test = 0
      status = 0
   results.append(('CM/Gaps', cm_gap_test, desc))

   if len(object['history']) > 0:
      cm_to_hist = cm / len(object['history'])
      if cm_to_hist < .25:
         results.append(('CM To Hist', 0, "CM to Hist too Low:" + str(cm_to_hist)))
         status = 0
      

   # Speed test
   if elp_frames > 0:
      px_per_frame =dist / elp_frames
   else:
      px_per_frame = 0
      status = 0
   desc = "{:2.2f} px/frame".format(px_per_frame) 
   results.append(('PX/Frame', 1, desc))




   # Moving test
   moving,desc  = meteor_test_moving(object['history']) 
   results.append(('Moving', moving, desc))
   if moving == 0:
      status = 0

   # Dupe PX Test (indicates star)
   tot_fr, unq_fr, uperc = meteor_test_dupe_px(object) 
   uperc = uperc * 100
   desc = "{:0.0f} percent unique. {:d} of {:d} ".format(uperc,unq_fr,tot_fr) 
   dupe = 1
   if uperc < 30:
      dupe = 0
      status = 0
   if unq_fr < 4:
      status = 0
      desc = "Not enough unique frames: {:0.0f} percent unique. {:d} of {:d} ".format(uperc,unq_fr,tot_fr) 
   results.append(('Dupe Px', dupe, desc))

   # Noise Test
   noise_perc = meteor_test_noise(object['history']) 
   noise = 1
   desc = "{:0.0f}:1 object to frame ratio.".format(noise_perc) 
   if float(noise_perc) > 2.1:
      noise = 0
      status = 0
   results.append(('Noise', noise, desc))

   # Fit line test   
   #fit_test = 1
   #if status == 1:
   #   fit_perc = meteor_test_fit_line(object) * 100
   #else:
   #   fit_perc = 0
   #if fit_perc < 50:
   #   fit_test = 0
   #   status = 0
   #desc = "{:0.0f}% of points fit line.".format(fit_perc) 
   #results.append(('Line Fit', fit_test, desc))

   # Test Peaks
   peak_test = 1
   peaks, peak_perc = meteor_test_peaks(object) 
   peak_perc = peak_perc * 100
   if len(peaks[0]) > 50 and peak_perc > 35:
      peak_test = 0
      status = 0

   desc = "{:d} Peaks {:2.2f}% of frames.{:s}".format(len(peaks[0]), peak_perc,str(peaks[0])) 
   results.append(('Peaks', peak_test, desc))


   return(status, results)


def meteor_test_direction(object):
   # test direction and distance between frames determine consistency
   hist = object['history']
   last_dist = 0
   fc = 0
   segs = []
   st_segs = []
   avl_segs = []
   for hs in hist:
      if len(hs) == 7:
         fn,x,y,w,h,mx,my = hs
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hs
      x = x  
      y = y  
      if fc > 0:
         dist = calc_dist((lx,ly),(x,y))
         st_dist = calc_dist((fx,fy),(x,y))
         avl = st_dist / fc
         segs.append(dist)
         st_segs.append(st_dist)
         avl_segs.append(avl)
      else:
         fx = x 
         fy = y

      lx = x
      ly = y 
      fc = fc + 1 

   avg_avl = np.mean(avl_segs)
   std_d = std_dev(avl_segs)
   tpass = 0
   vdiff = avg_avl * .35
   for avl in avl_segs:
      if avg_avl - vdiff <= avl <= avg_avl + vdiff:
         tpass = tpass + 1

   if len(avl_segs) > 0:
      perc_pass = tpass / len(avl_segs)
   else:
      perc_pass = 0

   return(perc_pass,avg_avl,avl_segs)

def std_dev(data):
   avg = np.mean(data)
   new_data = []
   for n in data:
      d = (avg - n)**2
      new_data.append(d)
   new_avg = np.mean(new_data)
   std_d = math.sqrt(new_avg)
   return(std_d)

def meteor_test_trailer(object,total_frames):
   last_frame = object['history'][-1][0]
   fdiff = total_frames - last_frame 
   if fdiff < 3:
      return(0, "No trailer, event never ends. {:d} {:d} {:d}".format(total_frames, last_frame, fdiff))
   else:
      return(1, "Good trailer ending. {:d} {:d} {:d}".format(total_frames, last_frame, fdiff))

def meteor_test_moving(hist):

   (max_x,max_y,min_x,min_y) = find_min_max_dist(hist)
   dist = calc_dist((min_x,min_y),(max_x,max_y))
   if dist <= 1:
      return 0, "Object is NOT moving."
   else:
      return 1, "Object is moving."

def meteor_test_big(object):
   big = 0
   hist = object['history']
   for hs in hist:
      if len(hs) == 7:
         fn,x,y,w,h,mx,my = hs
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hs


      if w > 50 or h > 50:
         big = big + 1
   if big > 1 and len(hist) > 0:
      big_perc = big / len(hist)
   else:
      big_perc = 0
   return(big,big_perc)

def meteor_test_dupe_px(object):
   hist = object['history']
   xs = []
   ys = []
   for hs in hist:
      if len(hs) == 7:
         fn,x,y,w,h,mx,my = hs
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hs


      cx = int(x+ (w/2))
      cy = int(y+ (h/2))
      xs.append((x,y))
   ux = list(set(xs))
   ul = len(ux)
   tl = len(hist)

   if tl > 0:
      uperc = ul / tl
   else:
      uperc = 0

   return(tl, ul, uperc)

def meteor_test_noise(hist):

   objs_per_frame = {}
   for hs in hist:
      if len(hs) == 7:
         fn,x,y,w,h,mx,my = hs
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hs

      if fn not in objs_per_frame.keys():
         objs_per_frame[fn] = 1
      else:
         objs_per_frame[fn] = objs_per_frame[fn] + 1
   total_obf = 0
   for obf in objs_per_frame:
      total_obf = total_obf + objs_per_frame[obf]

   if len(objs_per_frame) > 0:
      perc = total_obf / len(objs_per_frame)

   return(perc)

def meteor_test_fit_line(object):
   oid = object['oid']
   hist = object['history']
   xs = []
   ys = []
   for hs in hist:
      if len(hs) == 7:
         fn,x,y,w,h,mx,my = hs
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hs

      cx = int(x+ (w/2))
      cy = int(y+ (h/2))
      xs.append(cx)
      ys.append(cy)
   m,b = best_fit_slope_and_intercept(xs,ys)

   max_x = max(xs)
   max_y = max(ys)
   min_x = min(xs)
   min_y = min(ys)
   line_dist = calc_dist((min_x,min_y),(max_x,max_y))
   safe_dist = line_dist / 2

   if safe_dist < 5:
      safe_dist = 5
   regression_line = []
   for x in xs:
      regression_line.append((m*x)+b)
   good = 0
   for i in range(0,len(regression_line)):
      if len(hist[i]) == 7:
         fn,x,y,w,h,mx,my = hist[i]
      if len(hist[i]) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hist[i]
 
      #fn,x,y,w,h,mx,my = hist[i]
      cx = int(x+ (w/2))
      cy = int(y+ (h/2))
      ry = regression_line[i]
      dist = calc_dist((cx,cy),(cx,ry))

      if dist < safe_dist:
         good = good + 1

   match_perc = good / len(regression_line)

   #if int(oid) == 2:
      #import matplotlib.pyplot as plt
      #from matplotlib import style
      #style.use('ggplot')

      #plt.scatter(xs,ys,color='#003F72')
      #plt.plot(xs, regression_line)
      #plt.show()

   return(match_perc)

def meteor_test_peaks(object):
   points = []
   sizes = []
   hist = object['history']
   for hs in hist:
      if len(hs) == 7:
         fn,x,y,w,h,mx,my = hs
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hs

      size  = w * h
      sizes.append(size)
      point = x+mx,y+my
      points.append(point)

   sci_peaks = signal.find_peaks(sizes,threshold=3)
   total_peaks = len(sci_peaks[0])
   total_frames = len(points)
   if total_frames > 0:
      peak_to_frame = total_peaks / total_frames

   return(sci_peaks, peak_to_frame)



def meteor_test_distance(object):
   oid = object['oid']
   status = 1
   reason = "DISTANCE TEST PASSED: " + str(oid) + ": Distance test passed. "
   hist = object['history']
   (max_x,max_y,min_x,min_y) = find_min_max_dist(hist,1)

   dist = calc_dist((min_x,min_y),(max_x,max_y))

   return(dist)

def meteor_test_hist_len(object):
   status = 1
   reason = "History length test passed."
   hist = object['history']
   hist_len = len(hist)

   if hist_len > 300:
      status = 0
      reason = "HISTORY LENGTH TEST FAILED: Hist length of object is too long > 300: " + str(hist_len)
   if hist_len < 3:
      status = 0
      reason = "HISTORY LENGTH TEST FAILED: Hist length of object is too short < 3: " + str(hist_len)
   if status == 1:
      reason = "History length test passed: "+ str(hist_len)
   return(status,reason)

def meteor_test_elp_frames(object):
   hist = object['history']
   if len(hist) > 5:
      first_frame = hist[2][0]
      last_frame = hist[-1][0]
   else:
      first_frame = hist[0][0]
      last_frame = hist[-1][0]
   elp_frames = last_frame - first_frame
   return(elp_frames)

def meteor_test_cm_gaps(object):
   hist = object['history']
   cm = 0
   max_cm = 0
   gaps = 0
   max_gaps = 0
   gap_events = 0
   last_frame = hist[0][0] - 1
   for hs in hist:
      if len(hs) == 7:
         fn,x,y,w,h,mx,my = hs
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_val,sum_val = hs

      if ((last_frame + 1 == fn or last_frame + 2 == fn or last_frame + 3 == fn) and last_frame > 0) or last_frame == fn:
         cm = cm + 1
      else:
         if cm > max_cm:
            max_cm = cm
         cm = 0
         if last_frame > 5 :
            gaps = gaps + (fn - last_frame)
            if fn - last_frame > 1:
               gap_events = gap_events + 1
      if cm > max_cm:
         max_cm = cm
      if gaps > max_gaps:
         max_gaps = gaps
      last_frame = fn

   # max cm per hist len 1 is best score. < .5 is fail.
   max_cm = max_cm + 1
   if max_cm > 0:
      cm_hist_len_ratio = max_cm / len(hist)
   else:
      cm_hist_len_ratio = 0
   return(max_cm,gaps,gap_events,cm_hist_len_ratio)

def meteor_test_points(points):
   max_x = max(map(lambda x: x[0], points))
   max_y = max(map(lambda x: x[1], points))
   min_x = min(map(lambda x: x[0], points))
   min_y = min(map(lambda x: x[1], points))
   max_dist = calc_dist((min_x,min_y),(max_x,max_y))
   first_last_angle = find_angle(points[0], points[-1])
   dist_per_point = max_dist / len(points)

   pc = 0
   ap = 0
   for point in points:
      if pc + 1 <= len(points) - 1:
         next_point = points[pc+1]
         seg_dist = calc_dist(point, next_point)
         dist_from_first = calc_dist(points[0], point)
         angle = find_angle(point, next_point)
         if first_last_angle -10 <= angle <= first_last_angle + 10:
            ap = ap + 1

      pc = pc + 1
   app = ap / len(points)
   if app < .5:
      return(0)

   return(1)


