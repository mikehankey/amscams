
import subprocess
import datetime
import math
import ephem

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


def check_running(progname):
   cmd = "ps -aux |grep " + progname + " | grep -v grep |wc -l"
   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
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

def convert_filename_to_date_cam(file):
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
   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)


def bound_cnt(x,y,img_w,img_h,sz=10):

   if x - sz < 0:
      mnx = 0
   else:
      mnx = x - sz

   if y - sz < 0:
      mny = 0
   else:
      mny = y - sz

   if x + sz > img_w - 1:
      mxx = img_w - 1
   else:
      mxx = x + sz

   if y + sz > img_h -1:
      mxy = img_h - 1
   else:
      mxy = y + sz
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

