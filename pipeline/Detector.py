from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs, calc_dist
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

      # reject any object with less than 3 frames 
      if len(obj['ofns']) == 0:
         report['status'] = "reject"
         return(0, report)



      # determine gaps between frames, dist from start, dist from previous
      for i in range(0, len(obj['ofns'])):
         if i > 0:
            fn = obj['ofns'][i]
            fn_gaps = fn - obj['ofns'][i-1]

            dist_from_last = calc_dist((obj['oxs'][i], obj['oys'][i]), (obj['oxs'][i-1],obj['oys'][i-1]))
            dist_from_start = calc_dist((obj['oxs'][0], obj['oys'][0]), (obj['oxs'][i],obj['oys'][i]))

            gaps.append(fn_gaps)
            last_dists.append(dist_from_last)
            last_dists.append(dist_from_last)
            dists_from_start.append(dist_from_start)
         else:
            gaps.append(0)
            last_dists.append(0)
            dists_from_start.append(0)

      med_gaps = np.median(gaps)
      max_dist = max(dists_from_start)
      px_per_frame = max(dists_from_start) / dur_frames

      if max_dist < 5 or px_per_frame < .2:
         moving = 0
      else:
         moving = 1

      report['total_frames'] = obj['ofns']
      report['dur_frame'] = dur_frames
      report['dur_seconds'] = dur_seconds
      report['med_gaps'] = med_gaps 
      report['mean_fr_dist'] = np.mean(last_dists)
      report['max_mean_int_factor'] = max(obj['oint']) / np.mean(obj['oint'])
      report['max_px_dist'] = max(dists_from_start)
      report['px_per_second'] = max(dists_from_start) / dur_seconds 
      report['px_per_frame'] = max(dists_from_start) / dur_frames
      report['moving'] = moving
      return(1, report)

   def find_objects(fn,x,y,w,h,intensity,objects,dist_thresh=10):
      
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
            #print("OBJINFO:", obj, objects[obj])
            tcx = int(objects[obj]['oxs'][-1] + (objects[obj]['ows'][-1]/2))
            tcy = int(objects[obj]['oys'][-1] + (objects[obj]['ohs'][-1]/2))
            dist = calc_dist((cx,cy),(tcx,tcy))
            fn_diff = fn - objects[obj]['ofns'][-1]
            if dist < dist_thresh and fn_diff < 10 and fn not in objects[obj]['ofns']:
               maybe_matches.append((obj,dist))
         if len(maybe_matches) == 0:
            no_match = 1
         elif len(maybe_matches) == 1:
            obj = maybe_matches[0][0]
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
