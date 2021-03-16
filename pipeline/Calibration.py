from Camera import Camera
import datetime
from lib.PipeAutoCal import gen_cal_hist,update_center_radec
from lib.PipeUtil import load_json_file, save_json_file, cfe

class Calibration():
   def __init__(self, cam_num=None,cams_id=None,json_conf=None,datestr=None,meteor_file=None,cal_image_file=None,time_mod=0):
      print("init Calibration object")
      cp = None

      if cams_id is not None:
         camera = Camera(cams_id = cams_id)
      if cam_num is not None:
         camera = Camera(cam_num = cam_num)
      if json_conf is None:
         json_conf = load_json_file("../conf/as6.json")

      if datestr is not None:
         self.calib_dt = datetime.datetime.strptime(datestr, "%Y_%m_%d_%H_%M_%S")
      elif cal_image_file is not None:
         cal_fn = cal_image_file.split("/")[-1]
         datestr = cal_fn[0:19]
         self.calib_dt = datetime.datetime.strptime(datestr, "%Y_%m_%d_%H_%M_%S")
         if cfe(cal_image_file) == 1:
            cpf = cal_image_file.replace(".png", "-calparams.json")
            if cfe(cpf) == 1:
               cp = load_json_file(cpf)
               cp = update_center_radec(cpf,cp,json_conf)
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

      if cp is None:
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
         self.cal_status = 0

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
         print("This camera is calibrated")
         self.cal_range = sorted(self.cal_range, key=lambda x: x[1], reverse=True)
         self.default_az = self.cal_range[0][3]
         self.default_el = self.cal_range[0][4]
         self.default_position_angle = self.cal_range[0][5]
         self.default_pixel_scale = self.cal_range[0][6]
         self.default_total_res_px = self.cal_range[0][7]
         self.cal_status = 1

      # if the datetime was passed in (or a filename) 
      # update the RA/DEC center to match the current datetime

   def obj_to_json(self, defaults=0):
      calib = {}
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
      return(calib)

   def generate_cal_history(json_conf=None):
      if json_conf is None:
         json_conf = load_json_file("../conf/as6.json")
      gen_cal_hist(json_conf)

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

if __name__ == "__main__":
   import sys
   cal_image_file = "/mnt/ams2/cal/freecal/2020_12_13_08_32_26_000_010004/2020_12_13_08_32_26_000_010004-stacked.png"
   calibration = Calibration(cam_num=4, cal_image_file=cal_image_file)
   print("Cal DT:    ", calibration.calib_dt)
   print("AZ:        ", calibration.az)
   print("EL:        ", calibration.el)
   print("RA:        ", calibration.ra)
   print("DEC:       ", calibration.dec)
   print("POS:       ", calibration.position_angle)
   print("PXS:       ", calibration.pixel_scale)
   print("IMG STARS: ", len(calibration.user_stars))
   print("CAT STARS: ", len(calibration.cat_image_stars))
   print("RES:       ", calibration.total_res_px)
