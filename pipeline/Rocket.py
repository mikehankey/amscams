"""
ad hoc reducer / utility for dealing with rocket launches
"""
import time
import sqlite3
import scipy
import numpy as np 
import cv2
import os
import sys 

from lib.PipeDetect import find_object, analyze_object
from collections import deque
from Classes.AllSkyNetwork import AllSkyNetwork
from lib.PipeUtil import convert_filename_to_date_cam, calc_dist, angularSeparation
from lib.PipeVideo import load_frames_simple 
from recal import make_plate_image, get_star_points, get_image_stars, recenter_fov, reduce_fov_pos, get_contours_in_image, do_photo, get_xy_for_ra_dec, minimize_fov, remove_bad_stars, remote_cal
from lib.PipeAutoCal import minimize_poly_multi_star, get_catalog_stars, update_center_radec, draw_star_image, XYtoRADec
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.PipeUtil import load_json_file, save_json_file
import datetime
cv2.namedWindow("pepe")
cv2.resizeWindow("pepe", 1920, 1080)


def quick_pair_stars(cal_params):
   catalog_stars = get_catalog_stars(cal_params, 5)
   good_stars = []
   for cs in catalog_stars:
      (name,mag,ra,dec,new_cat_x,new_cat_y) = cs
      if 0 <= new_cat_x < 1900 and 0 <= new_cat_y <= 1080 and mag < 4:
         print(cs)
         good_stars.append(cs)
   print(len(good_stars), len(cal_params['star_points']))

   # loop over img stars and find closest cat star...


