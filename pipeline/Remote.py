#!/usr/bin/python3
"""

Functions for handling of remote sites

"""

import json
import os
from lib.PipeUtil import load_json_file, save_json_file, cfe
from lib.PipeAutoCal import fn_dir
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
   R_CAL_DIR = LOCAL_ROOT + r_station_id + "/CAL/"

   # SYNC CAL INDEX FILES
   local_cal_files = []
   cam_num = 1
   ci_data = {}
   cam_nums = {}
   menu_cam_select = "Available cameras for " + r_station_id + "\n"
   for cam in r_json_conf['cameras']:
 
      cams_id = r_json_conf['cameras'][cam]['cams_id']
      cam_nums[cam] = cams_id
      if cams_id not in ci_data:
         ci_data[cams_id] = {}
         ci_data[cams_id]['cal_index'] = []
      ci_file = R_CAL_DIR + r_station_id + "_" + cams_id + "_CAL_INDEX.json"
      if station_data['remote_url'] != "":
         remote_url_base = "https://" + station_data['remote_url'] 
         remote_url = "https://" + station_data['remote_url'] + ci_file
         fn, dir = fn_dir(ci_file)
         fne = fn.split("-")
         fnr = fne[0]
         local_dir = R_CAL_DIR   
         local_file = local_dir + fnr
         if cfe(local_dir, 1) == 0:
            os.makedirs(local_dir)
         if cfe(local_file) == 0:
            cmd = "wget \"" + remote_url + "\" -O " + local_file
            os.system(cmd)
         local_cal_files.append(local_file)
         cij = load_json_file(local_file)
         ci_data[cams_id]['cal_index'] = cij 
      menu_cam_select += "   1) " + cams_id + "\n"

   print(menu_cam_select)
   selected = input("Select camera number (1-7): ")
   selected_cam = "cam" + str(selected)
   cams_id = cam_nums[selected_cam]
   print("You selected:", cam_nums[selected_cam])
   cc = 1 
   for data in ci_data[cams_id]['cal_index']:
      file, az, el, pos, px, ustars, cstars, res = data 
      fn, dir = fn_dir(file)
      elm = fn.split("-")
      rfn = elm[0]
      print(str(cc) + ")" , rfn, az, el, pos, px, ustars, cstars, res) 
      cc += 1
   selected = input("Enter the cal file you want to work with, or enter ALL to do batch jobs on all cal files.")
   si = int(selected)
   sdata = ci_data[cams_id]['cal_index'][si]
   print("YOU SELECTED:", sdata)
   sync_remote_calib(r_station_id, remote_url_base, sdata)

def sync_remote_calib(station_id, remote_url_base, sdata):      
   rfile = sdata[0]
   fn, dir = fn_dir(rfile)
   elm = fn.split("-") 
   cal_base = elm[0]
   ldir = LOCAL_ROOT + "/CAL/BEST/"
   if cfe(ldir, 1) == 0:
      os.makedirs(ldir)
   l_cp_file = ldir + cal_base + "-calparams.json"
   l_cp_img_file = ldir + cal_base + "-src.png"

   # get cal_params_json
   if cfe(l_cp_file) == 0:
      remote_url = remote_url_base + rfile
      cmd = "wget \"" + remote_url + "\" -O " + l_cp_file 
      os.system(cmd)

   # get source image 
   if cfe(l_cp_img_file) == 0:
      remote_url = remote_url_base + rfile
      remote_url = remote_url.replace("-calparams.json", ".png")
      cmd = "wget \"" + remote_url + "\" -O " + l_cp_img_file 
      os.system(cmd)
   
if __name__ == "__main__":
   menu()

