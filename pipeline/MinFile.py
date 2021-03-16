import sys
import os
import glob
import cv2
import numpy as np
from PIL import ImageFont, ImageDraw, Image, ImageChops



from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs
from Detector import Detector

class MinFile:
   def __init__(self, sd_filename):
      self.sd_filename = sd_filename
      self.fn = self.sd_filename.split("/")[-1]
      self.day = self.fn[0:10]
      self.cam_id = self.fn[24:30]
      self.proc_dir = "/mnt/ams2/SD/proc2/" + self.day + "/" 
      self.proc_img_dir = "/mnt/ams2/SD/proc2/" + self.day + "/images/" 
      self.proc_data_dir = "/mnt/ams2/SD/proc2/" + self.day + "/odata/" 
      if cfe(self.proc_img_dir, 1) == 0:
         os.makedirs(proc_img_dir)
      if cfe(self.proc_data_dir, 1) == 0:
         os.makedirs(self.proc_data_dir)
      self.base_fn = self.fn.replace(".mp4", "")
      self.stack_file = self.proc_img_dir + self.fn.replace(".mp4", "-stacked.jpg")
      self.stack_thumb = self.proc_img_dir + self.fn.replace(".mp4", "-stacked-tn.jpg")
      self.detect_file = self.proc_data_dir + self.base_fn + "_detect.json" 
      self.moving_file = self.proc_data_dir + self.base_fn + "_moving.json" 
      self.meteor_file = self.proc_data_dir + self.base_fn + "_meteors.json" 
      if cfe(self.moving_file) == 1:
         self.moving_objects = load_json_file(self.moving_file)
         new_objs = []
         for obj in self.moving_objects:
            status, report = Detector.analyze_object(obj)
            obj['report'] = report
            new_objs.append(obj)
         self.moving_objects = new_objs

      else:
         self.moving_objects = None

      if cfe(self.detect_file) == 1:
         self.processed = 1 
      else:
         self.processed = 0
      if cfe(self.meteor_file) == 1:
         self.meteor_objects = load_json_file(self.meteor_file)
      else:
         self.meteor_objects = None
      #self.json_file = self.proc_data_dir + self.fn.replace(".mp4", "-vals.json")
      #self.sum_vals = []
      self.max_vals = []
      self.pos_vals = []

   def stack_stack(self, pic1, pic2):
      stacked_image=ImageChops.lighter(pic1,pic2)
      return(stacked_image)

   def get_contours(self,frame,sub,fc, multi=1):
      cont = []
      cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      noise = 0
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(sub[y:y+h,x:x+w]))
         x = int(x * multi)
         y = int(y * multi)
         h = int(h * multi)
         w = int(w * multi)
         if x != 0 and y != 0 and w > 1 and h > 1:
            cont.append((fc, x,y,w,h,intensity))
         else:
            noise += 1
      return(cont, noise)


   def scan_and_stack(self, mask_img=None):
      stacked_image = None
      bg_stack = None
      if cfe(self.detect_file) == 1 and cfe(self.stack_thumb) == 1:
         print("This detect file is already done.")
         return()
      cap = cv2.VideoCapture(self.sd_filename)
      fc = 0
      active_mask = None
      small_mask = None
      thresh_adj = 0
      while True:
         # grab each frame in video file
         grabbed , frame = cap.read()
         if fc % 100 == 0:
            print(fc)

         #break when done
         if not grabbed and fc > 5:
            break

         # setup mask if it exists
         if active_mask is None and mask_img is not None:
            active_mask = cv2.resize(mask_img,(frame.shape[1],frame.shape[0]))
            small_mask = cv2.resize(active_mask, (0,0),fx=.5, fy=.5)

         # resize frame to 1/2 size
         small_frame = cv2.resize(frame, (0,0),fx=.5, fy=.5)
         gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
         if fc > 0:
            sub = cv2.subtract(gray, last_gray)
            if bg_stack is not None:
               sub = cv2.subtract(sub, np.asarray(bg_stack))
            if small_mask is not None:
               sub = cv2.subtract(sub,small_mask)
         else:
            sub = cv2.subtract(gray, gray)


         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         self.max_vals.append(max_val)
         if fc >= 12:
            max_thresh = np.median(self.max_vals[0:10])
         else:
            max_thresh = 10
         if max_thresh < 15:
            max_thresh = 15
         max_thresh += thresh_adj
         #print(max_thresh, max_val)
         if max_val > max_thresh:
            _, thresh_frame = cv2.threshold(sub, 11, 255, cv2.THRESH_BINARY)
            #sum_val =cv2.sumElems(thresh_frame)[0]
            thresh_frame = cv2.dilate(thresh_frame.copy(), None , iterations=4)
            cnts,noise = self.get_contours(thresh_frame, sub, fc, 2)
            #print("LEN CNTS:", len(cnts), noise, thresh_adj)
            if len(cnts) + noise >= 3 and thresh_adj < 30:
               thresh_adj += 10
            #print(sum_val, len(cnts))
            #cv2.imshow('pepe2', small_frame)
            #cv2.imshow('pepe', thresh_frame)
            #cv2.waitKey(30)
            self.pos_vals.append(cnts)

            # add frame to stack
         if max_val > max_thresh or fc <= 25:
            frame_pil = Image.fromarray(frame)
            if stacked_image is None:
               stacked_image = self.stack_stack(frame_pil, frame_pil)
            else:
               stacked_image = self.stack_stack(stacked_image, frame_pil)

         if fc <= 100:

            frame_pil = Image.fromarray(sub)
            if bg_stack is None:
               bg_stack = self.stack_stack(frame_pil, frame_pil)
            else:
               bg_stack = self.stack_stack(bg_stack, frame_pil)

         last_gray = gray
         fc += 1

      det = Detector()
      objects = {}
      for i in range(0, len(self.pos_vals)):
         if len(self.pos_vals[i]) > 0:
            for fn,x,y,w,h,intensity in self.pos_vals[i]:
               oid, objects = Detector.find_objects(fn,x,y,w,h,intensity,objects, 20)

      moving_objs = []
      non_moving_objs = []
      meteor_objs = []
      for oid in objects:
         if len(objects[oid]['ofns']) >= 3 :
            status, report = Detector.analyze_object(objects[oid])
            if status == 1:
               if report['moving'] == 1:
                  #print(oid, status, report )
                  objects[oid]['report'] = report
                  moving_objs.append(objects[oid])
               else:
                  non_moving_objs.append(objects[oid])

      # save the stack, thumb stack and json files
      if cfe(self.stack_file) == 0:
         print("SAVED:", self.stack_file)
         print("STACKED IMG:", stacked_image)
         if stacked_image is not None:
            cv2.imwrite(self.stack_file, np.asarray(stacked_image) ,[cv2.IMWRITE_JPEG_QUALITY, 70])
         else:
            print("STACKED IMAGE IS NONE!", self.sd_filename)

      if cfe(self.stack_thumb) == 0:
         tn_stack = cv2.resize(np.asarray(stacked_image), (300,169))
         print("SAVED:", self.stack_thumb)
         cv2.imwrite(self.stack_thumb, np.asarray(tn_stack) ,[cv2.IMWRITE_JPEG_QUALITY, 70])

      # save json files 
      detect_info = {}
      detect_info['status'] = 0
      detect_info['moving'] = 0
      detect_info['non_moving_objs'] = non_moving_objs
      if len(moving_objs) > 0:
         detect_info['status'] = 1
         detect_info['moving'] = 1
         print("Saved motion detection.", self.moving_file)
         save_json_file(self.moving_file, moving_objs)
      save_json_file(self.detect_file, detect_info)

# MAIN SCRIPT
if __name__ == "__main__":
   vfile = sys.argv[1]
   min_file = MinFile(sd_filename= vfile)
   #print("MIN FILE:", min_file.fn, min_file.cam_id, min_file.moving_objects, min_file.processed)
   #for key in min_file.__dict__:
   #   print(key )
   for obj in min_file.moving_objects:
     # print(obj['report'])
      print("FNS:", obj['ofns']) 
      print("INT:", obj['oint']) 
      for key in obj['report']:
         print(key, obj['report'][key])
   #min_file.scan_and_stack()
