from Classes.MeteorNew import Meteor
import math
from Classes.DisplayFrame import DisplayFrame
import cv2
import glob
from lib.PipeUtil import cfe, convert_filename_to_date_cam
#import pickle5 as pickle
import os
import datetime
from datetime import datetime as dt
from lib.FFFuncs import ffprobe


def scan_report(meteor_date):
   all_meteor = Meteor()
   all_meteor.scan_report(meteor_date)


def make_media_for_day(meteor_date):
   print("Make media for day")

def scan_day(meteor_date):
   # We want to do 2 types of scans & then the media / save  processes
   #    Initial scan on full frame
   #    Follow crop scan
   #    Final Media Creation (based on scan results)
   # If the main scan doesn't show any meteors, but a human crop exists 
   # jump to the crop scan

   main_scan = 0
   crop_scan = 0

   all_meteor = Meteor()

   month = meteor_date[0:7]
   all_meteor.month = month
   SCAN_DIR = "/mnt/ams2/METEOR_SCAN/" 
  

   #all_meteor.scan_data = scan_data
   all_meteor.check_scan_status_month(meteor_date)
   #all_meteor.make_media_for_day(meteor_date)


   return()
   if True:
      all_meteor.mdir = "/mnt/ams2/meteors/" + meteor_date + "/"
      all_meteor.get_mfiles(all_meteor.mdir)
      for mfile in sorted(all_meteor.mfiles):
         print(mfile)
         mfn = mfile.split("/")[-1]
         if mfn in scan_data:
             print("DONE ALERADY!")
             # continue
             meteor_data = scan_data[mfn]
         else:
             meteor_data = {}
         meteor_data['mfn'] = mfn

         mfile = mfile.replace(".mp4", ".json")
         my_meteor = Meteor(meteor_file=all_meteor.mdir + mfile)
         my_meteor.meteor_scan()
         total_meteors = len(my_meteor.meteor_scan_meteors)
         meteor_data['mfn'] = mfn 

         # MJ VALS WE WANT TO GRAB FOR THE SCAN DB:
         #  version, dfv, manual_changes, aws_status, sync_status
         #  all_media_file, calib info (base & stars)
         mj_info = get_mj_info(my_meteor)
         meteor_data['mj_info'] = mj_info
         print("SAVING MJ INFO!", mj_info)
         if 'hd_trim' in my_meteor.mj:
            if cfe(my_meteor.mj['hd_trim']) == 1:
               meteor_data['hd_trim'] = my_meteor.mj['hd_trim']

         meteor_data['total_meteors'] = total_meteors
         meteor_data['meteor_scan_meteors'] = my_meteor.meteor_scan_meteors
         meteor_data['meteor_scan_nonmeteors'] = my_meteor.meteor_scan_nonmeteors
         
         show_img = my_meteor.sd_stacked_image_orig.copy()
         cv2.putText(show_img, str(mfn),  (25, 560), cv2.FONT_HERSHEY_SIMPLEX, .3, (200, 200, 200), 1)

            #cv2.imshow('pepe', my_meteor.sd_stacked_image_orig)
         if total_meteors == 0:
            print("This scan is bad / no meteors.")
            print("TOTAL OBJS:", len(my_meteor.meteor_scan_nonmeteors))
            for non_meteor in my_meteor.meteor_scan_nonmeteors:
               print("NON_METEOR:", non_meteor['ofns'], "\n")
               print("    oxs:", non_meteor['oxs'], "\n")
               print("    oys:", non_meteor['oys'], "\n")
               print("    ows:", non_meteor['ows'], "\n")
               print("    ohs:", non_meteor['ohs'], "\n")
               print("    oint:", non_meteor['oint'], "\n")
               for key in non_meteor['report']:
                  print("        " , key , non_meteor['report'][key])
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)
            meteor_data['meteor_scan_result'] = "no meteors"
            scan_data[mfn] = meteor_data

         elif total_meteors == 1:
            print("This scan is good")
            dx1,dy1,dx2,dy2 = my_meteor.meteor_scan_meteors[0]['roi']
            cv2.rectangle(show_img, (int(dx1), int(dy1)), (int(dx2) , int(dy2)), (0, 0, 255), 1)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)
            meteor_data['meteor_scan_result'] = "good"
            scan_data[mfn] = meteor_data
         elif total_meteors == 2:
            print("There are 2 meteors!?")
            dom_meteor = my_meteor.dom_meteor(my_meteor.meteor_scan_meteors)
            print("DOM METEOR:", dom_meteor)
            dx1,dy1,dx2,dy2 = dom_meteor['roi']
            show_img = my_meteor.sd_stacked_image_orig.copy()
            cv2.rectangle(show_img, (int(dx1), int(dy1)), (int(dx2) , int(dy2)), (0, 0, 255), 1)
            my_meteor.meteor_scan_meteors = [dom_meteor]
            meteor_data['meteor_scan_result'] = "good"
            scan_data[mfn] = meteor_data

            for obj in my_meteor.meteor_scan_meteors:
               print(obj)
            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)
         else:
            print("There are more than 2 meteors!?")
            for non_meteor in my_meteor.meteor_scan_meteors:
               print("METEOR:", non_meteor['ofns'], "\n")
               print("    oxs:", non_meteor['oxs'], "\n")
               print("    oys:", non_meteor['oys'], "\n")
               print("    ows:", non_meteor['ows'], "\n")
               print("    ohs:", non_meteor['ohs'], "\n")
               print("    oint:", non_meteor['oint'], "\n")
               for key in non_meteor['report']:
                  print("        " , key , non_meteor['report'][key])


            cv2.imshow('pepe', show_img)
            cv2.waitKey(30)
            meteor_data['meteor_scan_result'] = "multi"
            scan_data[mfn] = meteor_data

      # Store data (serialize)
      with open(SCAN_FILE, 'wb') as handle:
         pickle.dump(scan_data, handle, protocol=pickle.HIGHEST_PROTOCOL) 
      print("SAVED", SCAN_FILE)

