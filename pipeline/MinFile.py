from lib.PipeUtil import cfe, load_json_file, save_json_file, fn_dir, load_mask_imgs
import glob
import cv2


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

   def scan_and_stack(self, mask_img=None):
      print(self.sd_filename)
      cap = cv2.VideoCapture(self.sd_filename)
      fc = 0
      active_mask = None
      small_mask = None
      while True:
         # grab each frame in video file
         grabbed , frame = cap.read()
         print(grabbed, fc)

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


         cv2.imshow('pepe', sub)
         cv2.waitKey(30)
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(sub)


         last_gray = gray
         fc += 1


   json_conf = load_json_file("../conf/as6.json")
   mask_imgs, sd_mask_imgs = load_mask_imgs(json_conf)


min_file = MinFile(sd_filename= "/mnt/ams2/SD/proc2/2021_03_15/2021_03_15_10_33_01_000_010001.mp4")
min_file.scan_and_stack()
