from scipy import signal

import operator
import datetime
from lib.FileIO import load_json_file, save_json_file, cfe
import numpy as np
import cv2
from lib.UtilLib import calc_dist, better_parse_file_date, bound_cnt
from lib.VideoLib import load_video_frames 
from lib.ImageLib import adjustLevels 
from lib.UtilLib import find_slope 
import scipy.optimize

def find_best_match(matches, cnt, objects):
   # eval the following things. 
   # - distance from object
   # - slope from start in relation to current point 
   # - brightness of object? 
   # - if the original object is moving or not? 
   # - the last size of the object and the current size? 

   mscore = {}
   bscore = {}
   for match in matches:
      xs = []
      ys = []
      for hs in match['history']:
         oid = match['oid']
         if len(hs) == 9:
            fn,x,y,w,h,mx,my,max_px,intensity = hs
         if len(hs) == 8:
            fn,x,y,w,h,mx,my,max_px = hs
         xs.append(x)
         ys.append(y)
      m,b = best_fit_slope_and_intercept(xs,ys)
      cntx,cnty,cntw,cnth = cv2.boundingRect(cnt)
      cnt_cx,cnt_cy = center_point(cntx,cnty,cntw,cnth)
      txs = [xs[0], cnt_cx]
      tys = [ys[0], cnt_cy]
      tm,tb = best_fit_slope_and_intercept(txs,tys)
      mscore[oid] = abs(tm-m)
      bscore[oid] = abs(tb-b)
      print("M,B for this object is: ", m,b,tm,tb)
   
   best_mids = sorted(mscore.items(), key=operator.itemgetter(1))
   best_bids = sorted(bscore.items(), key=operator.itemgetter(1))
   best_mid = best_bids[0][0]
   print("BEST MID:", best_mid)
   for obj in matches:
      print("OBJ:", obj['oid'], best_mid)
      if int(obj['oid']) == int(best_mid):
         return(obj)

def build_thresh_frames(sd_frames):
   thresh_frames = []
   for frame in sd_frames:
      hd_img = frame
      if len(hd_img.shape) == 3:
         gray_frame = cv2.cvtColor(hd_img, cv2.COLOR_BGR2GRAY)
         gray_frame = cv2.convertScaleAbs(gray_frame)
      else:
         gray_frame = hd_img
      #frames.append(hd_img)

      # do image acc / diff
      blur_frame = cv2.GaussianBlur(frame, (7, 7), 0)
      level_frame = adjustLevels(blur_frame, 30,1,255)
      level_frame = cv2.convertScaleAbs(level_frame)
      gray_frame = level_frame

      #if image_acc is None:
      #   image_acc = np.float32(gray_frame)

      #alpha = .1
      #hello = cv2.accumulateWeighted(gray_frame, image_acc, alpha)

      #image_diff = cv2.absdiff(image_acc.astype(gray_frame.dtype), gray_frame,)
      #first_image_diff = cv2.absdiff(first_gray_frame.astype(gray_frame.dtype), gray_frame,)
      #image_diff = first_image_diff

      #thresh = np.max(image_diff) * .95
      ithresh = np.max(gray_frame) * .8
      #if thresh < 20:
      #   thresh = 20

      _, image_thresh = cv2.threshold(gray_frame.copy(), ithresh, 255, cv2.THRESH_BINARY)
      #show_img2 = cv2.resize(cv2.convertScaleAbs(image_thresh), (960,540))
      #cv2.imshow('diff image', show_img2)
      #cv2.waitKey(0)
      thresh_frames.append(image_thresh)
   return(thresh_frames)



