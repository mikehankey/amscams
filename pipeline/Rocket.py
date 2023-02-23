"""
ad hoc reducer / utility for dealing with rocket launches
"""
import scipy
import numpy as np 
import cv2
import os
import sys 

from lib.PipeDetect import find_object, analyze_object
from collections import deque
from Classes.AllSkyNetwork import AllSkyNetwork
from lib.PipeUtil import convert_filename_to_date_cam
from lib.PipeVideo import load_frames_simple 
from recal import make_plate_image, get_star_points, get_image_stars, recenter_fov, reduce_fov_pos, get_contours_in_image, do_photo
from lib.PipeAutoCal import minimize_poly_multi_star, get_catalog_stars, update_center_radec, draw_star_image, XYtoRADec
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.PipeUtil import load_json_file, save_json_file
import datetime


def test_cal(cal_params, gray_image):
   show_img = gray_image.copy()
   # loop over stars and display
   cat_stars = get_catalog_stars(cal_params)
   found = 0
   total = 0
   for star in cat_stars[0:100]:
      name, mag, ra, dec, cat_x, cat_y = star

      if 10 < cat_x < 1920 and 10 < cat_y < 1080:
         y1 = int(cat_y - 10)
         y2 = int(cat_y + 10)
         x1 = int(cat_x - 10)
         x2 = int(cat_x + 10)
         img = gray_image[y1:y2,x1:x2]

         cnts = find_star_in_img(img)

         if len(cnts) == 1:
            x,y,w,h = cnts[0]
            x += int(x1 + (w/2))
            y += int(y1 + (h/2))
            cv2.circle(show_img, (int(x),int(y)), 10, (255,255,255),1)
            found += 1
         total += 1 
      cv2.circle(show_img, (int(cat_x),int(cat_y)), 25, (255,255,255),1)
      cv2.imshow('pepe', show_img)
   if total > 0:
      perc_found = int((found / total) * 100)
   else:
      perc_found = 0
   print(perc_found , "%")
   cv2.putText(show_img, str(perc_found) + "% found",  (1000,500), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)
   
   cv2.imshow('pepe', show_img)
   cv2.waitKey(30)
   return(perc_found)


def find_star_in_img(img):
   min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(img)
   thresh_val = int(max_val * .95)
   avg_val = np.mean(img)
   pxd = max_val - avg_val
   if pxd < 10:
      return([])
   _, thresh_image = cv2.threshold(img, thresh_val, 255, cv2.THRESH_BINARY)

   cv2.imshow('pepe2', thresh_image)
   cv2.waitKey(30)
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

