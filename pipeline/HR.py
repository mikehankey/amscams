import cv2
import sys
import os
import json
from lib.PipeUtil import load_json_file, save_json_file

learn_yes = "F:/AI/DATASETS/NETWORK_PREV/METEORS/"
learn_no = "F:/AI/DATASETS/NETWORK_PREV/NO_METEORS/"



def load_day_from_obs_file(date, ev_review_file):
   review_data = load_json_file(ev_review_file)
   data = []
   c = 0
   for sdv in review_data:
      if isinstance(review_data[sdv], list) is True:
         print("RD:", review_data[sdv])
      else:
         print(review_data[sdv]['ai'])
         review_data[sdv]['ai']['fn'] = sdv
         conf =  review_data[sdv]['ai']['meteor_yn_confidence']
         if review_data[sdv]['ai']['meteor_yn_confidence'] > review_data[sdv]['ai']['meteor_fireball_yn_confidence']:
            conf =  review_data[sdv]['ai']['meteor_yn_confidence']
         else:
            conf =  review_data[sdv]['ai']['meteor_fireball_yn_confidence']
         if "meteor" in review_data[sdv]['ai']['mc_class'] and review_data[sdv]['ai']['mc_class_confidence'] > conf:
            conf = review_data[sdv]['ai']['mc_class_confidence']
         review_data[sdv]['ai']['conf'] = conf

         data.append(review_data[sdv]['ai'])

      c += 1
   return(data)

def load_day_from_dirs(date, ev_dir, ev_review_file):
   review_data = load_json_file(ev_review_file)
   yes_files = os.listdir(ev_dir + "OBS/METEOR")
   no_files = os.listdir(ev_dir + "OBS/NON_METEOR")
   all_data = []
   print(no_files)
   for ff in yes_files :
      fr = ff.split("AI")[0]
      fn = fr + ".mp4"
      if "AMS" in fn:
         st = fn.split("_")[0]
         fn_no_st = fn.replace(st + "_", "")
      if fn in review_data:
         print(fn, "YES!")
         data = review_data[fn]
      elif fn_no_st in review_data:
         print(fn_no_st, "YES!")
         data = review_data[fn_no_st]
      else:
         data = {}
         print(fn, fn_no_st, "NO!")

      if "ai" in data:
         conf =  data['ai']['meteor_yn_confidence']
         if data['ai']['meteor_yn_confidence'] > data['ai']['meteor_fireball_yn_confidence']:
            conf =  data['ai']['meteor_yn_confidence']
         else:
            conf =  data['ai']['meteor_fireball_yn_confidence']
         if "meteor" in data['ai']['mc_class'] and data['ai']['mc_class_confidence'] > conf:
            conf = data['ai']['mc_class_confidence']
         data['conf'] = conf
         data['loc'] = "METEOR"
         data['ff'] = ev_review_dir + "OBS/" + data['loc'] + "/" + ff

         all_data.append(data)

   for ff in no_files :
      fr = ff.split("AI")[0]
      fn = fr + ".mp4"
      if "AMS" in fn:
         st = fn.split("_")[0]
         fn_no_st = fn.replace(st + "_", "")

      if fn in review_data:
         print(fn, "YES!")
         data = review_data[fn]
      elif fn_no_st in review_data:
         print(fn_no_st, "YES!")
         data = review_data[fn_no_st]
      else:
         data = {}
         print(fn, fn_no_st, "NO!")

      if "ai" in data:
         conf =  data['ai']['meteor_yn_confidence']
         if data['ai']['meteor_yn_confidence'] > data['ai']['meteor_fireball_yn_confidence']:
            conf =  data['ai']['meteor_yn_confidence']
         else:
            conf =  data['ai']['meteor_fireball_yn_confidence']
         if "meteor" in data['ai']['mc_class'] and data['ai']['mc_class_confidence'] > conf:
            conf = data['ai']['mc_class_confidence']
         data['conf'] = conf
         data['loc'] = "METEOR"

          
         data['ff'] = ev_review_dir + "OBS/" + data['loc'] + "/" + ff
         all_data.append(data)

   return(sorted(all_data, key=lambda x: x['conf'], reverse=True)      )

obs_review_main = "/mnt/f/EVENTS/ALL_HUMAN_OBS.json"

if os.path.exists(obs_review_main) is True:
   obs_review = load_json_file(obs_review_main)
else:
   obs_review = {}

date = sys.argv[1]
y,m,d = date.split("_")
ev_review_dir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" 
ev_review_file = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" + date + "_OBS_REVIEWS.json"

data = load_day_from_dirs(date, ev_review_dir, ev_review_file)
print("FFF")
for d in data:
   print("DDD", d.keys())
   if os.path.exists(d['ff']):
      img = cv2.imread(d['ff'])
      img = cv2.resize(img, (500,500))
      cv2.imshow('ppp', img)
      cv2.waitKey(0)
   else:
      print(d['ff'])