def detect_meteor(video_file, json_conf, show = 0):
   red_file = video_file.replace(".mp4", "-reduced.json")
   met_file = video_file.replace(".mp4", ".json")
   if cfe(red_file) == 0:
      print("No reduction file yet.")
      red_data = {}
   else:
      print("Loading red data.")
      red_data = load_json_file(red_file)
   if cfe(met_file) == 0:
      print("No meteor file yet.")
      met_data = {}
   else:
      print("Loading met data.")
      met_data = load_json_file(met_file)
      for key in met_data:
         print(key, met_data[key])
   #exit()
   #cv2.namedWindow('pepe') 
   print("Play meteor:", video_file)
   sd_frames = load_video_frames(video_file, json_conf)
   frames = []

   image_acc = None
   fc = 0
   objects = []
   # find max px value
   mxpx = []
   for frame in sd_frames:
      max_px_diff = np.max(frame)
      mxpx.append(max_px_diff)

   min_px = min(mxpx)
   max_px = min(mxpx)
   thresh = min_px * .8
   first_gray_frame = None
   last_image_thresh = None

   #thresh_frames = build_thresh_frames(sd_frames)
   #exit()

   for frame in sd_frames:
      #hd_img = cv2.resize(frame, (1920,1080))
      hd_img = frame
      if len(hd_img.shape) == 3:
         gray_frame = cv2.cvtColor(hd_img, cv2.COLOR_BGR2GRAY)
         gray_frame = cv2.convertScaleAbs(gray_frame)
      else:
         gray_frame = hd_img
      frames.append(hd_img)


      # do image acc / diff
      blur_frame = cv2.GaussianBlur(gray_frame, (7, 7), 0)
      level_frame = adjustLevels(blur_frame, 50,1,255)
      level_frame = cv2.convertScaleAbs(level_frame)
      gray_frame = level_frame

      if first_gray_frame is None:
         first_gray_frame = gray_frame 

      if image_acc is None:
         image_acc = np.float32(gray_frame)

      alpha = .1
      hello = cv2.accumulateWeighted(gray_frame, image_acc, alpha)

      image_diff = cv2.absdiff(image_acc.astype(gray_frame.dtype), gray_frame,)
      first_image_diff = cv2.absdiff(first_gray_frame.astype(gray_frame.dtype), gray_frame,)
      image_diff = first_image_diff

      thresh = np.max(image_diff) * .95
      ithresh = np.max(gray_frame) * .8
      print("THRESH:", thresh)
      if thresh < 20:
         thresh = 20

      _, image_thresh = cv2.threshold(gray_frame.copy(), ithresh, 255, cv2.THRESH_BINARY)

      if last_image_thresh is not None:
         image_thresh_diff = cv2.absdiff(image_thresh.astype(gray_frame.dtype), last_image_thresh,)
      else:
         image_thresh_diff = image_thresh

      _, diff_thresh = cv2.threshold(image_diff.copy(), thresh, 255, cv2.THRESH_BINARY)
      #show_img2 = cv2.resize(cv2.convertScaleAbs(image_thresh_diff), (960,540))
      #cv2.imshow('diff image', show_img2) 
      #cv2.waitKey(0)

      # find contours and ID objects
      diff_thresh = image_thresh
      cnts,pos_cnts = find_contours(diff_thresh, gray_frame)
      if len(pos_cnts) > 1:
         _, diff_thresh = cv2.threshold(image_diff.copy(), 30, 255, cv2.THRESH_BINARY)
         cnts,pos_cnts = find_contours(diff_thresh, gray_frame)

      ic = 0
      marked_image = image_diff.copy()
      for cnt in cnts:
         x,y,w,h,size,mx,my,max_val,intensity = pos_cnts[ic]
         object, objects = id_object(cnt, objects,fc, (mx,my), max_val, intensity, 0)
         print(object)
         if "oid" in object:
            name = str(object['oid'])
            cv2.putText(marked_image, name ,  (x-5,y-12), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
         cv2.rectangle(marked_image, (x, y), (x+w, y+h), (128), 1)

         ic = ic + 1
      #print("OBJECTS:", fc, len(objects))
      #print("CNTS:", len(pos_cnts), pos_cnts)


      if show == 1:
         show_img = cv2.resize(cv2.convertScaleAbs(diff_thresh), (960,540))
         show_img2 = cv2.resize(cv2.convertScaleAbs(marked_image), (960,540))
         cv2.imshow('diff image', show_img2) 
         cv2.waitKey(0)
      last_image_thresh = image_thresh
      fc = fc + 1


   meteors = []

   for obj in objects:
      iis = []
      fns = []
      elp_fr = obj['history'][-1][0] - obj['history'][0][0]
      #print(obj)
      for hs in obj['history']:
         #print(obj['oid'], hs[-1])
         iis.append(hs[-1])
         fns.append(hs[0])

      sci_peaks, peak_to_frame = meteor_test_peaks(obj)

   #exit()
   for obj in objects:
      print(obj['oid'], obj['history'])

   for obj in objects:
      elp_fr = obj['history'][-1][0] - obj['history'][0][0]
      hist_len = len(obj['history'])
      if elp_fr > 0:
         elp_fr_to_hist_len_ratio = len(obj['history']) / elp_fr
         obj['elp_fr_to_hist_len_ratio'] = elp_fr_to_hist_len_ratio
         print("ELP HIST:", obj['oid'], elp_fr_to_hist_len_ratio)
      if obj['max_cm'] >= 3 and obj['gaps'] < 10 and (.9 <= elp_fr_to_hist_len_ratio <= 2):

         print(obj['oid'], obj['status'], obj['hist_len'], obj['is_straight'], obj['dist'], obj['max_cm'], obj['gaps'], obj['gap_events'], obj['cm_hist_len_ratio'])     
         x_dir_mod, y_dir_mod = find_dir_mod(obj['history'])
         obj['x_dir_mod'] = x_dir_mod
         obj['y_dir_mod'] = y_dir_mod
         meteors.append(obj)
   if len(meteors) == 0:
      print("No meteors found.") 
      for obj in objects:
         print(obj['oid'], obj)
      exit()
   elif len(meteors) == 1:
      metconf = {}
      metconf['x_dir_mod'] = meteors[0]['x_dir_mod']
      metconf['y_dir_mod'] = meteors[0]['y_dir_mod']
      metframes,xs,ys,fns = hist_to_metframes(meteors[0],metconf)
      m,b = best_fit_slope_and_intercept(xs,ys)
      metconf['m'] = m
      metconf['b'] = b
      metconf['sd_xs'] = xs
      metconf['sd_ys'] = ys
      metconf['sd_fns'] = fns
      metconf['sd_fx'] = xs[0]
      metconf['sd_fy'] = ys[0]
      metconf['first_frame'] = fns[0]
      metconf['sd_acl_poly'] = 0

      hdm_x = 2.7272
      hdm_y = 1.875
      sd_dist = calc_dist(( metconf['sd_xs'][0], metconf['sd_ys'][0]),( metconf['sd_xs'][-1], metconf['sd_ys'][-1]))
      hd_dist = calc_dist(( metconf['sd_xs'][0]*hdm_x, metconf['sd_ys'][0]*hdm_y),( metconf['sd_xs'][-1]*hdm_x, metconf['sd_ys'][-1]*hdm_y))
      metconf['sd_dist'] = sd_dist
      metconf['hist_len'] = meteors[0]['hist_len']
      elp_fr = meteors[0]['history'][-1][0] - meteors[0]['history'][0][0]
      metconf['sd_seg_len'] = sd_dist / elp_fr 
      metconf['med_seg_len'] = hd_dist / elp_fr 
#(meteors[0]['hist_len'] )
      #metconf['sd_seg_len'] = 2

      fc = 0
      for frame in frames:   
         orig_image = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
         m = 0
         if fc in metframes:
            cnt_img = frame[y:y+h,x:x+w]
            x = metframes[fc]['sd_x']
            y = metframes[fc]['sd_y']
            w = metframes[fc]['sd_w']
            h = metframes[fc]['sd_h']
            mx = metframes[fc]['sd_max_x']
            my = metframes[fc]['sd_max_y']
            lc_x = metframes[fc]['sd_lc_x']
            lc_y = metframes[fc]['sd_lc_y']
            lc_y = metframes[fc]['m'] = metconf['m']
            lc_y = metframes[fc]['b'] = metconf['b']
            cx = int(x + (w/2))
            cy = int(y + (h/2))
            fcc = fc - metconf['first_frame']
            print("FCC:", fcc)
            print("EQ: est_x = ", metconf['sd_fx'], " + ", metconf['x_dir_mod'] , " * ",  metconf['sd_seg_len'], " + " , metconf['sd_acl_poly'], " * ", fcc)
            est_x = int(metconf['sd_fx']) + (metconf['x_dir_mod'] * (metconf['sd_seg_len']*fcc)) + (metconf['sd_acl_poly'] * fcc)
            est_y = (metconf['m']*est_x)+metconf['b']
            est_x = int(est_x)
            est_y = int(est_y)


            cv2.circle(orig_image,(lc_x,lc_y), 1, (255,0,0), 1)
            cv2.circle(orig_image,(est_x,est_y), 1, (0,128,128), 1)
            cv2.circle(orig_image,(cx,cy), 1, (0,128,0), 1)
            cv2.circle(orig_image,(mx,my), 1, (0,0,255), 1)
            cv2.rectangle(orig_image, (x, y), (x+w, y+h), (128,128,128), 1)
            m = 1
         if show == 1:
            desc = str("FN:" + str(fc))
            cv2.putText(orig_image, desc,  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
          
            cv2.imshow('final', orig_image)
            if m == 0:
               cv2.waitKey(10)  
            else: 
               cv2.waitKey(0)  
            fc = fc + 1
   else:
      print("More than 1 meteor found.")
      for obj in meteors:
         print(obj)

   for fn in metframes:
      print(fn, metframes[fn])

   # make light curve:

   for hs in obj['history']:
      print("HIST:", hs)
      iis.append(hs[-1])
      fns.append(hs[0])

   import matplotlib
   matplotlib.use('Agg')
   import matplotlib.pyplot as plt
   #fig = plt.figure()
   plt.plot(fns,iis)
   curve_file = video_file.replace(".mp4", "-lightcurve.png")
   plt.savefig(curve_file)


   print("")
   for key in metconf:
      print(key, metconf[key])
   clean_metframes(metframes,metconf,frames)
   metframes, metconf = minimize_start_len(metframes,frames,metconf,show)

   mfd, metframes = metframes_to_mfd(metframes, video_file)

   print(mfd)
   cmp_imgs,metframes = make_meteor_cnt_composite_images(json_conf, mfd, metframes, frames, video_file)
   prefix = red_data['sd_video_file'].replace(".mp4", "-frm")
   prefix = prefix.replace("SD/proc2/", "meteors/")
   prefix = prefix.replace("/passed", "")
   for fn in cmp_imgs:
      cv2.imwrite(prefix  + str(fn) + ".png", cmp_imgs[fn])
      print("UPDATING!", prefix + str(fn) + ".png")
      metframes[fn]['cnt_thumb'] = prefix + str(fn) + ".png"


   red_data['metconf'] = metconf
   red_data['metframes'] = metframes
   red_data['meteor_frame_data'] = mfd
   print("saving json:", red_file)
   save_json_file(red_file, red_data)

   exit()
   return(metframes, frames, metconf)
  
def clean_metframes(mf, metconf, frames):
   last_fn = None
   last_cx = None
   last_cy = None
   first_fn = None
   first_cx = None
   first_cy = None
   max_dist_from_start = 0
   last_dist_from_start = None
   fwdm = 1
   for fn in mf:
      if last_fn is not None :
         dist_from_last = calc_dist((mf[fn]['sd_cx'], mf[fn]['sd_cy']), (last_cx, last_cy))
         dist_from_start= calc_dist((mf[fn]['sd_cx'], mf[fn]['sd_cy']), (first_cx, first_cy))
         mf[fn]['sd_dist_from_last'] = dist_from_last
         mf[fn]['sd_dist_from_first'] = dist_from_start
         if last_dist_from_start is not None:
            seg_diff = dist_from_start - last_dist_from_start 
            mf[fn]['sd_seg_diff'] = dist_from_start - last_dist_from_start
         last_dist_from_start = dist_from_start 
         fwdm = 0
         if max_dist_from_start < dist_from_start:
            max_dist_from_start = dist_from_start
            fwdm = 1
      if first_fn is None :
         first_fn = fn
         first_cx = mf[fn]['sd_cx']
         first_cy = mf[fn]['sd_cy']
      if 'sd_seg_diff' in mf[fn]:
         if fwdm == 1:
            print(fn, mf[fn]['sd_dist_from_last'], mf[fn]['sd_seg_diff'], mf[fn]['sd_dist_from_first']) 
         else: 
            print(fn, "NO FWD MOTION.", mf[fn]['sd_seg_diff'], mf[fn]['sd_dist_from_first'])
            first_cy = mf[fn]['bad'] = 1
      else:
         print(fn)
      last_cx = mf[fn]['sd_cx']
      last_cy = mf[fn]['sd_cy']
      last_fn = fn 

   cleaning = 1
   while cleaning == 1:
      last_f = first_fn + (len(mf) - 1)
      if last_f in mf:
         if "bad" in mf[last_f]:
            del mf[last_f]
         else:
            cleaning = 0
      else:
         cleaning = 0

   segs = []
   for fn in mf:
      if "sd_seg_diff" in mf[fn]:
         print(fn, mf[fn]['sd_dist_from_last'], mf[fn]['sd_seg_diff'], mf[fn]['sd_dist_from_first'], mf[fn]['sd_intensity']) 
         segs.append(mf[fn]['sd_seg_diff'])
      else:
         print(fn)
   metconf['sd_seg_len'] = np.median(segs)   
   #exit()   
   return(mf, metconf) 

def minimize_start_len(metframes,frames,metconf,show=0):
   this_poly = np.zeros(shape=(2,), dtype=np.float64)
   if "sd_seg_len" in metconf:
      this_poly[0] = np.float64(metconf['sd_seg_len'])
   else:
      this_poly[0] = np.float64(2)
   if "sd_acl_poly" in metconf:
      this_poly[1] = np.float64(metconf['sd_acl_poly'])
   else:
      this_poly[1] = np.float64(-.01)
   #err = reduce_start_len(metframes, frames, metconf,show)
   res = scipy.optimize.minimize(reduce_seg_acl, this_poly, args=( metframes, metconf,frames,show), method='Nelder-Mead', options={'maxiter':1000, 'xatol': .05})
   poly = res['x']
   fun = res['fun']

   print("ACL POLY:", poly[0], poly[1], fun)
   metconf['sd_seg_len'] = float(poly[0])
   metconf['sd_acl_poly'] = float(poly[1])
   return(metframes,metconf)


def reduce_seg_acl(this_poly,metframes,metconf,frames,show=0):
   
   fc = 0
   tot_res_err = 0
   for frame in frames:   
      orig_image = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
      met = 0
      if fc in metframes:
         x = metframes[fc]['sd_x']
         y = metframes[fc]['sd_y']
         w = metframes[fc]['sd_w']
         h = metframes[fc]['sd_h']
         mx = metframes[fc]['sd_max_x']
         my = metframes[fc]['sd_max_y']
         lc_x = metframes[fc]['sd_lc_x']
         lc_y = metframes[fc]['sd_lc_y']
         cx = int(x + (w/2))
         cy = int(y + (h/2))
         fcc = fc - metconf['first_frame']
         cnt_img = frame[y:y+h,x:x+w]
         #est_x = int(metconf['sd_fx']) + (metconf['x_dir_mod'] * (this_poly[0]*fcc)) + (0 * fcc)
         est_x = int(metconf['sd_fx']) + (metconf['x_dir_mod'] * (this_poly[0]*fcc)) + (this_poly[1] * (fcc**2))
         est_y = (metconf['m']*est_x)+metconf['b']
         est_x = int(est_x)
         est_y = int(est_y)
         #res_err = calc_dist((est_x,est_y),(lc_x,lc_y))
         res_err = calc_dist((est_x,est_y),(cx,cy))
         tot_res_err = tot_res_err + res_err
         #print("FCC:", fcc, this_poly[0], this_poly[1], res_err)
         cv2.circle(orig_image,(est_x,est_y), 1, (0,255,255), 1)
         cv2.circle(orig_image,(lc_x,lc_y), 1, (255,0,0), 1)
         cv2.circle(orig_image,(cx,cy), 1, (0,128,0), 1)
         cv2.circle(orig_image,(mx,my), 1, (0,0,255), 1)
         cv2.rectangle(orig_image, (x, y), (x+w, y+h), (128,128,128), 1)
         met = 1
      if met == 0:
         skip = 1
      else: 
         if show == 1:
            cv2.imshow('final', orig_image)
            cv2.waitKey(0)  
      fc = fc + 1
   res_err = np.float64(tot_res_err / fcc)
   #res_err = np.float64(tot_res_err )
   print("RES:", res_err, this_poly[0], this_poly[1]) 
   return(res_err)

def hist_to_metframes(obj,metconf):
   metframes = {}
   xs = []
   ys = []
   fns = []
   xdm = metconf['x_dir_mod']
   ydm = metconf['y_dir_mod']
   for hs in obj['history']:
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_px,intensity = hs
      if len(hs) == 8:
         fn,x,y,w,h,mx,my,max_px = hs
      cx = int(x + (w/2))
      cy = int(y + (h/2))
      fn = int(fn)
      if xdm < 0:
         lc_x = x
      else:
         lc_x = x + w
      if ydm < 0:
         lc_y = y
      else:
         lc_y = y + h
      metframes[fn] = {}
      metframes[fn]['sd_x'] = x
      metframes[fn]['sd_y'] = y
      metframes[fn]['sd_w'] = w
      metframes[fn]['sd_h'] = h
      metframes[fn]['sd_cx'] = cx
      metframes[fn]['sd_cy'] = cy
      metframes[fn]['sd_lc_x'] = lc_x
      metframes[fn]['sd_lc_y'] = lc_y
      metframes[fn]['sd_max_x'] = x + mx
      metframes[fn]['sd_max_y'] = y + my
      metframes[fn]['sd_px'] = max_px
      metframes[fn]['sd_intensity'] = float(intensity)
      xs.append(lc_x)
      ys.append(lc_y)
      fns.append(fn)
   return(metframes,xs,ys,fns)

def setup_metframes(mfd):
   # establish initial first x,y last x,y
   fx = mfd[0][2]
   fy = mfd[0][3]
   lx = mfd[-1][2]
   ly = mfd[-1][3]

   dir_x = fx - lx
   dir_y = fy - ly
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1


   # establish first frame number, last frame number and total frames
   ff = mfd[0][1]
   lf = mfd[-1][1]
   tf = lf - ff
   tf = tf + 1

   # establish initial line distance and x_incr
   line_dist = calc_dist((fx,fy),(lx,ly))
   x_incr = int(line_dist / (tf ))

   metframes = {}
   etime = 0
   for i in range(0,tf):
      fi = i + ff
      metframes[fi] = {}
      if i > 0:
         etime = i / 25
      else:
         etime = 0
      metframes[fi]['etime'] = etime
      metframes[fi]['fn'] = fi
      metframes[fi]['ft'] = 0
      metframes[fi]['hd_x'] = 0
      metframes[fi]['hd_y'] = 0
      metframes[fi]['w'] = 0
      metframes[fi]['h'] = 0
      metframes[fi]['max_px'] = 0
      metframes[fi]['ra'] = 0
      metframes[fi]['dec'] = 0
      metframes[fi]['az'] = 0
      metframes[fi]['el'] = 0
      metframes[fi]['len_from_last'] = 0
      metframes[fi]['len_from_start'] = 0
   xs = []
   ys = []
   for fd in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = fd
      fi = fn
      xs.append(hd_x)
      ys.append(hd_y)
      metframes[fi]['fn'] = fi
      metframes[fi]['ft'] = frame_time
      metframes[fi]['hd_x'] = hd_x
      metframes[fi]['hd_y'] = hd_y
      metframes[fi]['w'] = w
      metframes[fi]['h'] = h
      metframes[fi]['max_px'] = max_px
      metframes[fi]['ra'] = ra
      metframes[fi]['dec'] = dec
      metframes[fi]['az'] = az
      metframes[fi]['el'] = el
   metconf = {}
   metconf['xs'] = xs
   metconf['ys'] = ys
   metconf['fx'] = fx
   metconf['fy'] = fy
   metconf['lx'] = lx
   metconf['ly'] = ly
   metconf['tf'] = tf
   metconf['runs'] = 0
   metconf['line_dist'] = line_dist
   metconf['x_incr'] = x_incr
   metconf['x_dir_mod'] = x_dir_mod
   metconf['y_dir_mod'] = y_dir_mod

   return(metframes, metconf)

def id_object(cnt, objects, fc,max_loc, max_px, intensity, is_hd=0):

   mx,my= max_loc
   mx = mx
   my = my
   x,y,w,h = cv2.boundingRect(cnt)
   cx,cy = center_point(x,y,w,h)
   if fc < 5:
      return({},objects)

   if len(objects) == 0:
      oid = 1
      object = make_new_object(oid, fc,x,y,w,h,mx,my, max_px, intensity)
      objects.append(object)
      return(object, objects)


   # Find object or make new one
   obj_found = 0
   matches = []

   for obj in objects:
      dist = 0
      moid = obj['oid']
      oid = obj['oid']
      ox = obj['x']
      oy = obj['y']
      object_hist = obj['history']
      bx = x + mx
      by = y + my
      found = find_in_hist(obj,x,y,object_hist, is_hd)
      if found == 1:
         matches.append(obj)
      #else:
   if len(matches) == 0:
      # NOT FOUND MAKE NEW
      max_id = max(objects, key=lambda x:x['oid'])
      oid= max_id['oid'] + 1
      object = make_new_object(oid,fc,x,y,w,h,mx,my,max_px,intensity)
      object['status'] = "new"
      objects.append(object)
      object['hist_len'] = 1
      return(object, objects)
   if len(matches) > 1:
      best_match = find_best_match(matches, cnt, objects)
      matches = []
      print("BEST MATCH:", best_match)
      matches.append(best_match)

   if len(matches) == 1:
      object = matches[0]
      object_hist = object['history']
      this_hist = [fc,x,y,w,h,mx,my,max_px,intensity]
      object['status'] = "new-updated"
      hxs = []
      hys = []
      points = []
      for hs in object_hist:
         if len(hs) == 9:
            tfc,tx,ty,tw,th,tmx,tmy,t_max_px,t_int = hs
         if len(hs) == 8:
            tfc,tx,ty,tw,th,tmx,tmy,t_max_px = hs
         hxs.append(tx)
         hys.append(ty)
         points.append((tx,ty))
      if len(hxs) > 4:
         min_hx = min(hxs)
         min_hy = min(hys)
         max_hx = max(hxs)
         max_hy = max(hys)
         dist = calc_dist((min_hx,min_hy),(max_hx,max_hy))
         object['dist'] = dist
         if dist < 5:
            object['status'] = "not_moving"
         else:
            object['status'] = "moving"

      object['hist_len'] = len(hys)   
      if len(hys) > 0: 
         object['dist_per_frame'] = dist / len(hys)
      if len(points) > 3:
         is_straight = arecolinear(points)
         object['is_straight'] =  is_straight
      else:
         object['is_straight'] =  False

      if len(object_hist) <= 300:
         object_hist.append(this_hist)

      object['history'] = object_hist
      object['hist_len'] = len(object_hist)
      objects = save_object(object,objects)
      obj_found = 1
      return(object, objects)

   if len(matches) > 1:
      best_match = find_best_match(matches, cnt, objects)
      #print(fc, "MORE THAN ONE MATCH for",x,y, len(matches))
      #print("--------------------")
      #print(matches)
      #print("--------------------")
      min_dist = 25
      match_total_hist = 0
      for match in matches:
         match_hist = match['history']
         last_hist = match_hist[-1]
         match_x = last_hist[1]
         match_y = last_hist[2]
         dist_to_obj = calc_dist((bx,by),(match_x,match_y))
         if dist_to_obj < min_dist:
            best_dist_obj = match
            min_dist = dist_to_obj
         if len(match_hist) > match_total_hist:
            best_hist_obj = match
            match_total_hist = len(match_hist)

      object = best_hist_obj
      object['status'] = "updated"
      object_hist = object['history']
      this_hist = [fc,x,y,w,h,mx,my,max_px]
      if len(object_hist) <= 150:
         object_hist.append(this_hist)
      object['history'] = object_hist
      object['hist_len'] = len(object_hist)
      objects = save_object(object,objects)
      return(object, objects)

def find_contours(image, orig_image):
   cnt_res = cv2.findContours(image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   pos_cnts = []
   real_cnts = []
   if len(cnts) > 0:
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         size = w + h
        
         cnt_img = orig_image[y:y+h,x:x+w]
         #cv2.imshow('cnt', cnt_img)
         #cv2.waitKey(0)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cnt_img)
         intensity = np.sum(cnt_img)
           

         if w > 1 and h > 1 and max_val > 30:
            pos_cnts.append((x,y,w,h,size,mx,my,max_val,intensity))
            real_cnts.append(cnts[i])
   else:
      print("NO CNTS FOUND.")


   return(real_cnts,pos_cnts)

def make_new_object(oid, fc, x,y,w,h,max_x,max_y,max_px,intensity):
   object = {}
   object['oid'] = oid
   object['fc'] = fc
   object['x'] = x
   object['y'] = y
   object['w'] = w
   object['h'] = h
   object['max_cm'] = 0
   object['gaps'] = 0
   object['gap_events'] = 0 
   object['cm_hist_len_ratio'] = 0 
   object['is_straight'] =  0
   object['hist_len'] =  0
   object['dist'] =  0
   object['dist_per_frame'] =  0
   object['history'] = []
   object['history'].append([fc,x,y,w,h,max_x,max_y,max_px,intensity])
   return(object)

def center_point(x,y,w,h):
   cx = x + (w/2)
   cy = y + (h/2)
   return(cx,cy)

def find_in_hist(object,x,y,object_hist, hd = 0):
   oid = object['oid']
   found = 0
   if hd == 1:
      md = 40
   else:
      md = 25

   # check if this object_hist is stationary already.
   if len(object_hist) > 1:
      moving,desc = meteor_test_moving(object_hist)
      (max_cm,gaps,gap_events,cm_hist_len_ratio) = meteor_test_cm_gaps(object)
      object['max_cm'] = max_cm
      object['gaps'] = gaps
      object['gap_events'] = gap_events
      object['cm_hist_len_ratio'] = cm_hist_len_ratio
   else:
      moving = 0

   if moving == 1:
      fx = object_hist[0][1]
      fy = object_hist[0][2]
      lx = object_hist[-1][1]
      ly = object_hist[-1][2]
      first_last_slope = find_slope((fx,fy), (lx,ly))
      first_this_slope = find_slope((fx,fy), (x,y))
      last_this_slope = find_slope((lx,ly), (x,y))
      if int(oid) == 3:
         slope_diff = abs(abs(first_last_slope) - abs(first_this_slope))
         if slope_diff > 1:
            return(0)

   if len(object_hist) >=4:
      object_hist = object_hist[-3:]

   for hs in object_hist:
      if len(hs) == 9:
         fc,ox,oy,w,h,mx,my,max_px,intensity = hs
      if len(hs) == 8:
         fc,ox,oy,w,h,mx,my,max_px = hs
      
     
      cox = ox + int(w/2)
      coy = oy + int(h/w)
      if ox - md <= x <= ox + md and oy -md <= y <= oy + md:
         found = 1
         return(1)

   # if not found double distance and try again but only if moving!
   if moving == 1:
      md = md * 1.1
      for hs in object_hist:
         if len(hs) == 9:
            fc,ox,oy,w,h,mx,my,max_px, intensity = hs
         if len(hs) == 8:
            fc,ox,oy,w,h,mx,my,max_px = hs
         cox = ox + mx
         coy = oy + my
         if cox - md <= x <= cox + md and coy -md <= y <= coy + md:
            found = 1
            return(1)
   return(found)

def save_object(object,objects):
   new_objects = []
   for obj in objects:
      if object['oid'] == obj['oid']:
         new_objects.append(object)
      else:
         new_objects.append(obj)
   return(new_objects)


def meteor_test_moving(hist):

   (max_x,max_y,min_x,min_y) = find_min_max_dist(hist)
   dist = calc_dist((min_x,min_y),(max_x,max_y))
   if dist <= 1:
      return 0, "Object is NOT moving."
   else:
      return 1, "Object is moving."

def find_min_max_dist(hist,mute_wh=0):
   max_x = 0
   max_y = 0
   min_x = 10000
   min_y = 10000
   #for hs in hist:
   #print("HIST: ", hs)

   for hs in hist:
      #print("HIST: ", len(hs))
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_px,intensity = hs
      if len(hs) == 8:
         fn,x,y,w,h,mx,my,max_px = hs

      max_x, max_y,min_x,min_y = max_xy(x,y,w,h,max_x,max_y,min_x,min_y,mute_wh)

   return(max_x,max_y,min_x,min_y)

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

def arecolinear(points):
    xdiff1 = float(points[1][0] - points[0][0])
    ydiff1 = float(points[1][1] - points[0][1])
    xdiff2 = float(points[2][0] - points[1][0])
    ydiff2 = float(points[2][1] - points[1][1])

    # infinite slope?
    if xdiff1 == 0 or xdiff2 == 0:
        return xdiff1 == xdiff2
    elif ydiff1/xdiff1 == ydiff2/xdiff2:
        return True
    else:
        return False

def meteor_test_cm_gaps(object):
   hist = object['history']
   cm = 0
   max_cm = 0
   gaps = 0
   max_gaps = 0
   gap_events = 0
   last_frame = 0
   for hs in hist:
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_px,intensity = hs
      if len(hs) == 8:
         fn,x,y,w,h,mx,my,max_px = hs
      
      if ((last_frame + 1 == fn) and last_frame > 0) or last_frame == fn:
         cm = cm + 1
      else:
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
   if max_cm > 0:
      cm_hist_len_ratio = max_cm / len(hist)
   else:
      cm_hist_len_ratio = 0
   return(max_cm,gaps,gap_events,cm_hist_len_ratio)

def find_dir_mod(mfd):

   # [fc,x,y,w,h,mx,my,max_px]
   fx = mfd[0][1]
   fy = mfd[0][2]
   lx = mfd[-1][1]
   ly = mfd[-1][2]

   dir_x = fx - lx
   dir_y = fy - ly
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
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

    b = np.mean(ys) - m*np.mean(xs)

    return m, b

def meteor_test_peaks(object):
   points = []
   sizes = []
   hist = object['history']
   for hs in hist:
      if len(hs) == 9:
         fn,x,y,w,h,mx,my,max_px,intensity = hs
      else:
         fn,x,y,w,h,mx,my,max_px = hs
      sizes.append(intensity)
      point = x+mx,y+my
      points.append(point)

   sci_peaks = signal.find_peaks(sizes)
   total_peaks = len(sci_peaks[0])
   total_frames = len(points)
   if total_frames > 0:
      peak_to_frame = total_peaks / total_frames

   return(sci_peaks, peak_to_frame)

def metframes_to_mfd(metframes, sd_video_file):
   hdm_x = 2.7272
   hdm_y = 1.875

   meteor_frame_data = []
   for fn in metframes:
      frame_time,frame_time_str = calc_frame_time(sd_video_file, fn)
      metframes[fn]['frame_time'] = frame_time_str
      if "hd_x" not in metframes[fn]:
         metframes[fn]['hd_x'] = int(metframes[fn]['sd_cx'] * hdm_x)
         metframes[fn]['hd_y'] = int(metframes[fn]['sd_cy'] * hdm_y)
         metframes[fn]['w'] = metframes[fn]['sd_w']
         metframes[fn]['h'] = metframes[fn]['sd_h']
         metframes[fn]['ra'] = 0
         metframes[fn]['dec'] = 0
         metframes[fn]['az'] = 0
         metframes[fn]['el'] = 0
      metframes[fn]['max_px'] = metframes[fn]['sd_intensity']
      meteor_frame_data.append((frame_time_str,fn,int(metframes[fn]['hd_x']),int(metframes[fn]['hd_y']),int(metframes[fn]['w']),int(metframes[fn]['h']),int(metframes[fn]['max_px']),float(metframes[fn]['ra']),float(metframes[fn]['dec']),float(metframes[fn]['az']),float(metframes[fn]['el']) ))
   return(meteor_frame_data, metframes)

def calc_frame_time(video_file, frame_num):
   (f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S) = better_parse_file_date(video_file)
   el = video_file.split("-trim")
   min_file = el[0] + ".mp4"
   ttt = el[1].split(".")
   ttt[0] = ttt[0].replace("-stacked", "")
   trim_num = int(ttt[0])
   extra_sec = trim_num / 25
   start_trim_frame_time = f_datetime + datetime.timedelta(0,extra_sec)
   extra_meteor_sec = int(frame_num) / 25
   meteor_frame_time = start_trim_frame_time + datetime.timedelta(0,extra_meteor_sec)
   meteor_frame_time_str = meteor_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]



   return(meteor_frame_time,meteor_frame_time_str)


def make_meteor_cnt_composite_images(json_conf, mfd, metframes, frames, sd_video_file):
   cmp_images = {}
   cnt_max_w = 0
   cnt_max_h = 0
   for frame_data in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      if w > cnt_max_w:
         cnt_max_w = w
      if h > cnt_max_h:
         cnt_max_h = h

   cnt_w = int(cnt_max_w / 2)
   cnt_h = int(cnt_max_h / 2)
   #if cnt_w < 50 and cnt_h < 50:
   #   cnt_w = 50
   #   cnt_h = 50
   #if cnt_w < 40 and cnt_h < 40:
   #   cnt_w = 40
   #   cnt_h = 40
   if cnt_w < 25 and cnt_h < 25:
      cnt_w = 25
      cnt_h = 25
   else:
      cnt_w = 50
      cnt_h = 50
   #print(cnt_w,cnt_h)
   for frame_data in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = frame_data
      x1,y1,x2,y2 = bound_cnt(hd_x,hd_y,1920,1080,cnt_w)
      #x1 = hd_x - cnt_w
      #x2 = hd_x + cnt_w
      #y1 = hd_y - cnt_h
      #y2 = hd_y + cnt_h
      ifn = int(fn)
      img = frames[ifn]
      hd_img = cv2.resize(img, (1920,1080))
      cnt_img = hd_img[y1:y2,x1:x2]
      metframes[fn]['x1'] = x1
      metframes[fn]['y1'] = y1
      metframes[fn]['x2'] = x2
      metframes[fn]['y2'] = y2
      print("X1:", x1,y1,x2,y2)
      print("CNT:", cnt_img.shape)
      cmp_images[fn] = cnt_img
   return(cmp_images, metframes)

