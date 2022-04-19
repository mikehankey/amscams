from Classes.Events import Events
import cv2
import os
from Classes.MultiStationObs import MultiStationObs
from lib.PipeUtil import load_json_file, save_json_file

import sys

def sync_meteor(EV, root_fn, cloud_files, mdir, cloud_dir):
   ms_dir = mdir.replace("/meteors/", "/METEOR_SCAN/")
   types = ["prev.jpg", "180p.mp4", "360p.jpg", "360p.mp4", "1080p.jpg", "1080p.mp4"]
   missing = []
   cmds = []
   #print("CLOUD FILES:", cloud_files)
   #for cf in cloud_files:
   #   print(cf)
   #input('xxx')
   for cf in sorted(cloud_files):
      if root_fn in cf:
         for t in types:
            media_file = EV.station_id + "_" + root_fn + "-" + t 
            if media_file in cloud_files:
               print("CLOUD FILE EXISTS:", cf)
            else:

               if os.path.exists(ms_dir + media_file) is True:
                  #print("LOCAL FILE FOUND!", ms_dir + media_file)
                  cmd = "cp " + ms_dir + media_file + " " + cloud_dir + media_file
                  print(cmd)
                  cmds.append(cmd)
                  os.system(cmd)
               else:
                  print("NEED TO MAKE!", ms_dir + media_file)
                  if "360p.jpg" in media_file :
                     stack_file = media_file.replace("-360p.jpg", "-stacked.jpg")
                     stack_file = stack_file.replace("METEOR_SCAN", "meteors")
                     sd_stack_img = cv2.imread(stack_file)
                     try:
                        cv2.imwrite(ms_dir + media_file,sd_stack_img,[cv2.IMWRITE_JPEG_QUALITY, 80])
                        print("saved", ms_dir + media_file)
                     except:
                        print("Could not save image.")

                  if "1080p.jpg" in media_file :
                   
                     mjf = media_file.replace("-1080p.jpg", ".json")
                     mjf = mjf.replace(EV.station_id + "_", "")
                     mjf = mjf.replace("METEOR_SCAN", "meteors")
                     mj = load_json_file(mdir + mjf)
                     hd_trim = mj['hd_trim']
                     hd_stack_file = hd_trim.replace(".mp4", "-stacked.jpg")
                     hd_stack_img = cv2.imread(hd_stack_file)
                     print('saved', ms_dir + media_file)
                     cv2.imwrite(ms_dir + media_file,hd_stack_img,[cv2.IMWRITE_JPEG_QUALITY, 80])
           
               missing.append(ms_dir + media_file)
   #exit()
   #for mf in missing:
   #   print("MISSING:", mf)

def do_day(EV, date):
   EV.do_ms_day(date)
   EV.date = ev_date
   EV.year = ev_date.split("_")[0]
   EV.month = ev_date.split("_")[1]
   EV.day = ev_date.split("_")[2]
   ev_html = ""
   mdir = "/mnt/ams2/meteors/" + ev_date + "/"
   ms_vdir = "/METEOR_SCAN/" + ev_date + "/"
   cloud_dir = "/mnt/archive.allsky.tv/" + EV.station_id + "/METEORS/" + EV.year + "/" + EV.date + "/"
   print("CLOUD DIR:", cloud_dir)
   if os.path.exists(cloud_dir) is True:
      cloud_files = os.listdir(cloud_dir)
   else:
      cloud_files = []
   for mso in EV.my_ms_obs:
      print("Multi Station Obs:", mso )
      MSO.load_obs(mso)
      ev_html += "<img src=" + ms_vdir + EV.station_id + "_" + mso + "-ROI.jpg>\n"
      # for each MSO we should make sure ALL content is uploaded 
      # We should also check the AI?
   print(ev_html)
   if os.path.exists("/mnt/ams2/" + ms_vdir) is False:
      os.makedirs("/mnt/ams2/" + ms_vdir)
   fp = open("/mnt/ams2/" + ms_vdir + "events.html", "w")
   fp.write(ev_html)
   print("saved /mnt/ams2/" + ms_vdir + "events.html")
   save_json_file("/mnt/ams2/meteors/" + ev_date + "/" + ev_date + "_MY_MS_OBS.info", EV.my_ms_obs)
   for mm in sorted(EV.min_cnt):
      if isinstance(EV.min_cnt[mm]['times'], str) is True:
         EV.min_cnt[mm]['times'] = json.loads(EV.min_cnt[mm]['times'])
      if isinstance(EV.min_cnt[mm]['stations'], str) is True:
         EV.min_cnt[mm]['stations'] = json.loads(EV.min_cnt[mm]['stations'])
      if len(set(EV.min_cnt[mm]['stations'])) >= 2:
      
         for i in range(0,len(EV.min_cnt[mm]['times'])):
            st = EV.min_cnt[mm]['stations'][i]
            if st == EV.station_id:
               obs_file = EV.min_cnt[mm]['obs'][i]
               sync_meteor(EV, obs_file, cloud_files,mdir, cloud_dir)


EV = Events()
MSO = MultiStationObs()
ev_date = sys.argv[1]
do_day(EV, ev_date)
