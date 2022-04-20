import cv2
import numpy as np
import sys
import os
import json
from lib.PipeUtil import load_json_file, save_json_file
from lib.PipeVideo import load_frames_simple
from Classes.ASAI import AllSkyAI
import random
ASAI = AllSkyAI()
ASAI.load_all_models()

import matplotlib.pyplot as plt

learn_yes = "/mnt/f/AI/DATASETS/NETWORK_PREV/METEOR/"
learn_no = "/mnt/f/AI/DATASETS/NETWORK_PREV/NON_METEOR/"
final_yes = "/mnt/f/AI/DATASETS/NETWORK_PREV_FINAL/METEOR/"
final_no = "/mnt/f/AI/DATASETS/NETWORK_PREV_FINAL/NON_METEOR/"
if os.path.exists(final_yes) is False:
   os.makedirs(final_yes)
if os.path.exists(final_no) is False:
   os.makedirs(final_no)

def clean_repo(rdir):
   files = os.listdir(rdir)
   c = 0
   for ff in files:
      try:
         img = cv2.imread(rdir + ff)
         h,w = img.shape[:2]
         if h != w:
            print("REMOVE!", h,w)
            os.remove(rdir + ff)
      except:
         os.remove(rdir + ff)
         print("REMOVE BAD!")
      c+= 1
      if c % 100 == 0:
         print("Checked ", c)
   

def verify_video(ai_file, stack_img=None, roi=None):
   if roi is not None:
      x1,y1,x2,y2 = roi
   root_fn = ai_file.split("AI")[0]
   local_jpg_found = False 
   local_mp4_found = False 
   if "AMS" in root_fn:
      st = root_fn.split("_")[0]
      root_fn = root_fn.replace(st + "_", "")
   date = root_fn[0:10]
   y,m,d = date.split("_")
   evdir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/OBS/" 
   prev_jpg = evdir + root_fn + "-prev.jpg"
   if os.path.exists(prev_jpg):
      print("FOUND:", prev_jpg)
      local_jpg_found = True 
   else:
      prev_jpg = evdir + st + "_" + root_fn + "-prev.jpg"
      if os.path.exists(prev_jpg):
         local_jpg_found = True 
         print("FOUND:", prev_jpg)
   if local_jpg_found is True :
      local_mp4 = prev_jpg.replace("-prev.jpg", "-180p.mp4")
      cloud_mp4 = local_mp4.split("/")[-1]
      if "AMS" not in cloud_mp4:
         cloud_mp4 = st + "_" + cloud_mp4
      cloud_mp4 = "/mnt/archive.allsky.tv/" + st + "/METEORS/" + y + "/" + date + "/" + cloud_mp4

      if os.path.exists(local_mp4) is True :
         local_mp4_found = True
      if os.path.exists(cloud_mp4) is True and local_mp4_found is False:
         cmd = "cp " + cloud_mp4 + " " + local_mp4
         print(cmd)
      print(cloud_mp4) 
      frames = load_frames_simple(cloud_mp4)
      go = True 
      crop_frames = []
      while go is True:
         for fr in frames:
            fr = cv2.resize(fr,(640,360))
            #desc = "HI"
            #cv2.putText(fr, desc ,  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 1)
            roi_img = fr[y1:y2,x1:x2]
            crop_frames.append(roi_img)
            roi_img = cv2.resize(roi_img, (360,360))
            cv2.imshow('pepe', roi_img)


            cv2.imshow('pepe2', fr)
            cv2.waitKey(50)

         desc = "LABEL OBJECT : (m)eteor (n)on-meteor"
         desc2 = "Any key to re-play video. (q) to (q)uit."
         cv2.rectangle(fr, (x1,y1), (x2, y2) , (255, 255, 255), 1)
         cv2.putText(fr, desc ,  (10,180), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)
         cv2.putText(fr, desc2 ,  (10,220), cv2.FONT_HERSHEY_SIMPLEX, .8, (255,255,255), 1)

         cv2.imshow('pepe2', stack_img)
         key = cv2.waitKey(0)
         print("KEY:", key)
         if key == 113 or key == 27:
            # quit
            exit()
         if key == 110 or key == 109:
            go = False
            break
   #analyze_crop_frames(crop_frames)      
   return(key)

