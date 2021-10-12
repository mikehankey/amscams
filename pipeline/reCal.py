#!/usr/bin/python3

import os
from lib.PipeUtil import load_json_file, save_json_file, cfe


def update_lens_model():
   json_conf = load_json_file("../conf/as6.json")
   cameras = json_conf['cameras']
   for cam in cameras:
      cams_id = cameras[cam]['cams_id']
      cmd = "./Process.py deep_init " + cams_id
      print(cmd)
      os.system(cmd)


update_lens_model()
