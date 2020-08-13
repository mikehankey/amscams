"""

   multi-station functions here

"""
import os
from lib.DEFAULTS import *
import glob
from lib.PipeUtil import cfe, load_json_file, save_json_file

MLN_CACHE_DIR = "/mnt/ams2/MLN_CACHE/"

def mln_report(day=None):

   #now = dt.strptime(day, "%Y_%m_%d")
   no_data_stations = [] 
   all_meteors = []
   # yesterday = now - datetime.timedelta(days = 1)
   for station in stations:
      station_dir = "/mnt/archive.allsky.tv/" + station + "/LIVE/METEORS/" 
      data_file = station_dir + day + ".json"
      new_data_file = "/mnt/ams2/MLN_CACHE/" + day + "-" + station + ".json"
      cmd = "cp " + data_file + " " + new_data_file
      if cfe(data_file) == 1:
         if cfe(new_data_file) == 0 :
            print(cmd)
            os.system(cmd) 
         print("LOAD:", new_data_file)
         meteors = load_json_file (new_data_file)
         print(station, " METEORS: ", len(meteors.keys()))
         for mm in meteors:
            meteor = meteors[mm]
            meteor['station'] = station
            all_meteors.append(meteor)
      else:
         no_data_stations.append(station)
   print("SAVE:", MLN_CACHE_DIR + day + "-all.json")
   save_json_file(MLN_CACHE_DIR + day + "-all.json", all_meteors)

def mln_best(day, days_after = 1) :
   all_meteors = load_json_file(MLN_CACHE_DIR + day + "-all.json")
   all_sorted = sorted(all_meteors, key=lambda k: len(k['xs']), reverse=True)

   html = "<h1>Meteors Last Night " + day + "</h1><ul>\n"

   for m in all_sorted:
      file = m['hd_file'].split("/")[-1]
      station = m['station']
      link = "https://archive.allsky.tv/" + station + "/LIVE/METEORS/" + file
      print(station, len(m['xs']), link)
      html += "<li><a href=" + link + ">" + station + " " + file + "</a></li>\n"
 
   html += "</ul>"
   all_file = "/mnt/archive.allsky.tv/LAST_NIGHT/" + day + ".html"
   fp = open(all_file, "w")
   fp.write(html)
   fp.close()
   print(all_file)
   
