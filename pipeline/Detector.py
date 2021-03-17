from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs, calc_dist
from lib.PipeMeteorTests import obj_cm
import numpy as np

class Detector():
   def __init__(self):
      self.run = 1


   def analyze_object(obj):
      report = {}
      # determine event duration
      dur_frames = obj['ofns'][-1] - obj['ofns'][0]
      dur_seconds = dur_frames / 25
      gaps = []
      last_dists = []
      dists_from_start = []
      x_dist = []
      y_dist = []
      cls = "unknown"

      # reject any object with less than 3 frames 
      if len(obj['ofns']) < 3:
         report['status'] = "reject"
         cls = "noise"
         return(0, report)

      # determine gaps between frames, dist from start, dist from previous
      for i in range(0, len(obj['ofns'])):
         if i > 0:
            fn = obj['ofns'][i]
            fn_gaps = fn - obj['ofns'][i-1]

            dist_from_last = calc_dist((obj['oxs'][i], obj['oys'][i]), (obj['oxs'][i-1],obj['oys'][i-1]))
            dist_from_start = calc_dist((obj['oxs'][0], obj['oys'][0]), (obj['oxs'][i],obj['oys'][i]))
            x_dist.append((obj['oxs'][i] - obj['oxs'][i-1]))
            y_dist.append((obj['oys'][i] - obj['oys'][i-1]))

            gaps.append(fn_gaps)
            last_dists.append(dist_from_last)
            dists_from_start.append(dist_from_start)
         else:
            gaps.append(0)
            last_dists.append(0)
            dists_from_start.append(0)
            x_dist.append(0)
            y_dist.append(0)

      med_gaps = np.median(gaps)
      max_dist = max(dists_from_start)
      px_per_frame = max(dists_from_start) / dur_frames

      if max_dist < 5 or px_per_frame < .05:
         moving = 0
      else:
         moving = 1

      report['total_frames'] = len(obj['ofns'])
      report['dur_frame'] = dur_frames
      report['max_cm'] = obj_cm(obj['ofns'])
      report['dur_seconds'] = dur_seconds
      report['med_gaps'] = med_gaps 
      report['mean_fr_dist'] = np.mean(last_dists)
      report['max_mean_int_factor'] = max(obj['oint']) / np.mean(obj['oint'])
      report['max_px_dist'] = max(dists_from_start)
      report['px_per_second'] = max(dists_from_start) / dur_seconds 
      report['px_per_frame'] = max(dists_from_start) / dur_frames
      report['x_dist'] = x_dist
      report['y_dist'] = y_dist
      report['last_dists'] = last_dists
      report['dists_from_start'] = dists_from_start
      report['moving'] = moving

      # based on the above try to classify the object into 1 of the following:
      # 1 - meteor (cm, dist, speed,change in intensity,overall duration, low gaps)
      # 2 - fireball meteor (cm, dist, speed,change in intensity,overall duration, low gaps, higher max inensity, longer duration)
      # 3 - satellite (longer than meteor, more like plane, very low speed but high intensity difference)
      # 4 - plane (gaps, intensity change, duration, speed)
      # 5 - low flying plane/helicopter (bright overall intensity, big from start to end. VS fading off of fireball)
      # 6 - cloud/moon (large in size, hot spot / recurring)
      # 7 - car (large objects and also near bottom 1/3 of image)
      # 8 - bird (gaps, intensity, speed?, non linear movement, dark obj on light BG, occuring at daytime)

      # do plane first
      plane_score = 0

      # add points based on gaps
      if 2 <= report['med_gaps'] <= 4:
         plane_score += 1
      elif 5 < report['med_gaps'] <= 10:
         plane_score += 3

      # add points based on speed 
      if report['px_per_frame'] < .15:
         plane_score += 3
      if .15 < report['px_per_frame'] < .5:
         plane_score += 2
      if .5 < report['px_per_frame'] < 1:
         plane_score += 1 
      if 1 < report['px_per_frame'] < 2:
         plane_score += .5 

      # add point based on long dur
      if report['dur_seconds'] > 10:
         plane_score += 1 

      # add points based on intensity
      if report['max_mean_int_factor'] < 3:
         plane_score += 1


      if report['mean_fr_dist'] < 1.5:
         plane_score += 1
      

      report['plane_score'] = plane_score
      return(1, report)

   def find_objects(fn,x,y,w,h,intensity,objects,dist_thresh=30):
      
      maybe_matches = []
      cx = int(x + (w/2))
      cy = int(y + (h/2))
      if len(objects.keys()) == 0:
         objects[1] = {}
         objects[1]['oid'] = 1
         objects[1]['ofns'] = []
         objects[1]['oxs'] = []
         objects[1]['oys'] = []
         objects[1]['ows'] = []
         objects[1]['ohs'] = []
         objects[1]['oint'] = []
         objects[1]['ofns'].append(fn)
         objects[1]['oxs'].append(x)
         objects[1]['oys'].append(y)
         objects[1]['ows'].append(w)
         objects[1]['ohs'].append(h)
         objects[1]['oint'].append(intensity)
         return(1, objects)
      else:
         for obj in objects:
            tcx = int(objects[obj]['oxs'][-1] + (objects[obj]['ows'][-1]/2))
            tcy = int(objects[obj]['oys'][-1] + (objects[obj]['ohs'][-1]/2))
            dist = calc_dist((cx,cy),(tcx,tcy))
            fn_diff = fn - objects[obj]['ofns'][-1]
            if dist < dist_thresh and fn_diff < 90 and fn not in objects[obj]['ofns']:
               maybe_matches.append((obj,dist))
         if len(maybe_matches) == 0:
            no_match = 1
         elif len(maybe_matches) == 1:
            obj = maybe_matches[0][0]
            if "class" not in objects[obj] and len(objects[obj]['ofns']) > 5:
               # try to class the obj. if there is minimal distance it is a star
               dist = calc_dist((min(objects[obj]['oxs']), min(objects[obj]['oys'])), (max(objects[obj]['oxs']), max(objects[obj]['oys'])))
               if dist <= 2:
                  objects[obj]['class'] = "star"
            objects[obj]['oid'] = obj
            objects[obj]['ofns'].append(fn)
            objects[obj]['oxs'].append(x)
            objects[obj]['oys'].append(y)
            objects[obj]['ows'].append(w)
            objects[obj]['ohs'].append(h)
            objects[obj]['oint'].append(intensity)
            return(obj, objects)
         else:
            print("THERE IS MORE THAN 1 OBJECT WE COULD MATCH AGAINST! Which is it?", len(maybe_matches))
            maybe_matches = sorted(maybe_matches, key=lambda x: (x[1]), reverse=False)
            #for oid,dist in maybe_matches:
            #   print("TOO MANY!", oid, objects[oid], dist)
            obj = maybe_matches[0][0]
            objects[obj]['ofns'].append(fn)
            objects[obj]['oxs'].append(x)
            objects[obj]['oys'].append(y)
            objects[obj]['ows'].append(w)
            objects[obj]['ohs'].append(h)
            objects[obj]['oint'].append(intensity)
            print("BEST:", obj, objects[obj])
            return(obj, objects)
            #exit()

      # by here we should have a maybe match or a new match 
      # if there are no maybes make a new one
      if len(maybe_matches) == 0:
         nid = max(objects.keys()) + 1
         objects[nid] = {}
         objects[nid]['oid'] = nid
         objects[nid]['ofns'] = []
         objects[nid]['oxs'] = []
         objects[nid]['oys'] = []
         objects[nid]['ows'] = []
         objects[nid]['ohs'] = []
         objects[nid]['oint'] = []
         objects[nid]['ofns'].append(fn)
         objects[nid]['oxs'].append(x)
         objects[nid]['oys'].append(y)
         objects[nid]['ows'].append(w)
         objects[nid]['ohs'].append(h)
         objects[nid]['oint'].append(intensity)
         return(1, objects)
