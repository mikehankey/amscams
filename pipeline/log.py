#!/usr/bin/python3
import os
import time
import glob
from decimal import Decimal
import simplejson as json
from datetime import datetime
import math
import requests
from lib.FFFuncs import ffprobe
from lib.PipeUtil import load_json_file, save_json_file,cfe
import sys
try:
   from lib.DEFAULTS import API_URL 
except:
   os.system("echo 'API_URL = \"https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi\"' >> lib/DEFAULTS.py")
   API_URL = "https://kyvegys798.execute-api.us-east-1.amazonaws.com/api/allskyapi"

def push_log(msg):
   json_conf = load_json_file("../conf/as6.json")
   station_id = json_conf['site']['ams_id'] 
   log_data = {}
   log_datetime = datetime.now().strftime("%Y%m%d%H%M%S")
   log_data['station_id'] = station_id
   log_data['ts'] = log_datetime
   log_data['api_key'] = json_conf['api_key']
   log_data['msg'] = msg
   log_data['cmd'] = "log"
   log_data = json.loads(json.dumps(log_data), parse_float=Decimal)
   headers = {
      'content-type': 'application/json'
   }
   #aws_post_data = json.loads(json.dumps(log_data), parse_float=Decimal)
   headers = {'Content-type': 'application/json'}
   print("REQ:", json.dumps(log_data))
   response = requests.post(API_URL, data=json.dumps(log_data) , headers=headers)
   print("RESP:", response.content.decode())


if __name__ == "__main__":
   push_log(sys.argv[1])