def starttime_from_file(filename):
   (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(filename)
   trim_num = get_trim_num(filename)
   extra_sec = int(trim_num) / 25
   extra_sec += 2
   event_start_time = f_datetime + dt.timedelta(0,extra_sec)
   return(event_start_time)


def get_mj_info(my_meteor):
   mj = my_meteor.mj
   if "sd_video_file" in mj:
      sd_vid = mj['sd_video_file']
   else:
      sd_vid = None
   if "hd_trim" in mj:
      hd_vid = mj['hd_trim']
   else:
      hd_vid = None
   red_data = my_meteor.red_data
   if red_data is not None:
      if "meteor_frame_data" in red_data:
         mfd = red_data['meteor_frame_data']
         duration = len(red_data['meteor_frame_data']) / 25
         event_start_time = red_data['meteor_frame_data'][0][0]

      else:
         mfd = {}
         duration = 0
         event_start_datetime = starttime_from_file(my_meteor.meteor_file)
         event_start_datetime = event_start_datetime.strftime("%Y_%m_%d_%H_%M_%S")
   if True:
      if "user_mods" in mj:
         user_mods = mj['user_mods']
      else:
         user_mods = {}

      if "version" in mj:
         version = mj['version']
      else:
         version = 1
      if "dfv" in mj:
         dfv = mj['dfv']
      else:
         dfv = 1
      if "last_update" in mj:
         last_update = mj['last_update']
      else:
         last_update = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")

      if "final_trim" in mj:
         final_trim = mj['final_trim']
      else:
         final_trim = {}

      
      if "all_media_files" in mj and "sync_status" in mj:
         all_media_files = mj['all_media_files']
         sync_status = mj['sync_status']
      else:
         my_meteor.get_meteor_media_sync_status(my_meteor.vid_fn)
         sync_status = my_meteor.sync_status
         all_media_files = my_meteor.all_media_files

      event_id = 0
      solve_status = 0
      if "multi_station_event" in mj:
         if "event_id" in mj['multi_station_event']:
            event_id = mj['multi_station_event']['event_id']
         if "solve_status" in mj['multi_station_event']:
            solve_status = mj['multi_station_event']['solve_status']

      if "ffp" in mj:
         ffp = mj['ffp']
      else:
         ffp = {}
         if "hd_trim" in mj:
            if cfe(mj['hd_trim']) == 1:
               hd_vid = mj['hd_trim']
               ffp['hd'] = ffprobe(mj['hd_trim'])
            else:
               hd_vid = None
         else:
            hd_vid = None
         if "sd_video_file" in mj:
            if cfe(mj['sd_video_file']) == 1:
               sd_vid = mj['sd_video_file']
               ffp['sd'] = ffprobe(mj['sd_video_file'])
            else:
               sd_vid = None
         else:
            sd_vid = None

      if "sd_video_file" in mj:
         if cfe(mj['sd_video_file']) == 1:
            sd_vid = mj['sd_video_file']
      if "hd_trim" in mj:
         if cfe(mj['hd_trim']) == 1:
            hd_vid = mj['hd_trim']

      if "crop_box" in mj:
         crop_box = mj['crop_box']
      else:
         print("DEFINE HD CROP BOX FROM MS METEOR ROI CROP")
      if "cp" in mj:
         cp = mj['cp']
         if "total_res_px" not in cp:
            cp['total_res_px'] = 9999
         if "cat_image_stars" not in cp:
            cp['cat_image_stars'] = []
         if math.isnan(cp['total_res_px']):
            cp['total_res_px'] = 9999
         calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
         if "cat_image_stars" in cp:
            cat_image_stars = cp['cat_image_stars']
         else:
            cat_image_stars = []
      else:
         cat_image_stars = []
         calib = []
   mj_info = {}
   print("SELF:",my_meteor.meteor_file)
   if sd_vid is not None and sd_vid != 0:
      mj_info['sd_vid'] = sd_vid.split("/")[-1]
   if hd_vid is not None and hd_vid != 0:
      mj_info['hd_vid'] = hd_vid.split("/")[-1]
   mj_info['dfv'] = dfv
   mj_info['version'] = version
   mj_info['ffp'] = ffp
   mj_info['calib'] = calib
   mj_info['cat_image_stars'] = cat_image_stars
   mj_info['sync_status'] = sync_status
   mj_info['all_media_files'] = all_media_files
   mj_info['user_mods'] = user_mods
   mj_info['event_id'] = event_id
   mj_info['solve_status'] = solve_status
   mj_info['last_update'] = last_update

   my_meteor.mj['last_update'] = last_update
   my_meteor.mj['all_media_files'] = all_media_files
   my_meteor.mj['sync_status'] = sync_status
   my_meteor.mj['ffp'] = ffp
   my_meteor.mj['version'] = version
   my_meteor.mj['dfv'] = dfv

   return(mj_info)
   """ AWS OBS OBJ
    obs_data = {
      "station_id": station_id,
      "sd_video_file": sd_vid,
      "hd_video_file": hd_vid,
      "event_start_time": event_start_time,
      "event_id": event_id,
      "dur": duration,
      "peak_int": peak_int,
      "calib": calib,
      "crop_box": crop_box,
      "cat_image_stars": cat_image_stars,
      "ffp": ffp,
      "final_trim": final_trim,
      "meteor_frame_data": meteor_frame_data,
      "revision": revision,
      "dfv": dfv,
      "sync_status": sync_status,
      "last_update": update_time
    }



   """



def save_learning_dataset(my_meteor):
   # save non-meteor objects larger than 10x10 in the nonmeteor label
   # save meteor objects in the meteor label
   # use even width/height but do not resize

   fn_root = my_meteor.meteor_file.split("/")[-1].replace(".json", "")

   oc = 1
   for non_meteor in my_meteor.meteor_scan_nonmeteors:
      roi = non_meteor['roi']
      obj_id = non_meteor['obj_id']
      learning_file = "/mnt/ams2/datasets/training/nonmeteors/" + fn_root + "_obj" + str(obj_id) + ".jpg"
      x1,y1,x2,y2 = roi
      crop_img = my_meteor.sd_stacked_image_orig[y1:y2,x1:x2] 
      cv2.imshow('non meteor crop', crop_img)
      cv2.waitKey(30)
      cv2.imwrite(learning_file,crop_img,[cv2.IMWRITE_JPEG_QUALITY, 40])
      print("save non meteor", learning_file,  roi)
      oc += 1
   oc = 1
   for meteor in my_meteor.meteor_scan_meteors:
      roi = meteor['roi']
      obj_id = meteor['obj_id']
      x1,y1,x2,y2 = roi
      crop_img = my_meteor.sd_stacked_image_orig[y1:y2,x1:x2] 
      cv2.imshow('meteor crop', crop_img)
      cv2.waitKey(30)
      learning_file = "/mnt/ams2/datasets/training/meteors/" + fn_root + "-roi.jpg"
      roi_file = "/mnt/ams2/meteors/" + fn_root[0:10] + "/meteors/" + fn_root + "-roi.jpg"
      print("save meteor", learning_file,  roi)
      cv2.imwrite(learning_file,crop_img, [cv2.IMWRITE_JPEG_QUALITY, 60])
      cv2.imwrite(roi_file,crop_img, [cv2.IMWRITE_JPEG_QUALITY, 60])
      oc += 1

def scan_wild(meteor_wild):
   dirs = glob.glob("/mnt/ams2/meteors/" + meteor_wild + "*")
   mdirs = []
   for mdir in sorted(dirs, reverse=True):
      if cfe(mdir,1) == 1:
         day = mdir.split("/")[-1]
         mdirs.append(day)
   for md in sorted(mdirs, reverse=True):
      scan_day(md)



if __name__ == "__main__":
   import sys
   if len(sys.argv) > 1:
      cmd = sys.argv[1]
      meteor_date = sys.argv[2]
   else:
      meteor_date = None
      print("   COMMANDS:")
      print("   1) Scan meteors for 1 day -- will run all detections, calibrations and syncs needed to complete meteor processing.")
      print("   2) Scan meteors for 1 month or 1 year -- will run all detections, calibrations and syncs needed to complete meteor processing.")
      print("   3) Examine meteor -- will load meteor and provide all options / status.")
      print("   4) Meteor Scan Report ")
      cmd = input("Enter the command you want to run. ")
   if cmd == "1":
      cmd = "scan"
   if cmd == "2":
      cmd = "scan_wild"
   if cmd == "3":
      cmd = "meteor_status"
      meteor_file = sys.argv[2]
   if cmd == "4":
      cmd = "scan_report"
   if cmd == "scan":
      if meteor_date is None:
         meteor_date = input("Enter Date")
      scan_day(meteor_date)
   if cmd == "scan_wild":
      if meteor_date is None:
         meteor_date = input("Enter Date Str YYYY_MM or YYYY")
      scan_wild(meteor_date)
   if cmd == "scan_report":

      if meteor_date is None:
         meteor_date = input("Enter Date YYYY_MM_DD")
      scan_report(meteor_date)


   if cmd == "meteor_status":
      if meteor_date is None:
         meteor_file = input("Enter full path to the meteor json file")
      else:
         meteor_file = meteor_date
      my_meteor = Meteor(meteor_file=meteor_file)
      my_meteor.meteor_scan()
