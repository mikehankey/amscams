from Classes.ASAI import AllSkyAI 
import subprocess
import shutil
import glob
import cv2
#from lib.PipeUtil import mfd_roi , load_json_file
from Lib.Utils import load_json_file, save_json_file
import os
import sys
ASAI = AllSkyAI()


# TEST THE METEOR YN DETECT. 
ASAI.check_update_install()

if len(sys.argv) == 1:
   print("NO ARGS PASSED IN!?")
#   wish = input("Do you want to run the command [M]enu or see the [H]elp list for supported arguments?")


ai_db_file = "ai_db.json"
if os.path.exists(ai_db_file) is True:
   ai_db = load_json_file(ai_db_file)
else:
   ai_db = {}

if len(sys.argv) > 1:
   run_label = sys.argv[1]
else:
   run_label = None


if True:



   ASAI.load_all_models()


   main_dir = "D:/MRH/learning/WORK/re_train/"
   review_dir = "D:/MRH/learning/WORK/review/"
   labels = os.listdir(main_dir)

   # start new process for each label type! 
   #for label in labels:
   #   if run_label is None:
   #      cmd = "python MeteorYN.py " + label + " "
   #      print(cmd)
         #os.system(cmd)
         #subprocess.Popen(["python", "MeteorYN.py", "label"]) 
         #exit()

   tc = 0
   if run_label is not None:
      labels = [run_label]

   for label in labels:
      roi_dir = "D:/MRH/learning/WORK/re_train/" + label + "/"
      roi_files = glob.glob(roi_dir + "*ROI.jpg") 
      for roi_file in roi_files:
         if roi_file in ai_db:
            print("SKIP DONE!")
            #continue
         if "\\" in roi_file:
            roi_file = roi_file.replace("\\", "/")
         roi_fn = roi_file.split("/")[-1]

         #img = cv2.imread(roi_file)
         #resp = ASAI.meteor_yn(roi_file, img)
         resp = ASAI.meteor_yn(roi_file)
         print(resp)
         confidence = resp['mc_confidence'] 

         print("CONFIDENCE:", confidence)
         if resp is None:
            print("BAD FILE???:", roi_file)
            continue
         resp['roi_file'] = roi_fn
         file1 = roi_file
         ai_db[roi_fn] = resp
         if resp['meteor_yn'] is True or resp['meteor_fireball_yn'] is True:
            if "meteor" not in label:
               print("DETECTED METEOR IN NON_METEOR DIR! MOVE IT OUT.")
               file2 = review_dir + "non_meteor_meteor/" + roi_fn
               os.rename(file1,file2)
         if resp['meteor_yn'] is False and resp['meteor_fireball_yn'] is False and "meteor" in label:
            print("FALSE METEOR INSIDE METEOR DIR. MOVE IT OUT.") 
            file2 = review_dir + "meteor_non_meteor/" + roi_fn
            os.rename(file1,file2)
         else:
            # copy to the high, mid or low confidence dirs.
            if confidence >= 90:
               file2 = file1.replace("re_train", "retrain_high")
            elif 60 < confidence < 90:
               file2 = file1.replace("re_train", "retrain_mid")
            else:
               file2 = file1.replace("re_train", "retrain_low")
            rt_dir = file2.replace(roi_fn, "")
            if os.path.exists(rt_dir) is False:
               os.makedirs(rt_dir)
            try:
               shutil.copyfile(file1, file2)
            except:
               print("PROBLEM!?")
               continue

         if tc % 1000 == 0:
            save_json_file(ai_db_file, ai_db)
         tc += 1
         print(label, resp)


# OLDER TESTS STILL IMPORTANT!
exit()
ASAI.reindex_meteors()
#exit()
ASAI.make_ai_summary()
exit()
model = ASAI.load_my_model()

if False:
   ai_missing = load_json_file(ASAI.ai_missing_file)
   for roi_file in ai_missing:
      roi_fn = roi_file.split("/")[-1]
      predicted_class = ASAI.predict_image(roi_file, model)
      ASAI.machine_data[roi_fn] = predicted_class
      print(predicted_class, roi_file)
   ASAI.save_files()
   exit()



print("MI:", len(ASAI.ai_meteor_index))
no_ai = 0
bad_roi = 0
new_predict = 0
new_roi = 0
missing_roi = 0
none_label = 0
ai_labels = 0
roi_missing = 0
missing_roi_and_red = 0
total_mi = len(ASAI.ai_meteor_index)
for row in ASAI.ai_meteor_index:
   (meteor_file, reduced, start_time, dur, ang_vel, ang_dist, hotspot, msm,mlabel,hlabel) = row

   if hlabel != "NONE":
      mlabel = hlabel
   if mlabel != "NONE":
      ai_labels += 1
   if mlabel == "NONE" : #and reduced == 1:
      none_label += 1
      print("NO AI?", no_ai, row, )
      no_ai += 1
      red_file = meteor_file.replace(".json", "-reduced.json")
      if "AMS" not in meteor_file:
         roi_file = ASAI.station_id + "_" + meteor_file.replace(".json", "-ROI.jpg")
      else:
         roi_file = meteor_file.replace(".json", "-ROI.jpg")
      date = meteor_file[0:10]
      mdir = "/mnt/ams2/meteors/" + date + "/" 
      msdir = "/mnt/ams2/METEOR_SCAN/" + date + "/" 

      if os.path.exists(msdir + roi_file) is True:
         test_img = cv2.imread(msdir + roi_file)
         if test_img is None:
            print("BAD ROI IMAGE!",  msdir + roi_file)
            predicted_class = "BAD_ROI"
            ASAI.machine_data[roi_file] = predicted_class
            bad_roi += 1
            roi_missing += 1
         else:
            predicted_class = ASAI.predict_image(msdir + roi_file, model)
            #print(meteor_file, predicted_class)
            print("PREDICT ROI FILE:", roi_file, predicted_class)
            ASAI.machine_data[roi_file] = predicted_class
            new_predict += 1

      elif os.path.exists(mdir + red_file):
         mjr = load_json_file(mdir + red_file)
         x1,y1,x2,y2 = mfd_roi(mjr['meteor_frame_data'])
         print("MFD:", len(mjr['meteor_frame_data']))
         print("X1:", x1,y1,x2,y2)
         roi_missing += 1
         new_roi += 1
      else:
         print("Could not find the ROI FILE OR THE RED FILE!", meteor_file)
         missing_roi_and_red += 1
         roi_missing += 1

print("BAD ROIS:", bad_roi) 
print("NEW PREDICT:", new_predict) 
print("NEW ROI:", new_roi) 
print("MISSING RED & ROI:", missing_roi_and_red) 
print("TOTAL AI MI:", total_mi) 
print("TOTAL NONE LABEL:", none_label) 
print("TOTAL AI LABELS:", ai_labels) 
print("ROI MISSING:", roi_missing) 

ASAI.save_files()
print("Saved machine data")
# scan un-scanned meteors


exit()
(img, img_gray, img_thresh, img_dilate, avg_val, max_val, thresh_val) = ASAI.ai_open_image("/mnt/ams2/meteors/2020_11_19/2020_11_19_00_09_00_000_010001-trim-0300-stacked.jpg")
img_dilate = cv2.resize(img_dilate,(1920,1080))
cnts = ASAI.get_contours(img_dilate)
for x,y,w,h in cnts:
   cv2.rectangle(img_dilate, (x,y), (x+w, y+h) , (255, 255, 255), 1)
cv2.imwrite("/mnt/ams2/test.jpg", img_dilate)

