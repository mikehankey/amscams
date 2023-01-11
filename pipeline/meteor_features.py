from sklearn.cluster import KMeans
import os
import math
import cv2
from numpy import unique
from numpy import where
#import matplotlib.pyplot as plt
#from mpl_toolkits.mplot3d import Axes3D
import sys
import numpy as np
#%matplotlib inline
from sklearn import datasets
from lib.PipeUtil import load_json_file, save_json_file, cfe
from RMS.Math import angularSeparation
from lib.PipeDetect import gap_test
from Classes.Filters import Filters
import glob
from sklearn.mixture import GaussianMixture 
from lib.FFFuncs import  resize_video, crop_video
FLT = Filters()

def mfd_roi(mjr):
   xs = [row[2] for row in mjr['meteor_frame_data']]
   ys = [row[3] for row in mjr['meteor_frame_data']]
   ws = [row[4] for row in mjr['meteor_frame_data']]
   hs = [row[5] for row in mjr['meteor_frame_data']]
   if len(xs) == 0 or len(ys) == 0:
      return(0,1920,0,180)
   x1 = min(xs)
   x1 -= int(x1*.1)
   x2 = max(xs) + max(ws)
   x2 += int(x2*.1)
   y1 = min(ys) 
   y1 -= int(y1*.1)
   y2 = max(ys) + max(hs)
   y2 += int(y2*.1)
   if x2 - x1 > y2 - y1:
      size = x2 - x1
   else:
      size = y2 - y1
   mx = int((x1 + x2) / 2)
   my = int((y1 + y2) / 2)
   x1 = int(mx - (size/2))
   x2 = int(mx + (size/2))
   y1 = int(my - (size/2))
   y2 = int(my + (size/2))
   if x1 < 0:
      x1 = 0
      x2 = size
   if y1 < 0:
      y1 = 0
      y2 = size
   if x2 > 1920:
      x2 = 1919 
      x1 = 1919 - size
   if y2 > 1080:
      y2 = 1080 
      y1 = 1080 - size

   return(x1,y1,x2,y2)

def make_image(mfn):
   div_id = mfn.replace(".json", "")

   day = mfn[0:10]
   mvfile = "/METEOR_SCAN/" + day + "/" + mfn.replace(".json", "-ROI.jpg")
   html = """
   <div class="example-popover" style='float: left; padding: 10px'>
   <img data-id=""" + div_id + """ class="show_prev" div_id='img_""" + mfn.replace(".json", "") + """' onmouseover="hover(this);" onmouseout="unhover(this);" width=100 height=100 src=""" + mvfile + """><br>
   <caption id='""" + div_id + """'>
   <!--<button type="button" class="btn btn-primary show_prev" data-toggle="popover" data-id='""" + mfn + """'>X</button>-->

 
   </caption>
   </div>
   """
   return(html)

def make_roi_video(mjf):
   video_file = "/mnt/ams2/meteors/" + mjf[0:10] + "/" + mjf.replace(".json", ".mp4")
   video_file_360p = "/mnt/ams2/meteors/" + mjf[0:10] + "/" + mjf.replace(".json", "-360p.mp4")
   meteor_file = "/mnt/ams2/meteors/" + mjf[0:10] + "/" + mjf
   red_file = "/mnt/ams2/meteors/" + mjf[0:10] + "/" + mjf.replace(".json", "-reduced.json")
   mj = load_json_file(meteor_file)
   mjr = load_json_file(red_file)
   if "human_roi" in mj:
      x1,y1,x2,y2 = mj['human_roi']
   else:
      hdm_x = 1920/640
      hdm_y = 1080/360
      x1,y1,x2,y2= mfd_roi(mjr)
      x1,y1,x2,y2 = int(x1/hdm_x),int(y1/hdm_y),int(x2/hdm_x),int(y2/hdm_y)

   cw = x2 - x1
   ch = y2 - y1
   crop_box = [x1,y1,cw,ch]
   resize_video(video_file, video_file_360p, 640, 360, 28)
   final_sd_crop_vid = video_file_360p.replace("-360p.mp4", "-ROI.mp4")
   crop_video(video_file_360p, final_sd_crop_vid, crop_box)
   #print(video_file_360p, final_sd_crop_vid, crop_box)

