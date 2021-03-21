import glob
import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel
from PIL import ImageFont, ImageDraw, Image, ImageChops

from Detector import Detector
from Camera import Camera
from Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe


class Meteor():
   def __init__(self, meteor_file=None, min_file=None,detect_obj=None):

      self.json_conf = load_json_file("../conf/as6.json")
      self.sd_objects = None
      self.hd_objects = None
      self.best_meteor = None
      self.cp = None
      if min_file is not None:
         print("MIN FILE WORK!")
         # we are dealing with a new meteor detection here, so initialize appropriately
         # 1) take in the detect object and make trim around ofns
         # 2) find the HD file associated with this detect and make corresponding trim
         #   2a) attempt to sync frames or down sample HD to SD when successful HD detect is made???
         # 3) copy sd_vid, hd_vid to meteor dir and make all of the stacks and thumbs
         # 4) make the meteor json file and save it
         # 5) apply calib to the meteor (put/update cp into meteor file & red file)
         # 6) refine the initial points for error corrections and leading edge and good intensity values
         # 7) update/create the meteor frame data from the detect objects with az,el etc
         # 8) save reduction file
         

      elif meteor_file is not None:
         # we are dealing with a meteor that has already been processed. Set it up the best we can 
         # based on what data is available, the version etc. 
         self.station_id = self.json_conf['site']['ams_id']
         self.lat = self.json_conf['site']['device_lat']
         self.lon = self.json_conf['site']['device_lng']
         self.alt = self.json_conf['site']['device_alt']
         self.meteor_file = meteor_file
         self.meteor_fn = meteor_file.split("/")[-1]
         self.meteor_base = self.meteor_fn.replace(".json", "")
         self.reduce_file = self.meteor_file.replace(".json", "-reduced.json")

         self.trim_num = self.meteor_file.split("trim")[-1]
         self.trim_num = self.trim_num.replace("-", "")
         self.trim_num = self.trim_num.replace(".json", "")
         self.trim_num = self.trim_num.replace(".mp4", "")
         print("TRIM:", self.trim_num)
         self.extra_sec = int(self.trim_num) / 25
         self.file_start_time = datetime.datetime.strptime(self.meteor_fn[0:19], "%Y_%m_%d_%H_%M_%S")
         self.trim_start_time = self.file_start_time + datetime.timedelta(0,self.extra_sec)

         self.date = self.meteor_fn[0:10]
         self.year = self.meteor_fn[0:4]
         self.mon = self.meteor_fn[5:7]
         self.cache_dir_roi = "/mnt/ams2/CACHE/" + self.year + "/" + self.mon + "/" + self.meteor_base + "/"
         self.cache_dir_frames = "/mnt/ams2/CACHE/" + self.year + "/" + self.mon + "/" + self.meteor_base + "_frms/"
         self.cloud_meteor_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/" + self.year + "/" + self.date + "/"

         if cfe(self.cache_dir_roi,1) == 0:
            os.makedirs(self.cache_dir_roi)
         if cfe(self.cache_dir_frames,1) == 0:
            os.makedirs(self.cache_dir_frames)

         if cfe(self.meteor_file) == 1:
            mj = load_json_file(self.meteor_file)
            self.mj = mj
         else:
            self.mj = None
         if cfe(self.reduce_file) == 1:
            mjr = load_json_file(self.reduce_file)
            self.mjr = mjr
         else:
            self.mjr = None
 
         if mj is not None:
            if "sd_video_file" in self.mj:
               self.sd_vid = self.mj['sd_video_file'].split("/")[-1]
               self.sd_stack_file = self.sd_vid.replace(".mp4", "-stacked.jpg")
            else:
               self.sd_vid = None
               self.sd_stack_file = None
         else:
            self.sd_vid = None

         if "hd_trim" in self.mj:
            self.hd_vid = self.mj['hd_video_file'].split("/")[-1]
            self.hd_stack_file = self.hd_vid.replace(".mp4", "-stacked.jpg")
         else:
            self.hd_vid = None
            self.hd_stack_file = None


         calib = Calibration(meteor_file=meteor_file)
         self.cp = calib.cp
         if len(calib.cat_image_stars) > 10:
            calib.minimize_cal_params()
            self.cp['center_az'] = calib.az
            self.cp['center_el'] = calib.el
            self.cp['ra_center'] = calib.ra
            self.cp['dec_center'] = calib.dec
            self.cp['position_angle'] = calib.position_angle
            self.cp['pixscale'] = calib.pixel_scale
            self.cp['x_poly'] = calib.lens_model['x_poly']
            self.cp['y_poly'] = calib.lens_model['y_poly']
            self.cp['x_poly_fwd'] = calib.lens_model['x_poly_fwd']
            self.cp['y_poly_fwd'] = calib.lens_model['y_poly_fwd']
            self.cp['user_stars'] = calib.user_stars
            self.cp['cat_image_stars'] = calib.cat_image_stars
            self.cp['total_res_px'] = calib.total_res_px
            self.cp['total_res_deg'] = calib.total_res_deg
         calib.draw_cal_image()

         self.cams_id = self.sd_vid[24:30]
         self.meteor_day = self.sd_vid[0:10]
         self.meteor_year = self.sd_vid[0:4]
         self.meteor_dir = "/mnt/ams2/meteors/" + self.meteor_day + "/" 
         self.meteor_cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/" + self.meteor_year + "/" + self.meteor_day + "/" 
         self.meteor_url_dir = "https://archive.allsky.tv/" + self.station_id + "/" + self.meteor_year + "/" + self.meteor_day + "/" 
         self.camera = Camera(cams_id = self.cams_id)

         if "multi_station_event" in self.mj:
            self.event_id = self.mj['multi_station_event']['event_id']
         else:
            self.event_id = None

         if "best_meteor" in mj:
            self.best_meteor = mj['best_meteor']
         else:
            print("RUN METEOR SCAN!")
            self.meteor_scan()

   def meteor_scan_crop(self, obj):
      x1,y1,x2,y2 = self.define_area_box(obj, self.fw, self.fh, 10)
      crop_x1 = x1
      crop_y1 = y1
      crop_bg = self.sd_frames[0][y1:y2,x1:x2]
      crop_bg = cv2.cvtColor(crop_bg, cv2.COLOR_BGR2GRAY)
      last_best_cnt = None
      last_thresh = None
      self.sd_objects = []
      #for i in range(0, len(obj['ofns'])):
      fn = 0
      evc = 0
      crop_fd = []
      mike = 1
      x_dir = obj['report']['x_dir']
      y_dir = obj['report']['y_dir'] 
      dom_dir = obj['report']['dom_dir'] 
 

      for frame in self.sd_frames:
         #fn = obj['ofns'][i]
         crop = self.sd_frames[fn][y1:y2,x1:x2]
         crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
         crop_sub = cv2.subtract(crop, crop_bg)
         big_crop = cv2.resize(crop, (crop.shape[1]*10,crop.shape[0]*10))
         avg_val = np.median(crop_sub)
         max_val = np.max(crop_sub)
         thresh_val = (max_val/2) + avg_val
         if thresh_val < 10:
            thresh_val = 10
         if thresh_val > 10:
            thresh_val = 10 
         _, threshold = cv2.threshold(crop_sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnts,noise = self.get_contours(threshold, crop_sub, fn, 1)
         crop_show = crop.copy()
         if len(cnts) > 0:
            evc += 1

         # pick the leading cnt of all available
         best_cnt = None
         for data in cnts:
            fn, x, y, w, h, cx, cy, intensity = data
            if best_cnt is not None:
               if obj['report']['dom_dir'] == "x":
                  if x_dir > 0:
                     if x < best_cnt[1] :
                        best_cnt = data
                     # lower x is better
                  else:
                     if x > best_cnt[1] :
                        best_cnt = data
                     # higher x is better
               else:
                  if y_dir > 0:
                     if y < best_cnt[2]:
                        best_cnt = data
                  else:
                     if y > best_cnt[2]:
                        best_cnt = data
            else:
               best_cnt = data

         # only add the cnt if it is further on the track than the previous one
         if evc > 2:
            good = 0
         else:
            good = 1
         if last_best_cnt is not None and best_cnt is not None:
            fn, x, y, w, h, cx, cy, intensity = best_cnt 
            if obj['report']['dom_dir'] == "x":
               if x_dir > 0:
                  if x < last_best_cnt[1]:
                     good = 1
               else:
                  if x > last_best_cnt[1]:
                     good = 1
            else:
               if y_dir > 0:
                  if y < last_best_cnt[2]:
                     good = 1
               else:
                  if y > last_best_cnt[2]:
                     good = 1
         if best_cnt is not None: 
            if good == 1:
               cv2.rectangle(crop_show, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1) 
               crop_fd.append(("GOOD", best_cnt))
            else:
               cv2.rectangle(crop_show, (int(x), int(y)), (int(x+w) , int(y+h) ), (0, 0, 255), 1) 
               crop_fd.append(("BAD", best_cnt))


         fn += 1
         last_best_cnt = best_cnt
         last_thresh = threshold 

      # here we have all of the cnts in the crop area event time
      # some are bad so let's first remove the bad ones at the end

      first_fn = crop_fd[0][1][0]
      last_fn = crop_fd[-1][1][0]
    
      # here we will try to get the leading x,y
      temp = []
      for status, best_cnt in crop_fd:
         fn, x, y, w, h, cx, cy, intensity = best_cnt 

         # first get the leading corner of the cnt
         if x_dir > 0:
            lx = x 
         else:
            lx = x + w
         if y_dir > 0:
            ly = y
         else:
            ly = y + h

         temp.append((status,fn, x, y, w, h, cx, cy, lx, ly, intensity))
      temp = sorted(temp, key=lambda x: (x[1]), reverse=True)
      good = []
      first_good_frame = 0
      for best_cnt in temp:
         status, fn, x, y, w, h, cx, cy, lx, ly, intensity = best_cnt 
         if status == "BAD" and first_good_frame == 0:
            foo = 1
         else:
            first_good_frame = 1
         if first_good_frame == 1:
            good.append(best_cnt)
      good = sorted(good, key=lambda x: (x[1]), reverse=False)

      # now things will be pretty good, but we might still have a rouge bad frame at the start (from a star) 
      # check just the first frame and make sure it is good else delete it
      if good[0][0] == "BAD" or (good[0][1] - good[1][1] > 1):
         good.remove[0]
      good2 = []
      # now check frames in the middle. If there is just 1 bad frame separated by 2 good frames fix it. 
      for i in range(0, len(good)):
         status, fn, x, y, w, h, cx, cy, lx, ly, intensity = good[i] 
         if status == "BAD" and i + 1 < len(good) and i > 0:
            if good[i+1][0] == "GOOD":
               last_x = good[i-1][2]
               last_y = good[i-1][3]
               last_w = good[i-1][4]
               last_h = good[i-1][5]
               next_x = good[i+1][2]
               next_y = good[i+1][3]
               next_w = good[i+1][4]
               next_h = good[i+1][5]
               this_x = int((last_x + next_x)/2)
               this_y = int((last_y + next_y)/2)
               this_w = int((last_w + next_w)/2)
               this_h = int((last_h + next_h)/2)
               this_cx = int(this_x + (this_w/2))
               this_cy = int(this_y + (this_h/2))
               good2.append(("FIXED", fn, this_x, this_y, this_w, this_h, this_cx, this_cy, lx, ly, intensity))
         else:
            good2.append(("FIXED", fn, x, y, w, h, cx, cy, lx, ly, intensity))
            #good2.append(good[i])

      # now everything should be fixed but there might be some missing frames still in the middle of the event
      for i in range(0,len(good2)):
         data = good2[i]
         if i+ 1 < len(good2):
            act_next_fn = good2[i+1][1] 
            next_fn = data[1] + 1

      # now that all frames are as good as they can get, convert the frames to objects and classify
      objects = {}
      obj['ofns'] = []
      obj['oxs'] = []
      obj['oys'] = []
      obj['ows'] = []
      obj['ohs'] = []
      obj['ocxs'] = []
      obj['ocys'] = []
      obj['olxs'] = []
      obj['olys'] = []
      obj['oint'] = []
      for fd in good2:
         status, fn, x, y, w, h, cx, cy, lx, ly,intensity = fd
         obj['ofns'].append(fn)
         obj['oxs'].append(x+x1)
         obj['oys'].append(y+y1)
         obj['ows'].append(w)
         obj['ohs'].append(h)
         obj['ocxs'].append(cx+x1)
         obj['ocys'].append(cy+y1)
         obj['olxs'].append(lx+x1)
         obj['olys'].append(ly+y1)
         obj['oint'].append(intensity)
         oid, objects = Detector.find_objects(fn,x+crop_x1,y+crop_y1,w,h,cx+crop_x1,cy+crop_y1,intensity,objects, 20, lx+crop_x1, ly+crop_y1)
         status, report = Detector.analyze_object(obj)
         obj['report'] = report
         obj = self.add_obj_estimates(obj)
 
      oid = obj['oid']
      objects = {}
      objects[oid] = obj
      self.report_objects(objects)

   def add_obj_estimates(self, obj):
      lxs = obj['olxs']
      lys = obj['olys']
      med_x = obj['report']['med_x']
      med_y = obj['report']['med_y']
      oexs = []
      oeys = []
      oe2xs = []
      oe2ys = []
      for i in range(0, len(lxs)):
         if i > 0:
            est2_x = lxs[i-1] + int(med_x)
            est2_y = lys[i-1] + int(med_y)
         else:
            est2_x = lxs[i]
            est2_y = lys[i]
         if i > 3 and i + 3 < len(lxs):
            prevx = np.mean(lxs[i-3:i])
            nextx = np.mean(lxs[i:i+3])
            prevy = np.mean(lys[i-3:i])
            nexty = np.mean(lys[i:i+3])
            est_x = int((prevx+nextx)/2)
            est_y = int((prevy+nexty)/2)
         else:
            est_x = lxs[i]
            est_y = lys[i]
         oexs.append(est_x)
         oeys.append(est_y)
         oe2xs.append(est2_x)
         oe2ys.append(est2_y)
      obj['oexs'] = oexs 
      obj['oeys'] = oeys 
      obj['oe2xs'] = oe2xs 
      obj['oe2ys'] = oe2ys 
      return(obj)

   def merge_objects(self, objects):
      frame_data = {}
      obj = {}
      obj['ofns'] = []
      obj['oxs'] = []
      obj['oys'] = []
      obj['ows'] = []
      obj['ohs'] = []
      obj['ocxs'] = []
      obj['ocys'] = []
      obj['olxs'] = []
      obj['olys'] = []
      obj['oint'] = []

      for obj in objects:
         for i in range(0, len(obj['ofns'])):
            fn = obj['ofns'][i]
            if fn not in frame_data:
               frame_data[fn] = {}
               frame_data[fn]['cnts'] = []
            x = obj['oxs'][i]
            cx = obj['ocxs'][i]
            y = obj['oys'][i]
            cy = obj['ocys'][i]
            w = obj['ows'][i]
            h = obj['ohs'][i]
            oint = obj['oint'][i]
            frame_data[fn]['cnts'].append((fn,x,y,w,h,cx,cy,oint))

      for fn in frame_data:
         fn, x, y, w, h, cx, cy, intensity = frame_data[fn]['cnts'][0] 
         obj['ofns'].append(fn)
         obj['oxs'].append(x)
         obj['oys'].append(y)
         obj['ows'].append(w)
         obj['ohs'].append(h)
         obj['ocxs'].append(cx)
         obj['ocys'].append(cy)
         #obj['olxs'].append(lx)
         #obj['olys'].append(ly)
         obj['oint'].append(intensity)
         status, report = Detector.analyze_object(obj)
         obj['report'] = report
         #obj = self.add_obj_estimates(obj)
      return([obj]) 



   def report_objects(self, objects):

      show_img = self.sd_stacked_image.copy()
      for oid in objects:
         obj = objects[oid]
         x1,y1,x2,y2 = self.define_area_box(objects[oid], self.fw, self.fh, 10)

         mult1 = int(800/ (x2-x1))
         mult2 = int(800/ (y2-y1))
         #crop_img = show_img[y1:y2,x1:x2] 
         #crop_img_big = cv2.resize(crop_img, (crop_img.shape[1]*mult, crop_img.shape[0]*mult))
         if mult1 < mult2:
            mult = mult1 
         else:
            mult = mult2
         #big_crop = cv2.resize(crop_img,(int(crop_img.shape[1]*mult),int(crop_img.shape[0]*mult)))
         #if len(big_crop.shape) == 2:
         #   big_crop = cv2.cvtColor(big_crop, cv2.COLOR_GRAY2BGR)
         cv2.rectangle(show_img, (x1,y1), (x2,y2), (255, 255, 255), 1) 

         for i in range(0,len(obj['ofns'])):
            x = obj['oxs'][i]
            y = obj['oys'][i]
            w = obj['ows'][i]
            h = obj['ohs'][i]
            cx = obj['ocxs'][i]
            cy = obj['ocys'][i]
            if i < len(obj['olxs']):
               lx = obj['olxs'][i]
               ly = obj['olys'][i]
            else:
               lx = cx
               ly = cy
            bly = (ly - y1)* mult 
            blx = (lx - x1)* mult 
            # dom dir is left/right
            if w < h:
               wh = w
            else:
               wh = h
            if obj['report']['dom_dir'] == "x":
               if obj['report']['x_dir'] < 0:
                  # left to right
                  blx1 = blx - wh*mult/2
                  blx2 = blx + wh*mult
               else:
                  blx1 = blx 
                  blx2 = blx + wh*mult/2

               if obj['report']['y_dir'] < 0:
                  # top to bottom 
                  bly1 = bly - int(wh*mult/2)
                  bly2 = bly 
               else:
                  bly1 = bly 
                  bly2 = bly + int(wh*mult/2)
            # dom dir is up/down 
            else:
               if obj['report']['x_dir'] < 0:
                  # left to right
                  blx1 = blx - wh*mult/2
                  blx2 = blx 
               else:
                  # right to left
                  blx1 = blx 
                  blx2 = blx + wh/2*mult

               if obj['report']['y_dir'] <0:
                  bly1 = bly - int(wh*mult/2)
                  bly2 = bly 
               else:
                  bly1 = bly 
                  bly2 = bly + int(wh*mult/2)


            # leading edge corner cnt 
            #cv2.rectangle(big_crop, (int(blx1), int(bly1)), (int(blx2), int(bly2)), (0, 0, 255), 1) 

            cv2.rectangle(show_img, (int(x), int(y)), (int(x+w), int(y+h)), (128, 128, 128), 1) 
            #cnt_crop = show_img[y:y+h,x:x+w]
            #cv2.rectangle(big_crop, (int((x-x1)*mult), int((y-y1)*mult)), (int((x-x1)*mult+w*mult), int((y-y1)*mult+h*mult)), (128, 128, 128), 1) 
            #big_crop[bly,blx] = [0,0,255]
            #cv2.putText(big_crop, str(i),  ((blx), (bly)), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            #cv2.putText(big_crop, str(obj['report']['class']),  ((10), (20)), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            #cv2.circle(big_crop,(blx,bly), 2, (0,0,255), 1)
         cv2.putText(show_img,obj['report']['class'], ((obj['oxs'][0]), (obj['oys'][0])), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         #cv2.imshow('final_crop_big', big_crop)
      cv2.imshow('Report Objects', show_img)
      cv2.waitKey(100)

   def meteor_scan(self):
      print("   meteor scan.", self.meteor_dir + self.sd_vid)
      mask2 = None


      self.sd_frames, self.sd_stacked_image = self.load_frames(self.meteor_dir + self.sd_vid)

      self.sd_wh = (self.sd_frames[0].shape[1],self.sd_frames[0].shape[0])
      self.hdm_x = 1920 / self.sd_wh[0]
      self.hdm_y = 1080 / self.sd_wh[1]

      self.first_frame = self.sd_frames[0].copy()
      self.sd_subframes = []
      self.max_vals = []
      self.avg_vals = []
      self.cnts = []
      self.fw = self.sd_frames[0].shape[1] 
      self.fh = self.sd_frames[0].shape[0] 
      fc = 0
      frame_cnts = []
      detect = Detector()
      work_stack = self.sd_stacked_image.copy()

      # scan SD file first and gather the frame cnts 
      last_sub = None
      extra_thresh = 0
      for frame in self.sd_frames:
         if self.camera.mask_img is not None:
            if self.camera.mask_img.shape[0] != frame.shape[0]:
               self.camera_mask_img = cv2.resize(self.camera.mask_img, (frame.shape[1], frame.shape[0]))
            frame = cv2.subtract(frame, self.camera.mask_img)
            if mask2 is not None:
               frame = cv2.subtract(frame, mask2)

         sub = cv2.subtract(frame, self.first_frame)
         sub = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
         if fc > 10 :
            sub = cv2.subtract(sub, self.sd_subframes[fc-10])
         self.sd_subframes.append(sub)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         avg_val = np.mean(sub)
         sum_val = np.sum(sub)
         self.max_vals.append(max_val)
         self.avg_vals.append(avg_val)
         if len(self.max_vals) < 10:
            self.avg_max_val = np.median(self.max_vals)
            self.avg_avg_val = np.median(self.avg_vals)

         thresh_val = self.avg_avg_val + 5 + extra_thresh
         _, threshold = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)

         f_thresh_val = np.mean(frame) + (np.mean(frame) * .8)
         _, thresh2 = cv2.threshold(frame.copy(), f_thresh_val, 255, cv2.THRESH_BINARY)
         if mask2 is None :
            mask2 = cv2.dilate(thresh2.copy(), None , iterations=4)

         cnts,noise = self.get_contours(threshold, sub, fc, 1)
         if len(cnts) > 5 and extra_thresh < 15:
            extra_thresh += 5
         
         show_img = sub.copy()
         for data in cnts:
            fn, x, y, w, h, cx, cy, intensity = data
            cv2.rectangle(show_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1) 
            frame_cnts.append((fn,x,y,w,h,cx,cy,intensity))

         if fc > 10:
            self.first_frame = self.sd_frames[-10]
         fc += 1
         last_sub = threshold 
      self.sd_frame_cnts = frame_cnts
      # END 1st scan of frames

      # convert frame data into objects
      objects = {}
      for fn,x,y,w,h,cx,cy,intensity in self.sd_frame_cnts:
         oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 20)
      pos_meteors = []

      clean_objects = {}
      noise_objects = {}
      for oid in objects:
         status, report = Detector.analyze_object(objects[oid])
         objects[oid]['report'] = report
         new_objs = self.clean_met_obj(objects[oid])
         if len(new_objs) > 0:
            new_obj = new_objs[0]
            status, report = Detector.analyze_object(objects[oid])
            clean_objects[oid] = new_obj
            clean_objects[oid]['report'] = report
         else:
            noise_objects[oid] = objects[oid]

      # we only want to clean potential meteor objects!
      # important 
      #if len(clean_objects.keys()) > 0:
      #   foo = 1
         #objects = clean_objects
      #else:
      #   print("NO METEOR OBJECTS DETECTED!")
      #   cv2.imshow("NO METEOR OBJECTS DETECTED!", work_stack)
      #   cv2.waitKey(0)
         #return()


      for oid in objects:
         status, report = Detector.analyze_object(objects[oid])
         if report['class'] == "meteor" or report['class'] == "unknown":
            pos_meteors.append(objects[oid])

      print("      We have", len(pos_meteors), "possible meteors.")
      if len(pos_meteors) == 0:
         self.pos_meteors = pos_meteors
         self.sd_objects = objects
         self.meteor_detected = 0
      if len(pos_meteors) == 1:
         self.pos_meteors = pos_meteors
         self.sd_objects = objects
         self.meteor_detected = 1
         self.best_meteor = pos_meteors[0]
      if len(pos_meteors) == 2:
         # most likely case is these are the same overlapping check. 
         xs1 = pos_meteors[0]['oxs']
         ys1 = pos_meteors[0]['oys']
         xs2 = pos_meteors[1]['oxs']
         ys2 = pos_meteors[1]['oys']
         if len(xs1) > len(xs2):
            dom_x = xs1
            sub_x = xs2
            dom_y = ys1
            sub_y = ys2
         else:
            dom_x = xs2
            sub_x = xs1
            dom_y = ys2
            sub_y = ys1
         sub_cx = np.mean(sub_x)
         sub_cy = np.mean(sub_y)
         if min(dom_x) - 20 <= sub_cx <= max(dom_x) + 20 and min(dom_y) -20 <= sub_cy <= max(dom_y) + 20:
            # the sub is part of the dom merge the two
            print("SUB IS INSIDE DOM")
            pos_meteors = self.merge_objects(pos_meteors)
         else:
            print("SUB IS NOT PART OF THE DOM?", min(dom_x), sub_cx, max(dom_x), min(dom_y), sub_cy, max(dom_y))

         print("      AFTER MERGE WE HAVE", len(pos_meteors), "meteors")
         for pos in pos_meteors:
            print(pos)
         self.pos_meteors = pos_meteors
         self.sd_objects = objects
         self.meteor_detected = 1
         self.best_meteor = pos_meteors[0]

      if len(pos_meteors) > 2:
         # Lots of possible meteors here. Let's see how many fit inside the same cont
         work_stack = self.sd_stacked_image.copy()
         bsize = 0
         for pos in pos_meteors:
            size = len(pos['ofns']) 
            if size > bsize:
               dom_obj = pos
               bsize = size
         print("DOM OBJ : ", dom_obj['oid'])
         children = []
         other_objs = []
         spectra = []
         cv2.putText(work_stack, str(dom_obj['oid']) + " " + str(dom_obj['report']['class']),  (dom_obj['oxs'][0], dom_obj['oys'][0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         dx1 = min(dom_obj['oxs']) - 20
         dx2 = max(dom_obj['oxs']) - 20
         dy1 = min(dom_obj['oys']) + 20
         dy2 = max(dom_obj['oys']) + 20
         cx1 = np.mean(dom_obj['oxs'])
         cy1 = np.mean(dom_obj['oys'])
         for pos in pos_meteors:
            if pos['oid'] != dom_obj['oid']:
               center_x = np.mean(pos['oxs'])
               center_y = np.mean(pos['oys'])
               min_dist = self.min_obj_dist(dom_obj, pos)
               print("MIN DIST:", min_dist)
               if (dx1 <= center_x <= dx2 and dy1 <= center_y <= dy2) or min_dist < 25:
                  children.append(pos['oid'])
               elif cy1 - 20 <= center_y <= cy1 + 20:
                  spectra.append(pos['oid'])
               else:
                  other_objs.append(pos['oid'])
         print("CHILDREN:", children)
         print("NON-CHILDREN:", other_objs)
         print("SPECTRA :", spectra)



         for oid in children:
            obj = objects[oid]
            cv2.putText(work_stack, str(obj['oid']) + " " + str(obj['report']['class']),  (obj['oxs'][0], obj['oys'][0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            cv2.rectangle(work_stack, (int(min(obj['oxs'])), int(min(obj['oys']))), (int(max(obj['oxs'])) , int(max(obj['oys'])) ), (0, 0, 255), 1) 
            print("DOM FN:", dom_obj['ofns'])
            print("CHILD FN:", obj['ofns'])

         for oid in other_objs:
            obj = objects[oid]
            cv2.putText(work_stack, str(obj['oid']) + " " + str(obj['report']['class']),  (obj['oxs'][0], obj['oys'][0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         for oid in spectra:
            obj = objects[oid]
            cv2.putText(work_stack, str(obj['oid']) + " spectra" ,  (obj['oxs'][0], obj['oys'][0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)

         # MERGE DOM & CHILDREN INTO 1 OBJ. # still have merge fn bugs too!
         self.best_meteor = dom_obj
         self.pos_meteors = [dom_obj]
         doid = dom_obj['oid']
         objects[doid]['report']['class'] = "meteor"
         self.sd_objects = objects
         cv2.rectangle(work_stack, (int(dx1), int(dy1)), (int(dx2) , int(dy2) ), (0, 0, 255), 1) 
         cv2.imshow('pepe', work_stack)
         cv2.waitKey(0)
         #exit()

      #self.report_objects(objects)

      # at this point if we have 1 possible meteor we are done and can return. 
      # we will do crop scan / point refinement in next phase

      # if we have more than 1 pos_meteor we need to figure out what is going on.
      # most common issue is it is the same meteor split across 2 objects (due to spacing or gaps)
      # if the 2 objects are close to each other in space and fn time just merge them.
      # if they are separated far then maybe they are 2 simultaneous meteors
      # we need special handling for this. 
      # the other posibility is spectra lines so we should try to look for that and filter it out. 
      # the goal here is to have just 1 possible meteor inside this scan

   def min_obj_dist(self, obj1, obj2):
      # calculate the min distance between all points in both objects
      min_dist = 99999
      for i in range(0,len(obj1['ofns'])):
         x1 = obj1['ocxs'][i]
         y1 = obj1['ocys'][i]
         for i in range(0,len(obj2['ofns'])):
            x2 = obj2['ocxs'][i]
            y2 = obj2['ocys'][i]
            dist = calc_dist((x1,y1),(x2,y2))
            if dist < min_dist:
               min_dist = dist
      return(min_dist)

   def meteor_scan_phase2 (self):

      # clean up and re-analyze pos_meteors
      clean_objs = []
      for obj in pos_meteors:
         new_obj = self.clean_met_obj(obj)
         #status, report = Detector.analyze_object(objects[oid])
         #obj['report'] = report
         clean_objs.append(obj)
      pos_meteors = clean_objs
      if len(pos_meteors) > 1:
         pos_meteors = self.merge_objects(pos_meteors)

      if len(pos_meteors) == 1:
         #self.meteor_scan_crop(obj)
         met = pos_meteors[0]
         x1 = min(met['ocxs']) - 50
         y1 = min(met['ocys']) - 50
         x2 = max(met['ocxs']) + 50
         y2 = max(met['ocys']) + 50
         if x1 < 0:
            x1 = 0
         if y1 < 0:
            y1 = 0
         if x2 >= self.fw:
            x2 = self.fw
         if y2 >= self.fh:
            x2 = self.fh

         self.sd_min_max = [x1,x2,y1,y2]
         message = "METEOR DETECTED"
         cv2.rectangle(work_stack, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 255), 1) 

      elif len(pos_meteors) > 1:
         message = "MULTIPLE METEORS DETECTED"
         merged_meteors = self.merge_overlapping_objects(pos_meteors)
         for obj in pos_meteors:
            x1,y1,x2,y2 = self.define_area_box(obj, self.fw, self.fh)
            self.meteor_scan_crop(obj)
            if y1 < 100:
               cv2.putText(work_stack, str(obj['oid']) + " " + obj['report']['class'],  (x1, y2), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            else:
               cv2.putText(work_stack, str(obj['oid']) + " " + obj['report']['class'],  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            cv2.rectangle(work_stack, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1) 
      else:
         message = "NO METEOR LIKE OBJECTS DETECTED!"
         if len(work_stack) == 2:
            work_stack = cv2.cvtColor(work_stack,cv2.COLOR_GRAY2BGR)

      # now we are done with the initial meteor scan
      # all objects should be classed or unknown 
      # at this point we only care about meteors or unknowns
      # return the objs for now and we can finalize the clean up
      # in another function


      show_image = work_stack.copy()
      for oid in objects:
         obj = objects[oid]
         #self.meteor_scan_crop(obj)
         x = obj['oxs'][0]
         y = obj['oys'][0]
         x1,y1,x2,y2 = self.define_area_box(obj, self.fw, self.fh)
         if obj['report']['class'] == "meteor":
            cv2.rectangle(show_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 255), 1) 
            cv2.putText(show_image, str(obj['oid']) + " " + obj['report']['class'],  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         elif obj['report']['class'] == "unknown":
            cv2.rectangle(show_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 128, 128), 1) 
            cv2.putText(show_image, str(obj['oid']) + " " + obj['report']['class'],  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         elif obj['report']['class'] == "plane":
            cv2.rectangle(show_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 128, 128), 1) 
            cv2.putText(show_image, str(obj['oid']) + " " + obj['report']['class'],  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         elif obj['report']['class'] == "star":
            foo = 1
            #cv2.rectangle(show_image, (int(x1+40), int(y1+40)), (int(x2-40) , int(y2-40) ), (128, 128, 128), 1) 
         else:
            cv2.rectangle(show_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1) 
            cv2.putText(show_image, str(obj['oid']) + " " + obj['report']['class'],  (x, y), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)

      self.sd_min_max = [0,0,0,0]
      cv2.imshow("METEOR SCAN OBJ SUMMARY", show_image)
      cv2.waitKey(200)

      self.report_objects(objects)
      



   def clean_met_obj(self,obj):

      # flatten object into frames
      frame_data = {}
      if obj['report']['x_dir'] < 0:
         x_dir = "l2r"
      else:
         x_dir = "r2l"
      if obj['report']['y_dir'] < 0:
         y_dir = "t2b"
      else:
         y_dir = "b2t"
      for i in range(0, len(obj['ofns'])):
         fn = obj['ofns'][i]
         x = obj['oxs'][i]
         cx = obj['ocxs'][i]
         y = obj['oys'][i]
         cy = obj['ocys'][i]
         w = obj['ows'][i]
         h = obj['ohs'][i]
         oint = obj['oint'][i]
         if fn not in frame_data:
            frame_data[fn] = {}
            frame_data[fn]['cnts'] = []
         frame_data[fn]['cnts'].append((fn,x,y,w,h,cx,cy,oint))

      # pick best cnt if there is more than 1 
      for fn in frame_data:
         if len(frame_data[fn]['cnts']) > 1:
            if obj['report']['dom_dir'] == 'x':
               # sort cnts by x, lowest first
               cnts = sorted(frame_data[fn]['cnts'], key=lambda x: (x[1]), reverse=False)
               if x_dir == "r2l":
                  best_cnt = cnts[0]
               else:
                  best_cnt = cnts[-1]
            if obj['report']['dom_dir'] == 'y':
               # sort cnts by y, lowest first
               cnts = sorted(frame_data[fn]['cnts'], key=lambda x: (x[2]), reverse=False)
               if x_dir == "b2t":
                  best_cnt = cnts[0]
               else:
                  best_cnt = cnts[-1]
            frame_data[fn]['cnts'] = [best_cnt]

      # loop over frames but only add the frame if it 'works'
      good_frame_data = {}
      start = None
      last_dist_from_start = None
      last_fn = None
      for fn in frame_data:
         bad = 0
         cx = frame_data[fn]['cnts'][0][5]
         cy = frame_data[fn]['cnts'][0][6]
         if start is None:
            sx = cx
            sy = cy
            if fn + 1 in frame_data or fn + 2 in frame_data:
               start = fn
               # check 
         if start is not None:
            dist_from_start = calc_dist((sx,sy),(cx,cy))
            if last_fn is not None:
               fn_diff = fn - last_fn
            if last_dist_from_start is not None:
               if last_dist_from_start > dist_from_start and fn_diff < 3:
                  bad = 1
            
            if bad == 0:
               good_frame_data[fn] = frame_data[fn]
            last_dist_from_start = dist_from_start
            last_x = cx
            last_y = cy
            last_fn = fn

      # now check for missing frames in the middle.
      # NOT IMPLEMENTED YET (MAYBE MOVE THIS)
      #fc = None
      #for fn in good_frame_data:
      #   if fc is None:
      #      fc = fn
      #   print(fn, good_frame_data[fn])
      #   if fc not in good_frame_data:
      #      print("Add missing frame.", fc)
      #   fc += 1

      # convert the good clean frame data back to an object 
      # and analyze it
      objects = {}
      for fn in good_frame_data:
         (fn,x,y,w,h,cx,cy,intensity) = frame_data[fn]['cnts'][0]
         oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 20)

      best_objects = []
      for oid in objects:
         status, report = Detector.analyze_object(objects[oid])
         objects[oid]['report'] = report
         best_objects.append(objects[oid])

      return(best_objects)
   


   def merge_overlapping_objects(self, objects):
      merged = {}
      mc = 1
      merged_oids = []
      for obj in objects:
         oid = obj['oid']
         x1,y1,x2,y2 = self.define_area_box(obj, self.fw, self.fh)
         for merged_obj in objects:
            moid = merged_obj['oid']
            mx1,my1,mx2,my2 = self.define_area_box(merged_obj, self.fw, self.fh)
            if oid != moid:
               if (mx1 <= x1 <= mx2 and my1 <= y1 <= my2) or (mx1 <= x1 <= mx2 and my1 <= y2 <= my2) or (mx1 <= x2 <= mx2 and my1 <= y1 <= my2) or (mx1 <= x2 <= mx2 and my1 <= y2 <= my2) :
                  merged_oids.append((oid, moid))


   def merge_oids(self,oid,moid):
      area_points = []
      for i in range(0, len(oid['ofns'])):
         area_points.append((oid['oxs'][i], oid['oys'][i]))
      for i in range(0, len(moid['ofns'])):
         area_points.append((moid['oxs'][i], moid['oys'][i]))
      rect = cv2.minAreaRect(area_points)
      print("rect: {}".format(rect))
      exit() 
      if oid['oid'] < moid['oid']:
         o1 = oid 
         o2 = moid 
      else:
         o1 = moid 
         o2 = oid 
      nfns = []
      nxs = []
      nys = []
      nws = []
      nhs = []
      nintensity= []
      ncxs = []
      ncys = []
      for i in range(0, len(o1['ofns'])):
         nfns.append(o1['ofns'][i])
         nxs.append(o1['oxs'][i])
         nys.append(o1['oys'][i])
         nws.append(o1['ows'][i])
         nhs.append(o1['ohs'][i])
         nintensity.append(o1['oint'][i])
         ncxs.append(o1['ocxs'][i])
         ncys.append(o1['ocys'][i])
      new_obj = {}
      new_obj['oid'] = o1['oid']
      new_obj['ofns'] = nfns 
      new_obj['oxs'] = nxs 
      new_obj['oys'] = nys 
      new_obj['ows'] = nws 
      new_obj['ohs'] = nhs 
      new_obj['nintensity'] = nintensity
      new_obj['ncxs'] = ncxs
      new_obj['ncys'] = ncys
      return(new_obj) 

   def define_area_box(self,met,fw,fh,size=50):
      x1 = min(met['ocxs']) - size
      y1 = min(met['ocys']) - size
      x2 = max(met['ocxs']) + size
      y2 = max(met['ocys']) + size
      if x1 < 0:
         x1 = 0
      if y1 < 0:
         y1 = 0
      if x2 >= fw:
         x2 = fw
      if y2 >= fh:
         x2 = fh
      return(x1,y1,x2,y2)


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
      BXS = data[inliers,0]
      BYS = data[inliers,1]
      plt.show()
      return(XS,YS,BXS,BYS)


   def get_contours(self,thresh_frame,sub,fc, multi=1):
      cont = []
      cnt_res = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      noise = 0
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(sub[y:y+h,x:x+w]))
         x = int(x * multi)
         y = int(y * multi)
         h = int(h * multi)
         w = int(w * multi)
         cx = int(x + (w/2))
         cy = int(y + (h/2))
         # skip if this cnt is inside another already
         if x != 0 and y != 0 and w > 1 and h > 1:
            cont.append((fc, x,y,w,h,cx,cy,intensity))
         else:
            noise += 1

      good_cont = []
      for data in cont:
         fc, x,y,w,h,cx,cy,intensity = data
         if self.is_inside_cnt(x,y,w,h,cont) == 1:
            continue
         else:
            good_cont.append(data)



      return(good_cont, noise)

   def is_inside_cnt(self,tx,ty,tw,th,cnts):
      for fc,x,y,w,h,cx,cy,intensity in cnts:
         if tx != x and ty != y:
            if (x <= tx <= x+w or x <= tx + tw <= x+w) and (y <= ty <= y+h or y <= ty + th <= y+h) :
               return(1)
      return(0)

   def update_meteor_reduce(self):
      # update the DTs here too!
      # update current x,y points with latest calibration params
      # if we have LXs use those
      # if we have user mods use those!  
      self.best_meteor['ras'] = []
      self.best_meteor['decs'] = []
      self.best_meteor['azs'] = []
      self.best_meteor['els'] = []
      self.best_meteor['dt'] = []
      self.event_dur = (self.best_meteor['ofns'][-1] - self.best_meteor['ofns'][0])/2

      for i in range(0, len(self.best_meteor['oxs'])):
         fn = self.best_meteor['ofns'][i]
         extra_sec = fn / 25
         frame_time = self.trim_start_time + datetime.timedelta(0,extra_sec)
         frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
         self.best_meteor['dt'].append(frame_time_str)
         cx = int(self.best_meteor['ocxs'][i] * self.hdm_x)
         cy = int(self.best_meteor['ocys'][i] * self.hdm_y)
         tx, ty, ra ,dec , az, el = XYtoRADec(cx,cy,self.sd_vid,self.cp,self.json_conf)
         self.best_meteor['ras'].append(ra)
         self.best_meteor['decs'].append(dec)
         self.best_meteor['azs'].append(az)
         self.best_meteor['els'].append(el)
      self.best_meteor['report']['ang_dist'] = abs(angularSeparation(self.best_meteor['ras'][0],self.best_meteor['decs'][0],self.best_meteor['ras'][-1],self.best_meteor['decs'][-1]))
      self.best_meteor['report']['ang_sep'] = abs(angularSeparation(self.best_meteor['ras'][0],self.best_meteor['decs'][0],self.best_meteor['ras'][-1],self.best_meteor['decs'][-1]))
      self.best_meteor['report']['ang_vel'] = self.best_meteor['report']['ang_sep'] / self.event_dur


   def save_meteor_files(self):
      self.update_meteor_reduce()
      self.make_meteor_frame_data()
      print("save the meteor file and reduce file")
      if cfe(self.meteor_file) == 1:
         mj = load_json_file(self.meteor_file)
      else:
         mj = {}
      if cfe(self.reduce_file) == 1:
         mjr = load_json_file(self.reduce_file)
      else:
         mjr = {}
      mjr["station_id"] = self.station_id
      mjr["device_name"] = self.cams_id
      mjr["sd_video_file"] = self.sd_vid
      mjr["sd_stack"] = self.sd_stack_file
      mjr["hd_video_file"] = self.hd_vid
      mjr["hd_stack"] = self.hd_stack_file
      mjr["crop_box"] = self.crop_box

      mj['cp'] = self.cp
      mj['best_meteor'] = self.best_meteor

      mjr['meteor_frame_data'] = self.meteor_frame_data
      mjr['cal_params'] = self.cp
      save_json_file(self.meteor_file, mj)
      save_json_file(self.reduce_file, mjr)

   def make_meteor_frame_data(self):
      # don't forget to add the user_mods / user overrides. 
      self.meteor_frame_data = []
      hdm_x_720 = 1920 / 1280
      hdm_y_720 = 1080 / 720
      if self.best_meteor is not None:
         min_x = min(self.best_meteor['oxs'])
         max_x = max(self.best_meteor['oxs'])
         min_y = min(self.best_meteor['oys'])
         max_y = max(self.best_meteor['oys'])
         self.crop_box = [int(min_x*self.hdm_x),int(min_y*self.hdm_y),int(max_x*self.hdm_x),int(max_y*self.hdm_y)]
         for i in range(0, len(self.best_meteor['ofns'])):
            #dt = "1999-01-01 00:00:00"
            fn = self.best_meteor['ofns'][i]
            x = int(self.best_meteor['ocxs'][i] * self.hdm_x)
            y = int(self.best_meteor['ocys'][i] * self.hdm_y)
            w = self.best_meteor['ows'][i]
            h = self.best_meteor['ohs'][i]
            ra = self.best_meteor['ras'][i]
            dec = self.best_meteor['decs'][i]
            az = self.best_meteor['azs'][i]
            el = self.best_meteor['els'][i]
            oint = self.best_meteor['oint'][i]
            dt = self.best_meteor['dt'][i]
            oint = self.best_meteor['oint'][i]
            self.meteor_frame_data.append((dt, fn, x, y, w, h, oint, ra, dec, az, el))

   def make_cache_files(self):
      ff = self.meteor_frame_data[0][1] 
      lf = self.meteor_frame_data[-1][1]
      sf = ff - 10
      ef = lf + 10
      if sf < 0:
         sf = 0
      if ef > len(self.sd_frames):
         ef = len(self.sd_frames) - 1


      mfd = {}
      for data in self.meteor_frame_data:
         (dt, fn, x, y, w, h, oint, ra, dec, az, el) = data
         mfd[fn] = (dt, fn, x, y, w, h, oint, ra, dec, az, el)

      print(sf, ef)
      for i in range(sf, ef):
         frm_file = self.cache_dir_frames + self.meteor_base + "-{:04d}".format(i) + ".jpg"
         print(frm_file)
         frame = self.sd_frames[i]
         frame_1080 = cv2.resize(frame,(1920,1080))
         if i in mfd:
            print("MFD:", i)
            (dt, fn, x, y, w, h, oint, ra, dec, az, el) = mfd[i]
            x1,y1,x2,y2 = self.roi_area(x,y,1920,1080,50)
            roi_img = frame_1080[y1:y2,x1:x2]

            ffn = "{:04d}".format(int(fn))
            outfile = self.cache_dir_roi + self.meteor_base + "-frm" + ffn + ".jpg"
            print(outfile)
            cv2.imwrite(outfile, roi_img)

            cv2.imshow('pepe2', roi_img)
            cv2.imshow('pepe', frame)
            cv2.waitKey(0)

   def roi_area(self,x,y,iw,ih,roi_size):
      rs = int(roi_size/2)
      x1 = x - rs
      x2 = x + rs
      y1 = y - rs
      y2 = y + rs
      if x1 < 0:
         x2 = x2 + (x1*-1)
         x1 = 0 
      if y1 < 0:
         y2 = y2 + (y1*-1)
         y1 = 0 
      if x2 > iw:
         x2 = iw
         x1 = x1 - (x2-iw)
      if y2 > ih:
         y2 = ih
         y1 = y1 - (y2-ih)
      return(x1,y1,x2,y2) 

   def make_frame_cache_files(self):

      for data in self.meteor_frame_data:
         (dt, fn, x, y, w, h, oint, ra, dec, az, el) = data

   def make_final_trim(self, min_file, trim_start, trim_end ):
      print("Make ")


   def make_full_frame_cache(self):
      print("Make full frame cache.")

   def make_roi_thumbs(self):
      print("Make roi thumbs (for web admin).")

   def apply_calib_to_frames(self):
      print("Make ")

   def make_meteor_images(self):
      print("Make ")


   def retrim_minute_clip(self):
      print("Make ")

   def load_frames(self,trim_file):
      stacked_image = None
      if cfe(trim_file) == 0:
         print("trim file not found!", trim_file)

      cap = cv2.VideoCapture(trim_file)
      frames = []
      go = 1
      frame_count = 0
      while go == 1:
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return(frames, None)
            else:
               go = 0
         if frame is not None:
            frames.append(frame)
            if stacked_image is None:
               stacked_image = Image.fromarray(frame)
            else:
               frame_pil = Image.fromarray(frame)
               stacked_image=ImageChops.lighter(stacked_image,frame_pil)


         if frame_count > 1499:
            go = 0


         frame_count += 1

      cap.release()
      return(frames,np.asarray(stacked_image))






if __name__ == "__main__":
   import sys
   #meteors = glob.glob("/mnt/ams2/meteors/2021_03_20/*.json")
   meteors = ['/mnt/ams2/meteors/2021_03_20/2021_03_20_06_54_00_000_010002-trim-0528.json']
   for meteor_file in meteors:
      if "reduced" not in meteor_file:
         my_meteor = Meteor(meteor_file=meteor_file)
         print("My Meteor:", my_meteor.sd_vid)
         my_meteor.meteor_scan()
         my_meteor.report_objects(my_meteor.sd_objects)
         my_meteor.save_meteor_files()
         my_meteor.make_cache_files()
         exit()
