
import os
import ephem
import glob

from lib.Get_Cam_position import get_device_position
from lib.Get_Station_Id import get_station_id

MINUTE_FOLDER = '/mnt/ams2/SD/proc2/'
IMAGES_MINUTE_FOLDER = 'images'
DEFAULT_HORIZON_EPHEM = '-0:34'
DEFAULT_PRESSURE = 0

# Get sun az & alt to determine if it's a daytime or nightime minute
def get_sun_details(capture_date):

   device_position = get_device_position()

   if('lat' in device_position and 'lng' in  device_position):

      obs = ephem.Observer()

      obs.pressure = DEFAULT_PRESSURE
      obs.horizon = DEFAULT_HORIZON_EPHEM
      obs.lat  = device_position['lat']
      obs.lon  = device_position['lng']
      obs.date = capture_date

      sun = ephem.Sun()
      sun.compute(obs)

      (sun_alt, x,y) = str(sun.alt).split(":")
      saz = str(sun.az)
      (sun_az, x,y) = saz.split(":")
      if int(sun_alt) < -1:
         sun_status = "night"
      else:
         sun_status = "day"

      return sun_az,sun_alt,sun_status
   
   else:
      return 0,0,"?"


# Create index for a given year
def create_json_index_minute_day(day,month, year):

   # Main dir to glob
   main_dir = MINUTE_FOLDER +  os.sep + str(year) + '_' + str(month).zfill(2) + '_' + str(day).zfill(2) + os.sep + IMAGES_MINUTE_FOLDER
 
   index_year = {'station_id':get_station_id(),'year':int(year),'months':int(month)}
 
   for minute in sorted(glob.iglob(main_dir + '*' + os.sep + '*', recursive=True), reverse=True):	
      #cur_month = os.path.basename(os.path.normpath(month))
      print(minute)

# Write index for a given day
def write_day_minute_index(day, month, year):
   json_data = create_json_index_minute_day(day,month, year)  

   # Write Index if we have data
   if('days' in json_data): 
      main_dir = METEOR_ARCHIVE + get_station_id()  + os.sep + METEOR + str(year) + os.sep + str(month).zfill(2)

      if not os.path.exists(main_dir):
         os.makedirs(main_dir)

      with open(main_dir + os.sep + str(month).zfill(2) + ".json", 'w') as outfile:
         #Write compress format
         json.dump(json_data, outfile)

      outfile.close() 
      return True
   
   return False