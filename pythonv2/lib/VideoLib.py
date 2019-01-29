
import cv2
#import time
from lib.UtilLib import convert_filename_to_date_cam

def get_masks(this_cams_id, json_conf, hd = 0):
   #hdm_x = 2.7272
   #hdm_y = 1.875
   my_masks = []
   cameras = json_conf['cameras']
   for camera in cameras:
      if str(cameras[camera]['cams_id']) == str(this_cams_id):
         if hd == 1:
            masks = cameras[camera]['hd_masks']
         else:
            masks = cameras[camera]['masks']
         for key in masks:
            mask_el = masks[key].split(',')
            (mx, my, mw, mh) = mask_el
            masks[key] = str(mx) + "," + str(my) + "," + str(mw) + "," + str(mh)
            my_masks.append((masks[key]))
   return(my_masks)


def load_video_frames(trim_file, json_conf, limit=0, mask=1):
   (f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs) = convert_filename_to_date_cam(trim_file)
   cap = cv2.VideoCapture(trim_file)
   frames = []
   frame_count = 0
   go = 1
   while go == 1:
      _ , frame = cap.read()
      if frame is None:
         if frame_count <= 5 :
            cap.release()
            return(frames)
         else:
            go = 0
      else:
         if limit != 0 and frame_count > limit:
            cap.release()
            return(frames)
         if len(frame.shape) == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
         frames.append(frame)
         frame_count = frame_count + 1
   cap.release()
   return(frames)

#         if mask == 1:
#            for mask in masks:
#               mx,my,mw,mh = mask.split(",")
#               frame[int(my):int(my)+int(mh),int(mx):int(mx)+int(mw)] = 0
