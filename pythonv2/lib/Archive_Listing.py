# coding: utf-8
import sys  
import cgitb
import datetime
import os

import glob

from lib.Get_Station_Id import get_station_id
from lib.REDUCE_VARS import *



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
   main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
   
   # Get the available month for the current year 
   all_ = {}
   all_months = sorted(glob.glob(main_dir+'/*'))
   all_days = {}
 
   for i,month in enumerate(all_months): 
      all_[month] = {os.path.basename(x) for x in sorted(glob.glob(month+'/*'))}
      for x,day in enumerate(all_[month]):
         all_days[month] = {os.path.basename(y) for y in sorted(glob.glob(month+'/'+str(day)+'/*.json'))}
      all_[month][day] =  all_days[month]    
       

   print("<br>")
   print(all_)

   #print("ALL MONTHS")
   #print("<br>")
   #print(all_months)