#!/usr/bin/python3

from geopy.geocoders import Nominatim
geolocator = Nominatim(user_agent="geoapiExercises")
from Classes.AllSkyNetwork import AllSkyNetwork
import cv2
import os
import sys
import datetime as dt
from datetime import datetime
from lib.PipeUtil import get_file_info

cmd = sys.argv[1]

ASN = AllSkyNetwork()

now = datetime.now()
yest = now - dt.timedelta(days=1)
yest = yest.strftime("%Y_%m_%d")
today = datetime.now().strftime("%Y_%m_%d")

if len(sys.argv) < 1:
   ASN.help()
   exit()

if cmd == "ignore":
   event_id = sys.argv[2]
   ignore_string = sys.argv[3]
   ASN.ignore_add_item(event_id, ignore_string)

if cmd == "admin_event_links" or cmd == "edit_event":
   event_id = sys.argv[2]
   ASN.admin_event_links(event_id)

if cmd == "event_preview_images":
   date = sys.argv[2]
   ASN.make_event_preview_images(date)   

if cmd == "stations":
   rcmd = "cd /home/ams/amscams/pipeline; ./gitpull.py; uptime"
   ASN.station_list(rcmd)   
if cmd == "station_report":
   ASN.station_report(sys.argv[2])   

if cmd == "past_days":
   ASN.run_past_days()

if cmd == "filter_bad_detects":
   ASN.filter_bad_detects(sys.argv[2])


if cmd == "refresh_day":
   force = 0

   event_day = sys.argv[2]
   ASN.set_dates(event_day)
   cmd = "./DynaDB.py udc " + event_day
   os.system(cmd)
   ASN.day_load_sql(event_day, 1)
   ASN.day_solve(event_day,force)
   ASN.day_load_solves(event_day)
   ASN.publish_day(event_day)

   cmd = "python3 ER.py " + event_day
   print(cmd)
   os.system(cmd)

   cmd = "python3 EM.py aer " + event_day 
   #print(cmd)
   os.system(cmd)

   cmd = "python3 EM.py aei " + event_day 
   #print(cmd)
   os.system(cmd)

   cmd = "python3 DynaDB.py udc " + event_day + " events"
   #print(cmd)
   os.system(cmd)
   # make best obs
   ASN.best_obs_day(sys.argv[2])
   # make event table
   ASN.event_table(sys.argv[2])

   cmd = "python3 PLT.py all_rad " + event_day
   print(cmd)
   os.system(cmd)

   cmd = "/usr/bin/python3 solveWMPL.py vida_plots " + event_day 
   print(cmd)
   os.system(cmd)


   ASN.rsync_data_only(event_day)



if cmd == "update_meteor_days":
   ASN.update_meteor_days()

if cmd == "help":
   print("CMD:", cmd)
   ASN.help()

if cmd == "day_load_solves":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.day_load_solves(event_day)

if cmd == "plane_test_day":
   print("CMD:", cmd)
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.plane_test_day(event_day)

if cmd == "delete_bad_detects":
   ndate = sys.argv[2]
   ASN.delete_bad_detects(ndate)

if cmd == "report":
   print("CMD:", cmd)
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.quick_report(event_day)

if cmd == "rsync_data":
   print("CMD:", cmd)
   event_day = sys.argv[2]
   date = event_day
   ASN.help()
   ASN.set_dates(date)
   ASN.rsync_data_only(event_day)

if cmd == "resolve_failed_day" or cmd == "rerun_failed" or cmd == "resolve_failed":
   print("RESOLVE FAILED DAY")
   ASN.help()
   ASN.set_dates(sys.argv[2])
   event_day = sys.argv[2].replace("_", "")
   event_day = event_day.replace("-", "")
   event_day = event_day.replace("/", "")
   ASN.resolve_failed_day(event_day)

if cmd == "review_event_day":
   ASN.help()
   date = sys.argv[2]
   if date == "today":
      date = today
   if date == "yest":
      date = yest 


   ASN.review_event_day(date)


if cmd == "review_event_movie":
   event_id = sys.argv[2]
   event_day = ASN.event_id_to_date(event_id)
   ASN.set_dates(event_day)
   ASN.review_event_movie(sys.argv[2])


if cmd == "review_event":
   event_id = sys.argv[2]
   event_day = ASN.event_id_to_date(event_id)
   ASN.set_dates(event_day)
   ASN.review_event(sys.argv[2])
   (review_image, map_img, obs_imgs, marked_images, event_data, obs_data) = ASN.review_event_step2()
   cv2.imshow('pepe', review_image)
   cv2.waitKey(0)

if cmd == "multi_frame_event":
   ASN.help()
   event_id = sys.argv[2]
   event_day = ASN.event_id_to_date(event_id)
   ASN.set_dates(event_day)
   ASN.multi_frame_event(event_day, sys.argv[2])

if cmd == "refine_event":
   ASN.help()
   event_id = sys.argv[2]
   event_day = ASN.event_id_to_date(event_id)
   ASN.set_dates(event_day)
   ASN.refine_event(event_day, sys.argv[2])

