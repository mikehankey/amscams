# coding: utf-8
import sys  
import cgitb
import datetime
import re
import glob
import json

from os import *
from lib.Get_Station_Id import get_station_id
from lib.REDUCE_VARS import *
from collections import defaultdict 


ARCHIVE_SUB_FOLDER_REGEX = r"/([0-9]{4})*?/([0-9]{2})*?/([0-9]{2})*?/"
ARCHIVE_SUB_FOLDER_GROUP = ['year','month','day']


# PARSE ARCHIVE FOLDER TO RETRIEVE YEAR, MONTH & DAY
def folder_analyser(folder):
   n_folder = folder + "/"
   matches = re.finditer(ARCHIVE_SUB_FOLDER_REGEX, n_folder, re.MULTILINE)
   res = {}
  
   for matchNum, match in enumerate(matches, start=1):
      for groupNum in range(0, len(match.groups())): 
         if(match.group(groupNum) is not None):
            res[ARCHIVE_SUB_FOLDER_GROUP[groupNum]] = match.group(groupNum)
         groupNum = groupNum + 1
   
   print("RES: ")
   print(res)
   print("<br>")


def get_archive_for_year(year):
   main_dir = METEOR_ARCHIVE + get_station_id() + '/' + METEOR + str(year)
   d = defaultdict(list)

   for file in glob.iglob(path.join(main_dir, '**/*.json'), recursive=True):
      print(folder_analyser(path.dirname(file)))
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
   achr = get_archive_for_year(year)
   all = {year:achr}

   print(all)


 
