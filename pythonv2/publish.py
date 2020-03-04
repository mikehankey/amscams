#!/usr/bin/python3

"""
This script creates all the html pages related to a fireball event. 
  * Run this script through the day to keep data up to date and in sync.
  * Run this script after a day has finished to close out all work relating to that day. 
  * Script will perform the following functions.
     - Create an html page "report" for a given camera of a station
"""

import os
import glob
import sys
import json
import re

from lib.FileIO import * 

from doDay import analyse_report_file

REGEX_JSON_FROM_CLOUD = r"\/(\w*)\/METEOR\/(\d{4})\/(\d{2})\/(\d{2})\/(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{3})_(\w{6})-trim(\d{4}|\d{3}|\d{2}|\d{1}).json"
REGEX_GROUP_JSON_FROM_CLOUD = ["all_path","station_id","year","month","day","hour","min","sec","ms","cam_id","trim"]
 
#PATH TO CLOUD ARCHIVES
PATH_TO_CLOUD = "/mnt/archive.allsky.tv"

# TEMPLATES
OBSERVER_REPORT_TEMPLATE = "/home/ams/amscams/pythonv2/templates/allsky.tv.obs_report.html"
 


# Analyse the json file names
def analyse_event_json_file(file_name):
   matches = re.finditer(REGEX_JSON_FROM_CLOUD, file_name, re.MULTILINE)
   res = {}
  
   for matchNum, match in enumerate(matches, start=1):
      for groupNum in range(0, len(match.groups())): 
         if(match.group(groupNum) is not None):
            res[REGEX_GROUP_JSON_FROM_CLOUD[groupNum]] = match.group(groupNum)
         groupNum = groupNum + 1

   return res



def make_event_station_report(json_file):

   # Format of the JSON file:
   # /AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298.json
   # Format of the OUTPUT HTML file
   # /AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298.html
 

   # We load (and test) the json
   json_data = load_json_file(PATH_TO_CLOUD+json_file)
   if(json_data is False): 
      print(PATH_TO_CLOUD+json_file + " not found")
      sys.exit(0)

   # Build the page based on template  
   with open(OBSERVER_REPORT_TEMPLATE, 'r') as file:
      template = file.read()
   
   # Create Template
   f = open(PATH_TO_CLOUD+json_file.replace('.json','.html'), "w+")
   f.write(template)
   f.close()

   # Add station id & other static info on the title
   analysed_name = analyse_event_json_file(json_file)
   print("INPUT")
   print(json_file)
   print('analysed_name')
   print(analysed_name)
   sys.exit(0)

   template = template.replace('{STATION_ID}',analysed_name['station_id'])
   template = template.replace('{CAM_ID}',analysed_name['cam_id'])
   template = template.replace('{DATE}',analysed_name['year']+'/'+analysed_name['month']+'/'+analysed_name['year']+' '+analysed_name['hour'])+":"+analysed_name['min']+":"+analysed_name['sec']+":"+analysed_name['ms']

   print(json_file.replace('.json','.html') +  " created.")
 

### COMMAND
cmd = sys.argv[1]

if cmd == "event_station_report":
   make_event_station_report(sys.argv[2])