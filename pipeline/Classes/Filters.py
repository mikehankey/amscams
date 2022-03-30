import glob, os
import numpy as np
from lib.PipeUtil import load_json_file, save_json_file, cfe

from sklearn import linear_model, datasets
from skimage.measure import ransac, LineModelND, CircleModel

from sklearn.linear_model import RANSACRegressor
from sklearn.datasets import make_regression

class Filters():
   def __init__(self ):
      self.exp_dates = ['08_11', '08_12', '08_13', '08_14', '12_12', '12_13', '12_14']
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      # if there are more than this many detections on 1 day, more strict filters will be applied to the meteors 

      self.max_detect_thresh = 25

      self.mfiles = []

   def fn_gaps(self,obj):
      for i in range(0, len(obj['ofns'])):
         if i > 0:
            fn = obj['ofns'][i]
            fn_gaps = fn - obj['ofns'][i-1]
      return(fn_gaps)

   def get_weather_for_hour(self,day):
      self.weather_hours = {}
      wd = "/mnt/ams2/latest/" + day + "/"
      wfs = glob.glob(wd + "*.json")
      for wf in wfs:
         wfn = wf.split("/")[-1]
         print("WFN:", wfn)
         whour = wfn[0:13]
         print(wf)
         weather = load_json_file(wf)
         print(wfn, whour, weather)
         print("WH", whour)
         if whour not in self.weather_hours:
            self.weather_hours[whour] = weather
      save_json_file(wd + day + ".weather", self.weather_hours)
   
   
   def check_ai_day(self, day):
      if "ml" in self.json_conf:
         print("ML EXISTS")
         os.system("python3.6 MeteorScan.py " + day)
         exit()
      else:
         print("NO ML")
      exit() 

   def filter_month(self, mon):
      dirs = glob.glob("/mnt/ams2/meteors/" + mon + "*")
      for md in sorted(dirs, reverse=True):
         day = md.split("/")[-1]
         print("Checking", day)
         self.check_ai_day(day)
         self.check_day(day)

   def dir_change(self,obj):
      last_x = None
      last_y = None
      x_dir = None
      y_dir = None
      last_x_dir = None
      last_y_dir = None
      change_x = 0
      change_y = 0
      for x in obj['oxs']:
         if last_x is not None:
            x_dir = x - last_x
            if x_dir == 0:
               foo = 1
            elif x_dir < 0:
               x_dir = "R2L"
            else:
               x_dir = "L2R"
         if x_dir is not None:
            if last_x_dir != x_dir and last_x_dir is not None and x_dir != 0:
                change_x += 1
            last_x_dir = x_dir
         last_x = x
      for y in obj['oys']:
         if last_y is not None:
            y_dir = y - last_y
          
            if y_dir == 0:
               foo = 1
            elif y_dir < 0:
               y_dir = "B2T"
            else:
               y_dir = "T2B"
         if y_dir is not None:
            if last_y_dir != y_dir and last_y_dir is not None and y_dir != 0:
                change_y += 1
            last_y_dir = y_dir
         last_y = y
      tchange = (change_x + change_y) / 2
      if tchange > 0:
         perc_change = tchange / len(obj['oxs'])
      else:
         perc_change = 0
      frames_left  = len(obj['oxs']) - tchange
      status = 1
      if perc_change > .4:
         status = 0
      if frames_left < 3:
         status = 0
      if frames_left <= 3 and perc_change >= .33:
         status = 0
      return(status, perc_change)

   def check_segs(self,obj):
      segs = obj['report']['line_segments'][1:]
      pos_segs = []
      neg_segs = 0
      for seg in segs:
         if seg > 0:
            pos_segs.append(seg)
         else:
            neg_segs += 1
      if len(pos_segs) > 0:
         avg_seg = np.mean(pos_segs)
      else:
         avg_segs = 0
      good = 0
      if avg_seg > 0:
         for seg in segs:
            seg_diff = avg_seg - abs(seg)
            if seg_diff < 10:
               good += 1
      good = good - neg_segs
      if good > 0:
         good_perc = good / len(segs)
      else:
         good_perc = 0
      if len(segs) <= 3:
         good_perc = 1
      return(good_perc)

   def check_day(self,day):
      date = day
      os.system("python3 Rec.py del_aws_meteors " + day)
      os.system("./Process.py purge_meteors")
      os.system("./Process.py mmi_day " + date)
      os.system("cd ../pythonv2/; batch_jobs fi")

      self.get_weather_for_hour(day)
      trash_dir = "/mnt/ams2/trash/" + day + "/" 
      if cfe(trash_dir, 1) == 0:
         os.makedirs("/mnt/ams2/trash/" + day)
      year = day[0:4]
      shower_day = day.replace(year + "_", "")
      bad_detects = {}
      min_caps = {}
      hour_caps = {}
      print("CHECK DAY", shower_day)
      self.mfiles = []
      self.mdir = "/mnt/ams2/meteors/" + day + "/"
      self.get_mfiles("/mnt/ams2/meteors/" + day + "/")
      if len(self.mfiles) > self.max_detect_thresh and shower_day not in self.exp_dates:
         print("WOA WE HAVE A LOT OF CAPTURES. MIGHT BE A PROBLEM!", day, len(self.mfiles))
      else:
         print("THIS DAY IS OK", len(self.mfiles))
         return()
      # first define captures by minute and hour by cam. numerous caps in the same minute are a sign of errors, rain, fireflys, fast clouds/lightening, rain         
      for mf in self.mfiles:
         root_file = mf.split("-trim")[0]
         el = root_file.split("_")
         y,m,d,h,mm,s,ms,cam = el
         min_file = y + "_" + m + "_" + d + "_" + h + "_" + mm + "_" + cam 
         hour_file = y + "_" + m + "_" + d + "_" + h + "_" + cam 
         hour_key = y + "_" + m + "_" + d + "_" + h 
 

         if min_file not in min_caps:
            min_caps[min_file] = 1
         else:
            min_caps[min_file] += 1
         if hour_file not in hour_caps:
            hour_caps[hour_file] = 1
         else:
            hour_caps[hour_file] += 1

      for hkey in hour_caps:
         hour_key = hkey[0:13]
         if hour_key in self.weather_hours:
            cur_weather = self.weather_hours[hour_key]['conditions']
         else:
            cur_weather = None
         print("HOUR COUNT:", hour_key, hkey, cur_weather, hour_caps[hkey])   

      # main filter loop. 
      # bad flags = 
      # Bad Weather conditions : Overcast, = +1 
      # Frequency : More than X in the hour = +1 
      #             More than X in the minute = +1 
      # Point Analysis: 3 points and a bad score >= 2 = reject
      #                 Failed ransac and a badscore >= 2 reject
      #                 Bad line segs and a badscore >= 2
      # define bad scores
      bad_scores = {}
      bad_items = {}
      met_multi = {}
      all_weather = {}
      for mf in self.mfiles:

         met_multi[mf] = 1
         if mf not in bad_scores:
            bad_scores[mf] = 0
         if mf not in bad_items:
            bad_items[mf] = []
         rf = mf.replace(".mp4", "")
         bad = 0
         root_file = mf.split("-trim")[0]
         el = root_file.split("_")
         y,m,d,h,mm,s,ms,cam = el
         min_file = y + "_" + m + "_" + d + "_" + h + "_" + mm + "_" + cam 
         hour_file = y + "_" + m + "_" + d + "_" + h + "_" + cam 
         hour_key = y + "_" + m + "_" + d + "_" + h 
         if hour_key in self.weather_hours:
            print("WEATH KEYS:", self.weather_hours.keys())
            print("HOUR KEY:", hour_key)
            cur_weather = self.weather_hours[hour_key]['conditions']
         else:
            cur_weather = "" 
            print("NO WEATHER FOR HOUR! WEATH KEYS:", self.weather_hours.keys())
            print("HOUR KEY:", hour_key)
         bad_items[mf].append("Current Weather: " + cur_weather) 
         all_weather[mf] = cur_weather
         if cur_weather is not None and (cur_weather == "Overcast" or cur_weather == "Heavy rain" or "rain" in cur_weather or "drizzle" in cur_weather):
            if mf not in bad_scores:
               bad_scores[mf] = 1   
            else:
               bad_scores[mf] += 1   
            bad_items[mf].append("Bad Weather: " + cur_weather) 

         if min_caps[min_file] > 3:
            if mf not in bad_scores:
               bad_scores[mf] = 1   
            else:
               bad_scores[mf] += 1   
            bad_items[mf].append("Min cap thresh " + str(min_caps[min_file])) 
         if min_caps[min_file] > 5:
            if mf not in bad_scores:
               bad_scores[mf] = 1   
            else:
               bad_scores[mf] += 1   
            bad_items[mf].append("Min cap thresh " + str(min_caps[min_file])) 
         if min_caps[min_file] > 10:
            if mf not in bad_scores:
               bad_scores[mf] = 1   
            else:
               bad_scores[mf] += 1   
            bad_items[mf].append("Min cap thresh " + str(min_caps[min_file])) 
         if hour_caps[hour_file] > 9:
            if mf not in bad_scores:
               bad_scores[mf] = 1   
            else:
               bad_scores[mf] += 1   
            bad_items[mf].append("Hour cap thresh " + str(hour_caps[hour_file])) 
         if hour_caps[hour_file] > 50:
            if mf not in bad_scores:
               bad_scores[mf] = 2 
            else:
               bad_scores[mf] += 2   
            bad_items[mf].append("Hour cap thresh " + str(hour_caps[hour_file])) 
         if cur_weather is not None and (cur_weather == "Overcast" or cur_weather == "Heavy rain" or "rain" in cur_weather or "drizzel" in cur_weather):
            if mf not in bad_scores:
               bad_scores[mf] = 3   
            else:
               bad_scores[mf] += 3   
            if hour_caps[hour_file] > 25:
               bad_scores[mf] += 2   
               bad_items[mf].append("Bad weather + high hour cap" + str(cur_weather) + " " + str(hour_caps[hour_file])) 
        
            bad_items[mf].append("Bad weather" + str(cur_weather)) 
         else:
            print("CUIR WEATHER:", cur_weather)
      
      hot_zones = []
      
      for mf in sorted(bad_scores) :
         mjf = mf.replace(".mp4", ".json")
         cur_weather = all_weather[mf]
         if cfe(self.mdir + mjf) == 1:
            try:
               mj = load_json_file(self.mdir + mjf)
            except:
               print("CORRUPT JSON FILE:", self.mdir + mjf)
               continue
            if "multi_station_event" in mj or "hc" in mj :
               print("WHITE LISTED METEOR 1!", mf)
               print(mj.keys())
               continue
            if "user_mods" in mj:
               if len(mj['user_mods'].keys()) > 0:
                  print("WHITE LISTED METEOR 2!", mf)
                  print(mj['user_mods'].keys())
                  continue

 

            if "confirmed_meteors" in mj:
               confirmed_meteors = len(mj['confirmed_meteors'])
            else:
               confirmed_meteors = 0
               print("CONFIRMED METEORS NOT IN MJ?")
            if confirmed_meteors == 0:
               print("NO CONFIRMED METEORS?")
            if confirmed_meteors > 3:
               if mf not in bad_scores:
                  bad_scores[mf] = 1   
               else:
                  bad_scores[mf] += 1   
               
               bad_items[mf].append("too many confirmed meteors " + str(confirmed_meteors))

            if confirmed_meteors > 0:
               for obj in mj['confirmed_meteors']:
                  fn_gaps = self.fn_gaps(obj)
                  if fn_gaps > 25:
                     met_multi[mf] += 1
                  seg_good_perc = self.check_segs(obj)
                  if seg_good_perc < .4:
                     met_multi[mf] += 1

                  print("SEGS GOOD %:", seg_good_perc)
                  x1 = min(obj['oxs'])
                  x2 = max(obj['oxs'])
                  y1 = min(obj['oys'])
                  y2 = max(obj['oys'])
                  avg_x = np.mean(obj['oxs'])
                  avg_y = np.mean(obj['oys'])
                  hot_zone_hits = 0
                  for hx1,hy1,hx2,hy2 in hot_zones:
                     if hx1 <= avg_x <= hx2 and hy1 <= avg_y <= hy2: 
                        hot_zone_hits += 1
                  hot_zones.append((x1,y1,x2,y2))
                  print(obj['oxs'])
                  print(obj['oys'])
                  print(obj['ows'])
                  print(obj['ohs'])
                  print(obj['oint'])
                  print("HOT ZONE HITS:", hot_zone_hits)
                  if hot_zone_hits > 2:
                     if mf not in bad_scores:
                        bad_scores[mf] = 1   
                     else:
                        bad_scores[mf] +=  hot_zone_hits  
                     met_multi[mf] += 1
                     bad_items[mf].append("Hot zone hits:" + str(hot_zone_hits)) 
 
                  dc_status,dc_perc = self.dir_change(obj)
                  if dc_status == 0:
                     if mf not in bad_scores:
                        bad_scores[mf] = 1   
                     else:
                        bad_scores[mf] += 1   
                     bad_items[mf].append("Too many direction changes.") 

                  if seg_good_perc <=  .6:
                     if mf not in bad_scores:
                        bad_scores[mf] = 1   
                     else:
                        bad_scores[mf] += 1   
                     bad_items[mf].append("Bad seg perc" + str(seg_good_perc)) 
                  if seg_good_perc <=  .5:
                     if mf not in bad_scores:
                        bad_scores[mf] = 1   
                     else:
                        bad_scores[mf] += 1   
                     bad_items[mf].append("Bad seg perc" + str(seg_good_perc)) 

                  print("FN GAPS:", fn_gaps)
                  if fn_gaps > 4:
                     if mf not in bad_scores:
                        bad_scores[mf] = 1   
                     else:
                        bad_scores[mf] += 1   
                     bad_items[mf].append("Bad FN Gaps" + str(fn_gaps)) 

                  # check if the detection is near the bottom of the frame
                  min_y = min(obj['oys'])
                  max_y = max(obj['oys'])
                  print("MIN Y:", min_y)
                  if max_y > 300:
                     if mf not in bad_scores:
                        bad_scores[mf] = 1   
                     else:
                        bad_scores[mf] += 1   
                     bad_items[mf].append("Lower field hit max_y = " + str(max_y)) 
                  

                  try:
                     IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac,inlier_mask,outlier_mask = self.ransac_outliers(obj['oxs'], obj['oys'])
                  except:
                     IN_XS = []
                     IN_YS = []
                  rans_good_perc = len(IN_XS) / len(obj['ofns'])
                  print("GOOD RANSC:", rans_good_perc)
                  if rans_good_perc < .66 and rans_good_perc != 0:
                     met_multi[mf] += 1
                     if mf not in bad_scores:
                        bad_scores[mf] = 1   
                     else:
                        bad_scores[mf] += 1   
                     bad_items[mf].append("Bad Ransac Perc" + str(rans_good_perc)) 

                  if "oxs" in obj:
                     if len(obj['oxs']) <= 3:
                        bad_items[mf].append("short duration" + str(len(obj['oxs']))) 
                        if mf not in bad_scores:
                           bad_scores[mf] = 1   
                        else:
                           bad_scores[mf] += 1   

                     print(obj['oxs'])
                     print(obj['oys'])
                     print(obj['ows'])
                     print(obj['ohs'])
                     print(obj['oint'])

         bad_scores[mf] = bad_scores[mf] * met_multi[mf]
         print("BAD SCORE:",cur_weather, mf, bad_scores[mf], bad_items[mf], met_multi[mf])

      for mf in sorted(self.mfiles):
         if mf in bad_scores:
            print("BAD SCORE:",mf, bad_scores[mf], bad_items[mf])
            if bad_scores[mf] >= 4:
               bad_detects[mf] = bad_scores[mf] 
         else:
            print("GOOD MF:", mf)

      # deal with the bad detects
      for bd in bad_detects:
         print("BAD:", bd, bad_detects[bd])
         self.purge_meteor(bd)
      os.system("./Process.py purge_meteors")
      os.system("./Process.py mmi_day " + date)
      os.system("cd ../pythonv2/; ./batchJobs.py fi")
      print(len(self.mfiles), "total detects") 
      print(len(bad_detects), "bad detects") 



   def firefly_filter():
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
               try:
                  mj = load_json_file(meteor_file)
                  if "multi_station_event"  in mj:
                     # don't filter MSEs!
                     continue
               except:
                  continue

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

   def purge_meteor(self, root_file):
      if ".mp4" in root_file:
         root_file = root_file.replace(".mp4", "")
      print("DELETE THIS METEOR!", root_file)
      meteor_dir = "/mnt/ams2/meteors/" + root_file[0:10] + "/" 
      meteor_scan_dir = "/mnt/ams2/METEOR_SCAN/" + root_file[0:10] + "/" 
      cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + root_file[0:4] + "/" +  root_file[0:10] + "/" 
      mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
      print("DELETE THIS METEOR!", mfile)
      try:
         mj = load_json_file(mfile)
         if "multi_station_event" in mj:
            return()
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
