
import numpy as np
#from sklearn import linear_model, datasets
#from skimage.measure import ransac, LineModelND, CircleModel

from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs, calc_dist
from lib.PipeMeteorTests import obj_cm



class Detector():
   def __init__(self):
      self.run = 1


   def analyze_object(obj):
      self = Detector()
      report = {}
      # determine event duration
      dur_frames = (obj['ofns'][-1] - obj['ofns'][0]) + 1
      dur_seconds = dur_frames / 25
      gaps = []
      last_dists = []
      dists_from_start = []
      report['bad_items'] = []
      report['good_items'] = []
      report['x_dist'] = []
      report['y_dist'] = []
      cls = "unknown"
      report['max_dist'] = calc_dist((obj['oxs'][0], obj['oys'][0]), (obj['oxs'][-1] + obj['ows'][-1], obj['oys'][-1] + obj['ohs'][-1]))

      report['elapsed_frames'] = max(obj['ofns']) - min(obj['ofns'])
      report['plane_score'] = 0
      report['meteor_score'] = 0
      report['cloud_score'] = 0
      report['bird_score'] = 0
      report['class'] = "unknown"
      plane_score = 0
      cloud_score = 0
      if report['max_dist'] < 3:
         report['moving'] = 0
      else:
         report['moving'] = 1
         report['meteor_score'] += 1
         report['good_items'].append("object is moving.")

         

      # reject any object with 0 frames
      if len(obj['ofns']) == 0:
         report['status'] = "reject"
         cls = "noise"
         return(0, report)

      # determine unq points
      up = {}
      for i in range(0, len(obj['ofns'])):
         key = str(obj['oxs'][i]) + "." + str(obj['oys'][i])
         up[key] = 1
      report['unq_points'] = len(up.keys())
      #obj['oxs']
      #obj['oys']

      #print("OFNS:", obj['ofns'])
      #print("UNIQUE POINTS:", report['unq_points'])

      if report['unq_points'] == 1:
         report['class'] = "star"

      if report['unq_points'] <= 2:
         report['meteor_score'] += -10
         report['bad_items'].append("there are 2 or less unique points!?. " + str(report['unq_points'] ) + " " +  str(up))

      # determine cm and reject < 3
      report['max_cm'] = obj_cm(obj['ofns'])
      report['cm_perc'] = report['max_cm'] / len(obj['ofns'])
      if report['max_cm'] > 3 and report['cm_perc'] > .8 :
         report['meteor_score'] + 1
         report['good_items'].append("there are 3 or more consecutive motion frames!?.")

      # determine gaps between frames, dist from start, dist from previous
      report['segs'] = []
      for i in range(0, len(obj['ofns'])):
         if i > 0:
            fn = obj['ofns'][i]
            fn_gaps = fn - obj['ofns'][i-1]
         
            dist_from_last = calc_dist((obj['ccxs'][i], obj['ccys'][i]), (obj['ccxs'][i-1],obj['ccys'][i-1]))
            dist_from_start = calc_dist((obj['ccxs'][0], obj['ccys'][0]), (obj['ccxs'][i],obj['ccys'][i]))
            report['x_dist'].append((obj['ccxs'][i] - obj['ccxs'][i-1]))
            report['y_dist'].append((obj['ccys'][i] - obj['ccys'][i-1]))

            gaps.append(fn_gaps)
            last_dists.append(dist_from_last)
            dists_from_start.append(dist_from_start)
            seg = dist_from_start - last_dist_from_start
            last_dist_from_start = dist_from_start
            report['segs'].append(seg)
         else:
            fn_gaps = 0
            last_dist_from_start = 0
            gaps.append(0)
            last_dists.append(0)
            dists_from_start.append(0)
            report['x_dist'].append(0)
            report['y_dist'].append(0)
            report['segs'].append(0)

      total_gaps = sum(gaps)
      gaps_per_frame = total_gaps / len(obj['ofns'])
      report['total_gaps'] = total_gaps
      report['gaps_per_frame'] = gaps_per_frame

      if report['unq_points'] <= 3 and sum(gaps) > 3:
         report['meteor_score'] += -10
         report['bad_items'].append("there are 3 points and > 3 gaps!?. " )

      # determine the % of x & y agreement (with med)
      report['med_seg'] = np.median(report['segs'])
      report['med_x'] = np.median(report['x_dist'])
      report['med_y'] = np.median(report['y_dist'])
      x_agree = 1
      y_agree = 1
      good_xd = 0
      good_yd = 0
      for i in range(0, len(obj['ofns'])):
         if i > 0:
            xdf = abs(report['med_x'] - report['x_dist'][i])
            ydf = abs(report['med_y'] - report['y_dist'][i])
            if xdf <= abs(report['med_x']) + 1:
               good_xd += 1
            if ydf <= abs(report['med_y']) + 1:
               good_yd += 1
              
         report['xd_agree'] = good_xd + 1 / (len(obj['ofns']))
         report['yd_agree'] = good_yd + 1 / (len(obj['ofns']))
      if report['xd_agree'] >= .9:
         report['meteor_score'] += 1
         report['good_items'].append("agreement with x direction!?.")

      if report['yd_agree'] >= .9:
         report['meteor_score'] += 1
         report['good_items'].append("agreement with y direction!?.")
      if report['xd_agree'] <= .6:
         report['meteor_score'] -= 1
         report['bad_items'].append("disagreement with x direction!?.")
      if report['yd_agree'] <= .6:
         report['meteor_score'] -= 1
         report['bad_items'].append("disagreement with y direction!?.")
      if report['gaps_per_frame'] > 2:
         report['meteor_score'] -=5 
         report['bad_items'].append("Too many gaps per frame! " + str(report['gaps_per_frame']))


      # determine % of obj that are 'big frames'
      big = 0
      for i in range(0, len(obj['ows'])):
         size = obj['ows'][i] + obj['ohs'][i]
         if size > 20:
            big += 1
      if len(obj['ofns']) > 0:
         big_perc = big / len(obj['ofns'])
      else:
         big_perc = 0

      # determine % of x & y dists that are agreeing
      med_x = np.median(report['x_dist'])
      med_y = np.median(report['y_dist'])
      bad_xd = 0
      bad_yd = 0
      x_dir = obj['ccxs'][0] - obj['ccxs'][-1]
      y_dir = obj['ccys'][0] - obj['ccys'][-1]
      if abs(x_dir) > abs(y_dir):
         dom_dir = "x"
      else:
         dom_dir = "y"
      report['x_dir'] = x_dir
      report['y_dir'] = y_dir
      report['dom_dir'] = dom_dir
      for i in range (0, len(obj['ofns'])):
         if med_x > 0 and report['x_dist'][i] < 0:
            bad_xd += 1
         if med_y > 0 and report['y_dist'][i] < 0:
            bad_yd += 1

         if med_x < 0 and report['x_dist'][i] > 0:
            bad_xd += 1
         if med_y < 0 and report['y_dist'][i] > 0:
            bad_yd += 1

         if bad_xd > 0:
            bad_x_perc = bad_xd / len(obj['ofns'])
         else:
            bad_x_perc = 0
         if bad_yd > 0:
            bad_y_perc = bad_yd / len(obj['ofns'])
         else:
            bad_y_perc = 0

      report['big_perc'] = big_perc
      report['bad_x_perc'] = bad_x_perc
      report['bad_y_perc'] = bad_y_perc
      report['gaps'] = gaps
      med_gaps = np.median(gaps)
      max_dist = max(dists_from_start)
      report['med_gaps'] = med_gaps
      if dur_frames > 0:
         px_per_frame = max(dists_from_start) / dur_frames
      else:
         px_per_frame = 0

      if max_dist < 5 or px_per_frame < .05:
         moving = 0
      else:
         moving = 1

      if report['med_gaps'] > 3:
         report['meteor_score'] = -1
         report['plane_score'] += 1
         report['bad_items'].append("too many gaps for event length") 


      report['total_frames'] = len(obj['ofns'])
      report['dur_frame'] = dur_frames
      report['dur_seconds'] = dur_seconds
      report['med_gaps'] = med_gaps 
      report['mean_fr_dist'] = np.mean(last_dists)
      if len(obj['oint']) > 0 and sum(obj['oint']) != 0:
         report['max_mean_int_factor'] = max(obj['oint']) / np.mean(obj['oint'])
         report['min_max_int_factor'] = max(obj['oint']) / np.min(obj['oint'])
      else:
         report['max_mean_int_factor'] = 0 
         report['min_max_int_factor'] = 0 

      report['max_px_dist'] = max(dists_from_start)
      if dur_seconds > 0:
         report['px_per_second'] = max(dists_from_start) / dur_seconds 
      else:
         report['px_per_second'] = 9
      if dur_seconds > 0:
         report['px_per_frame'] = max(dists_from_start) / dur_frames
      else:
         report['px_per_frame'] = 0

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


      if report['cm_perc'] > .9:
         report['meteor_score'] += 1
         report['good_items'].append("cm perc good.")
      if report['cm_perc'] < .5:
         report['meteor_score'] -= 1
         report['good_items'].append("cm perc too low.")


      # add points based on gaps
      if 2 <= report['med_gaps'] <= 4:
         report['plane_score'] += 2
         report['meteor_score'] -= 1
      elif 5 < report['med_gaps'] <= 10:
         report['plane_score'] += 3
         report['meteor_score'] -= 2
         report['meteor_score'] -= 1 
         report['bad_items'].append("5-10 gaps detected.")
      if report['elapsed_frames'] < 4 and report['cm_perc'] < .9:
         report['meteor_score'] -= 1 
         report['bad_items'].append("less than 4 elapsed frames and also gaps detected.")


      # add points based on speed 
      if report['px_per_frame'] < .15:
         plane_score += 3
      if .15 < report['px_per_frame'] < .5:
         plane_score += 2
      if .5 < report['px_per_frame'] < 1:
         plane_score += 1 
      if 1 < report['px_per_frame'] < 2:
         plane_score += .5 
      if 2 < report['px_per_frame'] < 20:
         report['meteor_score'] += 1 
         report['good_items'].append("good meteor speed.")

      if report['px_per_frame'] < .6:
         report['meteor_score'] -= 1 
         report['bad_items'].append("low speed.")

      # add point based on long dur
      if report['dur_seconds'] > 10:
         plane_score += 1 

      # add points based on intensity
      if report['max_mean_int_factor'] < 3:
         plane_score += 1
      if report['max_mean_int_factor'] > 5 :
         report['meteor_score'] += 1
     
      # reject small dist objs
      if report['max_px_dist'] < 3.5:
         report['meteor_score'] = -5
         report['class'] = "star"



      if report['mean_fr_dist'] < 1.5:
         plane_score += 1
      if 2 <= report['mean_fr_dist'] <= 15 :
         report['meteor_score'] += 1


      report['plane_score'] = plane_score


      # if this is not already ID'd as a plane, check to see it's ransac outlier %
      #try:
      #   XS,YS,BXS,BYS = self.ransac_outliers(obj['ccxs'],obj['ccys'])
      #except:
      #   XS = obj['ccxs']
      #   YS = obj['ccys']
      #   BXS = []
      #   BYS = []
         
      #if len(XS) > 0:
      #   ransac_perc = len(BXS) / len(XS)
      #else:
      #   ransac_perc = 0
      #if len(BXS) == 0:
      #   ransac_perc = 1
      #report['ransac'] = ransac_perc
      #report['ransac_xs'] = []
      #report['ransac_ys'] = []
      #for X in XS:
      #   report['ransac_xs'].append(int(X))
      #for Y in YS:
      #   report['ransac_ys'].append(int(Y))


      # CLOUD DETECTOR 
      # how can we detect a cloud what meterics?
      # bp > .4 -- 
      # max_int > 30,000
      # px_vel < 3
      if report['big_perc'] >= .7:
         report['meteor_score'] = -10
      if report['big_perc'] >= .4:
         cloud_score += 1
      if report['big_perc'] >= .5:
         cloud_score += 1
      if report['big_perc'] >= .8:
         cloud_score += 1
      if max(obj['oint']) >= 30000 and report['px_per_frame'] < 3:
         cloud_score += 1
      report['cloud_score'] = cloud_score
      final_met_score = report['meteor_score'] - report['cloud_score'] - report['plane_score']

      if final_met_score >= 1 or report['meteor_score'] >= 2:
         report['class'] = "meteor"
      elif report['cloud_score'] >= 3 and report['meteor_score'] < 2:
         report['class'] = "cloud"
      elif report['plane_score'] >= 3 and report['meteor_score'] < 2:
         report['class'] = "plane"


      return(1, report)

   def ransac_outliers(self,XS,YS):
      XS = np.array(XS)
      YS = np.array(YS)
      XS.reshape(-1, 1)
      YS.reshape(-1, 1)

      self.sd_min_max = [int(min(XS))-50, int(min(YS))-50, int(max(XS))+50, int(max(YS)+50)]

      data = np.column_stack([XS,YS])
      model = LineModelND()
      model.estimate(data)
      model_robust, inliers = ransac(data, LineModelND, min_samples=2,
         residual_threshold=10, max_trials=1000)

      outliers = inliers == False

      # generate coordinates of estimated models
      line_x = np.arange(XS.min(),XS.max())  #[:, np.newaxis]
      line_y = model.predict_y(line_x)
      line_y_robust = model_robust.predict_y(line_x)

      # make plot for ransac filter
      import matplotlib
      matplotlib.use('TkAgg')
      from matplotlib import pyplot as plt

      fig, ax = plt.subplots()
      ax.plot(data[outliers, 0], data[outliers, 1], '.r', alpha=0.6,
        label='Outlier data')
      ax.plot(data[inliers, 0], data[inliers, 1], '.b', alpha=0.6,
        label='Inlier data')
      plt.gca().invert_yaxis()
      XS = data[inliers,0]
      YS = data[inliers,1]
      BXS = data[outliers,0]
      BYS = data[outliers,1]
      #plt.show()
      return(XS,YS,BXS,BYS)


   def find_objects(fn,x,y,w,h,cx,cy,intensity,objects,dist_thresh=50,lx=None,ly=None):
      #print("DIST THRESH IS:", dist_thresh)
      #print("x,y,w,h,cx,cy,int", x,y,w,h,cx,cy,intensity)
      maybe_matches = []
      last_closest_dist = None
      #cx = int(x + (w/2))
      #cy = int(y + (h/2))
      if len(objects.keys()) == 0:
         objects[1] = {}
         objects[1]['obj_id'] = 1
         objects[1]['ofns'] = []
         objects[1]['oxs'] = []
         objects[1]['oys'] = []
         objects[1]['ccxs'] = []
         objects[1]['ccys'] = []
         objects[1]['olxs'] = []
         objects[1]['olys'] = []
         objects[1]['ows'] = []
         objects[1]['ohs'] = []
         objects[1]['oint'] = []
         objects[1]['ofns'].append(fn)
         objects[1]['oxs'].append(x)
         objects[1]['oys'].append(y)
         objects[1]['ows'].append(w)
         objects[1]['ohs'].append(h)
         objects[1]['ccxs'].append(cx)
         objects[1]['ccys'].append(cy)
         if lx is not None:
            objects[1]['olxs'].append(lx)
            objects[1]['olys'].append(ly)
         objects[1]['oint'].append(intensity)
         return(1, objects)
      else:
         for obj in objects:
            tcx = int(objects[obj]['oxs'][-1] + (objects[obj]['ows'][-1]/2))
            tcy = int(objects[obj]['oys'][-1] + (objects[obj]['ohs'][-1]/2))
            dist = calc_dist((cx,cy),(tcx,tcy))
            fn_diff = fn - objects[obj]['ofns'][-1]

                #and fn not in objects[obj]['ofns'] :
            #print("DIST IS: ", dist)
            if dist < dist_thresh and fn_diff < 10: 
               mkeys = {}
               for i in range(0, len(objects[obj]['ofns'])):
                  key = str(objects[obj]['ccxs'][i]) + "." + str(objects[obj]['ccys'][i])
                  mkeys[key] = 1
               tkey = str(cx) + "." + str(cy)
               if tkey not in mkeys:
                  maybe_matches.append((obj,dist))
               else:
                  return(obj, objects)

            if last_closest_dist is None: 
               last_fn_diff = fn_diff
               last_obj = obj 
               last_closest_dist = dist
            if dist < last_closest_dist : 
               last_obj = obj 
               last_fn_diff = fn_diff
               last_closest_dist = dist
         if len(maybe_matches) == 0:
            no_match = 1
         elif len(maybe_matches) == 1:
            obj = maybe_matches[0][0]
            if "class" not in objects[obj] and len(objects[obj]['ofns']) > 5:
               # try to class the obj. if there is minimal distance it is a star
               dist = calc_dist((min(objects[obj]['oxs']), min(objects[obj]['oys'])), (max(objects[obj]['oxs']), max(objects[obj]['oys'])))
            objects[obj]['obj_id'] = obj
            objects[obj]['ofns'].append(fn)
            objects[obj]['oxs'].append(x)
            objects[obj]['oys'].append(y)
            objects[obj]['ows'].append(w)
            objects[obj]['ohs'].append(h)
            objects[obj]['ccxs'].append(cx)
            objects[obj]['ccys'].append(cy)
            objects[obj]['oint'].append(intensity)
            if lx is not None:
               objects[1]['olxs'].append(lx)
               objects[1]['olys'].append(ly)
            return(obj, objects)
         else:
            # Make new object
            maybe_matches = sorted(maybe_matches, key=lambda x: (x[1]), reverse=False)
            obj = maybe_matches[0][0]
            objects[obj]['ofns'].append(fn)
            objects[obj]['oxs'].append(x)
            objects[obj]['oys'].append(y)
            objects[obj]['ows'].append(w)
            objects[obj]['ohs'].append(h)
            objects[obj]['ccxs'].append(cx)
            objects[obj]['ccys'].append(cy)
            objects[obj]['oint'].append(intensity)
            if lx is not None:
               objects[1]['olxs'].append(lx)
               objects[1]['olys'].append(ly)
            return(obj, objects)

      # by here we should have a maybe match or a new match 
      # if there are no maybes make a new one
      if len(maybe_matches) == 0:
         nid = max(objects.keys()) + 1
         objects[nid] = {}
         objects[nid]['obj_id'] = nid
         objects[nid]['ofns'] = []
         objects[nid]['oxs'] = []
         objects[nid]['oys'] = []
         objects[nid]['ows'] = []
         objects[nid]['ohs'] = []
         objects[nid]['ccxs'] = []
         objects[nid]['ccys'] = []
         objects[nid]['olxs'] = []
         objects[nid]['olys'] = []
         objects[nid]['oint'] = []
         objects[nid]['ofns'].append(fn)
         objects[nid]['oxs'].append(x)
         objects[nid]['oys'].append(y)
         objects[nid]['ows'].append(w)
         objects[nid]['ohs'].append(h)
         objects[nid]['ccxs'].append(cx)
         objects[nid]['ccys'].append(cy)
         objects[nid]['oint'].append(intensity)
         if lx is not None:
            objects[1]['olxs'].append(lx)
            objects[1]['olys'].append(ly)
         return(1, objects)