if cmd == "event_calibs":
   ASN.help()
   event_id = sys.argv[2]
   event_day = ASN.event_id_to_date(event_id)
   ASN.set_dates(event_day)
   ASN.event_calibs(event_day, sys.argv[2])
    

if cmd == "resolve_event":
   ASN.help()
   event_id = sys.argv[2]
   event_day = ASN.event_id_to_date(event_id)
   ASN.set_dates(event_day)
   ASN.sync_log = {}
   
   wget_cmds = ASN.get_event_media(event_id)
   review = False 
   if len(sys.argv) > 3:
      review = True
   if review is True: 
      print("Step 1")
      ASN.review_event(sys.argv[2])
      print("Step 2")
      (review_image, map_img, obs_imgs, marked_images, event_data, obs_data) = ASN.review_event_step2()

      for ob in obs_data:
         print(ob)


      if "2d_status" not in event_data:
         event_data = ASN.get_2d_status(event_data, obs_data)

      ASN.echo_event_data(event_data, obs_data)

      if review_image is not None:
         #print("YO")
         cv2.imshow("REVIEW IMAGE", review_image)
         cv2.waitKey(30)


   event_data_file = ASN.local_evdir + ASN.event_id + "/" + ASN.event_id + "_EVENT_DATA.json"
   obs_data_file = ASN.local_evdir + ASN.event_id + "/" + ASN.event_id + "_OBS_DATA.json"

   ASN.resolve_event(sys.argv[2])
   exit()

if cmd == "publish_day":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.publish_day(event_day)
   cmd = "/usr/bin/python3 EM.py aer " + event_day 
   os.system(cmd)

   ASN.best_obs_day(sys.argv[2])
   # make event table
   ASN.event_table(sys.argv[2])

if cmd == "goto" or cmd == "goto_event":
   event_id = sys.argv[2]
   ASN.goto_event(event_id)

if cmd == "events_by_day":
   ASN.events_by_day_graph()

if cmd == "publish_event":
   event_day = sys.argv[2]
   ASN.help()
   force = 0
   ASN.publish_event(event_id)



if cmd == "day_solve":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   force = 0
   ASN.day_solve(event_day,force)

if cmd == "validate_events":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   force = 0
   ASN.validate_events(event_day)


if cmd == "timeline":

   event_day = sys.argv[2]
   ASN.event_timeline(event_day)

if cmd == "load_day_sql" or cmd == "reload":
   force = 0
   ASN.help()
   date = sys.argv[2]
   if date == "today":
      date = today
   if date == "yest":
      date = yest 
   ASN.day_load_sql(date, force)
   
 
   #ASN.review_event_day(date)
   print("Done load")

if cmd == "review_coin_events":
   event_day = sys.argv[2]
   ASN.set_dates(event_day)
   ASN.review_coin_events(event_day, fix_bad=True)

if cmd == "coin_events":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   force = 1 
   ASN.day_coin_events(event_day,force)


if cmd == "day_load_solve_results" or cmd == "load_solves":
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.day_load_solves(event_day)
   print("Loaded solves")

if cmd == "do_all":
   ASN.help()
   if len(sys.argv) == 4:
      force = 1
   else:
      force = 0
   date = sys.argv[2]
   if date == "today":
      date = today
   if date == "yest":
      date = yest 

   # don't load every time, this call takes a while!
   # this should be handled in set_dates! need to test/confirm though
   # this should be done on the AWS side and the gz file is all that should be 
   # downloaded. However, this is not always the case!

   year, month, day = date.split("_")
   evdir = "/mnt/f/EVENTS/" + year + "/" + month + "/" + day + "/" 
   obs_file = evdir + date + "_ALL_OBS.json"
   obs_dict_file = evdir + date + "_OBS_DICT.json"
   obs_file_old = 0
   obs_dict_old = 0
   if os.path.exists(obs_file):
      ss, obs_file_old = get_file_info(obs_file)
      print(ss, obs_file_old)
   if os.path.exists(obs_dict_file):
      ss, obs_dict_old = get_file_info(obs_dict_file)
      print(ss, obs_dict_old)

   # if this file is > 12 hours old re make it
   # or if date 
   if os.path.exists(obs_file) is False or obs_file_old > (60*4):
      os.system("./DynaDB.py udc " + date)

   # if obs dict file is > 24 hours old re make it 
   if os.path.exists(obs_dict_file) is True and obs_dict_old > (60*24) :
      os.system("rm " + obs_dict_file)
   #and older than or older than obs file
   if obs_dict_old > obs_file_old :
      os.system("rm " + obs_dict_file)


   force = 1
   print("Loading day SQL.")
   ASN.day_load_sql(date, force)
   print("Done load")

   print("Do Coin events.")
   ASN.day_coin_events(date,force)
   print("Done coin")
   print("Do Solve .")

   ASN.day_solve(date,force)

   print("Load Solves .")
   ASN.day_load_solves(date)

   print("Plane test day.")
   ASN.plane_test_day(date)

   print("Done solve")
   print("Rysnc Data  .")
   ASN.rsync_data_only(date)
   print("Publish day.")
   ASN.publish_day(date)
   print("Update Meteor Days.")
   ASN.update_meteor_days()

   cmd = "/usr/bin/python3 DynaDB.py udc " + date  + " events"
   print(cmd)
   os.system(cmd)


   cmd = "/usr/bin/python3 ER.py " + date
   print(cmd)
   os.system(cmd)
   
   # all_events_report aer
   cmd = "/usr/bin/python3 EM.py aer " + date
   print(cmd)
   os.system(cmd)

   cmd = "/usr/bin/python3 PLT.py all_rad " + date 
   print(cmd)
   os.system(cmd)

   cmd = "/usr/bin/python3 solveWMPL.py vida_plots " + date 
   print(cmd)
   os.system(cmd)


   ## make data table 
   #cmd = "python3 solveWMPL.py vida_plots " + date 
   #print(cmd)
   #os.system(cmd)

   # make best obs 
   ASN.best_obs_day(sys.argv[2])

   # make event table 
   ASN.event_table(sys.argv[2])

   # rsync minimum data set
   ASN.rsync_data_only(date)

   # make the obs file for the day
   cmd = "/usr/bin/python3 EVStations.py " + date
   os.system(cmd)

   print("Load Solves .")
   ASN.day_load_solves(date)

   print("Update Final Stats!")
   ASN.all_year_events(year)