def make_summary_html():
   if cfe("meteor_features_dict.json") == 1:
      features_dict = load_json_file("meteor_features_dict.json")
   main_stats = {}
   main_stats['total_reduced_meteors'] = len(features_dict.keys())
   main_json_missing = {}
   good_json = {}
   for key in features_dict:
      mfn = "/mnt/ams2/meteors/" + key[0:10] + "/" + key 
      if cfe(mfn) == 0:
         main_json_missing[mfn] = 1
      else:
         good_json[mfn] = 1
         features_obj = features_dict[key]['features_obj']
         if "hc" not in features_obj or "mse" not in features_obj:
            mj = load_json_file(mfn)
            if "hc" in mj:
               hc = mj['hc']
            if "multi_station_event" in mj:
               mse = mj['multi_station_event']['event_id']
             


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
   mjr = load_json_file(mdir + mjrf)
   roi_file = mdir + mjf.replace(".json", "-ROI.jpg")
   roi_file = roi_file.replace("/meteors/", "/METEOR_SCAN/")
   if "meteor_frame_data" in mjr:
      if len(mjr['meteor_frame_data']) < 1:
         return(None,None) 
      #(dt, frn, x, y, w, h, oint, ra, dec, az, el) = row
      if len(mjr['meteor_frame_data']) > 1:
         x1,y1,x2,y2= mfd_roi(mjr)
         x1,y1,x2,y2 = int(x1/hdm_x),int(y1/hdm_y),int(x2/hdm_x),int(y2/hdm_y)
         if x1 < 0:
            x1 =0
         if y1 < 0:
            y1 =0
         if y2 >= img.shape[0]:
            y2 = img.shape[0]-1
         if x2 >= img.shape[1]:
            x2 = img.shape[1]-1

         #print(x1,y1,x2,y2)
         #print(mjr['meteor_frame_data'])
         durf = len(mjr['meteor_frame_data'])
         durt = durf / 25
         croi_img = cimg[y1:y2,x1:x2]
         roi_img =  cv2.cvtColor(croi_img, cv2.COLOR_BGR2GRAY)
         cv2.imwrite(roi_file, croi_img)
         #print(roi_file)
         #print("ROI SHAPE:", croi_img.shape)
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
         features = [float(ang_vel), ran_perc,avg_px,max_val,avg_max_diff,green_max,blue_max,red_max] #, peak_times, ran_perc, max(oys)] #,float(ang_vel),float(max_int),float(min_int),float(peak_times),float(ran_perc),float(dc_perc),float(gap_test_info['total_gaps']),float(gap_test_info['gap_events']),float(min(oys)),float(max(oys))]
      #features=[float(max_int), float(durt), float(ang_vel)]
         features_obj = {}
         features_obj['ang_vel'] = float(ang_vel)
         features_obj['ran_perc'] = float(ran_perc)
         features_obj['avg_px'] = float(avg_px)
         features_obj['max_val'] = float(max_val)
         features_obj['avg_max_diff'] = float(avg_max_diff)
         features_obj['green_max'] = float(green_max)
         features_obj['blue_max'] = float(blue_max)
         features_obj['red_max'] = float(red_max)
         features_obj['peak_times'] = float(peak_times)
         features_obj['max_y'] = float(max(oys))
         features_obj['min_y'] = float(min(oys))
         features_obj['max_int'] = float(max_int)
         features_obj['min_int'] = float(min_int)
         features_obj['dc_perc'] = float(dc_perc)
         features_obj['total_gaps'] = float(gap_test_info['total_gaps'])
         features_obj['gap_events'] = float(gap_test_info['gap_events'])
         return(features, features_obj)
   return(None,None)


# START HERE!


make_summary_html()
exit()
# Build meteor feature data
feature_names = ["Duration Time", "Angular Separation", "Angular Velocity", "Max Int", "Min Int", "Peak Factor", "Ransac Percentage", "Direction Perc", "Total Gaps", "Gap Events", "Min Y", "Max Y"]

all_dirs = glob.glob("/mnt/ams2/meteors/" + sys.argv[1][0:8] + "*")
#print("/mnt/ams2/meteors/" + sys.argv[1][0:8] + "*")
all_features = []
if cfe("meteor_features_dict.json") == 1:
   features_dict = load_json_file("meteor_features_dict.json")
else:
   features_dict = {}
these_files = []
for md in sorted(all_dirs, reverse=True):
   tday = md.split("/")[-1]
   mfiles = sorted(glob.glob("/mnt/ams2/meteors/" + tday + "/*red*.json"),reverse=True)
   for mf in mfiles:
      mfn = mf.split("/")[-1]
      mfn = mfn.replace("-reduced.json", ".json")
      these_files.append(mfn)

bad_files = {}
for mfn in these_files:
   ms_dir = "/mnt/ams2/METEOR_SCAN/" + mfn[0:10] + "/" 
   if cfe(ms_dir, 1) == 0:
      os.makedirs(ms_dir)
   roi_file = ms_dir + mfn.replace(".json", "-ROI.jpg")
   roi_vid = ms_dir + mfn.replace(".json", "-ROI.mp4")
   vid_360p = ms_dir + mfn.replace(".json", "-ROI.mp4")
   if cfe(roi_vid) == 0 or cfe(vid_360p) == 0:
      make_roi_video(mfn)
   if mfn not in features_dict or cfe(roi_file) == 0:
      features,features_obj = get_met_data(mfn)
      
      if features is None:
         bad_files[mfn] = 1
         continue
      for f in features:
         if f is None or math.isnan(f) is True:
            bad_files[mfn] = 1
            continue
      features_dict[mfn] = {}
      features_dict[mfn]['features'] = features
      features_dict[mfn]['features_obj'] = features_obj

   else:
      features = features_dict[mfn]['features']
      for f in features:
         if f is None or math.isnan(f) is True:
            bad_files[mfn] = 1
            continue

      features_obj = features_dict[mfn]['features_obj']
   all_features.append((mfn,features))

