import cv2
from lib.PipeUtil import mfd_roi
from lib.PipeUtil import load_json_file, save_json_file
import numpy as np
import os
from Classes.Filters import Filters
FLT = Filters()

def get_met_data(mjf):
   day = mjf[0:10]
   mdir = "/mnt/ams2/meteors/" + day + "/"
   mjrf = mjf.replace(".json", "-reduced.json")
   thumb = mjf.replace(".json", "-stacked.jpg")
   cimg = cv2.imread(mdir + thumb )
   try:
      img =  cv2.cvtColor(cimg, cv2.COLOR_BGR2GRAY)
   except:
      img = np.zeros((1080,1920),dtype=np.uint8)
      cimg = np.zeros((1080,1920,3),dtype=np.uint8)
   hdm_x = 1920 / img.shape[1]
   hdm_y = 1080 / img.shape[0]
   durt = 0
   avg_px = 0
   #mj = load_json_file(mdir + mjf)
   if os.path.exists(mdir + mjrf) is False:
      return(None,None)
      
   mjr = load_json_file(mdir + mjrf)
   roi_file = mdir + mjf.replace(".json", "-ROI.jpg")
   roi_file = roi_file.replace("/meteors/", "/METEOR_SCAN/")
   if "meteor_frame_data" in mjr:
      if len(mjr['meteor_frame_data']) < 1:
         return(None,None)
      #(dt, frn, x, y, w, h, oint, ra, dec, az, el) = row
      if len(mjr['meteor_frame_data']) > 1:
         x1,y1,x2,y2= mfd_roi(mjr['meteor_frame_data'])
         x1,y1,x2,y2 = int(x1/hdm_x),int(y1/hdm_y),int(x2/hdm_x),int(y2/hdm_y)
         if x1 < 0:
            x1 =0
         if y1 < 0:
            y1 =0
         if y2 >= img.shape[0]:
            y2 = img.shape[0]-1
         if x2 >= img.shape[1]:
            x2 = img.shape[1]-1

         durf = len(mjr['meteor_frame_data'])
         durt = durf / 25
         croi_img = cimg[y1:y2,x1:x2]
         roi_img =  cv2.cvtColor(croi_img, cv2.COLOR_BGR2GRAY)
         cv2.imwrite(roi_file, croi_img)
         avg_px = np.mean(roi_img)
         blue_sum = float(np.sum(croi_img[0]))
         try:
            green_sum = float(np.sum(croi_img[1]))
         except:
            green_sum = float(blue_sum)
         try:
            red_sum = float(np.sum(croi_img[2]))
         except:
            red_sum = green_sum
         blue_max = float(np.max(croi_img[0]))
         try:
            green_max = float(np.max(croi_img[1]))
         except:
            green_max = blue_max
         try:
            red_max = float(np.max(croi_img[2]))
         except:
            red_max = green_max
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(roi_img)
         avg_max_diff = max_val / avg_px


         #ra1 = mjr['meteor_frame_data'][0][7]
         #dec1 = mjr['meteor_frame_data'][0][8]
         #ra2 = mjr['meteor_frame_data'][-1][7]
         #dec2 = mjr['meteor_frame_data'][-1][8]
         ints = [row[6] for row in mjr['meteor_frame_data']]
         fns = [row[1] for row in mjr['meteor_frame_data']]
         ras = [row[7] for row in mjr['meteor_frame_data']]
         decs= [row[8] for row in mjr['meteor_frame_data']]
         oxs = [row[2] for row in mjr['meteor_frame_data']]
         oys = [row[3] for row in mjr['meteor_frame_data']]
         if len(ints) > 0:
            max_int = max(ints)
            min_int = min(ints)
         else:
            max_int = 0
            min_int = 0

         try:
            ang_sep = np.degrees(angularSeparation(np.radians(min(ras)), np.radians(min(decs)), np.radians(max(ras)), np.radians(max(decs))))
            ang_vel = ang_sep / durt
         except:
            ang_sep = 0
            ang_vel = 0

         if min_int > 0:
            peak_times = max_int / min_int
         else:
            peak_times = max_int
         try:
            gap_test_res , gap_test_info = gap_test(fns)
         except:
            gap_test_info = {}
            gap_test_info['total_gaps'] = 0
            gap_test_info['gap_events'] = 0

         try:
            IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac,inlier_mask,outlier_mask = FLT.ransac_outliers(oxs, oys)
            if len(OUT_XS) == 0:
               ran_perc = 1
            else:
               ran_perc = len(IN_XS) / len(oxs)
         except:
            ran_perc = 0


         obj = {}
         obj['oxs'] = oxs
         obj['oys'] = oys
         dc_status,dc_perc = FLT.dir_change(obj)

         #features = [float(durt), float(ang_sep),float(ang_vel),float(max_int),float(min_int),float(peak_times),float(ran_perc),float(dc_perc),float(gap_test_info['total_gaps']),float(gap_test_info['gap_events']),float(min(oys)),float(max(oys)),avg_px, max_val, avg_max_diff,]
         features = [float(durt), float(ang_vel), avg_px, max_val,gap_test_info['total_gaps'],peak_times,ran_perc,dc_perc] #, peak_times, ran_perc, max(oys)] #,float(ang_vel),float(max_int),float(min_int),float(peak_times),float(ran_perc),float(dc_perc),float(gap_test_info['total_gaps']),float(gap_test_info['gap_events']),float(min(oys)),float(max(oys))]
         features = [float(durt), float(ang_vel), peak_times,ran_perc,avg_px,max_val,avg_max_diff,green_max,blue_max,red_max] #, peak_times, ran_perc, max(oys)] #,float(ang_vel),float(max_int),float(min_int),float(peak_times),float(ran_perc),float(dc_perc),float(gap_test_info['total_gaps']),float(gap_test_info['gap_events']),float(min(oys)),float(max(oys))]
         features = [float(durt), float(ang_vel), float(ran_perc),float(avg_px),float(max_val),float(avg_max_diff),float(green_max),float(blue_max),float(red_max),float(min_int),float(max_int),float(peak_times),float(min(oxs)),float(max(oxs)),float(min(oys)),float(max(oys)),float(dc_perc),float(gap_test_info['total_gaps']),float(gap_test_info['gap_events']) ] 
             #, peak_times, ran_perc, max(oys)] #,float(ang_vel),float(max_int),float(min_int),float(peak_times),float(ran_perc),float(dc_perc),float(gap_test_info['total_gaps']),float(gap_test_info['gap_events']),float(min(oys)),float(max(oys))]
      #features=[float(max_int), float(durt), float(ang_vel)]
         features_obj = {}
         features_obj['durt'] = float(durt)
         features_obj['ang_vel'] = float(ang_vel)
         features_obj['ran_perc'] = float(ran_perc)
         features_obj['avg_px'] = float(avg_px)
         features_obj['max_val'] = float(max_val)
         features_obj['avg_max_diff'] = float(avg_max_diff)
         features_obj['green_max'] = float(green_max)
         features_obj['blue_max'] = float(blue_max)
         features_obj['red_max'] = float(red_max)
         features_obj['peak_times'] = float(peak_times)
         features_obj['max_x'] = float(max(oxs))
         features_obj['min_x'] = float(min(oxs))
         features_obj['max_y'] = float(max(oys))
         features_obj['min_y'] = float(min(oys))
         features_obj['max_int'] = float(max_int)
         features_obj['min_int'] = float(min_int)
         features_obj['dc_perc'] = float(dc_perc)
         features_obj['total_gaps'] = float(gap_test_info['total_gaps'])
         features_obj['gap_events'] = float(gap_test_info['gap_events'])
         return(features, features_obj)
   return(None,None)

