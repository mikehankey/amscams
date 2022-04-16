#!/usr/bin/python3
from requests import get
import subprocess
import numpy as np
import os
import glob
from decimal import Decimal
import simplejson as json
from datetime import datetime
import datetime as dt
import math
import requests
from lib.PipeUtil import load_json_file, save_json_file,cfe
from lib.PipeImage import stack_frames
import sys
import cv2
from lib.FFFuncs import best_crop_size, crop_video, resize_video, splice_video, lower_bitrate, ffprobe
from lib.PipeVideo import load_frames_simple
from pushAWS import make_obs_data, push_obs
#import aws

# TWO TYPES OF PUSH REQUESTS ARE POSSIBLE.
# PUSH OBS and PUSH EVENT
# PUSH OBS REQUESTS ARE ONLY ALLOWED WITH A KEY THAT MATCHES THE STATION'S OR AN ADMIN KEY
# EVENTS ARE ONLY ALLOWED TO BE PUSH WITH ADMIN KEYS

class RegisterDevice():

   def __init__(self):
      self.API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"
      self.get_mac_info()
      self.mac_addr = None
      print(self.mac_info)
      for key in self.mac_info:
         if "ip" in self.mac_info[key]:
            if self.mac_info[key]['ip'] == "192.168.76.1" :
               self.cams_mac_addr = self.mac_info[key]['mac_addr']
               self.mac_addr = self.cams_mac_addr
         else:
            self.mac_info[key]['ip'] = "" 
            self.network_mac_addr = self.mac_info[key]['mac_addr']
      try:
         print("CAMS MAC:", self.cams_mac_addr)
      except:
         self.cams_mac_addr = None
      try:
         print("NET MAC:", self.network_mac_addr)
      except:
         self.network_mac_addr= None
      if self.network_mac_addr is None:
         print("CAMS ETH INTERFACE NOT FOUND")
         exit()

      #
      #data = json.loads(get("http://ip.jsontest.com/").text)
      data = {}
      data['ip'] = "0.0.0.0"
      self.public_ip = data["ip"]
      json_conf = load_json_file("../conf/as6.json")

      json_conf['mac_addr'] = self.mac_addr
      json_conf['api_key'] = self.mac_addr
      station_data = self.json_conf2_dyna_station(json_conf)
      station_data['mac_addr'] = self.mac_addr
      station_data['api_key'] = self.mac_addr
      station_data['public_ip'] = self.public_ip
      station_data['registration'] = {}
      station_data['registration']['register_date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
      json_conf['registration'] = station_data['registration']


      if self.mac_addr is None:
         print("CAMS ETH INTERFACE NOT FOUND")
         exit()

      #
      #data = json.loads(get("http://ip.jsontest.com/").text)
      data = {}
      data['ip'] = "0.0.0.0"
      self.public_ip = data["ip"]
      json_conf = load_json_file("../conf/as6.json")

      json_conf['mac_addr'] = self.mac_addr
      json_conf['api_key'] = self.mac_addr
      station_data = self.json_conf2_dyna_station(json_conf)
      station_data['mac_addr'] = self.mac_addr
      station_data['api_key'] = self.mac_addr
      station_data['public_ip'] = self.public_ip
      station_data['registration'] = {}
      station_data['registration']['register_date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
      json_conf['registration'] = station_data['registration']
      payload = {}
      payload['in_station_data'] = station_data
      payload['cmd'] = "register_device" 
      headers = {'Content-type': 'application/json'}

      response = requests.post(self.API_URL, data=json.dumps(payload), headers=headers)
      #, headers=headers)

      print(json.dumps(payload))
      print("\n RESPONSE \n")
      print(response.text)
      save_json_file("../conf/as6.json", json_conf)



   def json_conf2_dyna_station(self,json_conf):
      station_data = {}
      station_id = json_conf['site']['ams_id']
      operator_name = json_conf['site']['operator_name']
      city = json_conf['site']['operator_city']
      state = json_conf['site']['operator_state']
      if "username" in json_conf:
         username = json_conf['username']
      else:
         username = "unclaimed"
      if "mac_addr" in json_conf:
         api_key = json_conf['mac_addr']
      else:
         api_key = "abc123"
      if "operator_country" in json_conf:
         country = json_conf['site']['operator_country']
      else:
         country = "US"
      email = json_conf['site']['operator_email']
      lat = json_conf['site']['device_lat']
      lon = json_conf['site']['device_lng']
      alt = json_conf['site']['device_alt']
      if "obs_name" in json_conf['site']:
         obs_name = json_conf['site']['obs_name']
      else:
         obs_name = ""
      cameras = []
      for cam_num in json_conf['cameras']:
         cams_id = json_conf['cameras'][cam_num]['cams_id']
         cam_data = {}
         cam_data['cam_id'] = cams_id
         cameras.append(cam_data)

      # set dyna obj
      station_data['station_id']= station_id
      station_data['operator_name']= operator_name
      station_data['city']= city
      station_data['state']= state
      station_data['country']= country
      station_data['email']= email
      station_data['lat'] = lat
      station_data['lon'] = lon
      station_data['alt'] = alt
      station_data['obs_name'] = obs_name
      station_data['cameras'] = cameras
      station_data['username'] = username
      station_data['api_key'] = api_key
      return(station_data)

   def get_mac_info(self):
      mac_info = {}
      cmd = "ip a"
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      lines = output.split("\n")
      for line in lines:
         if "loop" in line or "inet6" in line or "127.0" in line:
            continue
         elif "inet" in line:
            el = line.split(" ")
            ip = el[5].split("/")[0]
            ip = ip.replace(" ", "")
            mac_info[inter]['ip'] = ip
         elif "BROADCAST" in line:
            el = line.split(":")
            inter = el[1]
            inter = inter.replace(" ", "")
            if inter not in mac_info:
               mac_info[inter] = {}
         elif "link/ether" in line:
            el = line.split(" ")
            mac = el[5].replace(" ", "")
            mac_info[inter]['mac_addr'] = mac

      self.mac_info = mac_info
