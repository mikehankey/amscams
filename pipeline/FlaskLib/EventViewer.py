import os
import numpy as np
import boto3
from datetime import datetime
import json
from decimal import Decimal
import sys
from lib.PipeAutoCal import fn_dir
import glob
from lib.PipeUtil import cfe, load_json_file, save_json_file, convert_filename_to_date_cam
from FlaskLib.FlaskUtils import make_default_template
import boto3
import socket
import subprocess
from boto3.dynamodb.conditions import Key

from Classes.Event import Event


from Classes.DisplayFrame import DisplayFrame
from Classes.Detector import Detector
from Classes.Camera import Camera
from Classes.Calibration import Calibration
from lib.PipeAutoCal import gen_cal_hist,update_center_radec, get_catalog_stars, pair_stars, scan_for_stars, calc_dist, minimize_fov, AzEltoRADec , HMS2deg, distort_xy, XYtoRADec, angularSeparation
from lib.PipeUtil import load_json_file, save_json_file, cfe, check_running
from lib.FFFuncs import best_crop_size, ffprobe



class EventViewer():
   def __init__(self, event_id=None):
      self.event_id = event_id
      self.EVO = Event(event_id=event_id)
     