feature_data = []
all_files = []
for mfn in bad_files:
   if mfn in features_dict:
      del(features_dict[mfn])
for key in features_dict:
   all_files.append(key)
   #feature_data.append((af[1][0],af[1][2]))
   if features_dict[key]['features'] is not None:
      feature_data.append(features_dict[key]['features'])
all_files = np.asarray(all_files)

save_json_file("meteor_features.json", all_features)
save_json_file("meteor_features_dict.json", features_dict)

# MET DETECT FEATURES
#feature_names = ["Duration Time", "Angular Separation", "Angular Velocity", "Max Int", "Min Int", "Peak Factor", "Ransac Percentage", "Direction Perc", "Total Gaps", "Gap Events", "Min Y", "Max Y"]

from sklearn.cluster import KMeans
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
#%matplotlib inline
from sklearn import datasets

#Iris Dataset
#iris = datasets.load_iris()

#$iris = datasets.load_iris()
#X = iris.data
#print(type(X))
X = np.asarray(feature_data) 
#X = X.astype(float)

if False:
   km = KMeans(n_clusters=3)
   km.fit(X)
   km.predict(X)
   labels = km.labels_
#Plotting
#feature_names = ["Duration Time", "Angular Separation", "Angular Velocity", "Max Int", "Min Int", "Peak Factor", "Ransac Percentage", "Direction Perc", "Total Gaps", "Gap Events", "Min Y", "Max Y"]
   fig = plt.figure(1, figsize=(8,8))
   ax = Axes3D(fig, rect=[0, 0, 0.95, 1], elev=0, azim=0)
   ax.scatter(X[:, 2], X[:, 0], X[:, 6],
          c=labels.astype(np.float), edgecolor="k", s=50)
   ax.set_xlabel(feature_names[2])
   ax.set_ylabel(feature_names[0])
   ax.set_zlabel(feature_names[6])
   plt.title("K Means", fontsize=14)#KMeans
   plt.savefig("/mnt/ams2/test.png")

model = GaussianMixture(n_components=12)
# fit model and predict clusters

model.fit(X)
yhat = model.fit_predict(X)
# retrieve unique clusters
clusters = unique(yhat)
# create scatter plot for samples from each cluster
html = {}
fig = plt.figure(1, figsize=(8,8))
fp = open("allsky.com/header.html")
html_head = ""
for line in fp:
   html_head += line
html_head += """
<script>
function hover(element) {
/*
  new_src = element.getAttribute('src').replace("-ROI.jpg", "-stacked.jpg")
  new_src = new_src.replace("/METEOR_SCAN/", "/meteors/")
  element.setAttribute('src', new_src);
  element.setAttribute('width', 320);
  element.setAttribute('height', 180);
  */
}

function unhover(element) {
/*
  new_src = element.getAttribute('src').replace("-stacked.jpg", "-ROI.jpg")
  new_src = new_src.replace("/meteors/", "/METEOR_SCAN/")
  element.setAttribute('src', new_src);
  element.setAttribute('width', 100);
  element.setAttribute('height', 100);
  */
}
</script>

"""

# write 1 page per group
# write 1 page sorted by intensity
# write 1 page sorted by time

"""
OUTPUT STRUCTURE FOR LEARNING HTML

LEARNING/html/index.html
   <h1>Machine Learning - Meteors</h1>
   XXX Total Meteors Inside AMSXX Since YYYY_MM_DD
   XXX Supervised Training
      XXX Multi Station Confirmed
      XXX Human Confirmed
   XXX Unsupervised Training 
      Group 1
      Group 2
      Group 3
      Group 4

   <h1>Machine Learning - Non Meteors</h1>

   LEARNING/html/meteors/unsupervised/
                         us-type1-grp1
                         us-type1-grp2
                         us-type1-grp3
"""

for cluster in clusters:
   # get row indexes for samples with this cluster
   html[cluster] = ""
   row_ix = where(yhat == cluster)
   # create scatter of these samples
   plt.scatter(X[row_ix, 0], X[row_ix, 1], marker='o')
   for mfn in all_files[row_ix]:
      html[cluster] += make_image(mfn)
plt.savefig("/mnt/ams2/test3.png")
out = open("/mnt/ams2/test.html", "w")
out.write(html_head )
for cluster in html:
   out.write("<div style='clear:both'></div>")
   out.write("<div style='border: 1px black solid; margin-left: 100px; margin-right: 100px; padding: 20px'>")
   out.write("<h1>" + str(cluster) + "</h1>") 

   out.write(html[cluster])
   out.write("<div style='clear:both'></div>")
   out.write("</div></body></html>")
out.close()
print("ALL FILES:", len(all_files))
print("FEATURE DATA:", len(feature_data))
