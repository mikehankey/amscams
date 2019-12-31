from lib.CalibLibv2 import *
from lib.MeteorReduce_Tools import name_analyser
from lib.FileIO import load_json_file



def XYtoRADec(img_x,img_y,json_conf):

   analysed_name = name_analyser(json_conf)

   # Get Data from analysed_name
   hd_y = analysed_name['year']
   hd_m = analysed_name['month']
   hd_d = analysed_name['day']
   hd_h = analysed_name['hour']
   hd_M = analysed_name['min'] 


   cal_params = load_json_file(json_conf)


   F_scale = 3600/float(cal_params['pixscale']) 

   total_min = (int(hd_h) * 60) + int(hd_M)
   day_frac = total_min / 1440 
   hd_d = int(hd_d) + day_frac
   jd = date_to_jd(int(hd_y),int(hd_m),float(hd_d))

   lat = float(json_conf['site']['device_lat'])
   lon = float(json_conf['site']['device_lng'])

   # Calculate the reference hour angle
   T = (jd - 2451545.0)/36525.0
   Ho = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 \
      - (T**3)/38710000.0)%360

   x_poly_fwd = cal_params['x_poly_fwd']
   y_poly_fwd = cal_params['y_poly_fwd']
   
   dec_d = float(cal_params['dec_center']) 
   RA_d = float(cal_params['ra_center']) 

   dec_d = dec_d + (x_poly_fwd[13] * 100)
   dec_d = dec_d + (y_poly_fwd[13] * 100)

   RA_d = RA_d + (x_poly_fwd[14] * 100)
   RA_d = RA_d + (y_poly_fwd[14] * 100)

   pos_angle_ref = float(cal_params['position_angle']) + (1000*x_poly_fwd[12]) + (1000*y_poly_fwd[12])

   # Convert declination to radians
   dec_rad = math.radians(dec_d)

   # Precalculate some parameters
   sl = math.sin(math.radians(lat))
   cl = math.cos(math.radians(lat))


   x_det = img_x - int(cal_params['imagew'])/2
   y_det = img_y - int(cal_params['imageh'])/2

   dx = (x_poly_fwd[0]
      + x_poly_fwd[1]*x_det
      + x_poly_fwd[2]*y_det
      + x_poly_fwd[3]*x_det**2
      + x_poly_fwd[4]*x_det*y_det
      + x_poly_fwd[5]*y_det**2
      + x_poly_fwd[6]*x_det**3
      + x_poly_fwd[7]*x_det**2*y_det
      + x_poly_fwd[8]*x_det*y_det**2
      + x_poly_fwd[9]*y_det**3
      + x_poly_fwd[10]*x_det*math.sqrt(x_det**2 + y_det**2)
      + x_poly_fwd[11]*y_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   x_pix = x_det + dx 

   #print("ORIG X:", img_x)
   #print("X DET:", x_det)
   #print("DX :", dx)
   #print("NEWX :", x_pix)

   dy = (y_poly_fwd[0]
      + y_poly_fwd[1]*x_det
      + y_poly_fwd[2]*y_det
      + y_poly_fwd[3]*x_det**2
      + y_poly_fwd[4]*x_det*y_det
      + y_poly_fwd[5]*y_det**2
      + y_poly_fwd[6]*x_det**3
      + y_poly_fwd[7]*x_det**2*y_det
      + y_poly_fwd[8]*x_det*y_det**2
      + y_poly_fwd[9]*y_det**3
      + y_poly_fwd[10]*y_det*math.sqrt(x_det**2 + y_det**2)
      + y_poly_fwd[11]*x_det*math.sqrt(x_det**2 + y_det**2))

   # Add the distortion correction
   y_pix = y_det + dy 

   x_pix = x_pix / F_scale
   y_pix = y_pix / F_scale

   ### Convert gnomonic X, Y to alt, az ###

   # Caulucate the needed parameters
   radius = math.radians(math.sqrt(x_pix**2 + y_pix**2))
   theta = math.radians((90 - pos_angle_ref + math.degrees(math.atan2(y_pix, x_pix)))%360)

   sin_t = math.sin(dec_rad)*math.cos(radius) + math.cos(dec_rad)*math.sin(radius)*math.cos(theta)
   Dec0det = math.atan2(sin_t, math.sqrt(1 - sin_t**2))

   sin_t = math.sin(theta)*math.sin(radius)/math.cos(Dec0det)
   cos_t = (math.cos(radius) - math.sin(Dec0det)*math.sin(dec_rad))/(math.cos(Dec0det)*math.cos(dec_rad))
   RA0det = (RA_d - math.degrees(math.atan2(sin_t, cos_t)))%360

   h = math.radians(Ho + lon - RA0det)
   sh = math.sin(h)
   sd = math.sin(Dec0det)
   ch = math.cos(h)
   cd = math.cos(Dec0det)

   x = -ch*cd*sl + sd*cl
   y = -sh*cd
   z = ch*cd*cl + sd*sl

   r = math.sqrt(x**2 + y**2)

   # Calculate azimuth and altitude
   azimuth = math.degrees(math.atan2(y, x))%360
   altitude = math.degrees(math.atan2(z, r))



   ### Convert alt, az to RA, Dec ###

   # Never allow the altitude to be exactly 90 deg due to numerical issues
   if altitude == 90:
      altitude = 89.9999

   # Convert altitude and azimuth to radians
   az_rad = math.radians(azimuth)
   alt_rad = math.radians(altitude)

   saz = math.sin(az_rad)
   salt = math.sin(alt_rad)
   caz = math.cos(az_rad)
   calt = math.cos(alt_rad)

   x = -saz*calt
   y = -caz*sl*calt + salt*cl
   HA = math.degrees(math.atan2(x, y))

   # Calculate the hour angle
   T = (jd - 2451545.0)/36525.0
   hour_angle = (280.46061837 + 360.98564736629*(jd - 2451545.0) + 0.000387933*T**2 - T**3/38710000.0)%360

   RA = (hour_angle + lon - HA)%360
   dec = math.degrees(math.asin(sl*salt + cl*calt*caz))

   ### ###


  return(x_pix+img_x,y_pix+img_y,RA,dec,azimuth,altitude)



img_x = 
img_y = 
cal_file = 
cal_params = 
json_conf = 

x_pix+img_x,y_pix+img_y,RA,dec,azimuth,altitude = XYtoRADec(img_x,img_y,cal_file,cal_params,json_conf)

print("x_pix+img_x : " + str(x_pix+img_x))
print("y_pix+img_y : " + str(y_pix+img_y))
print("RA : " + str(RA))
print("dec : " + str(dec))
print("azimuth : " + str(azimuth))
print("altitude " +  str(altitude))