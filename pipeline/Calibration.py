from Camera import Camera
import scipy.optimize
import numpy as np
import datetime
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy 
from lib.PipeUtil import load_json_file, save_json_file, cfe
import cv2

class Calibration():
   def __init__(self, cam_num=None,cams_id=None,json_conf=None,datestr=None,meteor_file=None,cal_image_file=None,time_mod=0):
      cp = None
      self.orev = 0

      if cams_id is not None:
         camera = Camera(cams_id = cams_id)
      if cam_num is not None:
         camera = Camera(cam_num = cam_num)
      if json_conf is None:
         json_conf = load_json_file("../conf/as6.json")
         self.json_conf = json_conf

      if datestr is not None:
         self.calib_dt = datetime.datetime.strptime(datestr, "%Y_%m_%d_%H_%M_%S")
      elif cal_image_file is not None:
         self.cal_image_file = cal_image_file
         cal_fn = cal_image_file.split("/")[-1]
         datestr = cal_fn[0:19]
         self.calib_dt = datetime.datetime.strptime(datestr, "%Y_%m_%d_%H_%M_%S")
         if cfe(self.cal_image_file) == 1:
            self.cal_img = cv2.imread(self.cal_image_file)
            if camera.mask_img is not None:
               camera.mask_img = cv2.resize(camera.mask_img, (self.cal_img.shape[1], self.cal_img.shape[0]))
               self.cal_img = cv2.subtract(self.cal_img, camera.mask_img)
         if cfe(cal_image_file) == 1:
            cpf = cal_image_file.replace(".png", "-calparams.json")
            if cfe(cpf) == 1:
               try:
                  cp = load_json_file(cpf)
                  cp = update_center_radec(cpf,cp,json_conf)
               except:
                  print("This calibration file doesn't exist or is corrupt.")
                  exit()
               if "orev" in cp:
                  self.orev = cp['orev']

            else:
               # try without the calparams? 
               print("Could not load file:", cpf)
               cpf = cpf.replace("-stacked", "")
               if cfe(cpf) == 1:
                  cp = load_json_file(cpf)
                  cp = update_center_radec(cpf,cp,json_conf)
                  if "orev" in cp:
                     self.orev = cp['orev']
               else:
                  print("Could not load file:", cpf)
         else:
            print("couldn't load cal image file.", cal_image_file)
      elif meteor_file is not None:
         if cfe(meteor_file) == 1:
            mj = load_json_file(meteor_file)
            cp = mj['cp']
            cp = update_center_radec(meteor_file,cp,json_conf)
         met_fn = meteor_file.split("/")[-1]
         datestr = met_fn[0:20]
         self.calib_dt = datetime.datetime.strptime(datestr, "%Y_%m_%d_%H_%M_%S")
      else:
         print("No date passed into the calib. Assume the current date is now.")
         self.calib_dt = datetime.datetime.now()


      self.station_id = json_conf['site']['ams_id']
      self.cam_num = camera.cam_num
      self.cams_id = camera.cams_id
      self.lat = json_conf['site']['device_lat']
      self.lon = json_conf['site']['device_lng']
      self.alt = json_conf['site']['device_alt']
      self.imagew = 1920
      self.imageh = 1080
      self.short_bright_stars = None

      if cp is None:
         print("CP IS NONE!")
         self.az = None
         self.el = None
         self.ra = None
         self.dec = None
         self.position_angle = None
         self.user_stars = None
         self.cat_image_stars = None
         self.pixel_scale = None
         self.total_res_px = None
         self.cal_status = 0
      else:
         self.az = cp['center_az']
         self.el = cp['center_el']
         self.ra = cp['ra_center'] 
         self.dec = cp['dec_center']
         self.position_angle = cp['position_angle']
         self.pixel_scale = cp['pixscale'] 
         self.total_res_px = cp['total_res_px']
         self.user_stars = cp['user_stars']
         self.cat_image_stars = cp['cat_image_stars']
         if "no_match_stars" in cp:
            self.no_match_stars = cp['no_match_stars']
         else:
            self.no_match_stars = []
         self.cal_status = 0
         self.F_scale = 3600 / self.pixel_scale


      self.mcp_file = "/mnt/ams2/cal/multi_poly-" + self.station_id + "-" + self.cams_id + ".info"
      self.cal_day_hist_file = "/mnt/ams2/cal/cal_day_hist.json"
      self.cal_range_file = "/mnt/ams2/cal/" + self.station_id + "_cal_range.json"

      # load lens model if it exists
      if cfe(self.mcp_file) == 1:
         self.lens_model = load_json_file(self.mcp_file)
      else:
         self.lens_model = None

      # load cal history if it exists
      if cfe(self.cal_day_hist_file) == 1:
         temp = load_json_file(self.cal_day_hist_file)
         self.cal_day_hist = []
         for data in temp:
            if data[0] == self.cams_id:
               self.cal_day_hist.append(data)
      else:
         self.cal_day_hist = None
      if cfe(self.cal_range_file) == 1:
         temp = load_json_file(self.cal_range_file)
         self.cal_range = []
         for data in temp:
            if data[0] == self.cams_id:
               self.cal_range.append(data)
      else:
         self.cal_range = None
      if self.cal_range is None and self.az is None:
         print("Warning: This camera is not entirely calibrated or the cal history has not been made.") 
         print("To fix: ./Process.py cal_man -- run options 4 & 5")

         self.default_az = None
         self.default_el = None
         self.default_position_angle = None
         self.default_pixel_scale = None
         self.default_total_res_px = None
         self.cal_status = 0
      else:
         if cp is not None:
            self.cp = cp
            self.cat_image_stars = self.find_more_stars_with_catalog()

         self.cal_range = sorted(self.cal_range, key=lambda x: x[1], reverse=True)
         self.default_az = self.cal_range[0][3]
         self.default_el = self.cal_range[0][4]
         self.default_position_angle = self.cal_range[0][5]
         self.default_pixel_scale = self.cal_range[0][6]
         self.default_total_res_px = self.cal_range[0][7]
         self.cal_status = 1
         self.default_F_scale = 3600 / self.default_pixel_scale
         


      # if the datetime was passed in (or a filename) 
      # update the RA/DEC center to match the current datetime


      self.user_stars = scan_for_stars(self.cal_img)
      if cp is None:
         self.cp = self.obj_to_json()
      else:
         self.cp = cp
         if "orev" in self.cp:
            self.orev = self.cp['orev']
      self.cp['user_stars'] = self.user_stars
      self.cp = pair_stars(self.cp, self.cal_image_file, json_conf, self.cal_img)
      cur_res = self.test_new_cal_params(self.az,self.el,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
      #xxx = input("These are the starting init values for this solve before doing the catalog solver." + str(self.total_res_px ) + " " +  str(self.orev) )

      self.short_bright_stars = get_catalog_stars(self.cp)
      self.cp['short_bright_stars'] = self.short_bright_stars

      more_stars = self.find_more_stars_with_catalog()
      self.cat_image_stars = more_stars
      cur_res = self.test_new_cal_params(self.az,self.el,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
      self.cp = self.obj_to_json()
     

      #good_stars, bad_stars = self.maga(self.cp['cat_image_stars']) 
      #self.cp['cat_image_stars'] = good_stars
      #self.cat_image_stars = self.cp['cat_image_stars'] 
      #print("Calibration initialized with res:", self.total_res_px)


   def obj_to_json(self, defaults=0):
      print("********************************************************    OBJ TO JSON CALIB IS :")
      print("********************************************************    OBJ TO JSON CALIB IS :")
      print("********************************************************    OBJ TO JSON CALIB IS :")
      print("********************************************************    OBJ TO JSON CALIB IS :")
      print("********************************************************    OBJ TO JSON CALIB IS :")
      calib = {}
      print("OBJ TO JSON CALIB IS :", calib) 
      if defaults == 0:
         calib['center_az'] = self.az
         calib['center_el'] = self.el
         calib['position_angle'] = self.position_angle
         calib['pixscale'] = self.pixel_scale
         calib['total_res_px'] = self.total_res_px
         calib['user_stars'] = self.user_stars
         calib['cat_image_stars'] = self.cat_image_stars
         calib['imagew'] = 1920
         calib['imageh'] = 1080
      else:
         calib['center_az'] = self.default_az
         calib['center_el'] = self.default_el
         calib['position_angle'] = self.default_position_angle
         calib['pixscale'] = self.default_pixel_scale
         calib['total_res_px'] = self.default_total_res_px
         calib['user_stars'] = self.default_user_stars
         calib['cat_image_stars'] = self.default_cat_image_stars
         calib['imagew'] = 1920
         calib['imageh'] = 1080

      if self.lens_model is not None:
         calib['x_poly'] = self.lens_model['x_poly']
         calib['y_poly'] = self.lens_model['y_poly']
         calib['x_poly_fwd'] = self.lens_model['x_poly_fwd']
         calib['y_poly_fwd'] = self.lens_model['y_poly_fwd']

      print("CALIB IS :", calib) 

      try:
         print("UPDATE CENTER :", calib) 
         calib = update_center_radec(self.cal_image_file,calib,self.json_conf)
         print("UPDATE CENTER :", calib) 
      except:
         print("Problems updating center ra/dec")
      if self.short_bright_stars is not None:
         calib['short_bright_stars'] = self.short_bright_stars
      if self.user_stars is not None:
         calib['user_stars'] = self.user_stars
      if self.cat_image_stars is not None:
         calib['cat_image_stars'] = self.cat_image_stars
      if self.orev is not None:
         calib['orev'] = self.orev
      print("CALIB IS :", calib) 
      return(calib)
   

   def generate_cal_history(json_conf=None):
      if json_conf is None:
         json_conf = load_json_file("../conf/as6.json")
      gen_cal_hist(json_conf)

   def draw_cal_image(self):
      new_res = self.test_new_cal_params(self.az,self.el,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
      all_stars = []
      cal_fn = self.cal_image_file.split("/")[-1]
      img = self.cal_img.copy()
      if cfe(self.cal_image_file) == 1:

         for star in self.cat_image_stars:
            name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,o_cat_x,o_cat_y,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
            star_cnt = self.find_star_blob(six,siy)
            if star_cnt is not None:
               cx,cy,cw,ch,cint = star_cnt
               star_int = cint
               all_stars.append((name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,o_cat_x,o_cat_y,new_cat_x,new_cat_y,six,siy,cat_dist,star_int)) 

         cur_res = self.test_new_cal_params(self.az,self.el,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])


         self.total_res_px = cur_res
         self.cp = self.obj_to_json()
         if self.total_res_px > 3 or self.orev == 0:
            print("RUN TWEEK?????:", calibration.total_res_px, calibration.orev)

            #more_stars = self.find_more_stars_with_catalog()
            #self.cat_image_stars = more_stars
            #self.ra = self.cp['ra_center']
            #self.dec = self.cp['dec_center']

            #more_stars = self.find_more_stars_with_catalog()
         else:
            more_stars = self.cat_image_stars

         more_stars = self.find_more_stars_with_catalog()
         for star in self.cat_image_stars:
            #(name,mag,ra,dec,new_cat_x,new_cat_y,scx,scy,cat_dist,star_int) = star
            (name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,o_cat_x,o_cat_y,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
            cv2.circle(img, (six,siy), 4, (0,255,255), 1)
            cv2.rectangle(img, (new_cat_x-2, new_cat_y-2), (new_cat_x+2, new_cat_y+2), (125,125,255), 1, cv2.LINE_AA) 
         #self.cp['cat_image_stars'] = more_stars
         #self.cat_image_stars = more_stars
         cal_fn = cal_fn.replace("-stacked.png", "")
         desc = "Res: " + str(self.total_res_px)[0:5]
         cv2.putText(img, str(desc),  (10, 1060), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         cv2.putText(img, str(cal_fn),  (10, 1040), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
         cv2.putText(img, "v" + str(self.orev),  (10, 1020), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)

         cv2.imshow('pepe', img)
         cv2.waitKey(30)

   def tweek_cal(self):
      # test the final result and see how it is?
      az_modify = 0 
      el_modify = 0
      pos_modify = 0 
      pix_modify = 0
      cur_res = self.test_new_cal_params(self.az,self.el,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])

      loop = 10

      if cur_res < 3:
         div_mod = 10
      else:
         div_mod = 10

      # tweek az to see if the res gets better
      for i in range (0,loop):
         modify = i / div_mod
         new_res = self.test_new_cal_params(self.az+modify,self.el,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
         if new_res < cur_res:
            az_modify = modify
            cur_res = new_res

         modify = modify * -1
         new_res = self.test_new_cal_params(self.az+modify,self.el,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
         if new_res < cur_res:
            az_modify = modify
            cur_res = new_res

      # tweek el to see if the res gets better
      for i in range (0,loop):
         modify = i / div_mod
         new_res = self.test_new_cal_params(self.az+az_modify,self.el+modify,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
         if new_res < cur_res:
            el_modify = modify
            cur_res = new_res

         modify = modify * -1
         new_res = self.test_new_cal_params(self.az+az_modify,self.el+modify,self.position_angle,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
         if new_res < cur_res:
            el_modify = modify
            cur_res = new_res

      # tweek pos to see if the res gets better
      for i in range (0,loop):
         modify = i / div_mod
         new_res = self.test_new_cal_params(self.az+az_modify,self.el+el_modify,self.position_angle+modify,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
         if new_res < cur_res:
            pos_modify = modify
            cur_res = new_res

         modify = modify * -1
         new_res = self.test_new_cal_params(self.az+az_modify,self.el+el_modify,self.position_angle+modify,self.pixel_scale,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
         if new_res < cur_res:
            pos_modify = modify
            cur_res = new_res

      # tweek px scale to see if the res gets better
      for i in range (0,loop):
         modify = i / div_mod
         new_res = self.test_new_cal_params(self.az+az_modify,self.el+el_modify,self.position_angle+pos_modify,self.pixel_scale+modify,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
         if new_res < cur_res:
            pix_modify = modify
            cur_res = new_res

         modify = modify * -1
         new_res = self.test_new_cal_params(self.az+az_modify,self.el+el_modify,self.position_angle+pos_modify,self.pixel_scale+modify,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
         if new_res < cur_res:
            pix_modify = modify
            cur_res = new_res


      self.az = self.az + az_modify
      self.el = self.el + el_modify
      self.position_angle = self.position_angle + pos_modify
      self.total_res_px = cur_res
      self.pixel_scale = self.pixel_scale + pix_modify 


   def find_more_stars_with_catalog(self):
      # find image stars from catalog stars in field
      self.short_bright_stars = get_catalog_stars(self.cp)
      more_stars = []
      img = self.cal_img.copy()
      for star in self.short_bright_stars:
         name,mag,ra,dec,cat_x,cat_y = star
         cat_x = int(cat_x)
         cat_y = int(cat_y)
         if mag < 5:
            if cat_x - 10 > 0 and cat_x + 10 < 1919 and cat_y - 10 > 0 and cat_y + 10 < 1079:
               cnt_img = self.cal_img[cat_y-10:cat_y+10,cat_x-10:cat_x+10]
               cnt_val = np.sum(cnt_img)
               if cnt_val > 0:
                  star_cnt = self.find_star_blob(cat_x,cat_y)
                  if star_cnt is not None:
                     scx,scy,scw,sch,scint = star_cnt
                     cv2.rectangle(img, (scx, scy), (scx+scw, scy+sch), (0,255,0), 1, cv2.LINE_AA) 
                     star_int = scint
                     cv2.rectangle(img, (cat_x-10, cat_y-10), (cat_x+10, cat_y+10), (0,255,0), 1, cv2.LINE_AA) 
                     cv2.circle(img, (scx,scy), 6, (0,255,255), 1)
                     cat_dist = calc_dist((cat_x,cat_y),(scx,scy))
                     match_dist = cat_dist
                     new_cat_x = cat_x
                     new_cat_y = cat_y
                     o_cat_x = cat_x
                     o_cat_y = cat_y
                     six = scx
                     siy = scy
                     star_int = scint
                     more_stars.append((name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,o_cat_x,o_cat_y,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))
                     #cv2.imshow("pepe", img)
                     #cv2.waitKey(30)
                  else:
                     cv2.rectangle(img, (cat_x-10, cat_y-10), (cat_x+10, cat_y+10), (0,0,255), 1, cv2.LINE_AA) 
                     cv2.circle(img, (cat_x,cat_y), 4, (0,0,255), 2)
      return(more_stars)



   def maga(self,all_stars):
      mags = []
      ints = []
      data = []
      good_stars = []
      bad_stars = []
      total_stars = len(all_stars)
      all_res = []
      for star in all_stars: 
         (name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,o_cat_x,o_cat_y,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
         #(name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star
         all_res.append(cat_dist)
         mags.append(mag)
         ints.append(star_int)

      if len(all_res) > 0: 
         med_res = np.median(all_res)
      else:
         med_res = None

      all_stars_by_mag = sorted(all_stars, key=lambda x: x[1], reverse=False)
      all_stars_by_int = sorted(all_stars, key=lambda x: x[9], reverse=True)

      mag_rank = {}
      r = 1
      for data in all_stars_by_mag:
         key = str(data[2]) + "_" + str(data[3])
         if key not in mag_rank:
            mag_rank[key] = {}
         mag_rank[key]['mag_rank'] = r
         r += 1


      r = 1
      for data in all_stars_by_int:
         key = str(data[2]) + "_" + str(data[3])
         if key not in mag_rank:
            mag_rank[key] = {}
         mag_rank[key]['int_rank'] = r
         r += 1

      for data in all_stars:
         key = str(data[2]) + "_" + str(data[3])
         (name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,o_cat_x,o_cat_y,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = data 
         #(name,mag,ra,dec,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = data
         if med_res is not None:
            if med_res < 2:
               med_res = 2
            med_diff = med_res - cat_dist
         else:
            med_diff = 0

         rank_diff = abs(mag_rank[key]['mag_rank'] - mag_rank[key]['int_rank'])
         if rank_diff > (total_stars / 2) or cat_dist > (med_res * 2):

            bad_stars.append(data)
         else:
            good_stars.append(data)


      return(good_stars, bad_stars)

   def find_star_blob(self, x,y):
      x1 = x - 10 
      x2 = x + 10 
      y1 = y - 10 
      y2 = y + 10 
      if x1 <= 0 or y1 <= 0 or x1 >= 1920 or y1 >= 1080:
         return(None)
      cnt_img = self.cal_img[y1:y2,x1:x2]
      cnt_img = cv2.cvtColor(cnt_img, cv2.COLOR_BGR2GRAY)
      img_avg = np.mean(cnt_img)
      _, cnt_thresh= cv2.threshold(cnt_img.copy(), img_avg + 20, 255, cv2.THRESH_BINARY)
      thresh_sum = np.sum(cnt_thresh)
      show_img = self.cal_img.copy()
      cnts = self.get_contours(cnt_thresh)
      desc = ""
      for cnt in cnts:
         cx,cy,cw,ch,cint = cnt 

         ccx = int(cx + (cw/2))
         ccy = int(cy + (ch/2))

         desc = str(len(cnts)) + " " + str(cint) + " " + str(cw) + " " + str(ch)
         cv2.rectangle(cnt_thresh, (cx, cy), (cx+cw, cy+ch), (125,125,125), 1, cv2.LINE_AA) 

      #cv2.circle(show_img, (x,y), 20, (255,0,0), 1)
      #cv2.putText(show_img, str(desc),  (x, y+10), cv2.FONT_HERSHEY_SIMPLEX, .3, (200, 200, 200), 1)
      #cv2.imshow('pepe', show_img)
      #cv2.imshow('STAR BLOB', cnt_thresh)
      #cv2.waitKey(0)

      if len(cnts) == 1:
         return(x-10+ccx,y-10+ccy,cw,ch,cint)
      else:
         return None

   def get_contours(self,frame):
      cont = []
      cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(frame[y:y+h,x:x+w]))
         x = int(x)
         y = int(y)
         h = int(h)
         w = int(w)
         if x != 0 and y != 0 and w > 1 and h > 1:
            cont.append((x,y,w,h,intensity))
      return(cont)

   def make_cal_defaults(json_conf=None, cams_id=None):
      default_hist = {}
      rdf = []
      if json_conf is None:
         json_conf = load_json_file("../conf/as6.json")
      for cam in json_conf['cameras']:
         cams_id = json_conf['cameras'][cam]['cams_id']
         default_hist[cams_id] = make_default_cal(json_conf, cams_id)

         for cams_id in default_hist:
            for row in default_hist[cams_id]['range_data']:
               rdf.append(row)
         save_json_file("/mnt/ams2/cal/" + amsid + "_cal_range.json", rdf)

      gen_cal_hist(json_conf)

   def test_new_cal_params(self, az,el,pos,pixscale,x_poly,y_poly,x_poly_fwd,y_poly_fwd):
      # test cal with current values
      test_img = self.cal_img.copy()
      cal_temp = {
         'center_az' : az,
         'center_el' : el,
         'position_angle' : pos,
         'pxscale' : pixscale,
         'site_lat' : self.lat,
         'site_lng' : self.lon,
         'site_alt' : self.alt,
         'user_stars' : self.user_stars,
      } 

      fov_w = self.imagew / self.F_scale
      fov_h = self.imageh / self.F_scale
      fov_radius = np.sqrt((fov_w/2)**2 + (fov_h/2)**2)

      rah,dech = AzEltoRADec(az,el,self.cal_image_file,cal_temp,self.json_conf)
      rah = str(rah).replace(":", " ")
      dech = str(dech).replace(":", " ")
      ra_center,dec_center = HMS2deg(str(rah),str(dech))
      #print("TESTING AZ/EL:", az, el)
      #print("TESTING RA/DEC:", ra_center, dec_center)
      #print("TESTING POS/PX:", pos, pixscale)

      dists = []
      for star in self.cat_image_stars:
         name,mag,ra,dec,ra,dec,match_dist,new_cat_x,new_cat_y,o_cat_x,o_cat_y,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
         new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,ra_center, dec_center, self.lens_model['x_poly'], self.lens_model['y_poly'], self.lens_model['imagew'], self.imageh, pos,self.F_scale)
         px_dist = calc_dist((new_cat_x,new_cat_y), (six,siy))
         cv2.circle(test_img, (six,siy), 4, (255,0,0), 1)
         cv2.circle(test_img, (int(new_cat_x),int(new_cat_y)), 4, (0,255,0), 1)
         dists.append(px_dist)

      if len(self.cat_image_stars) > 0:
         total_res_px = np.sum(dists) / len(self.cat_image_stars)
      else:
         total_res_px = 999

      desc = "Res: " + str(total_res_px)
      cal_fn = self.cal_image_file.split("/")[-1] 
      cal_fn = cal_fn.replace("-stacked.png", "")

      #cv2.putText(test_img, str(cal_fn),  (10, 1040), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
      #cv2.putText(test_img, "v" + str(self.orev),  (10, 1020), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)

      #cv2.putText(test_img, str(desc),  (10, 1060), cv2.FONT_HERSHEY_SIMPLEX, .5, (200, 200, 200), 1)
      #cv2.imshow("pepe", test_img)
      #cv2.waitKey(1)
      return(total_res_px)

   def save_cal_params(self):
      if "freecal" in self.cal_image_file:
         cp_file = self.cal_image_file.replace(".png", "-calparams.json")
         if cfe(cp_file) == 1:
            cp = load_json_file(cp_file)
         else:
            cp = {}
         cp['center_az'] = self.az
         cp['center_el'] = self.el
         cp['ra_center'] = self.ra
         cp['dec_center'] = self.dec
         cp['position_angle'] = self.position_angle
         cp['pixscale'] = self.pixel_scale
         cp['total_res_px'] = self.total_res_px

         cp['total_res_deg'] = (self.total_res_px * self.pixel_scale) / 60 / 60

         cp['user_stars'] = self.user_stars
         cp['cat_image_stars'] = self.cat_image_stars
         cp['short_bright_stars'] = self.cat_image_stars
         cp['x_poly'] = self.lens_model['x_poly']
         cp['y_poly'] = self.lens_model['y_poly']
         cp['x_poly_fwd'] = self.lens_model['x_poly_fwd']
         cp['y_poly_fwd'] = self.lens_model['y_poly_fwd']

         if "orev" not in cp:
            cp['orev'] = 1
         else:
            cp['orev'] = cp['orev'] + 1
         cp['last_update'] = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
         save_json_file(cp_file, cp)


   
   def minimize_cal_params(self):
      self.oaz = self.az
      self.oel = self.el
      self.oposition_angle = self.position_angle
      self.opixel_scale = self.pixel_scale

      this_poly = np.zeros(shape=(4,), dtype=np.float64)
      res = scipy.optimize.minimize(self.reduce_fov_pos, this_poly, args=(), method='Nelder-Mead')
      adj_az, adj_el, adj_pos, adj_px = res['x']

      mod_az = (adj_az*self.oaz)
      mod_el = (adj_el*self.oel)
      mod_pos = (adj_pos*self.oposition_angle)
      mod_pix = (adj_px*self.opixel_scale)

      #print("MODS:", mod_az, mod_el, mod_pos, mod_pix)
      #print("RES:", res)
      #print("OLD/NEW AZ:", self.az, self.az+mod_az)
      #print("OLD/NEW EL:", self.el, self.el+mod_el)
      #print("OLD/NEW POS:", self.position_angle, self.position_angle+mod_pos)
      #print("OLD/NEW PX:", self.pixel_scale, self.pixel_scale+mod_pix)

      new_res = self.test_new_cal_params(self.az+mod_az,self.el+mod_el,self.position_angle+mod_pos,self.pixel_scale+mod_pix,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
      self.az += mod_az
      self.el += mod_el
      self.position_angle += mod_pos
      self.pixel_scale += mod_pix
      #xxx = input("FIN MIN")

   def obj_to_json(self, defaults=0):
      calib = {}
      if defaults == 0 or self.az is not None:
         calib['center_az'] = self.az
         calib['center_el'] = self.el
         calib['position_angle'] = self.position_angle
         calib['pixscale'] = self.pixel_scale
         calib['total_res_px'] = self.total_res_px
         calib['user_stars'] = self.user_stars
         calib['cat_image_stars'] = self.cat_image_stars
         calib['short_bright_stars'] = self.short_bright_stars
      else:
         calib['center_az'] = self.default_az
         calib['center_el'] = self.default_el
         calib['ra_center'] = self.default_ra
         calib['dec_center'] = self.default_dec
         calib['position_angle'] = self.default_position_angle
         calib['pixscale'] = self.default_pixel_scale
         calib['total_res_px'] = self.default_total_res_px
         calib['user_stars'] = self.user_stars
         calib['cat_image_stars'] = self.cat_image_stars
         calib['short_bright_stars'] = self.short_bright_stars

      if self.cal_image_file is not None:
         calib = update_center_radec(self.cal_image_file,calib,self.json_conf)

         #calib['ra_center'] = self.ra
         #calib['dec_center'] = self.dec

      return(calib)


   def reduce_fov_pos(self, this_poly):
      #image = oimage.copy()
      #image = cv2.resize(image, (1920,1080))

      mod_az = this_poly[0]*self.oaz
      mod_el = this_poly[1]*self.oel
      mod_pos = this_poly[2]*self.oposition_angle
      mod_pix = this_poly[3]*self.opixel_scale

      new_res = self.test_new_cal_params(self.az+mod_az,self.el+mod_el,self.position_angle+mod_pos,self.pixel_scale+mod_pix,self.lens_model['x_poly'],self.lens_model['y_poly'],self.lens_model['x_poly_fwd'],self.lens_model['y_poly_fwd'])
      #print("RES:", self.orev, len(self.cat_image_stars), new_res)
      #print(mod_az, mod_el, mod_pos, mod_pix)
      return(new_res)

   def minimize_multi_poly():
      # merge the stars from all of the cal files
      print("Make star model.")
      #for star in merged_stars:
      #   (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star


   def reduce_fit_multi(this_poly,field, merged_stars, cal_params, fit_img, json_conf, cam_id=None,mode=0,show=0):

      # Portions of this function use RMS routines
      # The MIT License

      # Copyright (c) 2017, Denis Vida

      # Permission is hereby granted, free of charge, to any person obtaining a copy
      # of this software and associated documentation files (the "Software"), to deal
      # in the Software without restriction, including without limitation the rights
      # to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
      # copies of the Software, and to permit persons to whom the Software is
      # furnished to do so, subject to the following conditions:

      # The above copyright notice and this permission notice shall be included in
      # all copies or substantial portions of the Software.

      # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
      # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
      # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
      # AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
      # LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
      # OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
      # THE SOFTWARE.


      print("stars:", len(merged_stars))
      this_fit_img = np.zeros((1080,1920),dtype=np.uint8)
      this_fit_img = cv2.cvtColor(this_fit_img,cv2.COLOR_GRAY2RGB)
      global tries

      if field == 'x_poly':
         x_poly_fwd = cal_params['x_poly_fwd']
         y_poly_fwd = cal_params['y_poly_fwd']
         x_poly = this_poly
         cal_params['x_poly'] = x_poly
         y_poly = cal_params['y_poly']

      if field == 'y_poly':
         x_poly_fwd = cal_params['x_poly_fwd']
         y_poly_fwd = cal_params['y_poly_fwd']
         y_poly = this_poly
         cal_params['y_poly'] = y_poly
         x_poly = cal_params['x_poly']

      if field == 'x_poly_fwd':
         x_poly = cal_params['x_poly']
         y_poly = cal_params['y_poly']
         x_poly_fwd = this_poly
         cal_params['x_poly_fwd'] = x_poly_fwd
         y_poly_fwd = cal_params['y_poly_fwd']

      if field == 'y_poly_fwd':
         x_poly = cal_params['x_poly']
         y_poly = cal_params['y_poly']
         y_poly_fwd = this_poly
         cal_params['y_poly_fwd'] = y_poly_fwd
         x_poly_fwd = cal_params['x_poly_fwd']

      # loop over each pair of img/cat star and re-compute distortion with passed 'this poly', calc error distance and return avg distance for all pairs set
      total_res = 0
      total_res_fwd = 0

      # OK. For multi-fit, we need to add the cal_file (includes date) to the front of this list. and then calulate the RA/DEC center on-the-fly based on the AZ/EL and date conversion. The update the calparams for this specific star before doing the distortion.
      new_merged_stars = []
      avgpixscale = 162
      for star in merged_stars:
         (cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int) = star

         if field == 'x_poly' or field == 'y_poly':
            new_cat_x, new_cat_y = distort_xy(0,0,ra,dec,float(ra_center), float(dec_center), x_poly, y_poly, float(1920), float(1080), float(position_angle),3600/float(pixscale))

            img_res = abs(calc_dist((six,siy),(new_cat_x,new_cat_y)))
            if img_res <= 1:
               color = [0,255,0]
            elif 1 < img_res <= 2:
               color = [0,200,0]
            elif 2 < img_res <= 3:
               #rgb
               color = [255,0,0]
            elif 3 <  img_res <= 4:
               color = [0,69,255]
            else:
               color = [0,0,255]

            desc = str(pixscale)[0:4]
            cv2.rectangle(this_fit_img, (int(new_cat_x)-10, int(new_cat_y)-10), (int(new_cat_x) + 10, int(new_cat_y) + 10), color, 1)
            cv2.line(this_fit_img, (six,siy), (int(new_cat_x),int(new_cat_y)), color, 2)
            new_y = new_cat_y
            new_x = new_cat_x
         else:
            cal_params['ra_center'] = ra_center
            cal_params['dec_center'] = dec_center
            cal_params['position_angle'] = position_angle
            cal_params['pixscale'] = pixscale
            cal_params['imagew'] = 1920
            cal_params['imageh'] = 1080
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(six,siy,cal_file,cal_params,json_conf)
            new_x, new_y= distort_xy(0,0,img_ra,img_dec,float(ra_center), float(dec_center), x_poly, y_poly, float(cal_params['imagew']), float(cal_params['imageh']), float(cal_params['position_angle']),3600/float(cal_params['pixscale']))

            img_res = abs(angularSeparation(ra,dec,img_ra,img_dec))

            if img_res <= .1:
               color = [0,255,0]
            elif .1 < img_res <= .2:
               color = [0,200,0]
            elif .2 < img_res <= .3:
               color = [0,69,255]
            elif img_res > .3:
               color = [0,0,255]

            cv2.rectangle(this_fit_img, (int(new_x)-10, int(new_y)-10), (int(new_x) + 10, int(new_y) + 10), color, 1)
            cv2.line(this_fit_img, (six,siy), (int(new_x),int(new_y)), color, 2)
         cv2.circle(this_fit_img,(six,siy), 12, (128,128,128), 1)

         new_merged_stars.append((cal_file , center_az, center_el, ra_center, dec_center, position_angle, pixscale, dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int))
         total_res = total_res + img_res

      total_stars = len(merged_stars)
      if total_stars > 0:
         avg_res = total_res/total_stars
      else:
         avg_res = 999

      desc = "Cam: " + str(cam_id) + " Stars: " + str(total_stars) + " " + field + " Res: " + str(avg_res)[0:6]
      cv2.putText(this_fit_img, desc,  (5,1070), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 1)

      if SHOW == 1:
         simg = cv2.resize(this_fit_img, (960,540))
         cv2.imshow(cal_params['cam_id'], simg)
         cv2.waitKey(30)

      print("Total Residual Error:",field, total_res )
      print("Total Stars:", total_stars)
      print("Avg Residual Error:", avg_res )
      print("Show:", show)
      tries = tries + 1
      if mode == 0:
         return(avg_res)
      else:
         return(avg_res, new_merged_stars)





          


if __name__ == "__main__":
   import sys

   # scan all cal files in freecal dir and load them as class object and then view them
   # This process will skip files it has already optimized

   import glob
   json_conf = load_json_file("../conf/as6.json")
   for cam_num in json_conf['cameras']:
      if cam_num == "cam1":
         continue
      cams_id = json_conf['cameras'][cam_num]['cams_id']
      files = glob.glob("/mnt/ams2/cal/freecal/*" + cams_id + "*")
      print(cam_num, cams_id, len(files))
      c = 0
      for cal_dir in sorted(files, reverse=True):
         cdfn = cal_dir.split("/")[-1]
         cal_image_file = cal_dir + "/" + cdfn + "-stacked.png"
         print(cdfn)
         skip = 0
         if cfe(cal_image_file) == 1:
            cp_file = cal_image_file.replace(".png", "-calparams.json")
            if cfe(cp_file) == 1:
               try:
                  cp = load_json_file(cp_file)
               except:
                  print("BAD CPF:", cp_file)
                  continue 
                  #exit()
               if "orev" in cp:
                  if cp['orev'] >= 2 or cp['total_res_px'] < 2:
                     skip = 1
         if cfe(cal_image_file) == 1 and skip == 0:

            xcam_num = cam_num.replace("cam", "")
            calibration = Calibration(cam_num=xcam_num, cal_image_file=cal_image_file)
            #calibration.draw_cal_image()

            if (calibration.total_res_px > 2 or calibration.orev == 0) and calibration.orev < 5:
               calibration.minimize_cal_params()
               calibration.save_cal_params()
               print("RES:", len(calibration.cat_image_stars), calibration.total_res_px, calibration.orev)
               if calibration.total_res_px > 2:
                  print("RES still bad try to tweek.")
                  calibration.tweek_cal()
                  calibration.cp = update_center_radec(calibration.cal_image_file,calibration.cp,calibration.json_conf)
                  calibration.save_cal_params()

               #calibration.draw_cal_image()
            else:
               print("GOOD:", len(calibration.cat_image_stars), "stars", calibration.total_res_px, "px res")
         c += 1
      print("finished cam:", cam_num)


