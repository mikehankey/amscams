# coding: utf-8
import sys  
import cgitb
import datetime
import re
import glob
import json


# MAIN FUNCTION FOR THE ARCHIVE LISTING PAGE
def archive_listing(form):
   limit_day = form.getvalue('limit_day')
   cur_page  = form.getvalue('p')
   meteor_per_page = form.getvalue('meteor_per_page')

   print("NOTHING")
   sys.exit(0)

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
   achr = get_archive_for_year(year)
   all = {year:achr}

   print(json.dumps(all))


 
