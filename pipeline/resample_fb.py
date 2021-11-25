import os
from lib.PipeUtil import load_json_file, save_json_file
from find_object import find_object
import glob
import math
import cv2
import numpy as np
import sys
from ransac_lib import ransac_outliers
from predict import predict_image, load_my_model

def sort_meteors_by_length():
   station_id = "AMS152"
   scan_type =  "meteors_short"

   ml_dir = "D:/MRH/COMBINED_REPO/" + station_id + "/"
   scan_dir = ml_dir + scan_type + "/" 

   files = os.listdir(ml_dir + scan_type)
   for fb in files:
      station_id = fb.split("_")[0]
      roi_file = fb.replace(station_id + "_", "")
      day = roi_file[0:10]
      #mdir = "/mnt/ams2/meteors/" + day + "/"
      #mdir = "Y://METEOR_SCAN/" + day + "/"
      #stack_file = mdir + roi_file.replace("-ROI.jpg", "-stacked.jpg")
      stack_file = roi_file
      if "\\" in stack_file:
         stack_fn = roi_file.split("\\")[-1]
      else:
         stack_fn = roi_file.split("/")[-1]
      stack_fn = stack_fn.replace("-ROI.jpg", "-stacked.jpg")
      img = cv2.imread(ml_dir + scan_type + "/" + fb)
   
      if len(img.shape) > 2:
         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
      else:
         gray = img
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
      avg_val = np.mean(gray)
      px_diff = max_val - avg_val
      px_fact = max_val / avg_val
      thresh_val = max_val * .65
      _, thresh_img = cv2.threshold(gray.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      thresh_img = cv2.dilate(thresh_img.copy(), None , iterations=4)
      
      if True:
         xs = []
         ys = []
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = which_cnts(cnt_res)
   
         conts = []
         for (i,c) in enumerate(cnts):
            x,y,w,h = cv2.boundingRect(cnts[i])
            intensity = int(np.sum(gray[y:y+h,x:x+w]))
            px_avg = intensity / (w*h)
            if w >= 10 and h >= 10 and px_avg > 10:
               conts.append((x,y,w,h,intensity,px_avg))
               xs.append(x)
               xs.append(x+w)
               ys.append(y)
               ys.append(y+h)
      if len(xs) > 0:
         min_x = min(xs)
         min_y = min(ys)
         max_x = max(xs)
         max_y = max(ys)
         dist = calc_dist((min_x,min_y), (max_x, max_y))
         new_class = ""
         if dist <= 50:
            new_class = "meteors_short"
         if 50 < dist <= 200:
            new_class = "meteors_medium"
         if dist >= 200:
            new_class = "meteors_long"
         if px_fact <= 1.9:
            new_class = "meteors_faint"
         new_dir = ml_dir + new_class + "/"
         new_file = new_dir + station_id + "_" + roi_file
         orig_file = scan_dir + station_id + "_" + roi_file
         print("DIST/VAL", dist, max_val, px_diff, px_fact, new_class)
         print(scan_type, new_class)
         #orig_file = orig_file.replace("/", "\\")
         #new_file = new_file.replace("/", "\\")
         if os.path.exists(orig_file) is False:
            print("ORIG FILE MISSING!", orig_file)
         #   exit()
         if new_class != scan_type:
            print(orig_file, new_file)
            os.rename(orig_file, new_file)
         cv2.imshow('pepe', img)
         cv2.waitKey(10)

def merge_cnts(cnts):
   ucnts = []
   for x,y,w,h,size in cnts:
      exists = 0
      for ux,uy,uw,uh,size in ucnts:
         print ("X", ux,  x , ux + uw) 
         print ("Y", uy , y , uy + uh)
         if (ux <= x <= ux + uw) and ( uy <= y <= uy + uh):
            print("EXISTS 1")
            exists = 1 
         if (ux <= x+w <= ux + uw) and ( uy <= y+h <= uy + uh):
            exists = 1 
            print("EXISTS 2")
      if exists == 0:
         print("ADD CNT", x,y,w,h)
         ucnts.append((x,y,w,h,size))
   return(ucnts)   

def bound_cnt(x1,y1,x2,y2,img):
   ih,iw = img.shape[:2]
   rw = x2 - x1
   rh = y2 - y1
   if rw > rh:
      rh = rw
   else:
      rw = rh
   rw += int(rw * .3)
   rh += int(rh * .3)
   if rw >= ih or rh >= ih:
      rw = int(ih*.95)
      rh = int(ih*.95)
   if rw < 100 or rh < 100:
      rw = 100
      rh = 100

   cx = int((x1 + x2)/2)
   cy = int((y1 + y2)/2)
   nx1 = cx - int(rw / 2)
   nx2 = cx + int(rw / 2)
   ny1 = cy - int(rh / 2)
   ny2 = cy + int(rh / 2)
   if nx1 <= 0:
      nx1 = 0 
      nx2 = rw
   if ny1 <= 0:
      ny1 = 0 
      ny2 = rh
   if nx2 >= iw:
      nx1 = iw-rw-1
      nx2 = iw-1 
   if ny2 >= ih:
      ny2 = ih-1 
      ny1 = ih-rh-1
   if ny1 <= 0:
      ny1 = 0 
   if nx1 <= 0:
      nx1 = 0 
   print("NX", nx1,ny1,nx2,ny2)
   return(nx1,ny1,nx2,ny2)

def resample_fireballs():
   json_conf = load_json_file("../conf/as6.json")
   t_station_id = json_conf['site']['ams_id']
   model = load_my_model()
   #fb_dir = "/mnt/ams2/datasets/learning/scan_results/meteors/meteors_fireballs/"
   #fb_dir = "Y:/datasets/learning/scan_results/meteors/meteors_fireballs/"
   ml_dir = "D:/MRH/COMBINED_REPO/" + t_station_id + "/"
   resample_dir = "D:/MRH/COMBINED_REPO/" + t_station_id + "/resample_fireball/"
 
   ml_dir = "/mnt/ams2/datasets/COMBINED_REPO/" + t_station_id + "/"
   resample_dir = "/mnt/ams2/datasets/COMBINED_REPO/" + t_station_id + "/resample_fireball/"
   station_dir = "/mnt/ams2/datasets/COMBINED_REPO/" + t_station_id + "/"
 
   if os.path.exists("all_samples.json") is False:
      os.system("cp /mnt/archive.allsky.tv/AMS1/ML/all_samples.json.gz .")
      os.system("gunzip all_samples.json.gz")
   temp = load_json_file("all_samples.json")
   fireballs = temp['meteors_fireballs']

   if os.path.exists(resample_dir) is False:
      os.makedirs(resample_dir)
   fb_dir = ml_dir + "meteors_fireballs/"
   #files = os.listdir(fb_dir)
   for fb in fireballs:
      if t_station_id + "_" not in fb:
         continue
      print("FB:", fb)
      station_id = fb.split("_")[0]
      roi_file = fb.replace(station_id + "_", "")
      day = roi_file[0:10]
      mdir = "/mnt/ams2/meteors/" + day + "/"
      #mdir = "Y://meteors/" + day + "/"
      stack_file = mdir + roi_file.replace("-ROI.jpg", "-stacked.jpg")
      video_file = stack_file.replace("-stacked.jpg", ".mp4")
      print("./stackVideo.py " + video_file)
      os.system("./stackVideo.py " + video_file)

      if "\\" in stack_file:
         stack_fn = roi_file.split("\\")[-1]
      else:
         stack_fn = roi_file.split("/")[-1]
      stack_fn = stack_fn.replace("-ROI.jpg", "-stacked.jpg")
      print("STACK:", mdir + stack_fn)
      img = cv2.imread(mdir + stack_fn)
      if img is None:
         print("IMG IS NONE?", mdir + stack_fn)
         continue
      img = cv2.resize(img,(640,360))

      if len(img.shape) > 2:
         gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
      else:
         gray = img
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
      avg_val = np.mean(gray)
      px_diff = max_val - avg_val
      px_fact = max_val / avg_val
      thresh_val = max_val * .65
      _, thresh_img = cv2.threshold(gray.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      thresh_img = cv2.dilate(thresh_img.copy(), None , iterations=4)

      if True:
         xs = []
         ys = []
         cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
         cnts = which_cnts(cnt_res)

         conts = []
         fn = 1
         objects = {}
         for (i,c) in enumerate(cnts):
            x,y,w,h = cv2.boundingRect(cnts[i])
            intensity = int(np.sum(gray[y:y+h,x:x+w]))
            px_avg = intensity / (w*h)
            object, objects = find_object(objects, fn,x, y, w, h, 100, 0, 0, None)
            if w >= 5 and h >= 5 :
               conts.append((x,y,w,h,intensity,px_avg))
               xs.append(x)
               xs.append(x+w)
               ys.append(y)
               ys.append(y+h)
            fn += 1
      
      show_img = img.copy()
      ddd = 0
      hdm_x = 1920 / img.shape[1]
      hdm_y = 1080 / img.shape[0]
      hd_img = cv2.resize(img, (1920,1080))
      for obj_id in objects:
         obj = objects[obj_id]
         print(objects[obj_id])
         xs = []
         ys = []
         all_cnts = []
         for i in range(0,len(obj['oxs'])):
            xs.append(obj['oxs'][i])
            xs.append(obj['oxs'][i] + obj['ows'][i])
            ys.append(obj['oys'][i])
            ys.append(obj['oys'][i] + obj['ohs'][i])

            min_x = min(xs)
            min_y = min(ys)
            max_x = max(xs)
            max_y = max(ys)

            
            size = (max_x - min_x) * (max_y - min_y)
            all_cnts.append((min_x,min_y,max_x,max_y,size))
         all_cnts = sorted(all_cnts, key=lambda x: (x[4]), reverse=True)
         #all_cnts = merge_cnts(all_cnts)
          
         for cnt in all_cnts:

            (min_x, min_y, max_x, max_y, size) = cnt
            min_x,min_y,max_x,max_y = bound_cnt(min_x,min_y,max_x,max_y,img)

            hd_min_x = int(min_x * hdm_x)
            hd_max_x = int(max_x * hdm_x)
            hd_min_y = int(min_y * hdm_y)
            hd_max_y = int(max_y * hdm_y)


            roi_img = img[min_y:max_y,min_x:max_x] 
            hd_roi_img = hd_img[hd_min_y:hd_max_y,hd_min_x:hd_max_x] 
            resample_file = stack_file.replace("-stacked.jpg", "-RESAMP-" + str(ddd) + ".jpg")
            hd_resample_file = stack_file.replace("-stacked.jpg", "-HDRESAMP-" + str(ddd) + ".jpg")

            resample_file = resample_file.split("/")[-1]
            hd_resample_file = hd_resample_file.split("/")[-1]
            #size = (max_x - min_x) * (max_y - min_y)
            predict_class = None
            if True:
                  #cv2.imshow('pepe', roi_img)
                  #cv2.waitKey(0)
               if t_station_id not in resample_file:
                  resample_file = t_station_id + "_" + resample_file
               print("X1:", min_x,min_y,max_x,max_y)
               print("WROTE", t_station_id, resample_dir + resample_file )
               if os.path.exists(resample_dir) is False:
                  os.makedirs(resample_dir)
               #cv2.imwrite(resample_dir + resample_file, roi_img)
               cv2.imwrite(resample_dir + hd_resample_file, hd_roi_img)
               
               try:
                  xxx = hd_roi_img.shape[:2]
               except:
                  if os.path.exists(resample_dir + hd_resample_file) is True:
                     os.remove(resample_dir + hd_resample_file)
                     continue

               if os.path.exists(resample_dir + hd_resample_file) is True:
                  
                  #print(resample_dir + resample_file)
                  try:
                     predict_class = predict_image(resample_dir + hd_resample_file , model)
                     print("P:", predict_class)
                     cv2.putText(show_img, predict_class, (min_x,max_y), cv2.FONT_HERSHEY_SIMPLEX, .3, (0, 0, 255), 1)
                  except:
                     print("BAd roi", resample_dir + hd_resample_file)
                     
                     if os.path.exists(resample_dir + resample_file) is True:
                         os.remove(resample_dir + resample_file  )
                     if os.path.exists(resample_dir + hd_resample_file) is True:
                         os.remove(resample_dir + hd_resample_file  )
               else:
                  print("BAD ROI?")
                  continue
            #try:
            #except:
            #   print("FAILED TO WRITE ROI FILE!", min_x,min_y,max_x,max_y, resample_dir + resample_file) 
            #   continue
            if predict_class is None:
               predict_class = predict_image(resample_dir + hd_resample_file , model)
            print("RES", resample_dir + resample_file)
            print("MAKE REC!",min_x,min_y,max_x,max_y)
            print("Class", predict_class)
            cv2.rectangle(show_img, (min_x,min_y), (max_x, max_y) , (255, 255, 255), 1)
            if "meteors" not in predict_class and predict_class is not None:
               l_resample_dir = resample_dir + predict_class + "/"
               new_file = l_resample_dir + resample_file
               hd_new_file = l_resample_dir + hd_resample_file
               if os.path.exists(l_resample_dir) is False:
                  os.makedirs(l_resample_dir)
               print("MOVE TO:", new_file)
               #os.rename(resample_dir + resample_file, new_file)
               os.rename(resample_dir + hd_resample_file, hd_new_file)
            ddd += 1

   # tar it up
   #cv2.imshow('pepe', show_img)
   #cv2.waitKey(0)
   tar_cmd = "tar -cvf " + station_dir + t_station_id + "_ML_RESAMPLE_FB.tar " + resample_dir + "*" 
   os.system(tar_cmd)
   arc_dir = "/mnt/archive.allsky.tv/" + t_station_id + "/ML/" 
   tar_cmd = "tar -cvf " + station_dir + t_station_id + "_ML_RESAMPLE_FB.tar *" 
   tar_file = station_dir + t_station_id + "_ML_RESAMPLE_FB.tar"
   os.system("gzip " + tar_file)
   os.system("cp " + tar_file + ".gz" + " " + arc_dir )
   print("cp " + tar_file + ".gz" + " " + arc_dir )


def group_objects(XS,YS):
   resp = ransac_outliers(XS,YS,"")
   (IN_XS,IN_YS,OUT_XS,OUT_YS,line_X,line_Y,line_y_ransac,inlier_mask,outlier_mask) = resp
   print("INXS", IN_XS)
   print("INYS", IN_YS)
   print("MINMAX", min(IN_XS),min(IN_YS),max(IN_XS),max(IN_YS))
   return(min(IN_XS),min(IN_YS),max(IN_XS),max(IN_YS))


def which_cnts(cnt_res):
   if len(cnt_res) == 3:
      (_, cnts, xx) = cnt_res
   elif len(cnt_res) == 2:
      (cnts, xx) = cnt_res
   return(cnts)

def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist

if sys.argv[1] == "resample":
   resample_fireballs()
if sys.argv[1] == "sort":
   sort_meteors_by_length()