def test_cal(cal_params, gray_image, cal_fn, json_conf):
   show_img = gray_image.copy()
   # loop over stars and display
   cat_stars = get_catalog_stars(cal_params)
   found = 0
   total = 0
   img_stars = []
   cat_image_stars = []
   for star in cat_stars[0:50]:
      name, mag, ra, dec, cat_x, cat_y = star

      if 20 < cat_x < 1920 - 20 and 20 < cat_y < 1080 - 20:
         y1 = int(cat_y - 20)
         y2 = int(cat_y + 20)
         x1 = int(cat_x - 20)
         x2 = int(cat_x + 20)
         img = gray_image[y1:y2,x1:x2]
         cnts = find_star_in_img(img)

         if len(cnts) == 1:
            x,y,w,h = cnts[0]
            x += int(x1 + (w/2))
            y += int(y1 + (h/2))
            cv2.circle(show_img, (int(x),int(y)), 10, (255,255,255),1)
            new_cat_x, new_cat_y = get_xy_for_ra_dec(cal_params, ra, dec)
            res_px = calc_dist((x,y),(new_cat_x,new_cat_y))
            new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(x,y,cal_fn,cal_params,json_conf)
            match_dist = angularSeparation(ra,dec,img_ra,img_dec)
            real_res_px = res_px
            radius = 5
            try:
               star_flux = do_photo(gray_image, (x,y), radius)
            except:
               star_flux = 0
            img_stars.append((x,y,star_flux))
            cat_image_stars.append((name,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,x,y,real_res_px,star_flux))
            found += 1
         total += 1 
      cv2.circle(show_img, (int(cat_x),int(cat_y)), 25, (255,255,255),1)
      cv2.imshow('pepe', show_img)
   if total > 0:
      perc_found = int((found / total) * 100)
   else:
      perc_found = 0
   print(perc_found , "%")
   cv2.putText(show_img, str(perc_found) + "% of the top 50 brightest stars found",  (800,500), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
   
   cv2.imshow('pepe', show_img)
   cv2.waitKey(30)
   time.sleep(1)
   return(perc_found, img_stars,cat_image_stars)


def find_star_in_img(img):
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(img)
   thresh_val = int(max_val * .95)
   avg_val = np.mean(img)
   pxd = max_val - avg_val
   if pxd < 10:
      return([])
   _, thresh_image = cv2.threshold(img, thresh_val, 255, cv2.THRESH_BINARY)

   #cv2.imshow('pepe2', thresh_image)
   #cv2.waitKey(30)
   cnts = get_contours_in_image(thresh_image)

   if len(cnts) >= 1:
      cnts = sorted(cnts, key=lambda x: x[2] * x[3], reverse=True)
      #cnts = [cnts[0]]
   return(cnts)

def stack_stack( pic1, pic2):
      ipic1 = Image.fromarray(pic1)
      ipic2 = Image.fromarray(pic2)
      stacked_image=ImageChops.lighter(ipic1,ipic2)
      return(np.array(stacked_image))

def reduce_rocket_clip(vid_fn, frames, med_frame, cal_params, remote_json_conf):
   (start_clip_time, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(vid_file)

   fn = vid_fn.split("/")[-1]
   st = fn.split("_")[0]
   fn = fn.replace(st + "_", "")
   reduce_data = {}
   rolling = deque(maxlen=50)


   med_frame = cv2.resize(med_frame, (frames[0].shape[1],frames[0].shape[0]))
   last_frame = None
   fc = 0
   cap = cv2.VideoCapture(vid_fn)
   frames = []
   go = 1
   frame_count = 0
   objects = {}
   med_frame = cv2.resize(med_frame,(1920,1080))

   stack = None
   stack_notes = None
   stack_annotations = []

   if "roi_area" in obs_data:
      print("ROI", obs_data['roi_area'])
      rx1,ry1,rx2,ry2 = obs_data['roi_area']
      if type(rx1) != int:
         rx1 = int(rx1)
         rx2 = int(rx2)
         ry1 = int(ry1)
         ry2 = int(ry2)
      mask = np.zeros((1080,1920),dtype=np.uint8)
      mask[0:1080,0:1920] = 255
      mask[ry1:ry2,rx1:rx2] = 0 
   else:
      rx1,ry1,rx2,ry2 = 0,0,0,0
      mask = np.zeros((1080,1920),dtype=np.uint8)
 
   show_frame = None
   frame_data = {}
   hdm_x = 1920 / 1280 
   hdm_y = 1080 / 720
   while go == 1:

      _ , frame = cap.read()


      if frame is None:
         if frame_count <= 5 :
            cap.release()
         else:
            go = 0
         continue
      frame_count += 1

      frame = cv2.resize(frame,(1920,1080))
      frames.append(frame.copy())

      extra_sec = fc / 25
      frame_time = start_clip_time + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]




      if stack is None:
         stack = frame.copy()
         #stack_notes = frame.copy()

      rolling.append(frame)
      #if fc != 0 and fc % 2 != 0:
      #   fc += 1
      #   continue

      gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      show_img = frame.copy()
      if fc > 1:
         # too slow
         #med_frame = cv2.convertScaleAbs(np.median(np.array([rolling[0], rolling[1], rolling[2]]), axis=0))

         med_frame = rolling[0] #cv2.convertScaleAbs(np.median(np.array(rolling[0:5]), axis=0))
         med_frame = cv2.resize(med_frame, (frame.shape[1],frame.shape[0]))
         sub = cv2.subtract(frame, med_frame)
      else:    
         med_frame = cv2.resize(med_frame, (frame.shape[1],frame.shape[0]))
         sub = cv2.subtract(frame, med_frame)
      if len(sub.shape) == 3:
         sub= cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)
 
      #cv2.imshow('sub', sub)
      #cv2.imshow('mask', mask)
      
      sub = cv2.subtract(sub, mask)

      #cv2.imshow('mask', mask)
      #cv2.waitKey(30)

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
      thresh_val = int(max_val * .65)
      if thresh_val < 15:
         thresh_val = 15 
      _, thresh_image = cv2.threshold(sub, thresh_val, 255, cv2.THRESH_BINARY)
      thresh_image = cv2.dilate(thresh_image, None, iterations=4)
      cv2.imshow('sub', thresh_image)
      cnts = get_contours_in_image(thresh_image)
      if len(cnts) > 20:
         cnts = cnts[0:20]
      icnts = []
      print("CNTS", len(cnts) )
 
      if fc not in frame_data:
         frame_data[fc] = {}
      stack_notes = stack.copy()
      show_frame = frame.copy()  
      for x,y,w,h in cnts:
         cx = int(int(x + (w/2)))
         cy = int(int(y + (h/2)))
         
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(cx,cy,fn,cal_params,remote_json_conf)
         if w > h:
            radius = w
         else:
            radius = h 
         star_flux = do_photo(gray_frame, (cx,cy), radius+1)
         #if star_flux < 100:
         #   continue
         obj_id, objects = find_object(objects, fc,cx, cy, w, h, star_flux, 0, 0, None)
         icnts.append((obj_id,frame_time_str,cx,cy,radius,img_ra,img_dec,img_az,img_el,star_flux))
         #cv2.rectangle(show_img, (cx-radius,cy-radius), (cx+radius, cy+radius) , (0, 0, 0), 1)
         #cv2.putText(show_img, str(obj_id),  (cx+5,cy-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
         #cv2.putText(show_img, str(round(img_az,2)) + "/" + str(round(img_el,2)),  (cx+15,cy-15), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)

         #if fc % 1 == 0:
         if True:
            desc = str(fc) + " : " + str(obj_id) + " - " + str(round(img_az,2)) + " / " + str(round(img_el,2))
            stack_annotations.append((fc, frame_time_str, obj_id, cx, cy, radius, star_flux, img_ra, img_dec, img_az, img_el))

            cv2.rectangle(show_frame, (cx-radius,cy-radius), (cx+radius, cy+radius) , (255, 255, 255), 1)
            cv2.putText(show_frame, str(desc),  (cx+14,cy-14), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
            cv2.imshow('pepe', show_frame)
            cv2.waitKey(30)


         print(fc, frame_time_str, obj_id, cx, cy, radius, star_flux, img_ra,img_dec, img_az, img_el)

      frame_data[fc]['cnts'] = cnts 
      frame_data[fc]['icnts'] = icnts 

      fc += 1
   
   reduce_data["stack_annotations"] = stack_annotations
   reduce_data["frame_data"] = frame_data
   reduce_data["objects"] = objects 
   return(reduce_data, stack, frames)

# __main__
# setup
#
# create AllSkyNetwork object 
ASN = AllSkyNetwork()
# load station data
ASN.load_stations_file()
# create handles for the network calibration db 
ASN.setup_cal_db()

os.system("clear")

# START HERE. 

# LOAD IN 1 OBS FILE AT A TIME AND GET THE REDUCTION DATA BACK

# get filename to work on from args and then setup startup variables
obs_file = sys.argv[1]
obs_fn = obs_file.split("/")[-1]
obs_dir = obs_file.replace(obs_fn, "")
station_id = obs_fn.split("_")[0]


json_file = obs_file.replace(".mp4", ".json")
cal_image_file = obs_file.replace(".mp4", "-cal.jpg")
frame_data_file = obs_file.replace(".mp4", "-frame_data.json")
stack_file = obs_file.replace(".mp4", "-stacked.jpg")
if os.path.exists(frame_data_file) is True:
   obs_data = load_json_file(frame_data_file)
else:
   obs_data = {}

if "event_id" not in obs_data:
   obs_data['event_id'] = input("Event id?")

good_obs_file = obs_dir + obs_data['event_id'] + "_GOOD_OBS.json"
if os.path.exists(good_obs_file) :
   good_obs = load_json_file(good_obs_file)
   input("Loaded good obs data")
else:
   print(good_obs_file)
   input("no good obs data")
print("St:", station_id)
obs_file_name = obs_fn.replace(station_id + "_", "")
print("OBS:", obs_file_name)
good_obs_found = 0 
if station_id in good_obs:
   if obs_file_name in good_obs[station_id]:
      good_obs_found = 1 
print("OBS FOUND IN GOOD OBS:", good_obs_found)

if True:
   db_file = station_id + "_CALIB.db"
   #con = sqlite3.connect(":memory:")

   if os.path.exists(db_file) is False:
      cmd = "cat CALDB.sql |sqlite3 " + db_file
      print("Making calibration database...")

      print(cmd)
      os.system(cmd)
   #else:
   #   print("CAL DB EXISTS ALREADY")

   con = sqlite3.connect(db_file)
   cur = con.cursor()


vid_file = obs_fn.replace(station_id + "_", "")
cal_fn = vid_file
tdate = vid_file[0:10]
(f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(vid_file)

# load 25 frames of the video file 
first_frames = load_frames_simple(obs_file, 25)
stack = None

if False:
   for frame in frames:
      if stack is None:
         stack = frame
      else:
         stack = stack_stack( stack, frame)


# make a median star image from the 1st second of frames.
med_frame = cv2.convertScaleAbs(np.median(np.array(first_frames[0:25]), axis=0))
med_frame = cv2.resize(med_frame, (1920,1080))
show_img = med_frame.copy()

# make it a gray if it is not already image 
if len(med_frame.shape) == 3:
   gray_image = cv2.cvtColor(med_frame, cv2.COLOR_BGR2GRAY)
else:
   gray_image = med_frame

# save median image as a calib frame
cv2.imwrite(cal_image_file, gray_image)
# get the default cal params and lens model
print(station_id, cam_id, f_datetime, ASN.photo_credits[station_id])

# if cal params not already in the frame data fetch them
best_cal = None

if "cal_params" not in obs_data:
   cal_params, remote_json_conf = ASN.get_remote_cal(station_id, cam_id, vid_file)
   best_p = 0
   cc = 0
   first_cal = None
   for row in cal_params['cal_range']:
      rcam_id, best_rend_date, best_rstart_date, best_az, best_el, best_pos, best_pxs, res = row 
   
      cal_params['center_az'] = best_az
      cal_params['center_el'] = best_el
      cal_params['position_angle'] = best_pos
      cal_params['pixscale'] = best_pxs
      cal_params = update_center_radec(vid_file,cal_params,remote_json_conf)

      if rcam_id == cam_id :
         if np.isnan(best_az) :
            print("SKIP:", best_az)
            continue 
         perc,img_stars,cat_image_stars = test_cal(cal_params, gray_image, cal_fn, remote_json_conf)
         if perc > best_p:
            best_p = perc
            best_cal = cal_params.copy()
         if cc == 0:
            first_cal = cal_params.copy()
         cc += 1
   if best_cal is not None:
      cal_params = best_cal
   if best_p < 25:
      # not a good cal match, use 1st cal in range as default
      cal_params = first_cal
   # update remote_json_conf with latest lat/lon
   #ASN.station_loc[st_id] = [lat,lon,alt]
   remote_json_conf['site']['device_lat'] = ASN.station_loc[station_id][0]
   remote_json_conf['site']['device_lng'] = ASN.station_loc[station_id][1]
   remote_json_conf['site']['device_alt'] = ASN.station_loc[station_id][2]
   cal_params = update_center_radec(cal_fn, cal_params,remote_json_conf)
   # get calibration stars that should/might be in the FOV
else:
   cal_params = obs_data['cal_params']
   remote_json_conf = obs_data['remote_json_conf']
   cal_params = update_center_radec(vid_file,cal_params,remote_json_conf)

#FINAL 
perc, img_stars,cat_image_stars = test_cal(cal_params, gray_image, cal_fn, remote_json_conf)
cal_params['cat_image_stars'] = cat_image_stars
temp_file = cal_image_file.replace(station_id + "_", "")

# get stars and cat stars

star_points, show_img = get_star_points(temp_file, gray_image.copy(), cal_params, station_id, cam_id, remote_json_conf)

#cal_params['cat_image_stars'] = pair_star_points(temp_file, gray_image, cal_params, remote_json_conf, con, cur, mcp, False)
cal_params['total_res_px'] = 1
cal_params['star_points'] = star_points

#cal_params = quick_pair_stars(cal_params)
cal_params['station_id'] = station_id
#cal_params, cat_stars = recenter_fov(temp_file, cal_params, gray_image.copy(), img_stars, remote_json_conf, con, cur)
print("CAL INFO:", len(cal_params['cat_image_stars']), cal_params['total_res_px'])
cal_params = minimize_fov(temp_file, cal_params, temp_file,gray_image,remote_json_conf, False,cal_params, "")

station_dir = "/mnt/f/EVENTS/STATIONS/" + station_id + "/" 
freecal_dir = station_dir + "/CAL/FREECAL/"
cal_dir = station_dir + "/CAL/FREECAL/"
if os.path.exists(freecal_dir) is False:
   os.makedirs(freecal_dir)
cal_root = cal_fn.split("-")[0]

local_cal_file = freecal_dir + cal_root + ".png"
local_json_file = freecal_dir + cal_root + ".json"

#cal_params_file = obs_file.replace(".mp4", "-cal_params.json")
#cal_image_file = obs_file.replace(".mp4", ".png")
cal_params['device_lat'] = remote_json_conf['site']['device_lat']
cal_params['device_lng'] = remote_json_conf['site']['device_lng']
cal_params['device_alt'] = remote_json_conf['site']['device_alt']

save_json_file(local_json_file, cal_params)


cal_fn = local_cal_file.split("/")[-1]
cv2.imwrite(local_cal_file, gray_image)

tweak = input("Do you want to tweak the calibration?")
if tweak == "Y" or tweak == "y":
   cal_params = remote_cal(station_id + "_" + cal_fn, con, cur)

   print("CAL PARAMS:", cal_params)
   perc, img_stars,cat_image_stars = test_cal(cal_params, gray_image, cal_fn, remote_json_conf)



# Tweek the cal?

print("CAL INFO:", len(cal_params['cat_image_stars']), cal_params['total_res_px'])


print("CENTER AZ/EL", cal_params['center_az'],cal_params['center_el'])
print("PRIMARY OBJECTS")
if "primary_objects" not in obs_data:
   obs_data['primary_objects'] = []
   primary_objects = []
else:
   primary_objects = obs_data['primary_objects'] 


if "roi_area" in obs_data:
   rx1,ry1,rx2,ry2 = obs_data['roi_area']

if "frame_data" in obs_data:
   redo = input("Do you want to reprocess the frame data?")
   #redo = "Y"
   if redo == "Y" or redo == "y":
      reduce_data, stack, frames = reduce_rocket_clip(obs_file, first_frames, med_frame, cal_params, remote_json_conf)
      obs_data['frame_data'] = reduce_data['frame_data']
      obs_data['objects'] = reduce_data['objects']
      obs_data['stack_annotations'] = reduce_data['stack_annotations']
   else:
      stack = cv2.imread(stack_file)
      frames = load_frames_simple(obs_file)
else:
   print("DID NOT ALREADY DO IT")
   reduce_data, stack, frames = reduce_rocket_clip(obs_file, first_frames, med_frame, cal_params, remote_json_conf)
   obs_data['frame_data'] = reduce_data['frame_data']
   obs_data['objects'] = reduce_data['objects']
   obs_data['stack_annotations'] = reduce_data['stack_annotations']
   #reduce_data , stack, frames = reduce_rocket_clip(obs_file, frames, med_frame, cal_params, remote_json_conf)

print("DID IT", len(frames))


obs_data['remote_json_conf'] = remote_json_conf
obs_data['cal_params'] = cal_params 

if "roi_area" not in obs_data:
   get_roi = True
   while get_roi is True:
      roistr = input ("Enter the 4 ROI values (rx1,ry1,rx2,ry2) : ")
      temp = roistr.split(",")
      if len(temp) == 4:
         rx1,ry1,rx2,ry2 = roistr.split(",")
         get_roi = False
   obs_data['roi_area'] = [int(rx1),int(ry1),int(rx2),int(ry2)] 
  

try:
   obs_data['roi_area'] = [rx1,ry1,rx2,ry2] 
except:
   roistr = input ("Enter the 4 ROI values (rx1,ry1,rx2,ry2) : ")
   rx1,ry1,rx2,ry2 = roistr.split(",")
   obs_data['roi_area'] = [int(rx1),int(ry1),int(rx2),int(ry2)] 
   rx1,ry1,rx2,ry2 = obs_data['roi_area']

obs_data['primary_objects'] = primary_objects



if stack is not None:
   cv2.imwrite(stack_file, stack)
stack_notes_file = stack_file.replace(".jpg", "-notes.jpg")
stack_notes = stack.copy()

if True:
   if "roi_area" in obs_data:
      rx1,ry1,rx2,ry2 = obs_data['roi_area']
      if type(rx1) != int:
         rx1 = int(rx1)
         ry1 = int(ry1)
         rx2 = int(rx2)
         ry2 = int(ry2)
      mask = np.zeros((1080,1920),dtype=np.uint8)
      mask[0:1080,0:1920] = 255
      print("RX:", rx1,ry1,rx2,ry2)
      mask[ry1:ry2,rx1:rx2] = 0 
   else:
      rx1,ry1,rx2,ry2 = 0,0,0,0
      mask = np.zeros((1080,1920),dtype=np.uint8)

fns = []
xs = []
ys = []
els = []
azs = []
times = []
ints = []
meteor_frame_data = []
mfd = {}
for fc in obs_data['frame_data']: 
   #if obs_data['frame_data'][fc][3] == 1:
   row = obs_data['frame_data'][fc]['icnts']
   #print("DONE", fc, row)
   for cnt in row:
      (obj_id, frame_time_str,cx,cy,radius,img_ra,img_dec,img_az,img_el,star_flux) = cnt 
      #(fc, frame_time, obj_id, cx, cy, radius, star_flux, image_ra, img_dec, img_az, img_el) = row
      show_frame = frames[int(fc)].copy()
      if str(obj_id) in obs_data['primary_objects'] or int(obj_id) in obs_data['primary_objects']:
         print("FOUND", row)
         fns.append(fc)
         times.append(frame_time_str)
         xs.append(cx)
         ys.append(cy)
         azs.append(img_az)
         els.append(img_el)
         ints.append(star_flux)
         meteor_frame_data.append((frame_time_str, fc, cx, cy, radius, radius, star_flux, img_ra, img_dec, img_az, img_el))
         mfd[fc] = [frame_time_str, fc, cx, cy, radius, radius, star_flux, img_ra, img_dec, img_az, img_el]
         desc = str(obj_id) + " " + str(round(float(img_az),2)) + " " + str(round(float(img_el),2))
         cv2.rectangle(show_frame, (cx-radius,cy-radius), (cx+radius, cy+radius) , (255, 255, 255), 1)
         cv2.putText(show_frame, str(desc),  (cx+14,cy-14), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
         cv2.imshow('pepe', show_frame)
         cv2.waitKey(30)
      else:
         print("NOT FOUND", obj_id, obs_data['primary_objects'])
if len(fns) == 0:
   print("NO PRIMARY OBJECT EXISTS YET! ENTER IT NOW!")
   primary_objects = input("Enter primary object ids (separate with commas if more than one)")
   if "," in primary_objects:
      el = split(",", primary_objects)
      obs_data['primary_objects'] = []
      for e in el:
         obs_data['primary_objects'].append(e)
   else:
      obs_data['primary_objects'] = [primary_objects]
      save_json_file(frame_data_file, obs_data)
      print("Updated obs with primary object. Run again.")
      exit()




# now edit the MFD if needed.
fc = int(min(fns))
go = True
while go is True:
   if fc in mfd:
      mfd_row = mfd[fc]
      (frame_time_str, fc, cx, cy, radius, radius, star_flux, img_ra, img_dec, img_az, img_el) = mfd_row
   else:
      mfd_row = None

   #cv2.rectangle(show_frame, (cx-radius,cy-radius), (cx+radius, cy+radius) , (255, 255, 255), 1)

   show_frame = frames[int(fc)]


   cv2.putText(show_frame, "FN: " + str(fc),  (1920-50,50), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)
   if mfd_row is not None:
      cv2.rectangle(show_frame, (cx-radius,cy-radius), (cx+radius, cy+radius) , (255, 255, 255), 1)

   cv2.imshow('pepe', show_frame)
   key = cv2.waitKey(0)
   if key == 27:
      go = False
   elif key == 97:
      # a rev 1 frame
      fc = fc - 1
      show_frame = frames[int(fc)]
      cv2.imshow('pepe', show_frame)
   elif key == 102:
      # a rev 1 frame
      fc = fc + 1
      if fc > len(frames) - 1:
         fc = 0
   elif key == 120:
      # x
      print("DELETE MFD") 

      show_frame = frames[int(fc)]
      cv2.imshow('pepe', show_frame)
   else:
      print("KEY WAS:", key)
   if fc < 0:
      fc = len(frames) - 1 
   if fc > len(frames) - 1:
      fc = 0

print("Saved", frame_data_file)
print("""

"fns": {:s},
"xs": {:s},
"ys": {:s},
"times": {:s},
"azs": {:s},
"els": {:s},
"ints": {:s}

""".format(str(fns), str(xs), str(ys), str(times), str(azs), str(els), str(ints)))


save_json_file(frame_data_file, obs_data)
# save / update GOOD OBS FILE?
if os.path.exists(good_obs_file) :
   good_obs[station_id][obs_file_name]['fns'] = fns
   good_obs[station_id][obs_file_name]['xs'] = xs
   good_obs[station_id][obs_file_name]['ys'] = ys
   good_obs[station_id][obs_file_name]['times'] = times
   good_obs[station_id][obs_file_name]['azs'] = azs
   good_obs[station_id][obs_file_name]['els'] = els 
   good_obs[station_id][obs_file_name]['ints'] = ints
   save_json_file(good_obs_file, good_obs)
   print("Saved:", good_obs_file)
