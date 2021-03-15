from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs
import glob
import cv2
from Detector import Detector
import numpy as np

class MinFile:
   def __init__(self, sd_filename):
      self.sd_filename = sd_filename
      self.fn = self.sd_filename.split("/")[-1]
      self.day = self.fn[0:10]
      self.proc_dir = "/mnt/ams2/SD/proc2/" + self.day + "/" 
      self.proc_img_dir = "/mnt/ams2/SD/proc2/" + self.day + "/images/" 
      self.proc_data_dir = "/mnt/ams2/SD/proc2/" + self.day + "/data/" 
      if cfe(self.proc_img_dir, 1) == 0:
         os.makedirs(proc_img_dir)
      if cfe(self.proc_data_dir, 1) == 0:
         os.makedirs(self.proc_data_dir)
      self.stack_file = self.proc_img_dir + self.fn.replace(".mp4", "-stacked-tn.jpg")
      self.json_file = self.proc_data_dir + self.fn.replace(".mp4", "-vals.json")
      self.sum_vals = []
      self.max_vals = []
      self.pos_vals = []


   def get_contours(self,frame,sub,multi=1):
      cont = []
      cnt_res = cv2.findContours(frame.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = np.sum(sub[y:y+h,x:x+w])
         x = int(x * multi)
         y = int(y * multi)
         h = int(h * multi)
         w = int(w * multi)
         if x != 0 and y != 0 and w > 1 and h > 1:
            cont.append((x,y,w,h,intensity))
      return(cont)


   def scan_and_stack(self, mask_img=None):
      cap = cv2.VideoCapture(self.sd_filename)
      fc = 0
      active_mask = None
      small_mask = None
      while True:
         # grab each frame in video file
         grabbed , frame = cap.read()
         if fc % 100 == 0:
            print(fc)

         #break when done
         if not grabbed and fc > 5:
            print("FRAME NOT GRABBED:", fc)
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
            if small_mask is not None:
               sub = cv2.subtract(sub,small_mask)
         else:
            sub = cv2.subtract(gray, gray)


         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)
         if max_val > 10:
            _, thresh_frame = cv2.threshold(sub, 11, 255, cv2.THRESH_BINARY)
            sum_val =cv2.sumElems(thresh_frame)[0]
            cnts = self.get_contours(thresh_frame, sub, 2)
            #print(sum_val, len(cnts))
            #cv2.imshow('pepe', thresh_frame)
            #cv2.waitKey(30)
            self.pos_vals.append(cnts)
         else:
            self.pos_vals.append([])

         last_gray = gray
         fc += 1

      det = Detector()
      objects = {}
      for i in range(0, len(self.pos_vals)):
         if len(self.pos_vals[i]) > 0:
            for x,y,w,h,intensity in self.pos_vals[i]:
               oid, objects = Detector.find_objects(i,x,y,w,h,intensity,objects, 20)
      for oid in objects:
         if len(objects[oid]['ofns']) >= 3 :
            status, report = Detector.analyze_object(objects[oid])
            if status == 1:
               if report['moving'] == 1:
                  print(oid, status )

   #json_conf = load_json_file("../conf/as6.json")
   #mask_imgs, sd_mask_imgs = load_mask_imgs(json_conf)

# MAIN SCRIPT
if __name__ == "__main__":

   #min_file = MinFile(sd_filename= "/mnt/ams2/SD/proc2/2021_03_15/2021_03_15_08_25_01_000_010002.mp4")
   min_file = MinFile(sd_filename= "/mnt/ams2/SD/proc2/2021_03_15/2021_03_15_10_24_00_000_010001.mp4")
   min_file.scan_and_stack()
