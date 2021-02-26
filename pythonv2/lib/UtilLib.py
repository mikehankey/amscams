import json
import cv2
import subprocess
import datetime
import math
import ephem
import numpy as np

def logger(prog_name, func_name, msg):
   dt = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S.%f")
   date  = datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")
   logfile = "/mnt/ams2/logs/" + date + "-proc-log.txt"
   logline = date + "|" + prog_name + "|" + func_name + "|" + msg + "\n"
   log = open(logfile, "a")
   log.write(logline)

def best_fit_slope_and_intercept(xs,ys):
    xs = np.array(xs, dtype=np.float64)
    ys = np.array(ys, dtype=np.float64)
    m = (((np.mean(xs)*np.mean(ys)) - np.mean(xs*ys)) /
         ((np.mean(xs)*np.mean(xs)) - np.mean(xs*xs)))

    b = np.mean(ys) - m*np.mean(xs)
    if math.isnan(m) is True:
       m = 1
       b = 1

    return m, b


def date_to_jd(year,month,day):
    """
    Convert a date to Julian Day.
    Algorithm from 'Practical Astronomy with your Calculator or Spreadsheet',
        4th ed., Duffet-Smith and Zwart, 2011.
    Parameters
    ----------
    year : int
        Year as integer. Years preceding 1 A.D. should be 0 or negative.
        The year before 1 A.D. is 0, 10 B.C. is year -9.
    month : int
        Month as integer, Jan = 1, Feb. = 2, etc.
    day : float
        Day, may contain fractional part.
    Returns
    -------
    jd : float
        Julian Day
    Examples
    --------
    Convert 6 a.m., February 17, 1985 to Julian Day
    >>> date_to_jd(1985,2,17.25)
    2446113.75
    """
    if month == 1 or month == 2:
        yearp = year - 1
        monthp = month + 12
    else:
        yearp = year
        monthp = month

    # this checks where we are in relation to October 15, 1582, the beginning
    # of the Gregorian calendar.
    if ((year < 1582) or
        (year == 1582 and month < 10) or
        (year == 1582 and month == 10 and day < 15)):
        # before start of Gregorian calendar
        B = 0
    else:
        # after start of Gregorian calendar
        A = math.trunc(yearp / 100.)
        B = 2 - A + math.trunc(A / 4.)

    if yearp < 0:
        C = math.trunc((365.25 * yearp) - 0.75)
    else:
        C = math.trunc(365.25 * yearp)

    D = math.trunc(30.6001 * (monthp + 1))

    jd = B + C + D + day + 1720994.5

    return jd



def angularSeparation(ra1,dec1, ra2,dec2):

   ra1 = math.radians(float(ra1))
   dec1 = math.radians(float(dec1))
   ra2 = math.radians(float(ra2))
   dec2 = math.radians(float(dec2))
   return math.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1)))


def check_running(progname, sec_grep = None):
   cmd = "ps -aux |grep \"" + progname + "\" | grep -v grep |wc -l"
    
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   #print(cmd)
   #print(output)
   output = int(output.replace("\n", ""))
   if int(output) > 0:
      return(output)
   else:
      return(0)




def get_sun_info(capture_date, json_conf):

   device_lat = json_conf['site']['device_lat']
   device_lng = json_conf['site']['device_lng']

   obs = ephem.Observer()

   obs.pressure = 0
   obs.horizon = '-0:34'
   obs.lat = device_lat
   obs.lon = device_lng
   obs.date = capture_date

   sun = ephem.Sun()
   sun.compute(obs)

   (sun_alt, x,y) = str(sun.alt).split(":")

   saz = str(sun.az)
   (sun_az, x,y) = saz.split(":")
   if int(sun_alt) < -10:
      sun_status = "night"
   else:
      sun_status = "day"
   return(sun_status, sun_az, sun_alt)



def calc_dist(p1,p2):
   x1,y1 = p1
   x2,y2 = p2
   dist = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
   return dist

def find_angle(p1,p2):
   myrad = math.atan2(p1[1]-p2[1],p1[0]-p2[0])
   mydeg = math.degrees(myrad)
   return(mydeg)

