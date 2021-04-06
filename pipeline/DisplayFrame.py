import cv2
import numpy as np

class DisplayFrame():
   def __init__(self, width=1920, height=1080):
      self.w = width 
      self.h = height 
      self.display_frame = np.zeros((1080,1920,3),dtype=np.uint8)
      self.images = {}

      self.layout = [
         {
            "id": "1",
            "x1": 0,
            "y1": 0,
            "x2": 640,
            "y2": 360,
         },
         {
            "id": "2",
            "x1": 640,
            "y1": 0,
            "x2": 1280,
            "y2": 360,
         },
         {
            "id": "3",
            "x1": 1280,
            "y1": 0,
            "x2": 1920,
            "y2": 360,
         },
         {
            "id": "4",
            "x1": 0,
            "y1": 360,
            "x2": 1280,
            "y2": 1080,
         }
      ]

   def add_image(self, fn, loc, image):
      if fn not in self.images:
         self.images[fn] = {}
      self.images[fn][loc] = image

   def render_frame(self, fn, layout = None):
      if layout is None:
         layout = self.layout
      for i in range(1, len(layout)+1):
         si = i - 1
         x1 = layout[si]['x1']
         y1 = layout[si]['y1']
         x2 = layout[si]['x2']
         y2 = layout[si]['y2']
         if fn in self.images:
            if i in self.images[fn]:
               img = self.images[fn][i]
               w = x2 - x1
               h = y2 - y1
               img = cv2.resize(img,(w,h))
               if len(img.shape) == 2:
                  img = cv2.cvtColor(img,cv2.COLOR_GRAY2BGR)
               print("POS:", fn, i, x1,y1,x2,y2)
               print("IMG SAPE:", img.shape)
               print("DIS SAPE:", self.display_frame.shape)
               self.display_frame[y1:y2,x1:x2] = img
      cv2.imshow("MFD", self.display_frame)
      cv2.waitKey(100)
