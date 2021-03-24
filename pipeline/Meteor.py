import glob
import math
import os
import scipy.optimize
import numpy as np
import datetime
import cv2
from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

from PIL import ImageFont, ImageDraw, Image, ImageChops

from DisplayFrame import DisplayFrame 
from Detector import Detector
from Camera import Camera
from Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.FFFuncs import best_crop_size, ffprobe 



class Meteor():
   def __init__(self, meteor_file=None, min_file=None,detect_obj=None):
      self.DF = DisplayFrame()
      self.json_conf = load_json_file("../conf/as6.json")
      self.sd_objects = None
      self.hd_objects = None
      self.best_meteor = None
      self.frame_data = []
      self.meteor_scan_info = {}
      self.cp = None
      self.sd_frames = None
      self.hd_frames = None
      self.crop_frames = None
      self.crop_box = None
      self.crop_scan = None
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
         print("LOADING DATA FROM METEOR FILE:", meteor_file)
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
            if "sd_stack" in mj:
               if cfe(self.mj['sd_stack']) == 1:
                  self.sd_stacked_file = self.mj['sd_stack']
                  self.sd_stacked_image = cv2.imread(self.sd_stacked_file)
                  self.fw = self.sd_stacked_image.shape[1]
                  self.fh = self.sd_stacked_image.shape[0]

                  self.hdm_x = 1920 / self.fw
                  self.hdm_y = 1080 / self.fh
                  self.hdm_x_720 = 1280 / self.fw
                  self.hdm_y_720 = 720/ self.fh
            if "crop_scan" in mj:
               self.crop_scan = mj['crop_scan']

            if "meteor_scan_info" in mj:
               self.meteor_scan_info = mj['meteor_scan_info']
            else:
               self.meteor_scan_info = {}

            if "best_meteor" in mj:
               #print("LOAD BEST:", mj['best_meteor'])
               if "obj_id" in mj['best_meteor']:
                  oid = mj['best_meteor']['obj_id']
               else:
                  oid = 1
               if "sd_objects" not in self.meteor_scan_info:
                  self.meteor_scan_info['sd_objects'] = {}
               self.meteor_scan_info['sd_objects'][oid] = mj['best_meteor']
               self.best_meteor = mj['best_meteor']

               # Since ccxs are saved in 720 we need to convert these back to native SD for things to work right!
               # need to do on all objects in the meteor_scan['sd_objects'] array and the best_meteor array
               wi = self.sd_stacked_image.copy()
               wi7 = cv2.resize(wi, (1280,720))
               #for oid in self.meteor_scan_info['sd_objects']:
               if False:
                  obj = self.meteor_scan_info['sd_objects']
                  for oid in self.meteor_scan_info['sd_objects']:
                     # values saved at 720p res convert to SD
                     before_x = self.meteor_scan_info['sd_objects'][oid]['ccxs']
                     before_y = self.meteor_scan_info['sd_objects'][oid]['ccys']
                     print("BEFORE:", before_x, before_y)
                     for i in range(0, len(self.meteor_scan_info['sd_objects'][oid]['ofns'])):
                        cx = self.meteor_scan_info['sd_objects'][oid]['ccxs'][i]
                        cy = self.meteor_scan_info['sd_objects'][oid]['ccxs'][i]
                        cx7 = int(cx / self.hdm_x_720)
                        cy7 = int(cy / self.hdm_y_720)
                        print("CONV720:", cx,cy,cx7,cy7)
                        self.meteor_scan_info['sd_objects'][oid]['ccxs'][i] = cx7
                        self.meteor_scan_info['sd_objects'][oid]['ccxs'][i] = cy7
                     aft_x = self.meteor_scan_info['sd_objects'][oid]['ccxs']
                     aft_y = self.meteor_scan_info['sd_objects'][oid]['ccys']
                     print("AFT:", aft_x, aft_y)
               for i in range(0, len(self.best_meteor['ofns'])):
                  x = self.best_meteor['oxs'][i]
                  y = self.best_meteor['oys'][i]
                  w = self.best_meteor['ows'][i]
                  h = self.best_meteor['ohs'][i]
                  tcx = int(x + (w/2))
                  tcy = int(y + (h/2))
                  cx = self.best_meteor['ccxs'][i]
                  cy = self.best_meteor['ccys'][i]
                  cx7 = int(cx / self.hdm_x_720)
                  cy7 = int(cy / self.hdm_y_720)

                  tcx7 = int(tcx * self.hdm_x_720)
                  tcy7 = int(tcy * self.hdm_y_720)


                  cv2.circle(wi,(tcx,tcy), 2, (0,255,255), 1)
                  cv2.circle(wi,(cx7,cy7), 2, (0,0,255), 1)
                  cv2.circle(wi,(cx,cy), 2, (255,0,255), 1)


                  cv2.circle(wi7,(cx,cy), 2, (0,255,0), 1)
                  cv2.circle(wi7,(tcx7,tcy7), 2, (0,255,255), 1)
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



   def meteor_scan_crop(self, obj=None):
      print("METEOR SCAN CROP")
      if self.best_meteor is None and obj is None:
         print("    ABORT: THERE IS NO BEST METEOR OR OBJECT PASSED IN.")
         return()
      work_image = self.sd_stacked_image
      if "sd_objects" in self.meteor_scan_info:
         for oid in self.meteor_scan_info['sd_objects']:
            obj = self.meteor_scan_info['sd_objects'][oid]
            if len(obj['ofns']) >= 3:
               print("SD OBJ:", oid, obj['ofns'])
               print("SD OBJ:", oid, obj['ofns'])
               for i in range(0, len(obj['ofns'])):
                  cv2.circle(work_image,(obj['oxs'][i],obj['oys'][i]), 2, (0,0,255), 1)

         obj = self.best_meteor
         if len(obj['ofns']) >= 3:
            oid = obj['obj_id']
            print("SD OBJ:", oid, obj['ofns'])
            print("SD OBJ:", oid, obj['ofns'])
            for i in range(0, len(obj['ofns'])):
               cv2.circle(work_image,(obj['oxs'][i],obj['oys'][i]), 2, (0,255,255), 1)

         
      if self.sd_frames is None:
         self.load_frames(self.meteor_dir + self.sd_vid)

      self.crop_frames = self.make_object_crop_frames()
      self.crop_vals_data, self.crop_vals_event = self.vals_scan(self.crop_frames)
      self.crop_scan = {}

      self.contour_crop_scan(self.crop_frames)

      self.hd_stacked_image = cv2.resize(self.sd_stacked_image,(1920,1080))
      x1,y1,x2,y2 = self.hd_crop_box


      self.hd_crop_stacked_image = self.hd_stacked_image[y1:y2,x1:x2]
      work_stack = self.hd_crop_stacked_image.copy()
      if x1 < 540:
         cv2.putText(work_stack, str("Meteor"),  (x1,y2-20), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
      else:
         cv2.putText(work_stack, str("Meteor"),  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)

      # show the crop stack
      cv2.imshow('crop',work_stack)
      cv2.waitKey(300)
      my_meteor.save_meteor_files()
      print("SAVED METEOR FILES.", self.meteor_file)



   def contour_crop_scan(self, crop_frames):
      past_cnts = []
      self.crop_frame_data = {}
      last_cx = None
      last_cnt = None
      xds = []
      yds = []
 

      fc = 0
      crop_h, crop_w = self.crop_frames[0].shape[:2]
      for frame in self.crop_frames: 
         event, cm, mvf, fcc, sum_val, avg_val, max_val, mx, my = self.crop_vals_data[fc]
         frame = self.crop_frames[fc]
         thresh_val,cnts = self.find_best_thresh_val(frame, self.crop_frames[0], fc ,past_cnts)
         past_cnts.append(cnts)
         crop_show = frame.copy() 
         if len(cnts) > 0:
            fn, x, y, w, h, cx, cy, intensity = cnts[0]
            if last_cx is not None:
               x_dist = cx - last_cx
               y_dist = cy - last_cy
               xds.append(x_dist)
               yds.append(y_dist)
            if fn not in self.crop_frame_data:
               self.crop_frame_data[fn] = {}
               self.crop_frame_data[fn]['cnts'] = []
            self.crop_frame_data[fn]['cnts'].append(cnts[0])
            cv2.rectangle(crop_show, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1) 
            last_cnt = cnts[0]
            last_cx = cx
            last_cy = cy
         else:
            if fc > 0:
               #print("Contour is missing, use a real time estimate of where it should be!")
               print("Contour is missing, do not fill it might be a false cnt!")
               if last_cnt is not None:
                  fn, x, y, w, h, cx, cy, intensity = last_cnt 
                  if len(xds) > 3:
                     med_xd = np.median(xds)
                     med_yd = np.median(yds)
                  elif len(xds) > 1:
                     med_xd = np.mean(xds)
                     med_yd = np.mean(yds)
                  elif len(xds) == 1:
                     med_xd = xds[0]
                     med_yd = yds[0]
                  else:
                     med_xd = 0 
                     med_yd = 0
                  print("LAST X,Y, xd,yd:", cx,cy, med_xd,med_yd)
                  new_x = x + med_xd
                  new_y = y + med_yd
                  print("NEW X:", x, y, med_xd, med_yd) 
                  cv2.rectangle(crop_show, (int(new_x), int(new_y)), (int(new_x+w) , int(new_y+h) ), (128, 128, 255), 1) 
         fc += 1

         mult_x = int(1280/frame.shape[1])
         mult_y = int(720/frame.shape[0])
         if mult_x < mult_y:
            mult = int(mult_x)
         else:
            mult = int(mult_y)
         if mult > 1:
            crop_show = cv2.resize(crop_show, (frame.shape[1]*mult, frame.shape[0]*mult))

         cv2.imshow('crop', crop_show)
         cv2.waitKey(30)

      # now we should have good enough data to fit line
      # and make channel mask
      # we need to do this to avoid random false noise
      #cmask = self.make_channel(XS,YS)
      XS = []
      YS = []

      objects = {}
      crop_x1 = self.hd_crop_box[0]
      crop_y1 = self.hd_crop_box[1]
      for fn in self.crop_frame_data:
         print(fn, self.crop_frame_data[fn]['cnts'])
         for data in self.crop_frame_data[fn]['cnts']:
            fn, x, y, w, h, cx, cy, intensity = data
            print("FIND FN:", fn)
            oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 50)
      for oid in objects:
         if len(objects[oid]['ofns']) >= 3:
            status, report = Detector.analyze_object(objects[oid])
            print("STATUS:", status)
            objects[oid]['report'] = report
         else:
            print("BAD OBJ:", oid)
            #del objects[oid]
      
      # do we have a meteor obj that is what we want to build the channel from
      pos_meteors = []
      for oid in objects:
         self.print_object(objects[oid])
         if "report" not in objects[oid]:
            print("REJECT OBJ", oid)
            obj_class = "unknown"
         else:
            obj_class = objects[oid]['report']['class']
         if obj_class == "meteor":
            pos_meteors.append(objects[oid])
            print("********************************** METEORMETEOR ************************************")
            print("********************************** METEORMETEOR ************************************")
            print("********************************** METEORMETEOR ************************************")
            print("********************************** METEORMETEOR ************************************")
            print("********************************** METEORMETEOR ************************************")
            print("OBJ:", objects[oid]['ofns'])

            cmask = self.make_channel(objects[oid]['ccxs'],objects[oid]['ccys'], crop_w,crop_h)
            #cv2.imshow("MASK", cmask)
            #cv2.waitKey(30)

      # if the meteor has not been detected by here it doesn't exist or there is an issue we don't have code to handle. 
      # just fail out for now.
      if len(pos_meteors) == 0:
         self.crop_scan = {}
         self.crop_scan['status'] = -1
         self.crop_scan['desc'] = "No crop scan meteors found."
         return()

      # THE meteor should be good now in most cases, but lets run the scan 1 more time using the channel mask to fine too it.
      first_frame = self.crop_frames[0]
      fc = 0
      for frame in self.crop_frames:
         sub = cv2.subtract(frame, first_frame)
         sub = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
         sub = cv2.subtract(sub, cmask)
         fc += 1
      if len(pos_meteors) == 1:
         self.crop_scan['status'] = 1
         self.crop_scan['desc'] = "crop scan meteor found"
         self.crop_scan['best_meteor'] = pos_meteors[0]
      else:
         print("************** CRAP: there is more than one possible meteor after the crop scan.")
         # need to add merge/filter code
         self.crop_scan['status'] = 1
         self.crop_scan['desc'] = "crop scan meteor found"
         self.crop_scan['best_meteor'] = None
         self.crop_scan['pos_meteors'] = pos_meteors


   def print_object(self,obj):
      for key in obj:
         if key == "report":
            for rkey in obj[key]:
               print("      REPORT:", rkey, obj[key][rkey])
         print("   ", key, obj[key])

   def find_best_thresh_val(self,frame, first_frame, fn ,past_cnts=[]):
      i = 10

      for gcnt in past_cnts:
         for cnt in gcnt:
            print(cnt)
            pfn, x, y, w, h, cx, cy, intensity = cnt
            if w > 10 or h > 10:
               w = 10
               h = 10

            frame[y:y+h,x:x+w] = 0,0,0
      sub = cv2.subtract(frame, first_frame)

      max_val = np.max(frame)

      while i > 0:
         thresh_val = max_val + ((i - 10) * 20)
         if thresh_val < 10:
            thresh_val = 10

            
         _, threshold = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         threshold = cv2.cvtColor(threshold, cv2.COLOR_BGR2GRAY)
         print("SELF:", self.meteor_file)
         cnts,noise = self.get_contours(threshold, sub, fn, 1,thresh_val)
         print("    fn, max_val, thresh val, cnts :", fn, max_val, thresh_val, len(cnts))
         if cnts == 1 or thresh_val <= 10:
            i = -1
         i = i - 1
      return(thresh_val, cnts)

   def find_group(self, fn, x,y,groups):
      if len(groups.keys()) == 0:
         print("   GROUPS: MAKE FIRST GROUP")
         gid = 1
         groups[1] = []
         groups[1].append((gid,fn,x,y))
         return(gid, groups)
      else:
         print("   GROUPS: SEARCH FOR GROUP")
         for gid in groups:
            for cnt in groups[gid]:
               print(cnt)
               gid,gfn, gx,gy = cnt
               dist = calc_dist((x,y,),(gx,gy))
               if dist < 20:
                  group = [gid,fn,x,y]
                  groups[gid].append(group)
                  print("   GROUP FOUND: SEARCH FOR GROUP")
                  return(gid, groups)

      # if we made it this far it must be a new group
      print("   GROUPS: NEW GROUP MADE")
      gid = max(groups.keys())
      gid += 1
      groups[gid] = []
      group = [gid,fn,x,y]
      groups[gid].append(group)
      return(gid, groups)


   def vals_scan(self, frames):
      # scan the vals (sum,max,avg) of each frame and add detection metrics
      sub_vals_data = []
      fc = 0
      first_frame = None
      # get the basic vals data on the frames
      for frame in frames:
         gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         if first_frame is None:
            first_frame = gray_frame
         sub = cv2.subtract(gray_frame, first_frame)
         sum_val = int(np.sum(frame))
         avg_val = int(np.mean(frame))
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         sub_vals_data.append((fc, sum_val, avg_val, max_val, mx, my))
         fc += 1

      # find duplicate mx,my frames -- these are frames with nothing happening e.g. no event
      vdd = {}
      vd_masks = []
      for data in sub_vals_data:
          vdkey = str(data[4]) + "." + str(data[5])
          if vdkey not in vdd:
             vdd[vdkey] = 1
          else:
             vdd[vdkey] += 1
      for key in vdd:
         print("VDD:", key, vdd[key])
         if vdd[key] >= 2:
            vx,vy = key.split(".")
            vd_masks.append((int(vx),int(vy)))

      # determine starting mean max val
      vals_data = []
      perc15 = int(len(sub_vals_data) * .15)
      max_vals = [mdata[3] for mdata in sub_vals_data]

      print("P15", perc15, len(sub_vals_data))
      max_val_avg = np.mean(max_vals[0:perc15])
      print("P15", perc15, len(sub_vals_data), max_val_avg)
      if max_val_avg == 0 :
         max_val_avg = 1

      # enhance vals scan data to add event detection, consectutive motion and max val factor.
      # with these vars it is safe to say there is an event when event = 1, cm >= 1 and mvf is elevated. 
      # from this you can find the 1st and last frame for the meteor
      # we will use this to further refine the event
      cm = 0
      no_ev = 0
      event_data = []
      CXS = []
      CYS = []
      groups = {}
      for data in sub_vals_data:
          fc, sum_val, avg_val, max_val, mx, my = data

          CXS.append(mx)
          CYS.append(my)
          RES = self.find_group(fc,mx,my,groups)
          print("GR:", RES)
          gid, groups = RES
          vdkey = str(data[4]) + "." + str(data[5])
          mvf = int(max_val / max_val_avg)
          if vdd[vdkey] > 2 or (mx == 0 or my == 0):
             print("IGNORE:", fc, vdd[vdkey])
             no_ev += 1
             event = 0
             if cm == 1 and no_ev == 2:
                cm = 0
             if no_ev >= 5:
                cm = 0
          else:
             print("KEEP:", fc, vdd[vdkey])
             cm += 1
             no_ev = 0
             event = 1
          if cm >= 1 and no_ev >= 5:
             cm = 0
          if event == 1 and mvf >= 2:
             print("ADD EVENT DATA!", fc, event)
             event_data.append((event, cm, mvf, fc, sum_val, avg_val, max_val, mx, my))
          vals_data.append((event, cm, mvf, fc, sum_val, avg_val, max_val, mx, my))

      cv2.imshow('pepe', self.sd_stacked_image)
      cv2.waitKey(30)
      good_groups = []
      group_objects = []
      oc = 1
      for key in groups:
         print("GROUP:", key)
         CXS = []
         CYS = []
         KEYS = []

         obj = self.new_object() 
         obj['obj_id'] = 1
         #fn, x, y, w, h, cx, cy, intensity = cnt
         for cnt in groups[key]:
            gid,fn,x,y = cnt
            xxx = [fn,x,y,4,4,x+2,y+2,999]
            self.update_object(obj,xxx)
            CXS.append(x)
            CYS.append(y)
            KEYS.append(str(x) + "." + str(y))

         unq = set(KEYS)
         status, report = Detector.analyze_object(obj)
         obj['status'] = status
         obj['report'] = report
         group_objects.append((key,obj))

      print("GOOD GROUPS:", len(good_groups))
      work_img = self.sd_stacked_image.copy()
      meteor_found = 0
      for gid, obj in group_objects:
         print(gid, obj['ofns'], obj['report']['class'])

         if obj['report']['class'] == 'meteor' or obj['report']['class'] == "unknown":
            meteor_found = 1
            cv2.putText(work_img, str(obj['report']['class']),  ((obj['oxs'][0]), (obj['oys'][0])), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            cv2.imshow('pepe', work_img)

            try:
               NXS, NYS, BXS, BYS,LINE_X,LINE_Y,LINE_RANSAC_Y = self.ransac_outliers(CXS,CYS, "Group " + str(key))
               ransac_run = 1
               good_groups.append(groups[key])
            except:
               ranscan_failed = 1
         else:
            cv2.putText(work_img, str(obj['report']['class']),  ((obj['oxs'][0]), (obj['oys'][0])), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            cv2.imshow('pepe', work_img)
            cv2.waitKey(30)
      if meteor_found == 0:
         xxx = input("NO METEOR FOUND FROM THE VALS DETECTOR!")
      # find the event end and trim the array to only active event frames
      over = 0
      last_cm = 0
      new_cm = 0
      new_event_data = []
      last_fc = None
      last_frame_diff = 0 
      for data in event_data:
         (event, cm, mvf, fc, sum_val, avg_val, max_val, mx, my) = data
         if last_cm != 0 and cm - last_cm == 0:
            new_cm += 1 
         else:
            over = 0
         if last_fc is not None:
            last_frame_diff = fc - last_fc
         last_cm = cm
         (event, new_cm, mvf, fc, sum_val, avg_val, max_val, mx, my) = data
         print("MIKE:", fc, cm, last_frame_diff)
         if new_cm <= 1 or 0 <= last_frame_diff <= 2:
            new_event_data.append(data)
         last_fc = fc
      over = over * -1
      print("OVER:", over)
      active_event_data = new_event_data 
      # [0:over]
      if len(active_event_data) == 0:
         for data in vals_data:
            print(vals_data)
         xx = input("VALS EVENT DETECT FAILED." + self.meteor_file)

      return(vals_data, active_event_data)

   def make_object_crop_frames(self, obj=None):
      # take an existing meteor scan detection, crop the frames around it
      # and then re-scan to fix problems in the first scan
      # apply channel mask, detection monitor and start/end frame indicator based on the sum/max/avg val scans
      crop_frames = []
      if self.sd_frames is None:
         self.load_frames(self.meteor_dir + self.sd_vid)
      
      if obj is None:
         obj = self.best_meteor
      if obj is None:
         return(crop_frames)
      x1,y1,x2,y2 = self.define_area_box(obj, self.fw, self.fh, 10)
      x1 = int(x1 * self.hdm_x)
      x2 = int(x2 * self.hdm_x)
      y1 = int(y1 * self.hdm_y)
      y2 = int(y2 * self.hdm_y)
      x1,y1,x2,y2 = self.expand_crop_area(x1,y1,x2,y2,50)
      print("HD:", x1,y1,x2,y2)
      self.hd_crop_box = [x1,y1,x2,y2] 
      for sd_frame in self.sd_frames:
         # resize frame to 1080p and work in this scale
         hd_frame = cv2.resize(sd_frame.copy(), (1920,1080))
         crop_frame = hd_frame[y1:y2,x1:x2]
         crop_frames.append(crop_frame)
      return(crop_frames)

   def expand_crop_area(self,x1,y1,x2,y2,exp):
      x1 = x1 - exp
      y1 = y1 - exp
      x2 = x2 + exp
      y2 = y2 + exp
      if x1 < 0:
         x1 = 0
      if y1 < 0:
         y1 = 0
      if x2 >= 1920:
         x2 = 1919 
      if y2 >= 1080:
         y2 = 1079
      return(x1,y1,x2,y2)

   def meteor_scan_crop_old(self, obj):

      x1,y1,x2,y2 = self.define_area_box(obj, self.fw, self.fh, 10)
      x1 = x1 - 50
      y1 = y1 - 50
      x2 = x2 + 50
      y2 = y2 + 50
      if x1 < 0:
         x1 = 0
      if y1 < 0:
         y1 = 0
      if x2 > 1920:
         x2 = 1920 
      if y2 > 1080:
         y2 = 1080
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
         cnts,noise = self.get_contours(threshold, crop_sub, fn, 1,thresh_val)
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
      obj['ccxs'] = []
      obj['ccys'] = []
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
         obj['ccxs'].append(cx+x1)
         obj['ccys'].append(cy+y1)
         obj['olxs'].append(lx+x1)
         obj['olys'].append(ly+y1)
         obj['oint'].append(intensity)
         oid, objects = Detector.find_objects(fn,x+crop_x1,y+crop_y1,w,h,cx+crop_x1,cy+crop_y1,intensity,objects, 20, lx+crop_x1, ly+crop_y1)

      status, report = Detector.analyze_object(obj)
      obj['report'] = report
      obj = self.add_obj_estimates(obj)
 
      oid = obj['obj_id']
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
      obj['ccxs'] = []
      obj['ccys'] = []
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
            cx = obj['ccxs'][i]
            y = obj['oys'][i]
            cy = obj['ccys'][i]
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
         obj['ccxs'].append(cx)
         obj['ccys'].append(cy)
         #obj['olxs'].append(lx)
         #obj['olys'].append(ly)
         obj['oint'].append(intensity)
         status, report = Detector.analyze_object(obj)
         obj['report'] = report
         #obj = self.add_obj_estimates(obj)
      return([obj]) 



   def report_objects(self, objects=None):
      objects = self.meteor_scan_info['sd_objects']
      show_img = self.sd_stacked_image.copy()
      print("OBJECTS:", len(objects))
      for oid in objects:
         print("OID:", oid, objects[oid])
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
         print("X1:", x1,y1,x2,y2)
         cv2.rectangle(show_img, (x1,y1), (x2,y2), (255, 255, 255), 1) 

         for i in range(0,len(obj['ofns'])):
            x = obj['oxs'][i]
            y = obj['oys'][i]
            w = obj['ows'][i]
            h = obj['ohs'][i]
            cx = obj['ccxs'][i]
            cy = obj['ccys'][i]
            if "olxs" in obj:
               if i < len(obj['olxs']):
                  lx = obj['olxs'][i]
                  ly = obj['olys'][i]
               else:
                  lx = cx
                  ly = cy
               bly = (ly - y1)* mult 
               blx = (lx - x1)* mult 
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
            if "report" in obj:
               if "dom_dir" not in obj['report']:
                  continue
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
      self.DF.add_image(0,4,show_img)
      self.DF.render_frame(0 )
      print("Frame rendered for report obj")

   def vals_detect_crop_confirm(self):

      mxs = [data[7] for data in self.vals_event]
      mys = [data[8] for data in self.vals_event]
      x1 = min(mxs) 
      x2 = max(mxs)
      y1 = min(mys) 
      y2 = max(mys)
      cw = x2 - x1
      ch = y2 - y1
      if cw > ch:
         msize = cw 
      else:
         msize = ch 
      if msize > 50:
         msize = 50
      if msize < 25:
         msize = 25
      x1,y1,x2,y2 = self.expand_crop_area(x1,y1,x2,y2,msize)

      ff = self.sd_frames[0].copy()
      fcf = ff[y1:y2,x1:x2]
      frame_data = {}
      self.crop_frames = []
      fn = 0
      SD_XS = []
      SD_YS = []
      CXS = []
      CYS = []
      for frame in self.sd_frames:
            
         crop_frame = frame[y1:y2,x1:x2]
         self.crop_frames.append(crop_frame)
         sub_crop = cv2.subtract(crop_frame, fcf)
         sub_crop = cv2.cvtColor(sub_crop, cv2.COLOR_BGR2GRAY)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub_crop)
         if max_val > 10:
            thresh_val = max_val - (max_val * .25)
         else:
            thresh_val = 10
         _, sub_crop_thresh = cv2.threshold(sub_crop.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnts = self.get_contours_simple(sub_crop_thresh, sub_crop)

         for data in cnts:
            print("CNT:", data)
            (x,y,w,h,intensity) = data
            SD_XS.append(x+x1)
            SD_XS.append(x+x1+w)
            SD_YS.append(y+y1)
            SD_YS.append(y+h+y1)
            CXS.append(int(x + (w/2)))
            CYS.append(int(y + (h/2)))
            if fn not in frame_data:
               frame_data[fn] = {}
               frame_data[fn]['cnts'] = []
            frame_data[fn]['cnts'].append(data) 
            cv2.rectangle(sub_crop_thresh, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1) 
         sub_crop_thresh = cv2.resize(sub_crop_thresh, (sub_crop_thresh.shape[1]*5, sub_crop_thresh.shape[0]*5))

         cv2.imshow('vals_detect', sub_crop_thresh)
         if len(cnts) > 0:
            cv2.waitKey(30)
         else:
            cv2.waitKey(30)
         fn += 1

      # We could have bad points, so let's remove the outliers 
      try:
         NXS, NYS, BXS, BYS,LINE_X,LINE_Y,LINE_RANSAC_Y = self.ransac_outliers(CXS,CYS, "VALS CROP CONFIRM")
      except:
         print("RANSAC FAILED.")


      # convert the frame data to a new object and we are almost done
      # but first make sure we have choosen the best cnt for each frame (if there is more than 1)
      # to do this we need dom_dir/x_dir/y_dir info about the cnt
      dom_dir, x_dir, y_dir, move_area = self.get_move_info(CXS,CYS)
      obj = self.new_object() 
      for fn in frame_data:
         if len(frame_data[fn]['cnts']) > 1:
            lead_cnt = self.get_lead_cnt(frame_data[fn]['cnts'])
         else:
            lead_cnt = frame_data[fn]['cnts'][0]
         x, y, w, h, intensity = lead_cnt
         cx = int(x + (w/2))
         cy = int(y + (h/2))
         cnt = [fn, x+x1, y+y1, w, h, cx+x1,cy+y1, intensity]
         frame_data[fn]['cnts'] = [cnt]
         obj = self.update_object(obj, cnt)
      obj['obj_id'] = 1
      status, report = Detector.analyze_object(obj)
      obj['report'] = report

      self.print_object(obj)

      HDX1,HDY1,HDX2,HDY2 = self.get_hd_crop_area_169(SD_XS,SD_YS)
      obj['hd_crop_169'] = [HDX1,HDY1,HDX2,HDY2]
      hd_stack = cv2.resize(self.sd_stacked_image, (1920,1080))
      status = 0
      if obj['report']['class'] == "meteor":
         cv2.putText(hd_stack, str("Meteor"),  (HDX1,HDY2+20), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         status = 1

      cv2.rectangle(hd_stack, (int(HDX1), int(HDY1)), (int(HDX2) , int(HDY2) ), (255, 255, 255), 1) 
      self.hd_detect_stack = hd_stack
      return(status, obj)

   def get_lead_cnt(self, cnts):
      best_val = None
      best_cnt = None
      print("GET LEAD:", cnts)
      for cnt in cnts:
         x,y,w,h,intensity = cnt
         print("DOM:", self.dom_dir, self.x_dir, self.y_dir)
         print("CNT:", x,y,w,h)
         if self.dom_dir == "x":
            # dom movement is left/right use x_dir to decide best

            if self.x_dir > 0:
               # movement is right to left we want cnt with lowest x val (x)
               if best_val is None:
                  best_val = x
                  best_cnt = cnt
               if x < best_val :
                  best_val = x
                  best_cnt = cnt
            else:
               # movement is left to right we want cnt with highest x val (x+w)
               if best_val is None:
                  best_val = x + w
                  best_cnt = cnt
               if x + w >  best_val :
                  best_val = x + w
                  best_cnt = cnt
         else:
            # dom movement is up/down use y_dir to decide best
            if self.y_dir > 0:
               # movement is down to up we want cnt with lowest y val (y)
               if best_val is None:
                  best_val = y 
                  best_cnt = cnt
               if y < best_val :
                  best_val = y 
                  best_cnt = cnt
            else:
               # movement is up to down we want cnt with highest y val (y+h)
               if best_val is None:
                  best_val = y + h
                  best_cnt = cnt
               if y + h >  best_val :
                  best_val = y + h
                  best_cnt = cnt
      return(best_cnt)

   def get_move_info(self, XS,YS):
      # Should pass in list of center xs,ys for object
      min_x = min(XS)
      max_x = max(XS)
      min_y = min(YS)
      max_y = max(YS)
      x_dir = XS[0] - XS[-1]
      y_dir = YS[0] - YS[-1]
      if abs(x_dir) > abs(y_dir):
         dom_dir = "x"
      else:
         dom_dir = "y"
      self.dom_dir = dom_dir
      self.x_dir = x_dir
      self.y_dir = y_dir
      self.move_area = [min_x,min_y,max_x,max_y]
      return(dom_dir, x_dir, y_dir,[min_x,min_y,max_x,max_y])

   def meteor_scan(self):
      print("   meteor scan.", self.meteor_dir + self.sd_vid)
      mask2 = None

      self.load_frames(self.meteor_dir + self.sd_vid)

      self.fw = self.sd_frames[0].shape[1] 
      self.fh = self.sd_frames[0].shape[0] 
      self.hdm_x = 1920 / self.fw
      self.hdm_y = 1080 / self.fh
      self.hdm_x_720 = 1280 / self.fw
      self.hdm_y_720 = 720/ self.fh

      self.first_frame = self.sd_frames[0].copy()
      self.first_frame = cv2.cvtColor(self.first_frame, cv2.COLOR_BGR2GRAY)
      self.third_frame = cv2.cvtColor(self.sd_frames[3].copy(), cv2.COLOR_BGR2GRAY)
      self.sd_subframes = []
      self.max_vals = []
      self.avg_vals = []
      self.cnts = []
      frame_cnts = []
      detect = Detector()
      work_stack = self.sd_stacked_image.copy()

      # scan SD file first and gather the frame cnts 
      last_sub = None
      extra_thresh = 0

      self.sub_vals_sum = []
      self.sub_vals_avg = []
      self.sub_vals_max = []
      self.max_factor = []
      i = 0
      first_frame = None

      # first do a vals scan. from this determine a few things
      # 1) do we have a hit in here, if so confirm that (get the easiest meteors done first!)
      #    if we don't have a vals hit, then there is probably nothing here?
      # 2) are we dealing with a fireball or very bright event (VBE) if so we will need special processing
      #    check the max vals & event duration to figure this out

      self.vals_data, self.vals_event = self.vals_scan(self.sd_frames)
      for data in self.vals_data:
         (event, cm, mvf, fc, sum_val, avg_val, max_val, mx, my) = data
         self.sub_vals_sum.append(sum_val)
         self.sub_vals_max.append(max_val)
         self.sub_vals_avg.append(avg_val)
         self.max_factor.append(mvf)
         print("VALS:", data)

      # If we have a vals detect, lets do a quick crop scan for confirmation. 
      # If we validate the vals detect quickly we can exit out fast right now!
      if len(self.vals_event) >= 3:
         print("VALS EVENT DETECTED!")
         self.vals_detect = 1
         self.vals_event_status, vals_obj = self.vals_detect_crop_confirm()
      else:
         self.vals_event_status = 0
         print("VALS EVENT NOT DETECTED?!?!?")
         for data in self.vals_data:
            print("VALS DATA:", data)
         xxx = ("waiting")

      if self.vals_event_status == 1:
         # WE ARE DONE! THE DETECT IS CONFIRM. THE CROP SCAN IS DONE AND 
         # WE HAVE THE LEADING CNT FOR EACH FRAME 
         print("SAVE THE EVENT AND EXIT WE ARE DONE!")
         self.best_meteor = vals_obj
         self.meteor_scan_info['status'] = 1
         self.meteor_scan_info['desc'] = "Meteor Detected with vals detect and vals crop confirm"

         crop_scan = {}
         crop_scan['status'] = 1 
         crop_scan['desc'] = "Vals detect Crop scan successful."

         oid = vals_obj['obj_id']
         if "sd_objects" not in self.meteor_scan_info:
            self.meteor_scan_info['sd_objects'] = {}
         self.meteor_scan_info['sd_objects'][oid] = vals_obj
         self.meteor_scan_info['crop_scan'] = crop_scan
         self.save_meteor_files()
         return()
         #exit()
 
      # SKIP / DISABLE FOR NOW
      return()
      #self.plot_data(data_series=[self.sub_vals_sum],title="Subframe Sum Vals", labels=[], colors='r')
      #self.plot_data(data_series=[self.sub_vals_max,self.sub_vals_avg],title="Subframe Max Vals", labels=[], colors=['r', 'b'])

      max_sum = max(self.sub_vals_sum) 
      max_val = max(self.sub_vals_max) 
      init_avg_sum = np.mean(self.sub_vals_sum[0:5])
      init_max_val = np.mean(self.sub_vals_max[0:5])

      self.max_avg_sum = max_sum/init_avg_sum
      self.max_avg_val = max_val/init_max_val
      if self.max_avg_sum > 100:
         self.fireball = 1
      else:
         self.fireball = None



      # scan each frame and build a list of cnts in each frame
      work_img = self.sd_stacked_image.copy()
      print(work_img.shape)

      # make mask of bright spots (moon etc) in 1st frame
      ff = cv2.cvtColor(self.sd_frames[0], cv2.COLOR_BGR2GRAY)

      ff_mask = None
      f_thresh_val = np.mean(ff) + 10
      #+ (np.max(frame) * .25)

      if f_thresh_val < 80:
         f_thresh_val = 80 
      _, thresh2 = cv2.threshold(ff.copy(), f_thresh_val, 255, cv2.THRESH_BINARY)
      if mask2 is None :
         mask2 = cv2.dilate(thresh2.copy(), None , iterations=4)
         mask2 = cv2.cvtColor(mask2, cv2.COLOR_GRAY2BGR)
      print("THRESH VAL:", f_thresh_val)
      #cv2.imshow('ffmask', mask2)
      cv2.waitKey(30)
     
      self.first_frame = cv2.GaussianBlur(self.first_frame, (7, 7), 0)

      #display_frame.make_multi_frame(images = [])
      fc = 0
      sub = cv2.subtract(self.first_frame, self.third_frame)
      ideal_thresh = self.ideal_thresh(sub )
      thresh_val = ideal_thresh
      for frame in self.sd_frames:
         self.DF.add_image(fc,4,frame)
         if self.camera.mask_img is not None:
            if self.camera.mask_img.shape[0] != frame.shape[0]:
               self.camera_mask_img = cv2.resize(self.camera.mask_img, (frame.shape[1], frame.shape[0]))
            frame = cv2.subtract(frame, self.camera.mask_img)
            if mask2 is not None:
               frame = cv2.subtract(frame, mask2)
               #cv2.imshow('mask2', mask2)
               #cv2.waitKey(30)
               frame = cv2.subtract(frame, mask2)
         self.DF.add_image(fc,1,frame)
            #cv2.imshow('mask1', self.camera.mask_img)
            #cv2.waitKey(0)

         #sub = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)

         gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         sub = cv2.subtract(gray_frame, self.first_frame)

         if 10 <= fc <= 20 :
            sub = cv2.subtract(gray_frame, self.sd_subframes[fc-10])
         if 20 <= fc <= 30 :
            sub = cv2.subtract(gray_frame, self.sd_subframes[fc-20])
         self.sd_subframes.append(sub)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         avg_val = np.mean(sub)
         sum_val = np.sum(sub)
         self.max_vals.append(max_val)
         self.avg_vals.append(avg_val)

         if len(self.max_vals) < 10:
            self.avg_max_val = np.median(self.max_vals)
            self.avg_avg_val = np.median(self.avg_vals)

         #thresh_val = self.avg_avg_val + (max_val*.5) + extra_thresh
         print("VALS AVG, MAX, THRESH:", self.avg_avg_val, max_val, thresh_val )
         _, threshold = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)

         f_thresh_val = np.mean(sub) + (np.max(frame) * .5)

         if f_thresh_val < 30:
            f_thresh_val = 30 
         _, thresh2 = cv2.threshold(frame.copy(), f_thresh_val, 255, cv2.THRESH_BINARY)
         if mask2 is None :
            mask2 = cv2.dilate(thresh2.copy(), None , iterations=4)

         self.DF.add_image(fc,2,threshold)
         cnts,noise = self.get_contours(threshold, sub, fc, 1)

         # check for noise blasts
         if len(cnts) > 40:
            print ("NOISE FIX! 50")
            _, threshold = cv2.threshold(sub.copy(), thresh_val+50, 255, cv2.THRESH_BINARY)
            cnts,noise = self.get_contours(threshold, sub, fc, 1)
            self.DF.add_image(fc,2,threshold)
         print("   1ST SCAN CNTS (thresh,mask_thresh,fn,cnts):", thresh_val, f_thresh_val, fc, len(cnts))

         if len(cnts) > 20:
            print ("NOISE FIX! 20")
            _, threshold = cv2.threshold(sub.copy(), thresh_val+20, 255, cv2.THRESH_BINARY)
            cnts,noise = self.get_contours(threshold, sub, fc, 1)
            self.DF.add_image(fc,2,threshold)

         if len(cnts) > 8 and extra_thresh < 25:
            extra_thresh += 5
         
         show_img = sub.copy()
         if len(cnts) >= 3:
            cnts, spectra_cnts = self.filter_spectra_cnts(cnts)
         for data in cnts:
            fn, x, y, w, h, cx, cy, intensity = data
            cv2.rectangle(show_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1) 
            frame_cnts.append((fn,x,y,w,h,cx,cy,intensity))
            cv2.rectangle(work_img, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1) 
            self.DF.add_image(fn,3,work_img)

         #PHASE 1 SCAN DEBUG
         #cv2.imshow('dynamic mask', mask2)
         #cv2.imshow('meteor scan', show_img)
         #cv2.waitKey(30)
         if fc > 10:
            self.first_frame = self.sd_frames[-10]
            if len(self.first_frame.shape) > 2:
               self.first_frame = cv2.cvtColor(self.first_frame, cv2.COLOR_BGR2GRAY)

         #self.display_frame(fc)
         self.DF.render_frame(fc)
         fc += 1

      self.sd_frame_cnts = frame_cnts
      #cv2.imshow('meteor_scan', work_img)
      #cv2.waitKey(30)

      # END 1st scan of frames
      for data in frame_cnts:
         print(data)
      if self.fireball == 1:
         self.cleanup_fireball_data(frame_cnts)
         obj = self.best_meteor
         oid = 1
         objects = {}
         objects[oid] = obj
      else:
         # convert frame data into objects
         objects = {}
         for fn,x,y,w,h,cx,cy,intensity in self.sd_frame_cnts:
            oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 20)

      pos_meteors = []

      clean_objects = {}
      noise_objects = {}
      deletes = []

      print("TOTAL OBJECTS:", len(objects))

      for oid in objects:
         if objects[oid] is not None:
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
         else:
            print("OBJ IS NONE!", oid)
            cv2.imshow('pepe', self.sd_stacked_image)
            cv2.waitKey(300)
            deletes.append(oid)

      for oid in deletes:
         del objects[oid]

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
         self.meteor_scan_info['status'] = 0
         self.meteor_scan_info['desc'] = ['no meteors detected']
         self.meteor_scan_info['sd_objects'] = objects

      if len(pos_meteors) == 1:
         self.pos_meteors = pos_meteors
         self.sd_objects = objects
         self.meteor_detected = 1
         self.best_meteor = pos_meteors[0]
         if self.best_meteor['report']['class'] == "meteor":
            self.meteor_scan_info['status'] = 1 
            self.meteor_scan_info['desc'] = ['meteor detected']
            self.meteor_scan_info['sd_objects'] = objects
         elif self.best_meteor['report']['class'] == "unknown":
            self.meteor_scan_info['status'] = 2 
            self.meteor_scan_info['desc'] = ['unknown obj detected']
            self.meteor_scan_info['sd_objects'] = objects
         else:
            self.meteor_scan_info['status'] = 2 
            self.meteor_scan_info['desc'] = ['unknown obj detected']
            self.meteor_scan_info['sd_objects'] = objects

      if len(pos_meteors) == 2:
         # most likely case is these are the same overlapping check. 
         self.meteor_scan_info['status'] = 3 
         self.meteor_scan_info['desc'] = ['multi-meteors detected']
         self.meteor_scan_info['sd_objects'] = objects
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
         self.meteor_scan_info['status'] = 1
         self.meteor_scan_info['desc'] = ['meteor detected']
         self.meteor_scan_info['sd_objects'] = objects
         self.best_meteor = pos_meteors[0]

      if len(pos_meteors) > 2:
         # Lots of possible meteors here. Let's see how many fit inside the same cont
         self.meteor_scan_info['status'] = 3 
         self.meteor_scan_info['desc'] = ['multi-meteors detected']
         work_stack = self.sd_stacked_image.copy()
         bsize = 0
         for pos in pos_meteors:
            size = len(pos['ofns']) 
            if size > bsize:
               dom_obj = pos
               bsize = size
         print("DOM OBJ : ", dom_obj['obj_id'])
         children = []
         other_objs = []
         spectra = []
         cv2.putText(work_stack, str(dom_obj['obj_id']) + " " + str(dom_obj['report']['class']),  (dom_obj['oxs'][0], dom_obj['oys'][0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         dx1 = min(dom_obj['oxs']) - 20
         dx2 = max(dom_obj['oxs']) - 20
         dy1 = min(dom_obj['oys']) + 20
         dy2 = max(dom_obj['oys']) + 20
         cx1 = np.mean(dom_obj['oxs'])
         cy1 = np.mean(dom_obj['oys'])
         for pos in pos_meteors:
            if pos['obj_id'] != dom_obj['obj_id']:
               center_x = np.mean(pos['oxs'])
               center_y = np.mean(pos['oys'])
               min_dist = self.min_obj_dist(dom_obj, pos)
               print("MIN DIST:", min_dist)
               if (dx1 <= center_x <= dx2 and dy1 <= center_y <= dy2) or min_dist < 25:
                  children.append(pos['obj_id'])
               elif cy1 - 20 <= center_y <= cy1 + 20:
                  spectra.append(pos['obj_id'])
               else:
                  other_objs.append(pos['obj_id'])
         print("CHILDREN:", children)
         print("NON-CHILDREN:", other_objs)
         print("SPECTRA :", spectra)



         for oid in children:
            obj = objects[oid]
            cv2.putText(work_stack, str(obj['obj_id']) + " " + str(obj['report']['class']),  (obj['oxs'][0], obj['oys'][0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            cv2.rectangle(work_stack, (int(min(obj['oxs'])), int(min(obj['oys']))), (int(max(obj['oxs'])) , int(max(obj['oys'])) ), (0, 0, 255), 1) 
            print("DOM FN:", dom_obj['ofns'])
            print("CHILD FN:", obj['ofns'])

         for oid in other_objs:
            obj = objects[oid]
            cv2.putText(work_stack, str(obj['obj_id']) + " " + str(obj['report']['class']),  (obj['oxs'][0], obj['oys'][0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         for oid in spectra:
            obj = objects[oid]
            cv2.putText(work_stack, str(obj['obj_id']) + " spectra" ,  (obj['oxs'][0], obj['oys'][0]), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)

         # MERGE DOM & CHILDREN INTO 1 OBJ. # still have merge fn bugs too!
         self.best_meteor = dom_obj
         self.pos_meteors = [dom_obj]
         doid = dom_obj['obj_id']
         objects[doid]['report']['class'] = "meteor"

         self.meteor_scan_info['status'] = 1
         self.meteor_scan_info['desc'] = ['meteor detected']
         self.meteor_scan_info['sd_objects'] = objects
         self.sd_objects = objects
         cv2.rectangle(work_stack, (int(dx1), int(dy1)), (int(dx2) , int(dy2) ), (0, 0, 255), 1) 
         #cv2.imshow('pepe', work_stack)
         #cv2.waitKey(0)

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


   def get_hd_crop_area_169(self, SD_XS,SD_YS):
      vw = 1920
      vh = 1080
      HD_XS = []
      HD_YS = []
      print("SDXS", SD_XS,SD_YS)
      for i in range(0,len(SD_XS)):
         hd_x = SD_XS[i] * self.hdm_x
         hd_y = SD_YS[i] * self.hdm_y
         HD_XS.append(hd_x)
         HD_YS.append(hd_y)

      new_w, new_h = best_crop_size(HD_XS, HD_YS, vw,vh)
      cx = np.mean(HD_XS)
      cy = np.mean(HD_YS)
      X1 = int(cx - (new_w/2))
      Y1 = int(cy - (new_h/2))
      X2 = X1 + new_w
      Y2 = Y1 + new_h
      if X1 < 0:
         X1 = 0
         X2 = X1 + new_w
      if Y1 < 0:
         Y1 = 0
         Y2 = Y1 + new_h
      if X2 > vw:
         X1 = vw - (new_w + 1)
         X2 = vw - 1 
      if Y2 > vh:
         Y1 = vh - (new_h + 1)
         Y2 = vh - 1 
      return(X1,Y1,X2,Y2)

   def best_fit_slope_and_intercept(self,xs,ys):
       xs = np.array(xs, dtype=np.float64)
       ys = np.array(ys, dtype=np.float64)
       if len(xs) < 3:
          return(0,0)
       if ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)) == 0:
          m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) / 1)

       else:
          m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
            ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

       b = np.mean(ys) - m*np.mean(xs)
       if math.isnan(m) is True:
          m = 1
          b = 1

       return m, b

  
   def merge_cnts(self, cnts):
      avg_cx = int(np.mean([row[5] for row in cnts]))
      avg_cy = int(np.mean([row[6] for row in cnts]))
      avg_w = np.mean([row[3] for row in cnts])
      avg_h = np.mean([row[4] for row in cnts])
      max_i = np.max([row[7] for row in cnts])
      fn = cnts[0][0]
      x = int(avg_cx - (avg_w/2))
      y = int(avg_cy - (avg_h/2))
      new_cnt = [fn,x,y,avg_w,avg_h,avg_cx,avg_cy,max_i]
      return(new_cnt)

   def cleanup_fireball_data(self, frame_cnts):
      # review 1st scan fireball data and try to eliminate noise from spectra, fragmentation etc.
      fd = {}
      objects = {}
      for data in frame_cnts:
         (fn,x,y,w,h,cx,cy,intensity) = data
         if fn not in fd:
            fd[fn] = {} 
            fd[fn]['cnts'] = [] 
         fd[fn]['cnts'].append((fn,x,y,w,h,cx,cy,intensity))
         oid, objects = Detector.find_objects(fn,x,y,w,h,cx,cy,intensity,objects, 20)
      max_len = 0

      # find the dominant obj from 1st scan data
      for obj in objects:
         if len(objects[obj]['ofns']) > max_len :
            max_len = len(objects[obj]['ofns']) 
            dom_oid = objects[obj]['obj_id']

      # make channel 
      work_stack = self.sd_stacked_image.copy()
      dom_obj = objects[dom_oid]
      slope,intercept = self.best_fit_slope_and_intercept(dom_obj['oxs'], dom_obj['oys'])
      reg_x = dom_obj['oxs'].copy()
      reg_x.append(self.fw)
      print("SLOPE:", slope, intercept) 
      line_regr = [slope * xi + intercept for xi in reg_x]

      min_lin_x = min(reg_x)
      max_lin_x = max(reg_x)
      min_lin_y = min(line_regr)
      max_lin_y = max(line_regr)
      channel_img = np.zeros((self.fh,self.fw),dtype=np.uint8)
      cv2.line(channel_img, (int(min_lin_x),int(min_lin_y)), (int(max_lin_x),int(max_lin_y)), (255,255,255), 21)
      channel_img = self.invert_image(channel_img)

      fn = 0
      first_frame = cv2.cvtColor(self.sd_frames[0] ,cv2.COLOR_BGR2GRAY)
      
      # rescan with channel mask applied
      obj = self.new_object() 
      self.frame_cnts = []
      for frame in self.sd_frames:
         bw_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         cframe = cv2.subtract(bw_frame, channel_img)
         cframe = cv2.subtract(cframe, first_frame)
         max_px = np.max(cframe)
         avg_px = np.mean(cframe)

         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(cframe)
         cv2.circle(work_stack,(mx,my), 2, (255,0,0), 1)

         thresh_val = max_px - 2 
         if thresh_val < 50:
            thresh_val = 50
         _, threshold = cv2.threshold(cframe.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnts,noise = self.get_contours(threshold, cframe, fn, 1,thresh_val)
         if len(cnts) == 0:
            thresh_val = max_px - 10 
            if thresh_val < 50:
               thresh_val = 50
            _, threshold = cv2.threshold(cframe.copy(), thresh_val, 255, cv2.THRESH_BINARY)
            cnts,noise = self.get_contours(threshold, cframe, fn, 1,thresh_val)
         if len(cnts) == 0:
            thresh_val = max_px - 20 
            if thresh_val < 50:
               thresh_val = 50
            _, threshold = cv2.threshold(cframe.copy(), thresh_val, 255, cv2.THRESH_BINARY)
            cnts,noise = self.get_contours(threshold, cframe, fn, 1,thresh_val)
         if len(cnts) == 0:
            thresh_val = max_px - 30 
            if thresh_val < 50:
               thresh_val = 50
            _, threshold = cv2.threshold(cframe.copy(), thresh_val, 255, cv2.THRESH_BINARY)
            cnts,noise = self.get_contours(threshold, cframe, fn, 1,thresh_val)




         threshold = cv2.cvtColor(threshold, cv2.COLOR_GRAY2BGR)
         for cnt in cnts:
            fn, x, y, w, h, cx, cy, intensity = cnt
            obj = self.update_object(obj, cnt)
            self.frame_cnts.append(cnt)

         #cv2.imshow('pepe', threshold)
         #cv2.waitKey(30)
         fn += 1

      self.frame_data = self.fill_empty_frames()
     
      self.remove_bad_frame_data()

      #self.plot_xy_data(xs=obj['ccxs'],ys=obj['ccys'],title="CMASK SCAN POINTS", labels=[], colors=['g', 'b'], invert_y=1)

      #self.estimate_frame_data()

      self.sd_frame_cnts = []
      for fn in self.frame_data:
         if len(self.frame_data[fn]['cnts']) > 0:
            cnt = self.frame_data[fn]['cnts'][0]
            self.sd_frame_cnts.append(cnt)


      obj = self.frame_data_to_object()
      if len(obj['ofns']) > 0:
         return()
      if len(obj['ofns']) > 0:
         status, report = Detector.analyze_object(obj)
         obj['report'] = report
         if obj['report']['class'] == "meteor":
            self.meteor_scan_info['status'] = 1
            self.meteor_scan_info['status_desc'] = "meteor found."
         if obj['report']['class'] == "unknown":
            self.meteor_scan_info['status'] = 2 
            self.meteor_scan_info['status_desc'] = "unknown object found."
      else:
         report = None
         self.meteor_scan_info['status'] = -1
         self.meteor_scan_info['status_desc'] = "No meteor objects found."
         return()

      self.best_meteor = obj


      print("MY FINAL FIREBALL OBJECT:", obj) 
      print("REPORT:", report)
      XS = obj['ccxs']
      YS = obj['ccys']


      for key in obj:
         if key != "report":
            print(key, obj[key])
         else:
            for xx in obj['report']:
               print(xx, obj['report'][xx])


      work_stack = self.sd_stacked_image.copy()
      for i in range(0, len(obj['ofns'])):
         x1 = obj['oxs'][i]
         y1 = obj['oys'][i]
         x2 = obj['ows'][i] + x1
         y2 = obj['ohs'][i] + y1
         cx = obj['ccxs'][i]
         cy = obj['ccys'][i]
      
         cv2.circle(work_stack,(cx,cy), 2, (0,0,255), 1)
         #cv2.rectangle(work_stack, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 0, 255), 1) 


      #import matplotlib
      #matplotlib.use('TkAgg')
      #from matplotlib import pyplot as plt
      #plt.scatter(dom_obj['oxs'], dom_obj['oys'])
      #plt.plot(reg_x, line_regr, c='red')
      #plt.show()

      cv2.imshow('pepe', work_stack)
      cv2.waitKey(300)


   def remove_bad_frame_data(self):
      fns = self.frame_data.keys()

      used = {}
      bad_fns = []
      good = 0
      # start at the end if we hit any bad conditions consider the frame bad.
      fn_keys = sorted(fns, reverse=False)
      if len(fn_keys) == 0:
         return()
      first_fn = fn_keys[0]
      first_x = self.frame_data[first_fn]['cnts'][0][1]
      first_y = self.frame_data[first_fn]['cnts'][0][2]
      last_x = None

      for fn in sorted(fns, reverse=True):
         # merge cnts if there is more than 1
         if len(self.frame_data[fn]['cnts']) > 1:
            print("MERGE CNT!")
            mcnt = self.merge_cnts(self.frame_data[fn]['cnts'])
            self.frame_data[fn]['cnts'] = [mcnt]

      for fn in sorted(fns, reverse=True):
         # once we hit 3 good frames end this loop
         if fn not in self.frame_data or fn-1 not in self.frame_data:

            continue
            #self.frame_data[fn]['bad_items'] = []
            #self.frame_data[fn]['bad_items'].append("missing fd" + str(prev_dist_from_start) + " " + str(dist_from_start) )
            #self.frame_data[fn]['status'] = "BAD"

            continue
         if good >= 3:
            self.frame_data[fn]['bad_items'].append("missing fd in prev" + str(prev_dist_from_start) + " " + str(dist_from_start) )
            self.frame_data[fn]['status'] = "BAD"
            continue
         print("DEBUG:", fn, self.frame_data[fn])
         if "cnts" not in self.frame_data[fn]:
            print("NO CNTS!")
            self.frame_data[fn]['cnts'] = [] 

         # tag ending frames with dupe x,y
         if len(self.frame_data[fn]['cnts']) > 0:
            cnt = self.frame_data[fn]['cnts'][0]
            fn, x, y, w, h, cx, cy, intensity = cnt
            key = str(cx) + "." + str(cy)
            if key in used:
               self.frame_data[fn]['status'] = "BAD"
               if "bad_items" not in self.frame_data[fn]:
                  self.frame_data[fn]['bad_items'] = []
               self.frame_data[fn]['bad_items'].append('DUPE XY')
               self.frame_data[fn]['status'] = "BAD"
            used[key] = 1
         # tag ending frames bad dist or big int drop
         if fn not in self.frame_data or fn-1 not in self.frame_data[fn]:
            continue
         if len(self.frame_data[fn]['cnts']) > 0 and len(self.frame_data[fn-1]['cnts']) > 0:
            cnt = self.frame_data[fn]['cnts'][0]
            xfn, x, y, w, h, cx, cy, intensity = cnt
            prev_cnt = self.frame_data[fn-1]['cnts'][0]
            prev_fn, px, py, pw, ph, pcx, pcy, p_intensity = prev_cnt

            dist_to_prev = calc_dist((cx,cy),(pcx,pcy))
            int_diff_to_prev = p_intensity - intensity
            print("CNT:", fn, cnt)
            print("PCNT:", fn -1, prev_cnt)
            print("INT", fn, p_intensity, intensity)
            prev_dist_from_start = calc_dist((first_x,first_y), (pcx,pcy))
            dist_from_start = calc_dist((first_x,first_y), (cx,cy))
            if dist_from_start < prev_dist_from_start :
               if "bad_items" not in self.frame_data[fn]:
                  self.frame_data[fn]['bad_items'] = []
               self.frame_data[fn]['bad_items'].append("dist from start shorter than prev " + str(prev_dist_from_start) + " " + str(dist_from_start) )
               self.frame_data[fn]['status'] = "BAD"
            if intensity < 100 and int_diff_to_prev > 100:
               print("BAD PREV INT", fn, dist_to_prev, int_diff_to_prev)
               if "bad_items" not in self.frame_data[fn]:
                  self.frame_data[fn]['bad_items'] = []
                  self.frame_data[fn]['bad_items'].append("big intensity drop" + str(int_diff_to_prev) )
                  self.frame_data[fn]['status'] = "BAD"
         else:
            if "bad_items" not in self.frame_data[fn]:
               self.frame_data[fn]['bad_items'] = []
               self.frame_data[fn]['bad_items'].append("no cnt")
               self.frame_data[fn]['status'] = "BAD"

         if "status" not in self.frame_data[fn] and len(self.frame_data[fn]['cnts']) > 0:
            good += 1

      del_fns = {}
      for fn in sorted(fns, reverse=True):
         if fn-1 in self.frame_data:
            if "status" in self.frame_data[fn-1]:
               if self.frame_data[fn-1]['status'] == "BAD":
                  del_fns[fn] = 1
         if "status" in self.frame_data[fn]:
            if self.frame_data[fn]['status'] == "BAD":
               del_fns[fn] = 1
      for fn in del_fns:
         print("DEL FRAME:", fn)
         del(self.frame_data[fn])

      #for fn in sorted(fns, reverse=True):
      #   print("FINAL FRAME DATA:", fn, self.frame_data[fn])


   def estimate_frame_data(self):
      frame_data = {}
      XS = []
      YS = []
      XDS = []
      YDS = []
      fc = 0
      last_x = None
      for fn in sorted(self.frame_data.keys()):
         print("LOOP START FRAME:", fn)
         if len(XDS) < 10:
            xdist = np.median(XDS)
            ydist = np.median(YDS)
         else:
            xdist = np.median(XDS[fc-10:fc-1])
            ydist = np.median(YDS[fc-10:fc-1])

         if len(self.frame_data[fn]['cnts']) > 0:
            cnt = self.frame_data[fn]['cnts'][0]
            tfn, x, y, w, h, cx, cy, intensity = cnt
            XS.append(cx)
            YS.append(cy)

            if dist_to_prev > 10:
               print("BAD PREV DIST", fn, dist_to_prev, int_diff_to_prev)
               if "bad_items" not in self.frame_data[fn]:
                  self.frame_data[fn]['bad_items'] = []
               self.frame_data[fn]['bad_items'].append("dist to prev to large " + str(dist_to_prev) )
               self.frame_data[fn]['status'] = "BAD"
            if intensity < 100 and int_diff_to_prev > 100:
               print("BAD PREV INT", fn, dist_to_prev, int_diff_to_prev)
               if "bad_items" not in self.frame_data[fn]:
                  self.frame_data[fn]['bad_items'] = []
                  self.frame_data[fn]['bad_items'].append("big intensity drop" + str(int_diff_to_prev) )
                  self.frame_data[fn]['status'] = "BAD"
         else:
            if "bad_items" not in self.frame_data[fn]:
               self.frame_data[fn]['bad_items'] = []
               self.frame_data[fn]['bad_items'].append("no cnt")
               self.frame_data[fn]['status'] = "BAD"

         if "status" not in self.frame_data[fn] and len(self.frame_data[fn]['cnts']) > 0:
            good += 1

      for fn in sorted(fns, reverse=True):
         print(fn, self.frame_data[fn])

   def estimate_frame_data(self):
      frame_data = {}
      XS = []
      YS = []
      XDS = []
      YDS = []
      fc = 0
      last_x = None
      for fn in sorted(self.frame_data.keys()):
         print("LOOP START FRAME:", fn)
         if len(XDS) < 10:
            xdist = np.median(XDS)
            ydist = np.median(YDS)
         else:
            xdist = np.median(XDS[fc-10:fc-1])
            ydist = np.median(YDS[fc-10:fc-1])

         if len(self.frame_data[fn]['cnts']) > 0:
            cnt = self.frame_data[fn]['cnts'][0]
            tfn, x, y, w, h, cx, cy, intensity = cnt
            XS.append(cx)
            YS.append(cy)


            if last_x is not None:
               XDS.append((cx-last_x))
               YDS.append((cy-last_y))
            else:
               XDS.append(0)
               YDS.append(0)

            if last_x is not None:
               fn_diff = fn - last_fn
               est_x = last_x + (xdist*fn_diff)
               est_y = last_y + (ydist*fn_diff)

               print("   FRAME ", fn, "IS GOOD FN DIFF FROM LAST FRAME IS:", fn_diff, "THIS XY IS:", cx,cy,"LAST DIFF:", xdist,ydist, "ESTXY:", est_x,est_y)
            last_x = cx
            last_y = cy
         else:
            if last_x is not None:
               fn_diff = fn - last_fn
               est_x = last_x + (xdist*fn_diff)
               est_y = last_y + (ydist*fn_diff)
               print("   FRAME ", fn, "IS MISSING FN DIFF FROM LAST FRAME IS:", fn_diff, "LAST XY IS:", last_x,last_y,"LAST DIFF:", xdist,ydist, "ESTXY:", est_x,est_y)
            XS.append(est_x)
            YS.append(est_y)
         fc += 1
         last_fn = fn

      EXS = []
      EYS = []
      print("TOTAL XS:", len(XS))
      print("TOTAL YS:", len(YS))
      print("TOTAL FD:", len(self.frame_data.keys()))

      i = 0
      for fn in self.frame_data:
         print(fn, self.frame_data[fn])
      print(self.frame_data)
      for fn in sorted(self.frame_data.keys()):
         if fn not in self.frame_data:
            print(fn, "NOT IN FRAME DATA")
            continue
         elif "cnts" not in self.frame_data[fn]:
            continue
         if i > 5:
            if self.frame_data[fn]['cnts'] == 0:
               est_x, est_y, XS,YS = self.estimate_point(XS,YS,i)
               est_x = int(est_x)
               est_y = int(est_y)
               EXS.append(est_x)
               EYS.append(est_y)
            else: 
               est_x, est_y, XSx,YSx = self.estimate_point(XS,YS,i)
               est_x = int(est_x)
               est_y = int(est_y)
               EXS.append(est_x)
               EYS.append(est_y)
         else:
            if len(self.frame_data[fn]['cnts']) > 0:
               cnt = self.frame_data[fn]['cnts'][0]
               fn, x, y, w, h, cx, cy, intensity = cnt
               #est_x, est_y, XSx,YSx = self.estimate_point(XS,YS,i)
               est_x = cx
               est_y = cy
               EXS.append(cx)
               EYS.append(cy)
         print(fn, self.frame_data[fn])
         self.frame_data[fn]['est_x'] = est_x
         self.frame_data[fn]['est_y'] = est_y
         if len(self.frame_data[fn]['cnts']) > 0:

            cnt = self.frame_data[fn]['cnts'][0]
            fn, x, y, w, h, cx, cy, intensity = cnt
         i += 1
         if fn in self.frame_data:
            print("   EST FD:", fn, self.frame_data[fn])
      #self.plot_xy_data(xs=EXS,ys=EYS,title="Estimated Points", labels=[], colors=['g', 'b'], invert_y=1, show=1)


   def fill_empty_frames(self):
      #fn, x, y, w, h, cx, cy, intensity = cnt
      frame_data = {}
      fns = [row[0] for row in self.frame_cnts]
      if len(fns) < 1:
         return(frame_data)
      print("MINMAX:",min(fns),max(fns))
      for i in range(min(fns), max(fns)+1):
         if i not in frame_data:
            frame_data[i] = {}
            frame_data[i]['cnts'] = []
      for cnt in self.frame_cnts:
         fn, x, y, w, h, cx, cy, intensity = cnt

         frame_data[fn]['cnts'].append(cnt)

      for fn in frame_data:
         if len(frame_data[fn]['cnts']) > 1:
            avg_cx = int(np.mean([row[5] for row in frame_data[fn]['cnts']]))
            avg_cy = int(np.mean([row[6] for row in frame_data[fn]['cnts']]))
            avg_w = np.mean([row[3] for row in frame_data[fn]['cnts']])
            avg_h = np.mean([row[4] for row in frame_data[fn]['cnts']])
            max_i = np.max([row[7] for row in frame_data[fn]['cnts']])
            x = int(avg_cx - (avg_w/2))
            y = int(avg_cy - (avg_h/2))
            new_cnt = [fn,int(x),int(y),int(avg_w),int(avg_h),int(avg_cx),int(avg_cy),max_i]
            frame_data[fn]['cnts'] = [new_cnt]
            print("FILLED:", fn, frame_data[fn] )
         else:
            print("FINE:", fn, frame_data[fn] )

      XS = []
      YS = []
      for fn in frame_data:
         print(fn, frame_data[fn])
         if "merge_cnts" in frame_data[fn]:
            cnt = frame_data[fn]['merge_cnts']
         elif len(frame_data[fn]['cnts']) > 0:
            cnt = frame_data[fn]['cnts'][0]
         else:
            cnt = None
         if cnt is not None:
            print("CNT:", cnt)
            (fn,x,y,avg_w,avg_h,cx,cy,max_i) = cnt 
            XS.append(cx)
            YS.append(cy)

      slope,intercept = self.best_fit_slope_and_intercept(XS, YS)
      print("SLOP:", len(XS), len(YS))
      
      #self.plot_xy_data(xs=XS,ys=YS,title="", labels=[], colors=['g', 'b'], invert_y=1, show=0)
      cmask = self.make_channel(XS,YS)

      # reaquire points using dynamic cmask
      fc = 0
      first_frame = self.sd_frames[0]
      first_frame = cv2.cvtColor(first_frame,cv2.COLOR_BGR2GRAY)
      XS = []
      YS = []
      for frame in self.sd_frames:
         gray_frame = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
         if fn in frame_data:
            if "cnts" in frame_data[fn]:
               if len(frame_data[fn]['cnts']) > 0:
                  if fc > 30:
                     cmask = self.make_channel(XS[fc-30:fc-10],YS[fc-30:fc-10])
 
         print(gray_frame.shape)
         print(cmask.shape)
         if len(cmask.shape) == 3:
            cmask = cv2.cvtColor(cmask,cv2.COLOR_BGR2GRAY)
         gray_frame = cv2.subtract(gray_frame, cmask)
         gray_frame = cv2.subtract(gray_frame, first_frame)
         avg_val = np.mean(gray_frame) 
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_frame)
         if fn not in frame_data:
            frame_data[fn] = {}  
         frame_data[fn]['mx'] = mx
         frame_data[fn]['my'] = my
         frame_data[fn]['mv'] = max_val
         frame_data[fn]['av'] = np.mean(gray_frame)


         thresh_val = np.max(gray_frame) - 10
         if thresh_val < 20:
            thresh_val =20 
         _, threshold = cv2.threshold(gray_frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         cnts,noise = self.get_contours(threshold, gray_frame, fc, 1,thresh_val)

         if len(cnts) == 0:
            thresh_val = np.max(gray_frame) - 20
            _, threshold = cv2.threshold(gray_frame.copy(), thresh_val, 255, cv2.THRESH_BINARY)
            cnts,noise = self.get_contours(threshold, gray_frame, fc, 1,thresh_val)

         if fn not in frame_data:
            frame_data[fn] = {}
            frame_data[fn]['cnts'] = []
         frame_data[fn]['cnts'] = cnts
         for cnt in cnts:
            fn, x, y, w, h, cx, cy, intensity = cnt
            XS.append(cx)
            YS.append(cy)

         #cv2.imshow('pepe', threshold)
         #cv2.waitKey(30)
         fc += 1
      #self.plot_xy_data(xs=XS,ys=YS,title="", labels=[], colors=['g', 'b'], invert_y=1)
      return(frame_data)

   def estimate_point(self,XS,YS,pi):
      xds = []
      yds = []
      next_10_x = None

      # first make anchor points.
      tf = len(XS)
      an_seg = int(tf/5)
      an_sx = np.mean(XS[0:an_seg])
      an_sy = np.mean(YS[0:an_seg])
      an_sfn = int(an_seg)/2
      an_efn = tf - int(an_seg)/2
      an_mfn = tf / 2

      an_mx = np.mean(XS)
      an_my = np.mean(YS)

      an_ex = np.mean(XS[-1*an_seg:-1])
      an_ey = np.mean(YS[-1*an_seg:-1])

      an_xs = [an_sx,an_mx,an_ex]
      an_ys = [an_sy,an_my,an_ey]

      ans_fn_diff = pi - an_sfn
      ane_fn_diff = pi - an_efn
      anm_fn_diff = pi - an_mfn

      print("AN FN DIF:", ans_fn_diff, ane_fn_diff, anm_fn_diff)
      print("ANXS:", an_xs)
      print("ANYS:", an_ys)


      for i in range(0, len(XS)):
         if i == 0:
            xds.append(0)
         else:
            xds.append(XS[i]-XS[i-1])
            yds.append(YS[i]-YS[i-1])

      if pi > 6 and pi + 6 < len(XS):
         print("PI:", XS[pi-5:pi-1])
         last_10_x = np.mean(XS[pi-5:pi-1])
         last_10_y = np.mean(YS[pi-5:pi-1])
         next_10_x = np.mean(XS[pi+1:pi+5])
         next_10_y = np.mean(YS[pi+1:pi+5])
         est_x = int((last_10_x + next_10_x)/2)
         est_y = int((last_10_y + next_10_y)/2)

      if pi > 10 and pi + 10 < len(XS):
         last_10_x = np.mean(XS[pi-10:pi-1])
         last_10_y = np.mean(YS[pi-10:pi-1])

      an_ex = XS[-1*an_seg:-1]
      an_ey = YS[-1*an_seg:-1]

      for i in range(0, len(XS)):
         if i == 0:
            xds.append(0)
         else:
            xds.append(XS[i]-XS[i-1])
            yds.append(YS[i]-YS[i-1])

      if pi > 6 and pi + 6 < len(XS):
         print("PI:", XS[pi-5:pi-1])
         last_10_x = np.mean(XS[pi-5:pi-1])
         last_10_y = np.mean(YS[pi-5:pi-1])
         next_10_x = np.mean(XS[pi+1:pi+5])
         next_10_y = np.mean(YS[pi+1:pi+5])
         est_x = int((last_10_x + next_10_x)/2)
         est_y = int((last_10_y + next_10_y)/2)

      if pi > 10 and pi + 10 < len(XS):
         last_10_x = np.mean(XS[pi-10:pi-1])
         last_10_y = np.mean(YS[pi-10:pi-1])
         next_10_x = np.mean(XS[pi+1:pi+10])
         next_10_y = np.mean(YS[pi+1:pi+10])
         est_x = int((last_10_x + next_10_x)/2)
         est_y = int((last_10_y + next_10_y)/2)

      if pi <= 10:
         slope,intercept = self.best_fit_slope_and_intercept(XS[0:pi], YS[0:pi])
         x_dist = np.mean(xds[0:10])
         y_dist = np.mean(yds[0:10])
         print("XDIST", 0, pi-1, xds, x_dist)
      else:
         slope,intercept = self.best_fit_slope_and_intercept(XS[pi-6:pi-1], YS[pi-6:pi-1])
         x_dist = np.median(xds[pi-10:pi-1])
         y_dist = np.median(yds[pi-10::pi-1])
      if next_10_x is None:
         print("FIGURE IT OUT:", pi-1, x_dist)
         est_x = XS[pi-1] + x_dist
         est_y = slope * est_x + intercept
         
      XS[pi] = est_x
      YS[pi] = est_y
      #print("X_DIST:", x_dist)
      print("PI:", pi, XS[pi-1], YS[pi-1], est_x,est_y  )


      return(est_x,est_y, XS,YS)

   def make_channel(self, XS,YS, fw=None, fh=None ):
      slope,intercept = self.best_fit_slope_and_intercept(XS, YS)
      channel_img = None
      if len(XS) < 2:
         channel_img = np.zeros((self.fh,self.fw),dtype=np.uint8)
         channel_img = cv2.cvtColor(channel_img,cv2.COLOR_GRAY2BGR)
         return(channel_img)

      line_regr = [slope * xi + intercept for xi in XS]

      if fw is not None:
         channel_img = np.zeros((fh,fw),dtype=np.uint8)
      else:
         channel_img = np.zeros((self.fh,self.fw),dtype=np.uint8)

      #if channel_img is not None:
      #   for i in range(0, len(XS)):
      #      print("ADD CHANNEL CIRCLE:", XS[i], YS[i])
      #      cv2.circle(channel_img,(XS[i],YS[i]), 2, (255,255,255), 1)


      min_lin_x = XS[0]
      max_lin_x = XS[-1]
      min_lin_y = line_regr[0]
      max_lin_y = line_regr[-1]

      #channel_img = np.zeros((self.fh,self.fw),dtype=np.uint8)
      print("LINE:", XS, YS)
      cv2.line(channel_img, (int(min_lin_x),int(min_lin_y)), (int(max_lin_x),int(max_lin_y)), (255,255,255), 3)
      channel_img = self.invert_image(channel_img)
      #channel_img = cv2.cvtColor(channel_img,cv2.COLOR_GRAY2BGR)
      return(channel_img)

   def frame_data_to_object(self):
      obj = self.new_object()
      for fn in self.frame_data:
         if len(self.frame_data[fn]['cnts']) > 0:
            cnt = self.frame_data[fn]['cnts'][0]
            obj = self.update_object(obj,cnt)
      return(obj)


   def new_object(self):
      obj = {}
      obj['ofns'] = []
      obj['oxs'] = []
      obj['oys'] = []
      obj['ows'] = []
      obj['ohs'] = []
      obj['ccxs'] = []
      obj['ccys'] = []
      obj['olxs'] = []
      obj['olys'] = []
      obj['oint'] = []
      return(obj)

   def update_object(self,obj,cnt):
      fn, x, y, w, h, cx, cy, intensity = cnt
      obj['ofns'].append(fn)
      obj['oxs'].append(int(x))
      obj['oys'].append(int(y))
      obj['ows'].append(int(w))
      obj['ohs'].append(int(h))
      obj['ccxs'].append(int(cx))
      obj['ccys'].append(int(cy))
      obj['oint'].append(int(intensity))
      return(obj)

   def invert_image(self, imagem):
      imagem = (255-imagem)
      return(imagem)

   def filter_spectra_cnts(self,cnts):
      CXS = []
      CYS = []
      XS = []
      YS = []
      WS = []
      HS = []

      cnts= sorted(cnts, key=lambda x: (x[3]+x[4]), reverse=True)
      biggest_cnt = cnts[0]

      for cnt in cnts:
         fn, x, y, w, h, cx, cy, intensity = cnt
         CXS.append(cx)
         CYS.append(cy)
         WS.append(w)
         HS.append(h)
         XS.append(x)
         YS.append(y)

      med_y = np.median(YS)
      spectra_cnts = []
      good_cnts = []
      c = 0
      for cnt in cnts:
         fn, x, y, w, h, cx, cy, intensity = cnt
         if c == 0:
            #this is the biggest
            biggest_cnt = cnt
            by1 = biggest_cnt[2]
            by2 = biggest_cnt[2] + biggest_cnt[4]
            good_cnts.append(cnt)
         else:
            if (med_y - 10 <= cy <= med_y + 10) or by1 <= cy <= by2:
               spectra_cnts.append(cnt)
            else:
               good_cnts.append(cnt)
         c += 1
      if len(spectra_cnts) > 2: 
         # sort sc by size and grab largest as good one
         scnts = sorted(spectra_cnts, key=lambda x: (x[3]+x[4]), reverse=True)
         good_cnts.append(scnts[0])
            
      return(good_cnts, spectra_cnts)

   def min_obj_dist(self, obj1, obj2):
      # calculate the min distance between all points in both objects
      min_dist = 99999
      for i in range(0,len(obj1['ofns'])):
         x1 = obj1['ccxs'][i]
         y1 = obj1['ccys'][i]
         for i in range(0,len(obj2['ofns'])):
            x2 = obj2['ccxs'][i]
            y2 = obj2['ccys'][i]
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
         x1 = min(met['ccxs']) - 50
         y1 = min(met['ccys']) - 50
         x2 = max(met['ccxs']) + 50
         y2 = max(met['ccys']) + 50
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
               cv2.putText(work_stack, str(obj['obj_id']) + " " + obj['report']['class'],  (x1, y2), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
            else:
               cv2.putText(work_stack, str(obj['obj_id']) + " " + obj['report']['class'],  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
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
            cv2.putText(show_image, str(obj['obj_id']) + " " + obj['report']['class'],  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         elif obj['report']['class'] == "unknown":
            cv2.rectangle(show_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 128, 128), 1) 
            cv2.putText(show_image, str(obj['obj_id']) + " " + obj['report']['class'],  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         elif obj['report']['class'] == "plane":
            cv2.rectangle(show_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (0, 128, 128), 1) 
            cv2.putText(show_image, str(obj['obj_id']) + " " + obj['report']['class'],  (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         elif obj['report']['class'] == "star":
            foo = 1
            #cv2.rectangle(show_image, (int(x1+40), int(y1+40)), (int(x2-40) , int(y2-40) ), (128, 128, 128), 1) 
         else:
            cv2.rectangle(show_image, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1) 
            cv2.putText(show_image, str(obj['obj_id']) + " " + obj['report']['class'],  (x, y), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)

      self.meteor_scan_info['objects'] = objects
      #self.sd_min_max = [0,0,0,0]
      cv2.imshow("METEOR SCAN OBJ SUMMARY", show_image)
      cv2.waitKey(200)

      self.report_objects()
      



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
         cx = obj['ccxs'][i]
         y = obj['oys'][i]
         cy = obj['ccys'][i]
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
         oid = obj['obj_id']
         x1,y1,x2,y2 = self.define_area_box(obj, self.fw, self.fh)
         for merged_obj in objects:
            moid = merged_obj['obj_id']
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
      if oid['obj_id'] < moid['obj_id']:
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
         ncxs.append(o1['ccxs'][i])
         ncys.append(o1['ccys'][i])
      new_obj = {}
      new_obj['obj_id'] = o1['obj_id']
      new_obj['ofns'] = nfns 
      new_obj['oxs'] = nxs 
      new_obj['oys'] = nys 
      new_obj['ows'] = nws 
      new_obj['ohs'] = nhs 
      new_obj['nintensity'] = nintensity
      new_obj['ncxs'] = ncxs
      new_obj['ncys'] = ncys
      return(new_obj) 


   def display_frame(self,fn):
      disp = np.zeros((1080,1920,3),dtype=np.uint8)
      if fn > len(self.sd_frames) -1:
         return 
      frame = self.sd_frames[fn].copy()
      sub_frame = self.sd_sub_frames[fn].copy()
      stack_frame = self.sd_stacked_image.copy()
     
      sub_frame = cv2.resize(sub_frame, (640,360))
      normal_frame = cv2.resize(frame, (640,360))
      stack_frame = cv2.resize(stack_frame, (640,360))
      print(normal_frame.shape)
      disp[0:360,0:640] = stack_frame 
      disp[0:360,640:1280] = normal_frame 
      disp[0:360,1280:1920] = sub_frame
      cv2.imshow('DF', disp)
      cv2.waitKey(30)
      if fn in self.frame_data:
         print("we have frame data:", fn)

   def define_area_box(self,met,fw,fh,size=50):
      x1 = min(met['oxs']) - size
      y1 = min(met['oys']) - size
      x2 = max(met['oxs']) + max(met['ows']) + size
      y2 = max(met['oys']) + max(met['ohs']) + size
      if x1 < 0:
         x1 = 0
      if y1 < 0:
         y1 = 0
      if x2 >= fw:
         x2 = fw
      if y2 >= fh:
         x2 = fh
      if x1 > x2:
         x2a = x1
         x1 = x2
         x2 = x2a
      if y1 > y2:
         y2a = y1
         y1 = y2
         y2 = y2a
      return(x1,y1,x2,y2)

   def plot_xy_data(self,xs=[],ys=[],title="", labels=[], colors=[], invert_y=0, show=0):
      import matplotlib
      matplotlib.use('TkAgg')
      from matplotlib import pyplot as plt
      fig, ax = plt.subplots()
      ax.plot(xs,ys, 'r.', alpha=0.6,
           label='')
      if invert_y == 1:
         plt.gca().invert_yaxis()
      plt.title(title)
      if show == 1:
         plt.show()


   def plot_data(self,data_series=[],title="", labels=[], colors=[], invert_y=0):
      import matplotlib
      matplotlib.use('TkAgg')
      from matplotlib import pyplot as plt

      fig, ax = plt.subplots()
      i = 0
      for data in data_series:
         ax.plot(data, 'r', alpha=0.6,
           label='')
         i+= 1
      if invert_y == 1:
         plt.gca().invert_yaxis()
      #plt.show()


   def ransac_outliers(self,XS,YS,title):
      XS = np.array(XS)
      YS = np.array(YS)
      RXS = XS.reshape(-1, 1)
      RYS = YS.reshape(-1, 1)
      #oldway
      print("R", RXS)
      #XS.reshape(-1, 1)
      #YS.reshape(-1, 1)

      self.sd_min_max = [int(min(XS))-50, int(min(YS))-50, int(max(XS))+50, int(max(YS)+50)]

      if len(XS) > 0:
         lr = linear_model.LinearRegression()
         lr.fit(RXS,RYS)

         # find good and bad
         ransac = RANSACRegressor()
         ransac.fit(RXS,RYS)
         inlier_mask = ransac.inlier_mask_
         outlier_mask = np.logical_not(inlier_mask)

         # predict
         line_X = np.arange(RXS.min(),RXS.max())[:,np.newaxis] 
         line_Y = lr.predict(line_X)
         line_y_ransac = ransac.predict(line_X)

         print("I", inlier_mask)
         print("O", outlier_mask)

      # make plot for ransac filter
      import matplotlib
      matplotlib.use('TkAgg')
      from matplotlib import pyplot as plt
      title += " points:" + str(len(RXS))

      fig = plt.figure()
      plt.title(title)
      plt.scatter(RXS[inlier_mask], RYS[inlier_mask], color='yellowgreen', marker='.',
            label='Inliers')
      plt.scatter(RXS[outlier_mask], RYS[outlier_mask], color='gold', marker='.',
            label='Outliers')
      plt.plot(line_X, line_Y, color='navy', linewidth=1, label='Linear regressor')
      plt.plot(line_X, line_y_ransac, color='cornflowerblue', linewidth=1,
         label='RANSAC regressor')
      plt.legend(loc='lower right')
      plt.xlabel("X")
      plt.ylabel("Y")
      #plt.gca().invert_yaxis()
      #plt.show()
      fig.clf()
      plt.close(fig)
      #plt.clf()
      #plt.cla()
      #plt.close()
      IN_XS = RXS[inlier_mask].tolist() 
      IN_YS = RYS[inlier_mask].tolist()
      OUT_XS = RXS[outlier_mask].tolist() 
      OUT_YS = RYS[outlier_mask].tolist()
      

      return(IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac)


   def get_contours_simple(self,image,sub):
      cnt_res = cv2.findContours(image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

      conts = []
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(sub[y:y+h,x:x+w]))
         conts.append((x,y,w,h,intensity))

      return(conts)

   def ideal_thresh(self, sub ):
      first_val_with_cnt = None
      for i in range (0,25):
         test_val = 255 - (i * 10) 
         _, threshold = cv2.threshold(sub.copy(), test_val, 255, cv2.THRESH_BINARY)
         cnts = self.get_contours_simple(threshold, sub)
         if len(cnts) > 3:
            first_val_with_cnt = test_val
         print(test_val, len(cnts))
         cv2.imshow('pepe', threshold)
         cv2.waitKey(30)
         if test_val < 0:
            test_val = 5
      return(test_val+10)

   def get_contours(self,thresh_frame,sub,fc, multi=1, thresh_val = 10,min_size=2):
      cont = []
      cnt_res = cv2.findContours(thresh_frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      noise = 0
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res

      if len(cnts) > 10:
         # there are too many cnts raise the brightness and try again!
         max_val = np.max(sub)
         thresh_val = max_val - 50
         if thresh_val < 50:
            thresh_val = 50
         _, threshold = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         print("   ******* DEBUG:", thresh_val)
         print("   ******* DEBUG:", threshold.shape)
 
         if len(threshold.shape) == 3:
            threshold = cv2.cvtColor(threshold, cv2.COLOR_BGR2GRAY)
            
         cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         noise = 0
         if len(cnt_res) == 3:
            (_, cnts, xx) = cnt_res
         elif len(cnt_res) == 2:
            (cnts, xx) = cnt_res
         # check 1 more time and increase if needed!
         if len(cnts) > 10:
            thresh_val = max_val - 50
            _, threshold = cv2.threshold(sub.copy(), thresh_val, 255, cv2.THRESH_BINARY)
            if len(threshold.shape) == 3:
               threshold = cv2.cvtColor(threshold, cv2.COLOR_BGR2GRAY)
            cnt_res = cv2.findContours(threshold.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            noise = 0

            if len(cnt_res) == 3:
               (_, cnts, xx) = cnt_res
            elif len(cnt_res) == 2:
               (cnts, xx) = cnt_res


         for cnt in cnts:
            x,y,w,h = cv2.boundingRect(cnt)
            cnt_img = sub[y:y+h,x:x+w]
            int_val = np.sum(cnt_img)
            print("   CNT INT VAL:", int_val, w,h)
            cv2.rectangle(threshold, (int(x), int(y)), (int(x+w) , int(y+h) ), (255, 255, 255), 1) 

         cv2.imshow("INSIDE CNTS FUNC", threshold)
         cv2.waitKey(30)



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
         if x != 0 and y != 0 and (w > min_size and h > min_size):
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
      if "user_mods" in self.mj:
         if "frames" in self.mj['user_mods']:
            self.ufd = self.mj['user_mods']['frames']
         else:
            self.ufd = {}
      else:
         self.ufd = {}
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
         cx = int(self.best_meteor['ccxs'][i] * self.hdm_x)
         cy = int(self.best_meteor['ccys'][i] * self.hdm_y)
         sfn = str(fn)
         if sfn in self.ufd:
            temp_x,temp_y = self.ufd[sfn]
            cx = temp_x
            cy = temp_y
         
         tx, ty, ra ,dec , az, el = XYtoRADec(cx,cy,self.sd_vid,self.cp,self.json_conf)
         self.best_meteor['ras'].append(ra)
         self.best_meteor['decs'].append(dec)
         self.best_meteor['azs'].append(az)
         self.best_meteor['els'].append(el)
      self.best_meteor['report']['ang_dist'] = abs(angularSeparation(self.best_meteor['ras'][0],self.best_meteor['decs'][0],self.best_meteor['ras'][-1],self.best_meteor['decs'][-1]))
      self.best_meteor['report']['ang_sep'] = abs(angularSeparation(self.best_meteor['ras'][0],self.best_meteor['decs'][0],self.best_meteor['ras'][-1],self.best_meteor['decs'][-1]))
      if self.event_dur > 0:
         self.best_meteor['report']['ang_vel'] = self.best_meteor['report']['ang_sep'] / self.event_dur
      else:
         self.best_meteor['report']['ang_vel'] = 0


   def save_meteor_files(self):
      if self.best_meteor is not None:  
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

      mj['meteor_scan_info'] = self.meteor_scan_info
      mjr["station_id"] = self.station_id
      mjr["device_name"] = self.cams_id
      mjr["sd_video_file"] = self.sd_vid
      mjr["sd_stack"] = self.sd_stack_file
      mjr["hd_video_file"] = self.hd_vid
      mjr["hd_stack"] = self.hd_stack_file
      if self.crop_box is None:
         self.crop_box = [0,0,0,0]
      mjr["crop_box"] = self.crop_box

      mj['cp'] = self.cp
      if self.crop_scan is not None:
         mj['crop_scan'] = self.crop_scan
      mj['meteor_scan_info'] = self.meteor_scan_info
      # convert the ccx vars to 720p from native res
      #hdm_x_720 = 1280 / self.fw
      #hdm_y_720 = 720 / self.fh
      temp_x = []
      temp_y = []
      print("720:", self.hdm_x_720, self.hdm_y_720)
      if self.best_meteor is not None:
         print("SELF:", self.best_meteor['ccxs'])
         print("SELF:", self.best_meteor['ccys'])
         for i in range(0, len(self.best_meteor['ccxs'])):
            ccx = int(self.best_meteor['oxs'][i] + (self.best_meteor['ows'][i]/2))
            ccy = int(self.best_meteor['oys'][i] + (self.best_meteor['ohs'][i]/2))
            hx = int(ccx * self.hdm_x_720)
            hy = int(ccy * self.hdm_y_720)

            print("CCXY720", self.best_meteor['ccxs'][i], self.best_meteor['ccys'][i], hx, hy)
            temp_x.append(hx)
            temp_y.append(hy)
         self.best_meteor['ccxs'] = temp_x
         self.best_meteor['ccys'] = temp_y
         print("CCXS", self.best_meteor['ccxs'])
         mj['best_meteor'] = self.best_meteor

         mjr['meteor_frame_data'] = self.meteor_frame_data
         mjr['cal_params'] = self.cp
         for iii in mj['best_meteor']['oint']:
            print("INT", iii, type(iii))
         save_json_file(self.reduce_file, mjr)
      save_json_file(self.meteor_file, mj)

   def make_meteor_frame_data(self):
      # don't forget to add the user_mods / user overrides. 
      self.meteor_frame_data = []
      # for 720 to 1080 
      #hdm_x = 1920 / 1280
      #hdm_y = 1080 / 720

      if self.best_meteor is not None:
         min_x = min(self.best_meteor['oxs'])
         max_x = max(self.best_meteor['oxs'])
         min_y = min(self.best_meteor['oys'])
         max_y = max(self.best_meteor['oys'])
         self.crop_box = [int(min_x*self.hdm_x),int(min_y*self.hdm_y),int(max_x*self.hdm_x),int(max_y*self.hdm_y)]
         for i in range(0, len(self.best_meteor['ofns'])):
            #dt = "1999-01-01 00:00:00"
            fn = self.best_meteor['ofns'][i]

            ccx = int(self.best_meteor['oxs'][i] + (self.best_meteor['ows'][i]/2))
            ccy = int(self.best_meteor['oys'][i] + (self.best_meteor['ohs'][i]/2))

            x = int(ccx * self.hdm_x)
            y = int(ccy * self.hdm_y)

            w = self.best_meteor['ows'][i]
            h = self.best_meteor['ohs'][i]
            ra = self.best_meteor['ras'][i]
            dec = self.best_meteor['decs'][i]
            az = self.best_meteor['azs'][i]
            el = self.best_meteor['els'][i]
            oint = self.best_meteor['oint'][i]
            dt = self.best_meteor['dt'][i]
            oint = self.best_meteor['oint'][i]

            sfn = str(fn)
            if self.ufd is not None:
               if sfn in self.ufd:
                  temp_x,temp_y = self.ufd[sfn]
                  x = temp_x
                  y = temp_y


            self.meteor_frame_data.append((dt, fn, x, y, w, h, oint, ra, dec, az, el))

   def make_cache_files(self):
      if self.best_meteor is None:
         return
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
            print("MFD:", fn,x,y)
            (dt, fn, x, y, w, h, oint, ra, dec, az, el) = mfd[i]
            x1,y1,x2,y2 = self.roi_area(x,y,1920,1080,50)

            roi_img = frame_1080[y1:y2,x1:x2]

            ffn = "{:04d}".format(int(fn))
            outfile = self.cache_dir_roi + self.meteor_base + "-frm" + ffn + ".jpg"
            print(outfile)
            try:
               cv2.imwrite(outfile, roi_img)
            except: 
               print("FAILED TO WRITE ROI IMG FOR ", fn, outfile)

            #cv2.imshow('pepe2', roi_img)
            #cv2.imshow('pepe', frame)
            #cv2.waitKey(0)

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

   def load_frames(self,vid_file):
      self.sd_stacked_image = None
      if cfe(vid_file) == 0:
         print("vid file not found!", vid_file)

      cap = cv2.VideoCapture(vid_file)
      self.sd_frames = []
      self.sd_sub_frames = []
      last_frame = None
      go = 1
      frame_count = 0
      while go == 1:
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return
            else:
               go = 0
         if frame is not None:
            if last_frame is not None:
               sub = cv2.subtract(frame, last_frame)
               self.sd_sub_frames.append(sub)
            else:
               sub = cv2.subtract(frame, frame)
               self.sd_sub_frames.append(sub)
            self.sd_frames.append(frame)
            if self.sd_stacked_image is None:
               self.sd_stacked_image = Image.fromarray(frame)
            else:
               frame_pil = Image.fromarray(frame)
               self.sd_stacked_image=ImageChops.lighter(self.sd_stacked_image,frame_pil)


         if frame_count > 1499:
            go = 0


         frame_count += 1
         last_frame = frame

      self.sd_stacked_image=np.asarray(self.sd_stacked_image)
      cap.release()
      return






if __name__ == "__main__":
   import sys
   if len(sys.argv) > 1:
      cmd = sys.argv[1]
   else:
      print("   COMMANDS:")
      print("   1) Scan meteors for 1 day -- will run all detections, calibrations and syncs needed to complete meteor processing.")
      cmd = input("Enter the command you want to run. ")
      if cmd == "1":
         cmd = "scan"

   if cmd == "scan":
      if len(sys.argv) >= 3:
         day = sys.argv[2]
      else:
         day = input("Enter the day you want to scan (YYYY_MM_DD): ")
      meteors = glob.glob("/mnt/ams2/meteors/" + day + "/*.json")

      #for testing
      #meteors = ['/mnt/ams2/meteors/2021_03_23/2021_03_23_04_13_00_000_010001-trim-0096.json']

      for meteor_file in meteors:

         if "reduced" not in meteor_file:
            mj = load_json_file(meteor_file)
            if "meteor_scan_info" in mj:
               print(mj['meteor_scan_info'])
               print(meteor_file)
               if "sd_objects" in mj['meteor_scan_info']:
                  print("METEOR SCAN DONE", len(mj['meteor_scan_info']['sd_objects']), " total objects")
               else:
                  print("no SD objects found in meteor scan data:", meteor_file)
                  for key in mj['meteor_scan_info']:
                     print(key)
                     for skey in mj['meteor_scan_info'][key]:
                        print(skey, mj['meteor_scan_info'][key][skey])

               if mj['meteor_scan_info'] == 0:
                  print(" STATUS: NO METEORS FOUND")
                  #continue
            if "crop_scan" in mj:
               print("CROP SCAN DONE:")
               print("    STATUS:", mj['crop_scan']['status'], mj['crop_scan']['desc'])
               #continue
            print(meteor_file)
            my_meteor = Meteor(meteor_file=meteor_file)
            print("My Meteor:", my_meteor.sd_vid)
            go = 1
            if "sd_objects" not in my_meteor.meteor_scan_info:
               go = 1

            if my_meteor.meteor_scan_info is None or go == 1:
               my_meteor.meteor_scan()
            #   my_meteor.save_meteor_files()
            #   my_meteor.make_cache_files()
            #if my_meteor.best_meteor is not None and "crop_scan" not in my_meteor.meteor_scan_info :
            #   my_meteor.meteor_scan_crop()
            #my_meteor.report_objects(my_meteor.sd_objects)
      print("FINISHED THE SCAN FOR ", day)