if cmd == "day_solve" or cmd == 'ds' or cmd == "solve_day":
   ASN.help()
   force = 0
   date = sys.argv[2]
   if date == "today":
      date = today
   if date == "yest":
      date = yest 
   ASN.day_solve(date,force)
   print("Done solve")

if cmd == "sync_dyna_day":
   ASN.help()
   date = sys.argv[2]
   ASN.sync_dyna_day(date)

if cmd == "check_event_status" or cmd == 'ces':
   ASN.help()
   event_id = sys.argv[2]
   ASN.check_event_status(event_id)
if cmd == "status":
   if len(sys.argv) < 2:
      print("No date provided!")
      print("USAGE: ./AllSkyNetwork status [YYYY_MM_DD]")
   event_day = sys.argv[2]
   ASN.help()
   ASN.set_dates(event_day)
   ASN.update_all_event_status(sys.argv[2])
   ASN.day_status(sys.argv[2])

if cmd == "purge_invalid":
   event_day = sys.argv[2]
   ASN.purge_invalid_events(event_day)

if cmd == "edit_event":
   event_id = sys.argv[2]
   ASN.edit_event(event_id)

if cmd == "remote_reducer":
   event_id = sys.argv[2]
   ASN.remote_reducer(event_id)

if cmd == "remote_cal_one":
   cal_image_file = sys.argv[2]
   ASN.remote_cal_one(cal_image_file)

if cmd == "merge_obs":
   event_id = sys.argv[2]
   ASN.merge_obs(event_id)

if cmd == "event_page":
   event_id = sys.argv[2]
   ASN.make_event_page(event_id)

if cmd == "sync_event":
   event_id = sys.argv[2]
   ASN.sync_event(event_id)

if cmd == "all_year_events":
   year = sys.argv[2]
   ASN.all_year_events(year)
if cmd == "year_report":
   year = sys.argv[2]
   print("Start year report for", year)
   ASN.year_report(year)
   print("Done year report for", year)
if cmd == "publish_year":
   year = sys.argv[2]
   ASN.publish_year(year)

if cmd == "resolve_event_day":
   event_day = sys.argv[2]
   ASN.plane_test_day(event_day)
   ASN.resolve_event_day(event_day)

if cmd == "slideshow":
   event_day = sys.argv[2]
   ASN.slideshow(event_day)

if cmd == "min_file_size":
   event_day = sys.argv[2]
   ASN.min_file_size(event_day)

if cmd == "event_day_status":
   event_day = sys.argv[2]
   ASN.event_day_status(event_day)

if cmd == "best_of":
   # make station/event mapping for this day
   event_day = sys.argv[2]
   dur = sys.argv[3]
   ASN.best_of(event_day, dur)

  
if cmd == "station_events":
   # make station/event mapping for this day
   event_day = sys.argv[2]
   ASN.station_events(event_day)
if cmd == "alltime":
   # make station/event mapping for this day
   ASN.all_time_index()
if cmd == "event_table":
   # make station/event mapping for this day
   ASN.event_table(sys.argv[2])
if cmd == "reconcile_events_day":
   # make station/event mapping for this day
   ASN.reconcile_events_day(sys.argv[2])

if cmd == "best_obs_day":
   # make station/event mapping for this day
   ASN.best_obs_day(sys.argv[2])
if cmd == "rerun_month":
   # make station/event mapping for this day
   ASN.rerun_month(sys.argv[2])
if cmd == "reconcile_obs":
   # make station/event mapping for this day
   ASN.reconcile_obs_day(sys.argv[2])
if cmd == "station_cal":
   # make station/event mapping for this day
   ASN.station_cal()
if cmd == "update_obs_int":
   # make station/event mapping for this day
   if sys.argv[3] == "ALL" or sys.argv[3] == "all":
      ASN.update_all_obs_int(sys.argv[2])
   else:
      ASN.update_obs_intensity(sys.argv[2], sys.argv[3])
