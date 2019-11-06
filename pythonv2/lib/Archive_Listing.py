# coding: utf-8
import sys  
import cgitb
import datetime
import os
import glob
import json

from collections import defaultdict 
from lib.Get_Station_Id import get_station_id
from lib.REDUCE_VARS import *


def get_archive_for_year(year):
   main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
   d = defaultdict(list)

   for file in glob.iglob(path.join(base_path, '**/*.json'), recursive=True):
      print(file)
      d[path.basename(path.dirname(file))].append(path.basename(file))

   return d

def archive_listing(form):
   limit_day = form.getvalue('limit_day')
   cur_page  = form.getvalue('p')
   meteor_per_page = form.getvalue('meteor_per_page')

   if (cur_page is None) or (cur_page==0):
      cur_page = 1
   else:
      cur_page = int(cur_page)

   if (limit_day is None):
      now = datetime.datetime.now()
      year = now.year
      #TODO: else we get the date!
  
   # MAIN DIR:METEOR
   #/mnt/ams2/meteor_archive/[STATION_ID]/METEOR/[YEAR]
   #main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)



# Get the available month for the current year 
import glob
import os
main_dir  = '/mnt/ams2/meteor_archive/' + 'AMS7' + '/' + 'METEOR/' + '2019'
year = 2019
 
all_months = {int(os.path.basename(x)) for x in sorted(glob.glob(main_dir+'/*'))}
all_days = {}
_all = {year:all_months}
 

for i,month in enumerate(all_months):  
   days = {int(os.path.basename(x)) for x in sorted(glob.glob(main_dir+'/'+str(month)+'/*'))} 
   for x,day in enumerate(days): 
      all_detections =  [os.path.basename(y) for y in sorted(glob.glob(main_dir+'/'+str(month)+'/'+str(day)+'/*.json'))] 
      if(month not in _all[year]):
         _all{year:month}  = []
      _all{year:month} = all_detections

print(_all)

   _all = {"2019": {"01": {"23":['a','b']}}}



from collections import defaultdict
from os import path
import glob
import json

base_path = '/mnt/ams2/meteor_archive/' + 'AMS7' + '/' + 'METEOR/' + '2019'
d = defaultdict(list)

for file in glob.iglob(path.join(base_path, '**/*.json'), recursive=True):
  print(file)
  d[path.basename(path.dirname(file))].append(path.basename(file))

print(json.dumps(d))