def find_slope(p1,p2):
   (x1,y1) = p1
   (x2,y2) = p2
   top = y2 - y1
   bottom = x2 - y2
   if bottom != 0:
      slope = top / bottom
   else:
      slope = 0
   return(slope)

def convert_filename_to_date_cam(file, ms = 0):
   el = file.split("/")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   if "-" in filename:
      xxx = filename.split("-")
      filename = xxx[0]
   el = filename.split("_")
   if len(el) >= 8:
      fy,fm,fd,fh,fmin,fs,fms,cam = el[0], el[1], el[2], el[3], el[4], el[5], el[6], el[7]
   else:
      fy,fm,fd,fh,fmin,fs,fms,cam = "1999", "01", "01", "00", "00", "00", "000", "010001"
   if "-" in cam:
      cel = cam.split("-")
      cam = cel[0]

   #print("CAM:", cam)
   #exit()

   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   if ms == 1:
      return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs,fms)

   else:
      return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)

def bound_leading_edge_cnt(x,y,img_w,img_h,x_dir_mod,y_dir_mod,sz=10):
   # left to right meteor, so only grab pixels to the right of the x
   print("XDIR MOD/YDIR MOD:", x_dir_mod, y_dir_mod)
   if x_dir_mod == -1:
      print("LEFT TO RIGHT X DIR")
      mnx = x
      mxx = x + sz
   else:
      # right to left meteor, so only grab pixels to the left of the x
      print("RIGHT TO LEFT X DIR")
      mxx = x
      mnx = x - sz
   if y_dir_mod == -1:
      mny = y 
      mxy = y + sz
      print("TOP TO DOWN Y DIR ", x,y,mnx,mxx, mny, mxy)
   else:
      print("DOWN TO TO UP Y DIR ")
      mxy = y
      mny = y - sz
   if mnx < 0:
      mnx = 0
      mxx = 0 + sz
   if mny < 0:
      mny = 0
      mxy = 0 + sz
   if mxx >= img_w:
      mxx = img_w 
      mnx = img_w - sz 
   if mxy >= img_h:
      mxy = img_h
      mny = img_h - sz 

   return(mnx,mny,mxx,mxy)


def bound_cnt(x,y,img_w,img_h,sz=10):
   if x - sz < 0:
      mnx = 0
   else:
      mnx = int(x - sz)

   if y - sz < 0:
      mny = 0
   else:
      mny = int(y - sz)

   if x + sz > img_w - 1:
      mxx = int(img_w - 1)
   else:
      mxx = int(x + sz)

   if y + sz > img_h -1:
      mxy = int(img_h - 1)
   else:
      mxy = int(y + sz)
   return(mnx,mny,mxx,mxy)

def better_parse_file_date(input_file):
   el = input_file.split("/")
   fn = el[-1]
   ddd = fn.split("_")
   Y = ddd[0]
   M = ddd[1]
   D = ddd[2]
   H = ddd[3]
   MM = ddd[4]
   S = ddd[5]
   MS = ddd[6]
   CAM = ddd[7]
   extra = CAM.split("-")
   cam_id = extra[0]
   cam_id = cam_id.replace(".mp4", "")
   f_date_str = Y + "-" + M + "-" + D + " " + H + ":" + MM + ":" + S
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam_id, f_date_str,Y,M,D, H, MM, S)


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    # Radius of earth in kilometers is 6371
    km = 6371* c
    bearing = math.atan2(math.sin(lon2-lon1)*math.cos(lat2), math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(lon2-lon1))
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    return km, bearing

