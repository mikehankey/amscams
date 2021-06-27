from lib.PipeUtil import cfe, load_json_file, save_json_file, get_file_info, convert_filename_to_date_cam,get_trim_num
import os
from pushAWS import make_obs_data
import glob
from datetime import datetime

"""
 Reconcile -- Class for reconciling meteor data with latest detection, redis storage, calib, media, cloud, backup/archive and AWS. 



"""

class Reconcile():
   def __init__(self, year=None,month=None):
      self.data_dir = "/mnt/ams2/METEOR_SCAN/DATA/"
      if cfe(self.data_dir,1) == 0:
         os.makedirs(self.data_dir)
      self.media_exts = ['FRMS.jpg', 'HD.jpg', 'HD.mp4', 'PREV.jpg', 'ROI.jpg', 'ROI.mp4', 'ROIHD.jpg', 'ROIHD.mp4', 'SD.jpg', 'SD.mp4']
      if cfe(self.data_dir, 1) == 0:
         os.makedirs(self.data_dir)
      if year is not None and month is None:
         self.rec_file = self.data_dir + "reconcile_" + year + ".json"
      elif year is not None and month is not None:
         self.rec_file = self.data_dir + "reconcile_" + year + "_" + month + ".json"
      self.json_conf = load_json_file("../conf/as6.json")
      self.station_id = self.json_conf['site']['ams_id']
      self.cloud_dir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" 
      if cfe(self.cloud_dir,1) == 0:
         os.makedirs(self.cloud_dir)


      if cfe(self.rec_file) == 1:
         try:
            self.rec_data = load_json_file(self.rec_file)
         except:
            print("CORRUPT rec file?", self.rec_file)
            self.rec_data = {}
           # exit()
      else:
         self.rec_data = {}
      self.mfiles = []
      if "corrupt_json" not in self.rec_data:
         self.rec_data['corrupt_json'] = []

      if "needs_review" not in self.rec_data:
         self.rec_data['needs_review'] = []
      
      if month is None:
         self.get_all_meteor_files(year)
      else:
         self.get_all_meteor_files(year, month)

         self.rec_data['mfiles'] = self.mfiles
         save_json_file(self.rec_file, self.rec_data, True)
      if "meteor_index" not in self.rec_data:
         self.rec_data['meteor_index'] = {}   
      c = 0

      new = 0
      for root_file in self.rec_data['mfiles']:
         date = root_file[0:10]
         meteor_file = "/mnt/ams2/meteors/" + date + "/" + root_file + ".json"
         mon = date[0:7]
         if c > 0 and last_month != mon and new >= 500:
            # incrementally save
            save_json_file(self.rec_file, self.rec_data,True)
            new = 0

         if root_file not in self.rec_data['meteor_index']:
            self.rec_data['meteor_index'][root_file] = {}
            self.rec_data['meteor_index'][root_file]['last_update'] = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
            self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file) 
            new = new + 1
         else:
            print("DONE ALREADY.")

         c += 1
         last_month = mon

      print("GETTING SCAN MEDIA...", year, month)
      self.get_scan_media(year,month)
      self.get_cloud_media(year)
      new = 1
      if new >= 1:    
         print("saving " + year + " data")
         save_json_file(self.rec_file, self.rec_data)

      # REMOVE DELETED METEORS FROM THE REC_DATA METEOR INDEX
      deleted_meteors = []
      for root_file in self.rec_data['meteor_index']:
         mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json" 
         if cfe(mfile) == 0:
            print("   INFO: MFILE NO LONGER EXISTS. IT SHOULD BE DELETED FROM THE METEOR INDEX!")
            print("   ",mfile)
            deleted_meteors.append(root_file)
      for root_file in deleted_meteors:
         print("   INFO: REMOVED FILE FROM INDEX", root_file) 
         print(self.rec_data.keys())
         if root_file in self.rec_data['meteor_index']: 
            del(self.rec_data['meteor_index'][root_file])
         if root_file in self.rec_data['mfiles']: 
            del(self.rec_data['mfiles'][root_file])
         if root_file in self.rec_data['needs_review']: 
            del(self.rec_data['needs_review'][root_file])
         if root_file in self.rec_data['corrupt_json']: 
            del(self.rec_data['corrupt_json'][root_file])

   def save_rec_data(self):
      save_json_file(self.rec_file, self.rec_data)
      print("SAVED:", self.rec_file)

   def day_month_stats(self):
      for root_file in self.rec_data['meteor_index']:
         day = root_file[0:10]
         mon = root_file[0:7]
         if day not in self.rec_data['day_data']:
            self.rec_data['day_data'][day] = 1
         else:
            self.rec_data['day_data'][day] += 1
         if mon not in self.rec_data['month_data']:
            self.rec_data['month_data'][mon] = 1 
         else:
            self.rec_data['month_data'][mon] += 1 

      for day in self.rec_data['day_data']:
         print(day, self.rec_data['day_data'][day])
      for mon in self.rec_data['month_data']:
         print(mon, self.rec_data['month_data'][mon])



   def reconcile_report(self, year = None, month=None):
      print("RECONCILE REPORT FOR ", self.station_id, year, month)
      for root_file in sorted(self.rec_data['meteor_index'], reverse=True):
         obs_data = self.rec_data['meteor_index'][root_file]['obs_data']
         peak_int = 0
         ss = []
         mfd = 0
         if "meteor_frame_data" in obs_data:
            mfd = len(obs_data['meteor_frame_data'])
         else:
            print("   INFO: NO METEOR FRAME DATA!")
         if "sync_status" in obs_data:
            sync_status = obs_data['sync_status']
         else:
            print("   INFO: GET SYNC STATUS!")

         if "peak_int" in obs_data:
            peak_int = obs_data['peak_int']
            self.rec_data['meteor_index'][root_file]['obs_data']['peak_int'] = peak_int
         else:
            print("   INFO: GET PEAK INT!")

         if "scan_status" in obs_data :
            scan_status = obs_data['scan_status'] 
         else:
            print("   INFO: NEED TO GET SCAN STATUS!")
            scan_status = self.get_scan_status(root_file)
            self.rec_data['meteor_index'][root_file]['obs_data']['scan_status'] = scan_status
         print(root_file, mfd, peak_int, scan_status )
      
   def get_scan_status(self, root_file):
      mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
      scan_status = {}
      scan_status['jobs'] = [] 
      scan_status['mets'] = [] 
      meteor_scan_run = 0
      meteor_scan_meteors = 0
      meteor_crop_scan_run = 0
      meteor_crop_scan_meteors = 0
      meteor_hd_crop_scan_run = 0
      meteor_hd_crop_scan_meteors = 0
      resave_mj = 0
      if cfe(mfile) == 1:
         try:
            mj = load_json_file(mfile)
         except:
            mj = self.remake_mj(root_file)
            resave_mj = 1
            #exit()
         if "meteor_scan_meteors" in mj:
            meteor_scan_run = 1
            meteor_scan_meteors = len(mj['meteor_scan_meteors'])
         if "msc_meteors" in mj:
            meteor_crop_scan_run = 1
            if type(mj['msc_meteors']) == dict :
               mj['msc_meteors'] = self.fix_hd_scan_data(mj['msc_meteors'])
               print("FIXED MSC METEORS!")
               input()


            meteor_crop_scan_meteors = len(mj['msc_meteors'])



         if "meteor_scan_hd_crop_scan" in mj:
            if "meteors" in mj['meteor_scan_hd_crop_scan']:
               print("TYPE IS:",  type(mj['meteor_scan_hd_crop_scan']))
               mj['meteor_scan_hd_crop_scan'] = self.fix_hd_scan_data(mj['meteor_scan_hd_crop_scan']['meteors'])
               print("FIXED 1:", mfile)
            elif type(mj['meteor_scan_hd_crop_scan']) == dict :
               mj['meteor_scan_hd_crop_scan'] = self.fix_hd_scan_data(mj['meteor_scan_hd_crop_scan'])
               print("FIXED 2:", mfile)
            elif len(mj['meteor_scan_hd_crop_scan']) > 1:
               mj['meteor_scan_hd_crop_scan'] = self.only_meteors(mj['meteor_scan_hd_crop_scan'])

            meteor_hd_crop_scan_run = 1
            meteor_hd_crop_scan_meteors = len(mj['meteor_scan_hd_crop_scan'])
         scan_status['jobs'] = [meteor_scan_run, meteor_crop_scan_run, meteor_hd_crop_scan_run] 
         scan_status['mets'] = [meteor_scan_meteors, meteor_crop_scan_meteors, meteor_hd_crop_scan_meteors] 
         mj['scan_status'] = scan_status
         save_json_file(mfile, mj)
      else: 
         print("   ERROR MF NOT FOUND:", mfile )
         input()
      return(scan_status)

   def only_meteors(self, objects):
      final_meteors = []
      for obj in objects:
         if "report" in obj :
            if obj['report']['class'] == "meteor":
               final_meteors.append(obj)
      return(final_meteors)

   def fix_hd_scan_data(self, hd_scan_data):
      final_hd_meteors = []
      print(hd_scan_data)
      for obj_id in hd_scan_data:
         obj = hd_scan_data[obj_id]
         if "report" in obj:
            print(obj['report'])
            if obj['report']['class'] == "meteor":
               print("METEOR FOUND!")
               final_hd_meteors.append(obj)
      print("FINAL:", final_hd_meteors)
      return(final_hd_meteors)

            
   def get_cloud_media(self, year):
      cloud_files_file = "/mnt/ams2/METEOR_SCAN/DATA/cloud_files_" + year + ".txt"
      cloud_wild = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + year + "/" 
      if cfe(cloud_files_file) == 0:
         print("GETTING CLOUD FILES....")
         print ("find " + cloud_wild + " > " + cloud_files_file)
         os.system("find " + cloud_wild + " > " + cloud_files_file)
      fp = open(cloud_files_file)
      wild = year
      for line in fp:
         if wild not in line:
            continue
         line = line.replace("\n", "")
         fn = line.split("/")[-1]
         fn = fn.replace(self.station_id + "_","")
         ext = fn.split("-")[-1]
         root = fn.replace("-" + ext, "")
         if root in self.rec_data['meteor_index']:
            if "cloud_files" not in self.rec_data['meteor_index'][root]:
               self.rec_data['meteor_index'][root]['cloud_files'] = []
            self.rec_data['meteor_index'][root]['cloud_files'].append(ext)
            self.rec_data['meteor_index'][root]['cloud_files'] = sorted(list(set(self.rec_data['meteor_index'][root]['cloud_files'])))


   def get_scan_media(self, year, mon):
      media_files_file = "/mnt/ams2/METEOR_SCAN/DATA/media_files.txt"
      if mon is not None:
         wild = year + "_" + mon
      else :
         wild = year
      os.system("find /mnt/ams2/METEOR_SCAN/ > " + media_files_file)
      fp = open(media_files_file)
      for line in fp:
         if wild not in line:
            continue
         line = line.replace("\n", "")
         fn = line.split("/")[-1]
         fn = fn.replace(self.station_id + "_","")
         ext = fn.split("-")[-1]
         root = fn.replace("-" + ext, "")
         
         if root in self.rec_data['meteor_index']:
            if "exts" not in self.rec_data['meteor_index'][root]:
               self.rec_data['meteor_index'][root]['exts'] = []
               self.rec_data['meteor_index'][root]['cloud_files'] = []
            self.rec_data['meteor_index'][root]['exts'].append(ext)
            self.rec_data['meteor_index'][root]['exts'] = sorted(list(set(self.rec_data['meteor_index'][root]['exts'])))


   def reconcile_cloud_media(self):
      for root_file in self.rec_data['meteor_index']:
         date = root_file[0:10]
         meteor_file = "/mnt/ams2/meteors/" + date + "/" + root_file + ".json"
         if "cloud_files" in self.rec_data['meteor_index'][root_file]:
            cloud_files = self.rec_data['meteor_index'][root_file]['cloud_files']
            ext_files = self.rec_data['meteor_index'][root_file]['exts']
         else:
            print("MISSING CLOUD FIELD!?", root_file)
            continue 
         if "ROI.jpg" not in cloud_files or "ROI.mp4" not in cloud_files:
            if "hc" not in self.rec_data['meteor_index'][root_file]['obs_data']:
               self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file) 

         # MAKE DECISION ABOUT WHAT TO UPLOAD. 
         # LEVEL 1 -- ALL FILES SHOULD AT LEAST HAVE THE prev.jpg file
         # LEVEL 2 -- ALL FILES WITH METEOR SCAN METEORS OR CROP METEORS SHOULD HAVE THE FULL SD SET (prev.jpg, SD.jpg, SD.mp4, ROI.mp4)
         # LEVEL 3 -- ALL FILES WITH MSM DETECTIONS OR A HUMAN CONFIRMED METEOR SHOULD HAVE THE FULL SD & HD SET (prev.jpg, SD.jpg, SD.mp4, ROI.mp4)
         scan_confirmed = 0
         human_confirmed = 0
         msm_confirmed = 0
         if "hc" in self.rec_data['meteor_index'][root_file]['obs_data']:
            if self.rec_data['meteor_index'][root_file]['obs_data']['hc'] == 1:
               #HUMAN CONFIRMED
               human_confirmed = 1

         if "roi" in self.rec_data['meteor_index'][root_file]['obs_data']:
            if sum(self.rec_data['meteor_index'][root_file]['obs_data']['roi']) > 0:
               #METEOR SCAN CONFIRMED
               scan_confirmed = 1
         if "event_id" in self.rec_data['meteor_index'][root_file]['obs_data']:
            if self.rec_data['meteor_index'][root_file]['obs_data']['event_id'] != 0:
               #MULTI-STATION CONFIRMED
               msm_confirmed = 1

         sync_level = 0
         if scan_confirmed == 0:
            sync_level = 1
         if scan_confirmed == 1:
            sync_level = 2
         if human_confirmed == 1 or msm_confirmed == 1:
            sync_level = 3
         print(root_file, "SYNC LEVEL:", sync_level, scan_confirmed, human_confirmed, msm_confirmed)
         if sync_level >= 1:
            # METEOR SCAN FAILED ONLY PUT UP THE prev.jpg
            if "prev.jpg" not in self.rec_data['meteor_index'][root_file]['cloud_files']:
               self.sync_prev(root_file)
            else:
               print("     CLOUD PREV FILE IS SYNC'D.", root_file)
         if sync_level >= 2:
            print("LEVEL2")
            self.sync_sd_files(root_file)
            # SYNC PREV and ALL SD MEDIA: prev.jpg, SD.mp4, SD.jpg, ROI.jpg, ROI.mp4


   def sync_sd_files(self, root_file):
      sd_exts = ['prev.jpg', 'SD.mp4', 'SD.jpg', 'ROI.jpg', 'ROI.mp4']
      date = root_file[0:10]
      for ext in sd_exts:
         if ext == "prev.jpg":
            skiping = 1
         elif ext not in self.rec_data['meteor_index'][root_file]['cloud_files'] or (ext == "SD.mp4" and "ROI.mp4" not in self.rec_data['meteor_index'][root_file]['cloud_files'] ):
            ms_file = "/mnt/ams2/METEOR_SCAN/" + date + "/" + self.station_id + "_" + root_file + "-" + ext 
            cloud_file = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + date + "/" + self.station_id + "_" + root_file + "-" + ext
            self.rec_data['meteor_index'][root_file]['cloud_files'].append(ext)
            cmd = "cp " + ms_file + " " + cloud_file
            print(cmd)
            os.system(cmd)
         else:
            print("FILE IN CLOUD ALREADY", root_file, ext)
         

   def sync_prev(self, root_file):
      local_prev = "/mnt/ams2/meteors/" + date + "/cloud_files/" + self.station_id + "_" + root_file + "-prev.jpg"
      ms_prev = "/mnt/ams2/METEOR_SCAN/" + date + "/cloud_files/" + self.station_id + "_" + root_file + "-PREV.jpg"
      cloud_prev = "/mnt/archive.allsky.tv/" + station_id + "/METEOR_SCAN/" + date + "/cloud_files/" + self.station_id + "_" + root_file + "-prev.jpg"
      if cfe(local_prev) == 1:
         print("LOCAL prev.jpg EXISTS", root_file)
         cmd = "cp " + local_prev + " " + cloud_prev
         print(cmd)
         os.system(cmd)
         self.rec_data['meteor_index'][root_file]['cloud_files'].append("prev.jpg")

      elif cfe(ms_prev) == 1:
         print("METEOR SCAN PREV.jpg EXISTS", root_file)
         cmd = "cp " + local_prev + " " + cloud_prev
         print(cmd)
         os.system(cmd)
         self.rec_data['meteor_index'][root_file]['cloud_files'].append("prev.jpg")
      else:
         print("NO PREV FILE EXISTS YET!", root_file)
         cmd = "cp " + local_prev + " " + cloud_prev
         print(cmd)
         os.system(cmd)
      


   def reconcile_media(self):
      self.missing_scans = []
      print("REC MEDIA")
      """ 
          FOR MEDIA WE WANT TO DO THIS IN 3 PHASES
          1) Push the AWS data and prev thumbnail and that is it
          2) For successful meteor scan meteors upload the SD video, ROI video, ROI thumb, SD STACK IMAGE (here we wil have 5 total files: prev.jpg, SD.jpg, ROI.jpg SD.mp4 ROI.mp4
          3) For MSM or HC confirmed meteors, push the HD files too -- we will add HD.mp4 HDROI.mp4 HD.jpg and ROIHD.jpg (4 more files)
          If the meteor is confirmed and all media is sync'd there should be a total of 9 files for the meteor inside the METEOR_SCAN DIR
          If these don't exist yet, then the scan was not run, but should be. 

          * CAP THIS / ONLY DO OPTION 1 if there are more than 100 meteors for the day. 
          * IF THERE ARE MORE THAN 200 meteors, abort unless it is Aug 8-16 or Dec 10-16
      """
      for root_file in self.rec_data['meteor_index']:
         if "exts" not in self.rec_data['meteor_index'][root_file]:
            self.rec_data['meteor_index'][root_file]['exts'] = []
         obs_data = self.rec_data['meteor_index'][root_file]['obs_data']
         date = root_file[0:10]
         mdir = "/mnt/archive.allsky.tv/" + self.station_id + "/METEORS/" + date + "/" 
         if cfe(mdir, 1) == 0:
            os.makedirs(mdir)
         # IS THERE FRAME DATA?
         # AREA THERE EXTS? HAS ALL MEDIA BEEN MADE?
         # WHAT HAS BEEN SYNC'D?
         if "meteor_frame_data" in self.rec_data['meteor_index'][root_file]['obs_data']:
            mfd = len(self.rec_data['meteor_index'][root_file]['obs_data']['meteor_frame_data'])
         else:
            mfd = 0
         if "exts" in self.rec_data['meteor_index'][root_file]:
            ext = self.rec_data['meteor_index'][root_file]['exts']
         else:
            ext = 0
         if "cloud_files" in self.rec_data['meteor_index'][root_file]:
            cloud_files = self.rec_data['meteor_index'][root_file]['cloud_files']
         if "ROI" not in cloud_files:
            cloud_missing = 1

         exts_missing = 0         
         missing_media = []
         for ext_type in self.media_exts: 
            if root_file in self.rec_data['meteor_index']:
               if "exts" not in self.rec_data['meteor_index'][root_file]:
                  self.rec_data['meteor_index'][root_file]['exts'] = []
               print(self.rec_data['meteor_index'][root_file])
               print("KEYS:", root_file, self.rec_data['meteor_index'][root_file].keys())
               if ext_type not in self.rec_data['meteor_index'][root_file]['exts']:
                  exts_missing = 1
                  missing_media.append(ext_type)

           
         if "ROI.jpg" in missing_media or "ROI.mp4" in missing_media:
            self.missing_scans.append(root_file)

         print(root_file, mfd, exts_missing, cloud_missing, missing_media)
         #print(ext)
         #print(cloud_files)

      # SCAN METEORS THAT HAVEN'T BEEN SCANNED YET (this will create missing media) 
      mc = 0
      for root_file in self.missing_scans:
         if root_file in self.rec_data['corrupt_json']:
            continue 
         # before rescanning check 2 things. 
         # 1) has the scan already run but failed? if there is no "meteor_scan_meteors" meteors then this is the case
         # 2) is the ROI field missing or are they all zeros. If this is the case a meteor was not detected, so we shouldn't scan. 
         # 3) save as a 'scan_failure' so we don't redo this!
         # 4) scan failures will be treated as LEVEL 1 syncs. -- only thumb and data.
         print("NEED SCAN FOR :", root_file)
         date = root_file[0:10]
         meteor_file = "/mnt/ams2/meteors/" + date + "/" + root_file + ".json"
         if cfe(meteor_file) == 1:
            scan_failed = 0
            try:
               mj = load_json_file(meteor_file)
               if "roi" in mj:
                  sum_roi = sum(mj['roi'])
               if "meteor_scan_meteors" in mj:
                  if len(mj['meteor_scan_meteors']) == 0:
                     # the scan has run but it has failed. if the sum roi is 0 there is no hope for this file. 
                     scan_failed = 1
                     
               
            except:
               print("CORRUPT FILE or DELETED?", root_file)
               self.rec_data['corrupt_json'].append(root_file)
               continue
         if scan_failed != 1:
            cmd = "python3 Meteor.py 3 " + root_file + ".json"
            print(mc, cmd)
            os.system(cmd)
            self.rec_data['meteor_index'][root_file]['obs_data'] = make_obs_data(self.station_id, date, meteor_file) 
            mc += 1
         else:
            print("The scan for this meteor has failed and the ROI is 0. There is nothing we can do. Maybe it is a false or dim meteor.")
            print("This file needs review!")
             
            self.rec_data['needs_review'].append(root_file)

   def get_all_meteor_files(self, year, month ):
      if month is not None:
         mdirs = glob.glob("/mnt/ams2/meteors/" + year + "_" + month + "*")
      else:
         mdirs = glob.glob("/mnt/ams2/meteors/" + year + "*")
      mds = []
      for md in mdirs:
         if cfe(md,1) == 1:
            mds.append(md + "/")

      for md in sorted(mds,reverse=True):
         print(md)
         self.get_mfiles(md)

   def get_mfiles(self, mdir):
      temp = glob.glob(mdir + "/*.json")
      for json_file in temp:
          if "frame" not in json_file and "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
            root = json_file.split("/")[-1].replace(".json", "")

            self.mfiles.append(root)

   def remake_mj(self, root_file):
      mfile = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + root_file + ".json"
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(root_file)
      base_file = fy + "_" + fmon + "_" + fd + "_" + fh + "_" + fm
      hd_wild = "/mnt/ams2/meteors/" + root_file[0:10] + "/" + base_file + "*HD-meteor.mp4"
      pos_hds = glob.glob(hd_wild)
      def_mj = {}
      def_mj['sd_video_file'] = mfile.replace(".json", ".mp4")
      def_mj['sd_stack'] = mfile.replace(".json", "-stacked.jpg")

      if len(pos_hds) >= 1:
         def_mj['hd_trim'] = pos_hds[0]
         def_mj['hd_stack'] = pos_hds[0].replace(".mp4", "-stacked.mp4")
         def_mj['hd_video_file'] = pos_hds[0]
      return(def_mj)