def reduce_rocket_clip(vid_fn, frames, med_frame, cal_params, remote_json_conf,reduce_data={}):
   (start_clip_time, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(vid_file)

   fn = vid_fn.split("/")[-1]
   st = fn.split("_")[0]
   fn = fn.replace(st + "_", "")
   reduce_data = {}
   rolling = deque(maxlen=50)
   print("FRAMES:", len(frames))


   med_frame = cv2.resize(med_frame, (frames[0].shape[1],frames[0].shape[0]))
   last_frame = None
   fc = 0
   print(vid_fn)
   cap = cv2.VideoCapture(vid_fn)
   frames = []
   go = 1
   frame_count = 0
   objects = {}
   med_frame = cv2.resize(med_frame,(1920,1080))

   stack = None
   stack_notes = None
   stack_annotations = []

   if "roi_area" in frame_data:
      print("ROI", frame_data['roi_area'])
      rx1,ry1,rx2,ry2 = frame_data['roi_area']
      mask = np.zeros((1080,1920),dtype=np.uint8)
      mask[0:1080,0:1920] = 255
      mask[ry1:ry2,rx1:rx2] = 0 
   else:
      rx1,ry1,rx2,ry2 = 0,0,0,0
      mask = np.zeros((1080,1920),dtype=np.uint8)
 
   show_frame = None
   while go == 1:
      _ , frame = cap.read()
      extra_sec = fc / 25
      frame_time = start_clip_time + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


      if frame is None:
         if frame_count <= 5 :
            cap.release()
         else:
            go = 0
         continue
      frame_count += 1

      frame = cv2.resize(frame,(1920,1080))

      if stack is None:
         stack = frame.copy()
         #stack_notes = frame.copy()

      rolling.append(frame)

      gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      show_img = frame.copy()
      if fc > 25:
         med_frame = rolling[0] #cv2.convertScaleAbs(np.median(np.array(rolling[0:5]), axis=0))
         med_frame = cv2.resize(med_frame, (frame.shape[1],frame.shape[0]))
         sub = cv2.subtract(frame, med_frame)
      else:    
         med_frame = cv2.resize(med_frame, (frame.shape[1],frame.shape[0]))
         sub = cv2.subtract(frame, med_frame)
      if len(sub.shape) == 3:
         sub= cv2.cvtColor(sub, cv2.COLOR_BGR2GRAY)

      
      sub = cv2.subtract(sub, mask)
      #cv2.imshow('sub', sub)

      #cv2.imshow('mask', mask)
      #cv2.waitKey(30)

      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
      thresh_val = int(max_val * .65)
      if thresh_val < 15:
         thresh_val = 15 
      _, thresh_image = cv2.threshold(sub, thresh_val, 255, cv2.THRESH_BINARY)
      thresh_image = cv2.dilate(thresh_image, None, iterations=4)
      cnts = get_contours_in_image(thresh_image)
      icnts = []
      #print("CNTS", cnts) 

      if fc not in frame_data:
         frame_data[fc] = {}
      stack_notes = stack.copy()
      for x,y,w,h in cnts:
         cx = int(x + w/2)
         cy = int(y + h/2)
         new_x, new_y, img_ra,img_dec, img_az, img_el = XYtoRADec(cx,cy,fn,cal_params,remote_json_conf)
         if w > h:
            radius = w
         else:
            radius = h 
         star_flux = do_photo(gray_frame, (cx,cy), radius+1)
         if star_flux < 100:
            continue
         obj_id, objects = find_object(objects, fc,cx, cy, w, h, star_flux, 0, 0, None)
         icnts.append((frame_time_str,cx,cy,radius,img_ra,img_dec,img_az,img_el,star_flux))
         cv2.rectangle(show_img, (cx-radius,cy-radius), (cx+radius, cy+radius) , (0, 0, 0), 1)
         cv2.putText(show_img, str(obj_id),  (cx+5,cy-5), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)
         cv2.putText(show_img, str(round(img_az,2)) + "/" + str(round(img_el,2)),  (cx+15,cy-15), cv2.FONT_HERSHEY_SIMPLEX, .4, (128,128,128), 1)

         show_frame = frame.copy()  
         if fc % 250 == 0:
            desc = str(obj_id) + " : " + str(int(cx)) + ", " + str(int(cy)) + " - " + str(round(img_az,2)) + " / " + str(round(img_el,2))
            stack_annotations.append((fc, frame_time_str, obj_id, cx, cy, radius, star_flux, img_ra, img_dec, img_az, img_el))

            cv2.rectangle(show_frame, (cx-radius,cy-radius), (cx+radius, cy+radius) , (0, 0, 0), 1)
            cv2.rectangle(stack_notes, (cx-radius,cy-radius), (cx+radius, cy+radius) , (0, 0, 0), 1)
            cv2.putText(stack_notes, str(desc),  (cx+14,cy-14), cv2.FONT_HERSHEY_SIMPLEX, .6, (0,0,0), 1)
            cv2.putText(stack_notes, str(desc),  (cx+15,cy-15), cv2.FONT_HERSHEY_SIMPLEX, .6, (255,255,255), 1)


         print(fc, frame_time_str, obj_id, cx, cy, radius, star_flux, img_ra,img_dec, img_az, img_el)

      frame_data[fc]['cnts'] = cnts 
      frame_data[fc]['icnts'] = icnts 

      #cv2.imshow('pepe2', thresh_image)
      #cv2.imshow('pepe', show_img)
      #cv2.waitKey(30)
      if fc % 250 == 0:
         stack = stack_stack(frame, stack)
         if stack_notes is None:
            stack_notes = stack.copy()
         cv2.rectangle(stack_notes, (rx1,ry1), (rx2 , ry2 ), (255, 255, 255), 1)
         if show_frame is None:
            show_frame = frame.copy()
         cv2.rectangle(show_frame, (rx1,ry1), (rx2 , ry2 ), (255, 255, 255), 1)
         cv2.imshow('frame', show_frame)
         cv2.imshow('stack', stack_notes)
         cv2.waitKey(30)


      fc += 1
   reduce_data["stack_annotations"] = stack_annotations
   reduce_data["frame_data"] = frame_data
   reduce_data["objects"] = objects 
   return(reduce_data, stack)

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
json_file = obs_file.replace(".mp4", ".json")
cal_image_file = obs_file.replace(".mp4", "-cal.jpg")
frame_data_file = obs_file.replace(".mp4", "-frame_data.json")
stack_file = obs_file.replace(".mp4", "-stacked.jpg")
if os.path.exists(frame_data_file) is True:
   frame_data = load_json_file(frame_data_file)
else:
   frame_data = {}

obs_fn = obs_file.split("/")[-1]
obs_dir = obs_file.replace(obs_fn, "")
station_id = obs_fn.split("_")[0]
vid_file = obs_fn.replace(station_id + "_", "")
cal_fn = vid_file
tdate = vid_file[0:10]
(f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(vid_file)

# load 25 frames of the video file 
frames = load_frames_simple(obs_file, 25)

# make a median star image from the 1st second of frames.
med_frame = cv2.convertScaleAbs(np.median(np.array(frames[0:25]), axis=0))
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
print(frame_data.keys())

if "cal_params" not in frame_data:
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
         perc = test_cal(cal_params, gray_image)
         if perc > best_p:
            best_p = perc
            best_cal = cal_params.copy()
         if cc == 0:
            first_cal = cal_params.copy()
         print("R", row)
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
   cal_params = frame_data['cal_params']
   remote_json_conf = frame_data['remote_json_conf']
   cal_params = update_center_radec(vid_file,cal_params,remote_json_conf)

print("CENTER AZ/EL", cal_params['center_az'],cal_params['center_el'])
print("PRIMARY OBJECTS")
if "primary_objects" not in frame_data:
   frame_data['primary_objects'] = []
   primary_objects = []
else:
   primary_objects = frame_data['primary_objects'] 


if "roi_area" in frame_data:
   rx1,ry1,rx2,ry2 = frame_data['roi_area']

if "cal_params" in frame_data:
   #redo = input("Do you want to reprocess the frame data?")
   redo = "Y"
   if redo == "Y" or redo == "y":
      frame_data, stack = reduce_rocket_clip(obs_file, frames, med_frame, cal_params, remote_json_conf, frame_data)
   else:
      stack = cv2.imread(stack_file)
else:
   frame_data, stack = reduce_rocket_clip(obs_file, frames, med_frame, cal_params, remote_json_conf, frame_data)



frame_data['remote_json_conf'] = remote_json_conf
frame_data['cal_params'] = cal_params 
try:
   frame_data['roi_area'] = [rx1,ry1,rx2,ry2] 
except:
   roistr = input ("Enter the 4 ROI values (rx1,ry1,rx2,ry2) : ")
   rx1,ry1,rx2,ry2 = roistr.split(",")
   frame_data['roi_area'] = [int(rx1),int(ry1),int(rx2),int(ry2)] 

frame_data['primary_objects'] = primary_objects
cv2.imwrite(stack_file, stack)
stack_notes_file = stack_file.replace(".jpg", "-notes.jpg")
stack_notes = stack.copy()

if True:
   if "roi_area" in frame_data:
      rx1,ry1,rx2,ry2 = frame_data['roi_area']
      mask = np.zeros((1080,1920),dtype=np.uint8)
      mask[0:1080,0:1920] = 255
      mask[ry1:ry2,rx1:rx2] = 0 
   else:
      rx1,ry1,rx2,ry2 = 0,0,0,0
      mask = np.zeros((1080,1920),dtype=np.uint8)


for row in frame_data['stack_annotations']:
   (fc, frame_time, obj_id, cx, cy, radius, star_flux, image_ra, img_dec, img_az, img_el) = row
   if mask[cy,cx] == 255:
      continue
   frame_file = obs_dir + "imgs/" + obs_fn + "-" + str(fc) + ".jpg"
   if os.path.exists(frame_file) is True:
      fimg = cv2.imread(frame_file)
      stack_notes = fimg
   if len(frame_data['primary_objects']) > 1 and obj_id not in frame_data['primary_objects']:
      tsize = .4
      desc = str(obj_id) 
      color = [128,128,128]
   else:
      tsize = .6
      color = [255,255,255]
      #desc = str(fc) + "-" + str(obj_id) + " : " + str(int(cx)) + ", " + str(int(cy)) + " - " + str(round(img_az,2)) + " / " + str(round(img_el,2))
      frame_time_short = frame_time.split(" ")[-1]
      desc = str(obj_id) + " : " + str(frame_time_short) + " " + str(round(img_az,2)) + " / " + str(round(img_el,1))
      cv2.putText(stack_notes, desc,  (cx+14,cy+14), cv2.FONT_HERSHEY_SIMPLEX, tsize, color, 1)
      cv2.putText(stack_notes, desc,  (cx+15,cy+15), cv2.FONT_HERSHEY_SIMPLEX, tsize, color, 1)
      cv2.rectangle(stack_notes, (rx1,ry1), (rx2, ry2) , (0, 0, 0), 1)
   cv2.imshow('pepe', stack_notes)
   cv2.waitKey(30)

cv2.imwrite(stack_notes_file, stack_notes)
save_json_file(frame_data_file, frame_data)