station_id = "AMS1"

ai_labels = {}
meteor_ids = load_json_file("/mnt/ams2/meteors/" + station_id + "_OBS_IDS.json")
feature_data_file = "/mnt/ams2/meteors/" + station_id + "_feature_data.json"
all_samples = load_json_file("all_samples.json")
for label in all_samples:
   for sample in all_samples[label]:
      if station_id in sample:
         sample = sample.replace("-ROI.jpg", "")
         ai_labels[sample] = label

lines="filename,label,durt,ang_vel,ran_perc,avg_px,max_val,avg_max_diff,green_max,blue_max,red_max,min_int,max_int,peak_times,max_y,min_y,dc_perc,total_gaps,gap_events"
if os.path.exists(feature_data_file) is False:
   feature_data = []
else:
   feature_data = load_json_file(feature_data_file)
for filename, datetime in meteor_ids:
   if station_id not in filename:
      ai_key = station_id + filename.replace(".json", "")
   else:
      ai_key = filename.replace(".json", "")
   if ai_key in ai_labels:
      label = ai_labels[ai_key]
   else:
      label = ""
   if label != "":
      mjf = ai_key.replace(station_id + "_", "") + ".json"

      features, features_obj = get_met_data(mjf)
      line = filename + "," + label 
      if features is not None:
         for data in features:
            line += ","
            line += str(data)
         line += "\n"
         lines += line
         print(line)
out = open("/mnt/ams2/meteors/" + station_id + "_meteor_features.json", "w")
out.write(lines)
