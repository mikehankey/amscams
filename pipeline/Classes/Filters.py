import glob, os
import numpy as np
from lib.PipeUtil import load_json_file, save_json_file, cfe

from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

class Filters():
   def __init__(self ):
      self.exp_dates = ['08_10', '08_11', '08_12', '08_13', '08_14', '12_12', '12_13', '12_14']
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      # if there are more than this many detections on 1 day, more strict filters will be applied to the meteors 

      self.max_detect_thresh = 125

      self.mfiles = []

   def filter_month(self, mon):
      dirs = glob.glob("/mnt/ams2/meteors/" + mon + "*")
      for md in sorted(dirs, reverse=True):
         day = md.split("/")[-1]
         print("Checking", day)
         self.check_day(day)

   def check_day(self,day):
      trash_dir = "/mnt/ams2/trash/" + day + "/" 
      if cfe(trash_dir, 1) == 0:
         os.makedirs("/mnt/ams2/trash/" + day)
      year = day[0:4]
      shower_day = day.replace(year + "_", "")
      bad_detects = {}
      min_caps = {}
      print("CHECK DAY", shower_day)
      self.get_mfiles("/mnt/ams2/meteors/" + day + "/")
      if len(self.mfiles) > self.max_detect_thresh and shower_day not in self.exp_dates:
         print("WOA WE HAVE A LOT OF CAPTURES. MIGHT BE A PROBLEM!", day, len(self.mfiles))
         input() 
      else:
         print("THIS DAY IS OK", len(self.mfiles))
         return()
      # first define captures by minute. numerous caps in the same minute are a sign of errors, rain, fireflys, fast clouds/lightening, rain         
      for mf in self.mfiles:
         root_file = mf.split("-trim")[0]
         el = root_file.split("_")
         y,m,d,h,mm,s,ms,cam = el
         min_file = y + "_" + m + "_" + d + "_" + h + "_" + mm + "_" #+ cam 

         if min_file not in min_caps:
            min_caps[min_file] = 1
         else:
            min_caps[min_file] += 1

      # firefly filter?
      maybe = 0
      bad_mets = 0
      for mf in self.mfiles:
         rf = mf.replace(".mp4", "")
         bad = 0
         root_file = mf.split("-trim")[0]
         el = root_file.split("_")
         y,m,d,h,mm,s,ms,cam = el
         min_file = y + "_" + m + "_" + d + "_" + h + "_" + mm + "_" #+ cam 
         if min_caps[min_file] > 1:
            bad += min_caps[min_file]
            bad_detects[rf] = {}
            bad_detects[rf]['reason'] = 'Multi-minute capture failure.' + str(min_caps[min_file])
         else:
            maybe += 1
            meteor_file = "/mnt/ams2/meteors/" + mf[0:10] + "/" + mf.replace(".mp4", ".json")
            if cfe(meteor_file) == 1:
               mj = load_json_file(meteor_file)
            else:
               continue
            confirmed_meteors = 0
            if "confirmed_meteors" in mj:
               confirmed_meteors = len(mj['confirmed_meteors']) 

            print(min_file, min_caps[min_file],confirmed_meteors )

            if confirmed_meteors > 0: 
               for obj in mj['confirmed_meteors']:
                  print("   OFNS", obj['ofns'])
                  print("   OXS", obj['oxs'])
                  print("   OYS", obj['oys'])
                  print("   SEGS", obj['report']['line_segments'])
                  print("   ANGV", obj['report']['ang_vel'])

                  try:
                     IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac,inlier_mask,outlier_mask = self.ransac_outliers(obj['oxs'], obj['oys'])
                  except:
                     IN_XS = []
                     IN_YS = []
                  print("   RANS IN:", len(IN_XS))
                  if len(obj['oxs']) > 0:
                     print("   RANS %:", len(IN_YS) / len(obj['oxs']) )
                     rans_perc = len(IN_YS) / len(obj['oxs'])
                  else:
                     print("   RANS %: 0")
                     rans_perc = 0
                  if rans_perc < .7:
                     print("RANS FAILED!")
                     bad += 1
                     bad_mets += 1
                     if rf not in bad_detects:
                        bad_detects[rf] = {}

                     bad_detects[rf]['reason'] = 'Ransac Failed.' + str(rans_perc)
                  print("   BAD", bad)
      for bd in bad_detects:
         print("BAD:", bd, bad_detects[bd])
         self.purge_meteor(bd)
      print(len(self.mfiles), "total detects") 
      print(len(bad_detects), "bad detects") 

   def purge_meteor(self, root_file):
      print("DELETE THIS METEOR!", root_file)
      meteor_dir = "/mnt/ams2/meteors/" + root_file[0:10] + "/" 
      meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/" + root_file[0:10] + "/" 
      cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + root_file[0:4] + "/" +  root_file[0:10] + "/" 
      mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
      print("DELETE THIS METEOR!", mfile)
      try:
         mj = load_json_file(mfile)
      except:
         return()

      sd_fn = mj['sd_video_file'].replace(".mp4", "")
      sd_fn = sd_fn.split("/")[-1]

      try:
         hd_fn = mj['hd_trim'].replace(".mp4", "")
         hd_fn = hd_fn.split("/")[-1]
      except:
         hd_fn = None

      # we want to remove or move references to this file from the :
      # meteor_dir, meteor_dir/cloud_files, meteor_dir/cloud_stage, METEOR_SCAN, cloud_files dir
      places = [meteor_dir, meteor_dir + "cloud_files/" + self.station_id + "_", meteor_dir + "cloud_stage/" + self.station_id + "_", meteor_scan_dir, cloud_dir + self.station_id + "_" ]
      trash_dir = "/mnt/ams2/trash/" + root_file[0:10] + "/" 
      for place in places:
         if "archive.allsky.tv" in place:
            cmd = "rm " + place + sd_fn + "*" 
            print(cmd)
            os.system(cmd)
            if hd_fn is not None:
               cmd = "rm " + place + hd_fn + "*" 
               print(cmd)
               os.system(cmd)

         else:
            cmd = "mv " + place + sd_fn + "* " + trash_dir
            print(cmd)
            os.system(cmd)
            if hd_fn is not None:
               cmd = "mv " + place + hd_fn + "* " + trash_dir
               print(cmd)
               os.system(cmd)

   def get_mfiles(self, mdir):
      temp = glob.glob(mdir + "/*.json")
      for json_file in temp:
          if "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            vfn = json_file.split("/")[-1].replace(".json", ".mp4")
            self.mfiles.append(vfn)

   def ransac_outliers(self,XS,YS):
      XS = np.array(XS)
      YS = np.array(YS)
      RXS = XS.reshape(-1, 1)
      RYS = YS.reshape(-1, 1)
      #oldway
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

      # make plot for ransac filter

      IN_XS = RXS[inlier_mask].tolist()
      IN_YS = RYS[inlier_mask].tolist()
      OUT_XS = RXS[outlier_mask].tolist()
      OUT_YS = RYS[outlier_mask].tolist()
      return(IN_XS,IN_YS,OUT_XS,OUT_YS,line_X.tolist(),line_Y.tolist(),line_y_ransac.tolist(),inlier_mask.tolist(),outlier_mask.tolist())   
