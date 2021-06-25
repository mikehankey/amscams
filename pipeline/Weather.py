from Classes.Weather import Weather
import math
import cv2
import glob
from lib.PipeUtil import cfe, convert_filename_to_date_cam
import pickle
import os
import datetime
from datetime import datetime as dt
from lib.FFFuncs import ffprobe
import sys

WW = Weather()
if len(sys.argv) == 1:
   WW.index_weather_snaps_all()
else:
   if sys.argv[1] == 'stack_index':
      WW.index_local_stacks()
   
