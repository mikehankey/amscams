import cv2
import numpy as np
import os
from tensorflow.keras.models import *
from lib.PipeUtil import load_json_file, save_json_file, calc_dist
import tensorflow.keras
from tensorflow.keras.models import load_model
from tensorflow.keras.models import Sequential
import cv2
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator, array_to_img, img_to_array, load_img
import glob
import sys
#sys.setrecursionlimit(10000)


class ASAI_Detect():

   def __init__(self):
      print("ASAI Detect")

   def which_cnts(self, cnt_res):
      if len(cnt_res) == 3:
         (_, cnts, xx) = cnt_res
      elif len(cnt_res) == 2:
         (cnts, xx) = cnt_res
      return(cnts)

   def make_first_frame(self, video_file):
      cap = cv2.VideoCapture(video_file)
      grabbed , frame = cap.read()      
      return(frame)

   def make_roi_video(self, video_file, x1,y1,x2,y2, frames=None):
      frame_data = []
      roi_frames = []
      roi_sub_frames = []
      frame = True
      if frames is None:
         frames = []
         cap = cv2.VideoCapture(video_file)
         while frame is not None:
            grabbed , frame = cap.read()      
            if frame is not None:
               frames.append(frame)

      for frame in frames:
         frame = cv2.resize(frame,(1920,1080))
         roi = frame[y1:y2,x1:x2]
         roi_frames.append(roi)

      fn = 0
      rolling = []
      nomo = 0
      cm = 0
      first_event_frame = None
      last_event_frame = None
      events = []
      last_blur = None
      combined = None
      for roi in roi_frames:
         pfn = fn - 1 
         if pfn < 0:
            pfn = 0
         blur_img = cv2.GaussianBlur(roi_frames[pfn], (7, 7), 0)
         if last_blur is not None:
            if combined is None:
               combined = cv2.addWeighted(blur_img, .5, last_blur, .5,0)
            else:
               combined = cv2.addWeighted(blur_img, .5, combined, .5,0)
            sub_roi = cv2.subtract(roi, combined)
         else:
            sub_roi = cv2.subtract(roi, blur_img)
         roi_sub_frames.append(sub_roi)
         sum_val = np.sum(sub_roi)
         rolling.append(np.sum(sub_roi))
         gray = cv2.cvtColor(sub_roi, cv2.COLOR_BGR2GRAY)
         max_val = np.max(gray)
         thresh_val = max_val * .7
         if thresh_val < 20:
            thresh_val = 20 

         _, threshold = cv2.threshold(gray.copy(), thresh_val, 255, cv2.THRESH_BINARY)
         threshold = cv2.dilate(threshold.copy(), None , iterations=4)
         cnts = self.get_contours(threshold)

         #cv2.imshow('pepe3',threshold)
         #cv2.waitKey(30)
         last_blur = blur_img


         if len(rolling) <= 1:
            avg = sum_val
         else:
            avg = np.mean(rolling)
         factor = sum_val / avg
         if factor > 1.2:
            det = "*"
            cm += 1
            nomo = 0
         else:
            det = ""
            nomo += 1
            cm = 0
         if cm == 3:
            first_event_frame = fn - 3

         if first_event_frame is not None and last_event_frame is None and cm == 0 and nomo >= 3:
            last_event_frame = fn
            events.append((first_event_frame,last_event_frame))
            first_event_frame = None
            last_event_frame = None

        
         if len(cnts) > 0:
            frame_data.append((int(fn), int(cm), int(nomo), int(avg), int(np.sum(sub_roi)), float(factor), cnts))
            #print(first_event_frame, last_event_frame, det, fn, cm, nomo, avg, np.sum(sub_roi), factor, cnts)
         #cv2.imshow('pepe', sub_roi)
         #cv2.waitKey(30)
         fn += 1
        
      return(frames, roi_frames, roi_sub_frames, frame_data)

   
   def get_contours(self,thresh_img):
      cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
      cnts = self.which_cnts(cnt_res)
   
      conts = []
      for (i,c) in enumerate(cnts):
         x,y,w,h = cv2.boundingRect(cnts[i])
         intensity = int(np.sum(thresh_img[y:y+h,x:x+w]))
         px_avg = intensity / (w*h)
         if w > 9 and h > 9 and px_avg > 3:
            conts.append((x,y,w,h,int(intensity),int(px_avg)))
      return(conts)
   
   def detect_roi(self,roi_img):
      img = roi_img.copy()
      imgfile = "temp_img.png"
      cv2.imwrite(imgfile, roi_img)


      #img = cv2.resize(img,(150,150)) 
      #img = np.reshape(img,[1,150,150,3])
      #img_size = [150,150]
      #img = keras.preprocessing.image.load_img(imgfile, target_size = img_size)
      #img = keras.preprocessing.image.img_to_array(img).astype(np.float32)
      #img /= 255.
      #img = np.expand_dims(img, axis = 0)


      img_height = 150
      img_width = 150
      #img = keras.utils.load_img(
      img = load_img(
         imgfile, target_size=(img_height, img_width)
      )
      img_array = img_to_array(img)
      img_array = tf.expand_dims(img_array, 0) # Create a batch

      predictions = self.model.predict(img_array)

      score = tf.nn.softmax(predictions[0])
      predicted_class = self.class_names[np.argmax(score)]

      return(predicted_class)

   def merge_cnts(self,cnts):
      parents = []
      children = []
      for x,y,w,h,ii, mv in cnts:
         cx = int(x + (w/2))
         cy = int(y + (h/2))
         merge = False
         for px, py, pw,ph in parents:
            dist = calc_dist((cx,cy), (px,py))   
            if dist < 300:
               merge = True
               parent_x = px
               parent_y = py
         if merge is False:
            parents.append((cx,cy,w/2,h/2))
         else:
            children.append((parent_x,parent_y,cx,cy,w/2,h/2))

      #print("P", parents)
      #print("C", children)

      groups = {}
      for row in children:
         px,py,cx,cy,w,h = row
         key = str(px) + "_" + str(py)
         if key not in groups:
            groups[key] = {}
            groups[key]['xs'] = []
            groups[key]['ys'] = []
         groups[key]['xs'].append(px)
         groups[key]['ys'].append(py)
         groups[key]['xs'].append(cx)
         groups[key]['ys'].append(cy)

      for row in parents:
         px,py,w,h = row
         key = str(px) + "_" + str(py)
         if key not in groups:
            groups[key] = {}
            groups[key]['xs'] = []
            groups[key]['ys'] = []
         groups[key]['xs'].append(px+w)
         groups[key]['ys'].append(py+h)
         groups[key]['xs'].append(px-w)
         groups[key]['ys'].append(py-h)

      final_cnts = []
      for key in groups:
         min_x = min(groups[key]['xs'])
         max_x = max(groups[key]['xs'])
         min_y = min(groups[key]['ys'])
         max_y = max(groups[key]['ys'])
         final_cnts.append((int(min_x),int(min_y),int(max_x),int(max_y))) 
         


      return(final_cnts)
   
   def detect_in_stack(self,stack_file, model, labels):
      self.model = model
      self.class_names = labels['labels']
      video_file = stack_file.replace("-stacked.jpg", ".mp4")

      first_frame = self.make_first_frame(video_file)

      stack_img = cv2.imread(stack_file)
      stack_img = cv2.resize(stack_img, (1920,1080))
      first_frame = cv2.resize(first_frame, (stack_img.shape[1], stack_img.shape[0]))
      stack_img_sub = cv2.subtract(stack_img, first_frame)
      #cv2.imshow('pepe2', stack_img_sub)
      #cv2.waitKey(0)
      try:
         stack_gray =  cv2.cvtColor(stack_img_sub, cv2.COLOR_BGR2GRAY)
      except:
         print("BAD STACK IMAGE", stack_file)
         exit()
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(stack_gray)

      thresh_val = max_val * .50
      if thresh_val < 50:
         thresh_val = 50
      _, threshold = cv2.threshold(stack_gray.copy(), thresh_val, 255, cv2.THRESH_BINARY)
      threshold = cv2.dilate(threshold.copy(), None , iterations=4)
      #cv2.imshow('pepe', threshold)
      #cv2.waitKey(0)

      cnts = self.get_contours(threshold)
      if len(cnts) > 1:
         cnts = self.merge_cnts(cnts)
      stack_1080 = cv2.resize(stack_img, (1920,1080))
      show_img = stack_1080.copy()
      sd_h, sd_w = stack_img.shape[:2]
      hdm_x = 1920 / sd_w
      hdm_y = 1080 / sd_h
      roi_imgs = [] 
      roi_vals = [] 
      for row in cnts:
         if len(row) == 6:
            x,y,w,h,i,m = row
            #x = int(x * hdm_x)
            #y = int(y * hdm_y)
            #w = int(w * hdm_x)
            #h = int(h * hdm_y)
            xs = []
            ys = []
            xs.append(x)
            xs.append(x+w)
            ys.append(y)
            ys.append(y+h)
            x1, y1, x2, y2 = self.mfd_roi(None, xs, ys, 0, 0)
         else:
            x1,y1,x2,y2 = row

         x1,y1,x2,y2 = self.bound_cnt( x1,y1,x2,y2,stack_1080, .5)
         #print("X1Y1:", x1,y1,x2,y2)
   
         cv2.rectangle(show_img, (x1,y1), (x2 , y2) , (255, 255, 255), 1)
         roi_img = stack_1080[y1:y2,x1:x2] 
         detect_class = self.detect_roi(roi_img)
         roi_imgs.append(roi_img)
         roi_vals.append((x1,y1,x2,y2))
         if detect_class == "NONMETEOR":
            color = [0,0,255]
         else:
            color = [0,255,0]
         cv2.putText(show_img, detect_class, (x1,y2), cv2.FONT_HERSHEY_SIMPLEX, .5, color, 1)
      show_img = cv2.resize(show_img,(1280,720)) 
      return(show_img, roi_imgs, roi_vals)
   
   
   def mfd_roi(self,mfd=None, xs=None, ys=None, ex=0, ey=0):
      if mfd is not None:
         if len(mfd) == 0:
            return(0,0,1080,1080)
         xs = [row[2] for row in mfd]
         ys = [row[3] for row in mfd]
      x1 = min(xs)
      y1 = min(ys)
      x2 = max(xs)
      y2 = max(ys)
      mx = int(np.mean(xs))
      my = int(np.mean(ys))
      w = x2 - x1
      h = y2 - y1
      if w >= h:
         h = w
      else:
         w = h
      if w < 150 or h < 150:
         w = 150
         h = 150
      if w > 1079 or h > 1079 :
         w = 1060
         h = 1060
      w += ex
      h += ey
      x1 = mx - int(w / 2)
      x2 = mx + int(w / 2)
      y1 = my - int(h / 2)
      y2 = my + int(h / 2)
      w = x2 - x1
      h = y2 - y1
   
      if x1 < 0:
         x1 = 0
         x2 = w
      if y1 < 0:
         y1 = 0
         y2 = h
      if x2 >= 1920:
         x2 = 1919
         x1 = 1919 - w
      if y2 >= 1080:
         y2 = 1079
         y1 = 1079 - h
      return(x1,y1,x2,y2)
   
   def load_my_model(self,model_file):
      model = Sequential()
   
      #model =load_model('first_try_model.h5')
      #print(model_file)
      model =load_model(model_file)
      model.compile(loss='binary_crossentropy',
                    optimizer='rmsprop',
                    metrics=['accuracy'])
      return(model)

   def bound_cnt(self, x1,y1,x2,y2,img, margin=.5):
      ih,iw = img.shape[:2]
      rw = x2 - x1
      rh = y2 - y1
      if rw > rh:
         rh = rw
      else:
         rw = rh
      rw += int(rw*margin )
      rh += int(rh*margin )
      if rw >= ih or rh >= ih:
         rw = int(ih*.95)
         rh = int(ih*.95)
      if rw < 180 or rh < 180:
         rw = 180
         rh = 180

      cx = int((x1 + x2)/2)
      cy = int((y1 + y2)/2)
      nx1 = cx - int(rw / 2)
      nx2 = cx + int(rw / 2)
      ny1 = cy - int(rh / 2)
      ny2 = cy + int(rh / 2)
      if nx1 <= 0:
         nx1 = 0
         nx2 = rw
      if ny1 <= 0:
         ny1 = 0
         ny2 = rh
      if nx2 >= iw:
         nx1 = iw-rw-1
         nx2 = iw-1
      if ny2 >= ih:
         ny2 = ih-1
         ny1 = ih-rh-1
      if ny1 <= 0:
         ny1 = 0
      if nx1 <= 0:
         nx1 = 0
      #print("NX", nx1,ny1,nx2,ny2)
      return(nx1,ny1,nx2,ny2)
  
if __name__ == '__main__':
   date = sys.argv[1]
   model_file = "D:/MRH/ALLSKYOS/first_try_model.h5"
   model = self.load_my_model(model_file)
   files = glob.glob("Y:/meteors/" + date + "/*stacked.jpg")
   for stack_file in files:
      #stack_file = "Y:/meteors/2019_06_08/2019_06_08_04_33_28_000_010006-trim0232-stacked.jpg"
      self.detect_in_stack(stack_file, model)
   
