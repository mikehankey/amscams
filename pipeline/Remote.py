#!/usr/bin/python3
"""

Functions for handling of remote sites

"""

import json
import os
from lib.PipeUtil import load_json_file, save_json_file, cfe
CLOUD_ROOT = "/mnt/archive.allsky.tv/"
LOCAL_ROOT = "/mnt/ams2/meteor_archive/"


def load_remote_conf(station_id):
   station_data = None
   stations = load_json_file("../conf/stations.json")
   for data in stations:
      if station_id == data['id']:
         station_data = data

   local_cal_dir = LOCAL_ROOT + station_id + "/CAL/"
   cloud_cal_dir = CLOUD_ROOT + station_id + "/CAL/"
   lconf_file = local_cal_dir + "as6.json"
   cconf_file = cloud_cal_dir + "as6.json"
   if cfe(local_cal_dir, 1) == 0:
      os.makedirs(local_cal_dir)
   if cfe(lconf_file) == 1:
      json_conf = load_json_file(lconf_file)
      return(json_conf, station_data)
   elif cfe(cconf_file) == 1:
      json_conf = load_json_file(cconf_file)
      save_json_file(lconf_file, json_conf)
      return(json_conf, station_data)
   else:
      print("Cloud conf not available.")
   return(None, station_data)
   

def sync_configs():
   adirs = glob.glob("/mnt/ams2/archive.allsky.tv") 

def menu():
   out = """
      Functions:
         1) Copy / Update Remote Station Config Files
         2) Remote Calibrate

   """
   print(out)
   cmd = input("Select Function")
   print(cmd)
   if cmd == "2":
      remote_calibrate()



def remote_calibrate():
   r_station_num = input("Enter station id number AMSX:")
   #remote_ip = input("Enter remote http IP for direct host access or blank to use cloud drive data")
   r_station_id = "AMS" + r_station_num
   r_json_conf, station_data = load_remote_conf(r_station_id)
   print(r_json_conf, station_data)

if __name__ == "__main__":
   menu()