def analyze_crop_frames(crop_frames):
   med = np.median(crop_frames)
   bps = []
   for fr in crop_frames:
      sub= cv2.subtract(fr,med)
      sub = cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
      bp = np.sum(max_val)
      #sub = cv2.resize(sub,(360,360))
      bps.append(bp)
      #cv2.imshow('pepe', sub)
      #cv2.waitKey(30)

   avg_bp = np.mean(bps[:-1])
   c = 0
   net_bps = []
   cs = [] 
   for bp in bps[:-1]:
      net_bp = bp - avg_bp
      if net_bp < 0:
         net_bp = 0
      net_bps.append(net_bp)
      cs.append(c)
      print("BP:", c, net_bp)
      c += 1
   plt.scatter(cs, net_bps)
   plt.show()


def build_prev_meteor_or_star():
   limit = 10000
   star_src = "/mnt/f/AI/DATASETS/AA_SOURCE/moving_objects/stars/"
   meteor_src = "/mnt/f/AI/DATASETS/AA_SOURCE/moving_objects/meteor/"
   out_dir = "/mnt/f/AI/DATASETS/METEOR_OR_STAR/"
   if os.path.exists(out_dir + "STARS/") is False:
      os.makedirs(out_dir + "STARS/") 
   if os.path.exists(out_dir + "METEORS/") is False:
      os.makedirs(out_dir + "METEORS/") 

   stars = os.listdir(star_src)
   mets = os.listdir(meteor_src)
   random.shuffle(stars)
   random.shuffle(mets)
   for i in range(0, limit):
      fn = stars[i]
      star_img = cv2.imread(star_src + fn)
      star_img = cv2.resize(star_img, (38,38))
      star_img = cv2.resize(star_img, (224,224))
      star_img = cv2.resize(star_img, (38,38))
      ofile = out_dir + "STARS/" + fn 
      if star_img.shape[0] == star_img.shape[1]:
         cv2.imwrite(ofile, star_img)
   for i in range(0, limit):
      fn = mets[i]
      star_img = cv2.imread(meteor_src + fn)
      star_img = cv2.resize(star_img, (38,38))
      star_img = cv2.resize(star_img, (224,224))
      star_img = cv2.resize(star_img, (38,38))
      ofile = out_dir + "METEORS/" + fn 
      if star_img.shape[0] == star_img.shape[1]:
         cv2.imwrite(ofile, star_img)



def build_prev_repo_from_yn():
   limit = 116000
   yes_fb_dir = "/mnt/f/AI/DATASETS/FIREBALL_YN/fireball/"
   yes_dir = "/mnt/f/AI/DATASETS/METEOR_YN/meteors/"
   no_dir = "/mnt/f/AI/DATASETS/METEOR_YN/non_meteors/"
   yes_files = os.listdir(yes_dir)
   no_files = os.listdir(no_dir)

   fireballs = os.listdir(yes_fb_dir)
   for fb in fireballs:
      ofile = final_yes + fb 
      if os.path.exists(ofile) is False:
         print(yes_fb_dir + fb)
         yes_img = cv2.imread(yes_fb_dir + fb)
         yes_img = cv2.resize(yes_img, (38,38))
         yes_img = cv2.resize(yes_img, (224,224))
         yes_img = cv2.resize(yes_img, (38,38))
         if yes_img.shape[0] == yes_img.shape[1]:
            cv2.imwrite(ofile, yes_img)


   final_mets = os.listdir(final_yes)
   final_non_mets = os.listdir(final_no)

   mets_needed = limit - len(final_mets) 
   non_mets_needed = limit - len(final_non_mets) 
   random.shuffle(yes_files)
   random.shuffle(no_files)
   if non_mets_needed < 0:
      non_mets_needed = 0
   if mets_needed < 0:
      mets_needed = 0
   print("FINAL METS:", len(final_mets))
   print("FINAL NON METS:", len(final_non_mets))
   print("METS NEEDED:", mets_needed)
   print("NON METS NEEDED:", non_mets_needed)
   for i in range(0, mets_needed):
      yes_img = cv2.imread(yes_dir + yes_files[i])
      yes_img = cv2.resize(yes_img, (38,38))
      yes_img = cv2.resize(yes_img, (224,224))
      yes_img = cv2.resize(yes_img, (38,38))
      if yes_img.shape[0] == yes_img.shape[1]:
         cv2.imwrite(final_yes+ yes_files[i], yes_img)
         print("saving:", final_yes + yes_files[i])

   for i in range(0, non_mets_needed):
      no_img = cv2.imread(no_dir + no_files[i])
      no_img = cv2.resize(no_img, (38,38))
      no_img = cv2.resize(no_img, (224,224))
      no_img = cv2.resize(no_img, (38,38))
      if no_img.shape[0] == no_img.shape[1]:
         cv2.imwrite(final_no+ no_files[i], no_img)
      print("saving:", final_no+ no_files[i])


