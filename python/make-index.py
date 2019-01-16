#!/usr/bin/python3

import os
import glob
import json

json_file = open('../conf/as6.json')
json_str = json_file.read()
json_conf = json.loads(json_str)
proc_dir = json_conf['site']['proc_dir']

data_dir = json_conf['site']['proc_dir'] + "json/"

from caliblib import load_json_file, save_json_file


def get_days():
   days = []
   files = os.listdir(proc_dir)
   for file in files:
      if file[0] == "2":
         # the above line will stop working in 980 years i.e. y3k
         days.append(file)
   return(sorted(days, reverse=True))



def main():
   days = get_days()
   d = 0
   html = ""
   stats = {}

   json_file = data_dir + "main-index.json"

   for day in days:

      html = html + "<h2>" + day + "</h2> "
      total_detects, total_meteors, total_non_meteors = get_stats(day)
      stats[day] = {}
      stats[day]['total_detects'] = total_detects
      stats[day]['total_meteors'] = total_meteors
      stats[day]['total_non_meteors'] = total_non_meteors
   print(stats)
   json_file = data_dir + "main-index.json"
   save_json_file(json_file, stats)
   print(json_file)
    

def get_stats(day):
   # find total trim files
   # find total meteor files
   # find total objfail files
   meteor_trims = []
   all_trims = []
   trim_files = glob.glob(proc_dir + "/" + day + "/*trim*.mp4")
   for file in trim_files:
      if "meteor" in file:
         meteor_trims.append(file)
      else:
         all_trims.append(file)

   objfail = glob.glob(proc_dir + "/" + day + "/data/*objfail*.txt")

   total_meteors = len(meteor_trims)
   total_trims = len(all_trims)
   total_non_meteors = len(objfail)

   stats = [total_trims, total_meteors, total_non_meteors]

   #print("TOTAL BRIGHT PIXEL DETECTIONS:", total_trims, "<BR>")
   #print("TOTAL METEOR DETECTIONS:", total_meteors, "<BR>")
   #print("TOTAL NON-METEOR DETECTIONS:", total_non_meteors, "<BR>")

   return(stats)


main()
