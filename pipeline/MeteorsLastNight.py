#!/usr/bin/python3
from lib.PipeUtil import load_json_file, save_json_file
from Classes.RenderFrames import RenderFrames
import imutils
import cv2
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from Classes.VideoEffects import VideoEffects
import cv2
import sys , os
# test script for render functions.

RF = RenderFrames()
VE = VideoEffects()

date = sys.argv[1]

y,m,d = date.split("_")
mdir = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/"
obs_file = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/"  + y + "_" + m + "_" + d + "_ALL_OBS.json"
events_file = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/"  + y + "_" + m + "_" + d + "_ALL_EVENTS.json"
stations_file = "/mnt/f/EVENTS/" + y + "/" + m + "/" + d + "/"  + y + "_" + m + "_" + d + "_ALL_STATIONS.json"

obs = load_json_file(obs_file)
events = load_json_file(events_file)
stations = load_json_file(stations_file)
total_obs = len(obs)
total_events = len(events)
total_stations = len(stations)
total_cams = len(stations) * 7

files = os.listdir(mdir)

for f in files:
   check_file = cv2.imread(mdir + f)

# do tv frame

base_frame = RF.tv_frame()


        #"This video encompases an overview of multi-station meteors captured on {:s}/{:s}/{:s} ".format(m,d,y),
        #"{:d} cameras across {:d} total stations reported {:d} observations to the network ".format(total_cams, total_stations, total_obs),
        #"From these, we have identified {:d} coincindent meteor events. ".format(total_events)

phrases = [
        "Hi, there. Welcome to Meteors of the Last Night. ".format(m,d,y)
        ]

#(self, phrases=["Well, hello there..."], base_frame = None, duration=1, font_face=None, font_size=20, font_color="white", pos_x=None, pos_y=None, x_space=20 , phrase_pause=20)

main_w = 1760
main_h = 990
frames = VE.type_text(phrases, base_frame, 3, font_size=30, pos_y=480,phrase_pause=20)

solved = []
failed = []
pending = []

station_stats = {}
for ev_data in events:
   print(ev_data['solve_status'])
   events_fast = []
   if "SOLVE" in ev_data['solve_status']:
      solved.append(ev_data)
   elif "FAIL" in ev_data['solve_status']:
      failed.append(ev_data)
   else:
      pending.append(ev_data)

events_summary = ['{:d} events solved, {:d} failed to solve and {:} events are pending '.format(len(solved), len(failed), len(pending))]
frames = VE.type_text(events_summary, base_frame, duration=3, font_size=30, pos_y=480,phrase_pause=30)
cv2.waitKey(0)
   # Now load up some files!

for ev_data in solved:
   for st in ev_data['stations']:
      if st not in station_stats:
         station_stats[st] = {}
         station_stats[st]['solved'] = 0
         station_stats[st]['failed'] = 0
         station_stats[st]['pending'] = 0
      station_stats[st]['solved'] += 1

for ev_data in failed:
   for st in ev_data['stations']:
      if st not in station_stats:
         station_stats[st] = {}
         station_stats[st]['solved'] = 0
         station_stats[st]['failed'] = 0
         station_stats[st]['pending'] = 0
      station_stats[st]['failed'] += 1

for ev_data in pending:
   for st in ev_data['stations']:
      if st not in station_stats:
         station_stats[st] = {}
         station_stats[st]['solved'] = 0
         station_stats[st]['failed'] = 0
         station_stats[st]['pending'] = 0
      station_stats[st]['pending'] += 1

fin = []

for st in station_stats:
   success = station_stats[st]['solved'] / (station_stats[st]['solved'] + station_stats[st]['failed'] + station_stats[st]['pending'])
   station_stats[st]['success'] = success
   fin.append((st, success, station_stats[st]))
fin = sorted(fin, key=lambda x: x[1],reverse=True)
for x in fin:
   print(x)
save_json_file(mdir + date + "_STATION_STATS.json", station_stats)
print(mdir + date + "_STATION_STATS.json")


exit()
# ADD LOGO WATER MARK TO BACKGROUND! 

blank_image = np.zeros((1080,1920,3),dtype=np.uint8)
background = cv2.imread("/mnt/ams2/latest/010001.jpg")
img2 = cv2.imread("/mnt/ams2/latest/010002.jpg")
img3 = cv2.imread("/mnt/ams2/latest/010003.jpg")
img4 = cv2.imread("/mnt/ams2/latest/010004.jpg")
img5 = cv2.imread("/mnt/ams2/latest/010005.jpg")
img6 = cv2.imread("/mnt/ams2/latest/010006.jpg")

logo = RF.logo_1920

y = background.shape[0] - logo.shape[0]
x = background.shape[1] - logo.shape[1]

cx = int((background.shape[1] / 2) - (logo.shape[1] / 2))
cy = int((background.shape[0] / 2) - (logo.shape[0] / 2))

image = RF.watermark_image(background, logo, cx,cy, .1)
cv2.imshow('pepe', image)
cv2.waitKey(0)

# Get UI Frame Template 4 Panel Version

frame_4p = RF.frame_template("1920_row_x", [background, img2, img3,img4, img5,img6])
cv2.imshow('pepe', frame_4p)
cv2.waitKey(0)

# Get UI Frame Template 1 Panel Version

frame_1p = RF.frame_template("1920_1p", [background])
cv2.imshow('pepe', frame_1p)
cv2.waitKey(0)

logo = RF.logo_1920

y = background.shape[0] - logo.shape[0]
x = background.shape[1] - logo.shape[1]
cx = int((background.shape[1] / 2) - (logo.shape[1] / 2))
cy = int((background.shape[0] / 2) - (logo.shape[0] / 2))
title_image = RF.watermark_image(blank_image, logo, cx,cy, .1)

cv2.imshow('pepe', title_image)
cv2.waitKey(0)