def build_prev_repo():
   ai_data_file = "AI_DATA.json"
   ai_data = load_json_file(ai_data_file)
   repo_dir = "/mnt/f/AI/DATASETS/NETWORK_PREV/"
   mdirs = []
   nmdirs = []
   meteors = []
   non_meteors = []
   files = os.listdir(repo_dir + "METEOR/")
   for ff in files:
      if os.path.isdir(repo_dir + "METEOR/" + ff) is True:
         mdirs.append(repo_dir + "METEOR/" + ff + "/")
   files = os.listdir(repo_dir + "NON_METEOR/")
   for ff in files:
      if os.path.isdir(repo_dir + "NON_METEOR/" + ff) is True:
         nmdirs.append(repo_dir + "NON_METEOR/" + ff + "/")

   for mdir in mdirs:
      mfiles = os.listdir(mdir)
      for mfile in mfiles:
         meteors.append(mdir + mfile)
   for nmdir in nmdirs:
      nmfiles = os.listdir(nmdir)
      for nmfile in nmfiles:
         non_meteors.append(nmdir + nmfile)


   missing_ai = 0
   have_ai = 0
   ais = []
   good_non = []
   good_met = []
 
   for mfile in non_meteors:
      mfn = mfile.split("/")[-1]
      if "ai" in ai_data[mfn]:
         ai = ai_data[mfn]['ai']
         mc = ai['meteor_yn_confidence']
         if mc < 10:
            good_non.append(mfile)

   for mfile in meteors:
      mfn = mfile.split("/")[-1]
      if "ai" in ai_data[mfn]:
         ai = ai_data[mfn]['ai']
         mc = ai['meteor_yn_confidence']
         if mc > 90:
            good_met.append(mfile)
   print("BEST MET:", len(good_met))
   print("BEST NON:", len(good_non))

   for ifile in good_non[0:1300]:
      print(ifile)
      img = cv2.imread(ifile)
      cmd = "cp " + ifile + " " + final_no
      os.system(cmd)
      cv2.imshow('pepe', img)
      cv2.waitKey(50)


   random.shuffle(good_met)
   for ifile in good_met[0:1300]:
      print(ifile)
      img = cv2.imread(ifile)
      cmd = "cp " + ifile + " " + final_yes
      os.system(cmd)
      cv2.imshow('pepe', img)
      cv2.waitKey(50)

   exit()

   for mfile in non_meteors:
      go = False
      mfile = mfile.replace("\\", "/")
      mfn = mfile.split("/")[-1]
      if mfn not in ai_data:
         go = True

         ai_data[mfn] = {}

      if "ai" not in ai_data[mfn]:
         go = True
      else:
         if "meteor_yn" not in ai_data[mfn]['ai']:
            go = True

      if go is True:
         tfile = "temp.jpg"
         img = cv2.imread(mfile)
         roi_img_1080p_224 = cv2.resize(img,(224,224))

         resp = ASAI.meteor_yn(tfile, None, roi_img_1080p_224)
         ai_data[mfn]['ai'] = resp
         ai = resp
         missing_ai += 1
      else :
         ai = ai_data[mfn]['ai']
         if "human_data" in ai_data[mfn]:
            ai['human_data'] = ai_data[mfn]['human_data']
         have_ai += 1

      ai['mfile'] = mfile
      ais.append(ai)

   ais = sorted(ais, key=lambda x: x['meteor_yn_confidence'])
   save_json_file(ai_data_file, ai_data)
   for ai in ais:

      if "human_data" in ai:
         hd = ai['human_data']
      else:
         hd = ""
      if "NON_METEOR" in ai['mfile']:
         rtype = "NON_METEOR"
      else:
         rtype = "METEOR"

      if os.path.exists(ai['mfile']) is True:
         mfn = ai['mfile'].split("/")[-1]
         img = cv2.imread(ai['mfile'])
         print(ai['mfile'], ai['meteor_yn_confidence'], hd)
         cv2.imshow('pepe', img)
         if "human_data" in ai:
            print("HUMAN DATA EXISTS ALREADY!", ai['human_data'])
            key = cv2.waitKey(30)
         else:
            key = cv2.waitKey(0)
         print("KEY", key)
         
         if key == 109:
            # confirmed meteor
            ai['human_data'] = "METEOR"
            if mfn in ai_data:
               ai_data[mfn]['human_data'] = "METEOR"
               print("SAVING HUMAN DATA FOR ", mfn, "METEOR")
            if rtype == "NON_METEOR":
               cmd = "mv " + ai['mfile'] + " " + learn_yes + ff
               print(cmd)
               os.system(cmd)

         elif key == 110:
            # confirmed NON meteor
            ai['human_data'] = "NON_METEOR"
            if mfn in ai_data:
               print("SAVING HUMAN DATA FOR ", mfn, "NON_METEOR")
               ai_data[mfn]['human_data'] = "NON_METEOR"
            if rtype == "METEOR":
               cmd = "mv " + ai['mfile'] + " " + learn_no + ff
               print(cmd)
               os.system(cmd)

         elif key == 115:
            save_json_file(ai_data_file, ai_data)
         elif key == 113 or key == 27:
            save_json_file(ai_data_file, ai_data)
            exit()


   #print(len(non_meteors))


