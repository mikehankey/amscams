import datetime
import cv2
import numpy as np
import ephem
import glob
from lib.VideoLib import load_video_frames, get_masks
from lib.ImageLib import stack_frames, median_frames, adjustLevels, mask_frame
from lib.UtilLib import convert_filename_to_date_cam

def find_image_stars(cal_img):
   bgavg = np.mean(cal_img)
   thresh = bgavg * 1.5
   if thresh < 1:
      thresh =  10

   print("THREHS:", thresh)
   if cal_img.shape == 3:
      cal_img= cv2.cvtColor(cal_img, cv2.COLOR_BGR2GRAY)
   cal_img = cv2.GaussianBlur(cal_img, (7, 7), 0)
   _, threshold = cv2.threshold(cal_img.copy(), thresh, 255, cv2.THRESH_BINARY)
   #cal_img = cv2.dilate(threshold, None , iterations=4)
   cal_img= cv2.convertScaleAbs(threshold)
   (_, cnts, xx) = cv2.findContours(cal_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
   star_pixels = []
   non_star_pixels = []
   cloudy_areas = []
   for (i,c) in enumerate(cnts):
      x,y,w,h= cv2.boundingRect(cnts[i])
      if w > 1 and h > 1:
         star_pixels.append((x,y,w,h))
         cv2.rectangle(cal_img, (x, y), (x + w, y + h), (128, 128, 128), 1)
   return(star_pixels,cal_img)

def last_sunrise_set(json_conf):
   cal_date =  datetime.date.today().strftime("%Y-%m-%d %H:%M:%S")
   print("CAL DATE:", cal_date)
   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = cal_date

   sun = ephem.Sun()
   sun.compute(obs)
   last_sunrise = obs.previous_rising(ephem.Sun())
   last_sunset = obs.previous_setting(ephem.Sun())
   # if the sun is currently set, use the next sunset as the end time not prev
   timediff = last_sunrise - last_sunset
   print(last_sunrise, last_sunset)
   print(timediff)
   sr_datetime = last_sunrise.datetime().strftime('%Y-%m-%d %H:%M:%S')
   ss_datetime = last_sunset.datetime().strftime('%Y-%m-%d %H:%M:%S')
   print(sr_datetime)
   print(ss_datetime)
   sr_datetime_t = datetime.datetime.strptime(sr_datetime, "%Y-%m-%d %H:%M:%S")
   ss_datetime_t = datetime.datetime.strptime(ss_datetime, "%Y-%m-%d %H:%M:%S")

   time_diff = sr_datetime_t - ss_datetime_t
   hr = time_diff.seconds / (3600)   
   print(sr_datetime,ss_datetime,hr)
   return(sr_datetime_t, ss_datetime_t,hr)

def find_hd_file(cal_glob):
   files = glob.glob(cal_glob)
   return(files)

def calibrate_camera(cams_id, json_conf, cal_date = None):
   # unless passed in use the last night as the calibration date
   # check 1 frame per hour and if there are enough stars then 
   # attempt to plate solve with astrometry
   # if that succeeds fit the plate and save the calibration file

   # first find the time of the last sun rise and sun set...
   last_sunrise, last_sunset,hr = last_sunrise_set(json_conf)
   print("Hours of Dark:", hr)
   for i in range (1,int(hr)-1):
      cal_date = last_sunset + datetime.timedelta(hours=i)
      cal_video = find_hd_file(cal_date.strftime('/mnt/ams2/HD/%Y_%m_%d_%H_%M*' + cams_id + '*.mp4') )
      frames = load_video_frames(cal_video[0],json_conf,25)
      cal_file = cal_video[0].replace('.mp4', '.jpg')
      el = cal_file.split("/")
      cal_file = "/mnt/ams2/cal/tmp/" + el[-1]
      print(cal_file)
      #cal_image, cal_image_np = stack_frames(frames,cal_file) 
      cal_image_np =  median_frames(frames) 
      cal_image_np = adjustLevels(cal_image_np, 55,1,255)
      masks = get_masks(cams_id, json_conf, hd = 1)
      cal_image_np = mask_frame(cal_image_np, [], masks)
      stars,cal_image_stars = find_image_stars(cal_image_np)
      print(len(stars) )
      cal_star_file = cal_file.replace(".jpg", "-stars.jpg")
      cv2.imwrite(cal_file, cal_image_np)
      cv2.imwrite(cal_star_file, cal_image_stars)
      exit() 

def find_best_cal_file(hd_datetime, hd_cam):
   cal_file = None
   return(cal_file)

def reduce_object(object, sd_video_file, hd_file, hd_trim, hd_crop_file, hd_crop_box, json_conf, cal_file = None):

   hd_datetime, hd_cam, hd_date, hd_y, hd_m, hd_d, hd_h, hd_M, hd_s = convert_filename_to_date_cam(hd_file)

   if cal_file is None:
      cal_file = find_best_cal_file(hd_datetime, hd_cam)

   el = hd_trim.split("-trim-")
   min_file = el[0] + ".mp4"
   print(el[1])
   ttt = el[1].split("-")
   trim_num = ttt[0]

   print("REDUCE OBJECT", trim_num)

   meteor_frames = []
   extra_sec = int(trim_num) / 25
   start_frame_time = hd_datetime + datetime.timedelta(0,extra_sec)
   start_frame_str = start_frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
   start_frame_num = object['history'][0][0]
   for hist in object['history']:
      fc,x,y,w,h,mx,my = hist
      hd_x = x + hd_crop_box[0] 
      hd_y = x + hd_crop_box[1] 

      extra_sec = (start_frame_num + fc) /  25
      frame_time = hd_datetime + datetime.timedelta(0,extra_sec)
      frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      if cal_file is None:
         ra, dec, rad, decd, az, el = 0,0,0,0,0,0
      meteor_frames.append((fc,frame_time_str,x,y,w,h,hd_x,hd_y,ra,dec,rad,decd,az,el))

   return(meteor_frames) 

def plate_solve(cal_file):

   el = cal_file.split("/")

   wcs_file = cal_file.replace(".jpg", ".wcs")
   grid_file = cal_file.replace(".jpg", "-grid.png")

   star_file = cal_file.replace(".jpg", "-stars-out.jpg")
   star_data_file = cal_file.replace(".jpg", "-stars.txt")
   astr_out = cal_file.replace(".jpg", "-astrometry-output.txt")

   wcs_info_file = cal_file.replace(".jpg", "-wcsinfo.txt")

   quarter_file = cal_file.replace(".jpg", "-1.jpg")

   image = cv2.imread(cal_file)

   if len(image.shape) > 2:
      gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
   else:
      gray = image
   height = gray.shape[0]
   width = gray.shape[1]

   cmd = "/usr/local/astrometry/bin/solve-field " + cal_file + " --crpix-center --cpulimit=30 --verbose --no-delete-temp --overwrite --width=" + str(width) + " --height=" + str(height) + " --scale-low 50 --scale-high 90 > " + astr_out + " 2>&1"
   print(cmd)
   os.system(cmd)
   os.system("grep Mike " + astr_out + " >" +star_data_file + " 2>&1" )

   cmd = "/usr/bin/jpegtopnm " + cal_file + "|/usr/local/astrometry/bin/plot-constellations -w " + wcs_file + " -o " + grid_file + " -i - -N -C -G 600"
   os.system(cmd)

   cmd = "/usr/local/astrometry/bin/wcsinfo " + wcs_file + " > " + wcs_info_file
   os.system(cmd)

   bright_star_data = parse_astr_star_file(star_data_file)
   #plot_bright_stars(cal_file, image, bright_star_data)
   solved = cfe(grid_file)

   return(solved)

