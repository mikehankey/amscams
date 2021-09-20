#!/usr/bin/python3

from lib.PipeUtil import load_json_file, save_json_file, cfe
import cv2

def menu():
   print("""
      1) Detect/Reduce and Import meteor-clip into the system

   """)
   cmd = input("Select command")

   if cmd == "1":
      man_detect()

def scan_meteor_video(meteor_video_file):
   cap = cv2.VideoCapture(self.sd_filename)
   fc = 0
   active_mask = None
   small_mask = None
   thresh_adj = 0
   grabbed = True
   last_frame = None
   while grabbed is True:
      grabbed , frame = cap.read()

      #break when done
      if not grabbed and fc > 5:
         break
   

def man_detect():
   meteor_video_file = input("Enter the full path and filename to the minute file or meteor trim file you want to import.")
   if cfe(meteor_video_file) == 1:
      print("found file.", meteor_video_file)  
      data = scan_meteor_video(meteor_video_file)

menu()