def calculate_initial_compass_bearing(pointA, pointB):
    """
    Calculates the bearing between two points.
    The formulae used is the following:
    :Parameters:
      - `pointA: The tuple representing the latitude/longitude for the
        first point. Latitude and longitude must be in decimal degrees
      - `pointB: The tuple representing the latitude/longitude for the
        second point. Latitude and longitude must be in decimal degrees
    :Returns:
      The bearing in degrees
    :Returns Type:
      float
    """
    if (type(pointA) != tuple) or (type(pointB) != tuple):
        raise TypeError("Only tuples are supported as arguments")

    lat1 = math.radians(pointA[0])
    lat2 = math.radians(pointB[0])

    diffLong = math.radians(pointB[1] - pointA[1])

    x = math.sin(diffLong) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1)
            * math.cos(lat2) * math.cos(diffLong))

    initial_bearing = math.atan2(x, y)

    # Now we have the initial bearing but math.atan2 return values
    # from -180 to + 180 which is not what we want for a compass bearing
    # The solution is to normalize the initial bearing as shown below
    initial_bearing = math.degrees(initial_bearing)
    compass_bearing = (initial_bearing + 360) % 360

    return compass_bearing

def calc_radiant(end_lon, end_lat, end_alt, start_lon, start_lat, start_alt, arg_date, arg_time):
# arguments
# - impact point lat as decimal
# - impact point long as decimal
# - start point lat as decimal
# - start point long as decimal
# - date
# - time

   ang_alt = (start_alt - end_alt) 
   distance,bear = haversine(float(end_lon), float(end_lat), float(start_lon), float(start_lat))
   entry_angle = math.atan(ang_alt/ distance) * (180 / math.pi)
   point1 = (float(end_lat),float(end_lon))
   point2 = (float(start_lat),float(start_lon))
   date = arg_date
   time =  arg_time
   year, month, day= date.split('-')
   hour,min,sec = time.split(':')
   seconds = int(hour) * 3600 + (int(min) * 60)
   fraction = float(seconds) / 86400
   frac_day = int(day) + fraction
   #julian_date = bearing.date_to_jd(int(year),int(month),frac_day)

   julian_date = date_to_jd(int(year),int(month),float(frac_day))
   az_deg = calculate_initial_compass_bearing(point1, point2)
   #print("AZ DEG:", az_deg, bear)
   el_deg = entry_angle
   pi = math.pi
   az = (az_deg * pi)/180 #rad
   el = (el_deg * pi)/180 #rad
   lat = point1[0] #deg
   lon = point1[1] #deg
   #alt = 0 #m
   #print("LAT", lat)
   #print("LON", lon)
   #print("ALT", alt)
   ut = julian_date #julian date
   # Which Julian Date does Ephem start its own count at?
   J0 = ephem.julian_date(0)
   observer = ephem.Observer()
   observer.lon = str(lon)  # str() forces deg -> rad conversion
   observer.lat = str(lat)  # deg -> rad
   observer.elevation = end_alt * 1000
   #observer.date = ut - J0
   #print("<h1>MIKE!", arg_date,arg_time,"</h1>")
   observer.date = arg_date +  " " + arg_time
   ra,dec = observer.radec_of(az, el)
   return ra, dec, az_deg, el_deg, distance, entry_angle

def cnt_max_px(cnt_img):
   cnt_img = cv2.GaussianBlur(cnt_img, (7, 7), 0)
   min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)

   return(max_loc, min_val, max_val)

def fix_json_file(json_file):
   fp = open(json_file)
   new_file = json_file.replace(".json", "-new.json")
   out = open(new_file, "w")
   try: 
      load_json_file(json_file)
   except:
      print("JSON CORRUPT:", json_file)
      #exit()
   over = 0
   for line in fp:
      if "metframes" in line or "metconf" in line:
         over = 1
      if over == 0: 
         out.write(line)
   if over == 1:
      out.write("   \"version\" : 1 } ")
      print("JSON FIXED", json_file)
      out.close()
      fixed_json = load_json_file(new_file)
      #save_json_file(json_file, fixed_json)
      return(1)

   else:
      return(None)


def save_json_file(json_file, json_data):
   with open(json_file, 'w') as outfile:
      json.dump(json_data, outfile, indent=4)
   outfile.close()

def load_json_file(json_file):
   with open(json_file, 'r') as infile:
      json_data = json.load(infile)
   return(json_data)




def fn_dir(file):
   fn = file.split("/")[-1]
   dir = file.replace(fn, "")
   return(fn, dir)