def load_imgs_from_dir(in_dir):
   cc = 0
   ai_data_file = "AI_DATA.json"
   if os.path.exists(ai_data_file) is False:
      ai_data = {}
   else:
      print(ai_data_file)
      ai_data = load_json_file(ai_data_file)
   #print("AI DATA KEYS:", ai_data.keys())

   if "NON_METEOR" in in_dir:
      rtype = "NON_METEOR"
   else:
      rtype = "METEOR"
   files = os.listdir(in_dir)
   total = len(files)
   hdm_x = 1920 / 640
   hdm_y = 1080 / 360
   for ff in files:
      if "jpg" not in ff:
         continue
      cc += 1
      root_fn = ff.split("AI")[0]
      extra = ff.split("AI_")[1].replace(".jpg", "")
      x1,y1,x2,y2 = extra.split("_")
      x1 = int(int(x1)/hdm_x)
      x2 = int(int(x2)/hdm_x)
      y1 = int(int(y1)/hdm_y)
      y2 = int(int(y2)/hdm_y)
      #x1,y1,x2,y2 = x1*hdm_x,y1*hdm_y,x2*hdm_x,y2*hdm_y
      print(hdm_x) 
      print("EX", x1,y1,x2,y2)
      if "AMS" in root_fn:
         st = root_fn.split("_")[0]
         root_fn = root_fn.replace(st + "_", "")
      print("ROOT:", root_fn )
      date = root_fn[0:10]
      y,m,d = date.split("_")
      ofile = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/OBS/" + root_fn + "-prev.jpg"
      if os.path.exists(ofile) is True:
         oimg = cv2.imread(ofile)
         oimg = cv2.resize(oimg,(640,360))
         desc = "LABEL OBJECT : (m)eteor (n)on-meteor"
         desc2 = "or (p)play video any key to skip"
         cv2.rectangle(oimg, (x1,y1), (x2, y2) , (255, 255, 255), 1)
         color = [255,255,255]
         cv2.putText(oimg, desc ,  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 1)
         cv2.putText(oimg, desc2 ,  (10,50), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 1)
         cv2.imshow('pepe2', oimg)
      else:
         print("MISSING:", ofile)
      #print("ROOTFN/date:", root_fn, date)
      print("RTYPE:", rtype)
      if ff not in ai_data:
         print("FF NOT FOUND IN AI DATA YET!", ff)
         ai_data[ff] = {}
      else:
         print("FF IS FOUND IN AI",ff)
         if "human_data" in ai_data[ff]:
            print("HUMAN DATA FOUND!")
            img = cv2.imread(in_dir + ff)

            img = cv2.resize(img, (360,360))
            cv2.imshow('pepe', img)
            cv2.waitKey(30)
           
            if rtype == "METEOR" and ai_data[ff]['human_data'] == "NON_METEOR":
               cmd = "mv " + in_dir + ff + " " + learn_no + ff
               print(cmd)
               os.system(cmd)
            if rtype == "NON_METEOR" and ai_data[ff]['human_data'] == "METEOR":
               cmd = "mv " + in_dir + ff + " " + learn_yes + ff
               print(cmd)
               os.system(cmd)

            continue
      print("TRY IMG", in_dir + ff)
      img = cv2.imread(in_dir + ff)
      #try:
      if True:
         tfile = "temp.jpg"
         roi_img_1080p_224 = cv2.resize(img,(224,224))
         if "ai" not in ai_data[ff]:
            resp = ASAI.meteor_yn(tfile, None, roi_img_1080p_224)
            ai_data[ff]['ai'] = resp
         else:
            resp = ai_data[ff]['ai']
         img = cv2.resize(img, (360,360))


         print(ff, img.shape)
         if resp['meteor_yn_confidence'] >= resp['meteor_fireball_yn_confidence']: 
            meteor_conf = resp['meteor_yn_confidence']
         else:
            meteor_conf = resp['meteor_fireball_yn_confidence']

         desc = resp['mc_class'] + " " + str(int(resp['mc_class_confidence'])) + " " + str(int(meteor_conf)) + "% METEOR"
         if meteor_conf > 50:
            color = (0,255,0)
         else:
            color = (0,0,255)

         cv2.putText(img, desc ,  (10,20), cv2.FONT_HERSHEY_SIMPLEX, .6, color, 1)
         cv2.imshow('pepe', img)
     
         

         key = ""
         if rtype == "NON_METEOR" and meteor_conf > 10:
            # non-meteor that needs to be reviewed
            key = cv2.waitKey(0)
         if rtype == "METEOR" and meteor_conf < 99 :
            # meteor that needs to be reviewed
            key = cv2.waitKey(0)


         print("KEY", key)

         if key == 101 or key == 112:
            # (e)xamine

            key = verify_video(ff, oimg, (x1,y1,x2,y2))

         print("KEY", key)
         if key == 109:
            # confirmed meteor
            ai_data[ff]['human_data'] = "METEOR"
            if rtype == "NON_METEOR":
               cmd = "mv " + in_dir + ff + " " + learn_no + ff
               print(cmd)
               os.system(cmd)
         elif key == 110:
            # confirmed NON meteor
            ai_data[ff]['human_data'] = "NON_METEOR"
            if rtype == "METEOR":
               cmd = "mv " + in_dir + ff + " " + learn_no + ff
               print(cmd)
               os.system(cmd)
         elif key == 115:
            save_json_file(ai_data_file, ai_data)
         elif key == 107 or key == 27:
            save_json_file(ai_data_file, ai_data)
            exit()

         print(cc, total, key)
      #except:
      #   print("BAD IMG")
      save_json_file(ai_data_file, ai_data)
   print("ALL DONE", total)

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
   yes_files = os.listdir(learn_yes)
   no_files = os.listdir(learn_no)
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

#date = sys.argv[1]
#y,m,d = date.split("_")
#ev_review_dir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" 
#ev_review_file = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/" + date + "_OBS_REVIEWS.json"


#clean_repo(final_yes)
#clean_repo(final_no)
#exit()
build_prev_meteor_or_star()
exit()

build_prev_repo_from_yn()
exit()
build_prev_repo()
exit()

load_imgs_from_dir(sys.argv[1])
exit()
data = load_day_from_dirs(date, ev_review_dir, ev_review_file)
print("FFF")
for d in data:
   print("DDD", d.keys())
   if os.path.exists(d['ff']):
      img = cv2.imread(d['ff'])
      tfile = "temp.jpg"
      roi_img_1080p_224 = cv2.resize(img,(224,224))
      resp = ASAI.meteor_yn(tfile, None, roi_img_1080p_224)
      print(resp)
      img = cv2.resize(img, (500,500))
      cv2.imshow('ppp', img)
      cv2.waitKey(0)
   else:
      print(d['ff'])
