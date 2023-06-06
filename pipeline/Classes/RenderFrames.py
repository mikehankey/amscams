import imutils
from PIL import ImageFont, ImageDraw, Image, ImageChops
from lib.PipeVideo import load_frames_simple
import numpy as np
import os
import cv2

class RenderFrames():
   def __init__(self):
      version = 1
      #self.logo_src = cv2.imread("ALLSKY_LOGO_TRANSPARENT.png")
      self.logo_src = cv2.imread("ALLSKY7_LOGO_BLACK.png")
      #self.logo_src[np.all(self.logo_src == (255,255,255), axis=-1)] = (0,0,0)
      self.logo_1920 = imutils.resize(self.logo_src, width=1920)
      self.logo_1280 = imutils.resize(self.logo_src, width=1280)
      #425
      self.logo_640 = imutils.resize(self.logo_src, width=640)
      self.logo_320 = imutils.resize(self.logo_src, width=320)
      self.logo_160 = imutils.resize(self.logo_src, width=160)

      self.slogo_1920 = cv2.resize(self.logo_src, (1920, 1080))
      self.clean_frame = np.zeros((1080,1920,3),dtype=np.uint8)

   def tv_frame(self, images=[], text_data = [], w=1920, h=1080):
      # main frame area
      main_w = 1760 
      main_h = 990 
      margin_x = int((1920 - main_w) / 2)
      margin_y = int((1080 - main_h) / 2)
      mx1 = margin_x 
      my1 = int(margin_y / 2)
      mx2 = mx1 + main_w 
      my2 = my1 + main_h 
      ui = np.zeros((h,w,3),dtype=np.uint8)
      lh = int(main_h + (margin_y / 1.8))
      ui = self.watermark_image(ui, self.logo_160, margin_x, lh, .6, text_data, False)
      cv2.rectangle(ui, (mx1,my1), (mx2,my2) , [200,200,200], 2)
      print("TV FRAME:", ui.shape, type(ui), ui[100,100])
      return(ui, mx1,my1,mx2,my2)


   def frame_template(self, frame_type="1920_1p", images=[], text_data = []):
      ui = self.clean_frame.copy()

      if frame_type == "1920_row_x":
         num_imgs = len(images)
         max_cols = 6
         max_cols = 6

         max_per_row = 4

         width = int(1920 / max_per_row)
         ratio = 1920 / width 
         height = int(1080 / ratio)
         row = 0
         col = 0
         for i in range(0,len(images)):
            y1 = row * height
            y2 = y1 + int(height)
            x1 = int(width*col)
            x2 = x1 + int(width)

            print("ROW,COL:", row, col)
            print("XYs", x1,y1,x2,y2)
            ui[y1:y2,x1:x2] = cv2.resize(images[i] , (width,height))
            col += 1
            cv2.rectangle(ui, (x1,y1), (x2,y2) , [255,255,255], 1)
            #if SHOW == 1:
               #cv2.imshow('pepe', ui)
               #cv2.waitKey(30)
            if x2 >= 1920:
               col = 0
               row += 1
         if len(images) == 10:
            ui[540:1080,0:960] = cv2.resize(images[-2] , (960,540))
            ui[540:1080,960:1920] = cv2.resize(images[-1] , (960,540))


      if frame_type == "1920_4p":
         lh, lw = self.logo_1280.shape[:2]
         cv2.rectangle(ui, (0,0), (1280,720) , [255,255,255], 1)
         cv2.rectangle(ui, (1280,0), (1920,360) , [255,255,255], 1)
         cv2.rectangle(ui, (1280,360), (1920,720) , [255,255,255], 1)
         cv2.rectangle(ui, (0,720), (1280,317+720) , [255,255,255], 1)
         #ui[740:317+740,2:1282] = self.logo_1280
         ui[540:lh+540,2:1282] = self.logo_1280
         cv2.rectangle(ui, (1280,720), (1920,1080) , [255,255,255], 1)

         if len(images) >= 1:
            ui[0:720,0:1280] = cv2.resize(images[0],(1280,720))
         if len(images) >= 2:
            ui[0:360,1280:1920] = cv2.resize(images[1],(640,360))
         if len(images) >= 3:
            ui[360:720,1280:1920] = cv2.resize(images[2],(640,360))
         if len(images) >= 4:
            ui[720:1080,1280:1920] = cv2.resize(images[3],(640,360))
         if len(images) >= 5:
            ui[720:1080,0:640] = cv2.resize(images[4],(640,360))
         if len(images) >= 6:
            ui[720:1080,640:1280] = cv2.resize(images[5],(640,360))
     
         ui = self.watermark_image(ui, self.logo_320, 0, 0, .3, text_data)

      if frame_type == "1920_1p":
         # small logo in bottom right
         logo = self.logo_320
         x1 = 0
         x2 = logo.shape[1]
         y1 = 1080 - logo.shape[0]
         y2 = 1080
         if len(images) >= 1:
            #print("IMG SHAPE:", images[0].shape)
            if len(images[0].shape) == 3:
               ui[0:1080,0:1920] = cv2.resize(images[0] , (1920,1080))
            else:
               print("ERR:", ui.shape, images[0].shape)
         #ui[y1:y2,x1:x2] = logo
         ui = self.watermark_image(ui, logo, x1, y1, .5, text_data)

      self.default_frame = ui

      if frame_type == "1920_pip1_tl":
         # small logo in bottom right
         logo = self.logo_320
         x1 = 0
         x2 = logo.shape[1]
         y1 = 1080 - logo.shape[0]
         y2 = 1080
         if len(images) >= 1:
            #print("IMG SHAPE:", images[0].shape)
            ui[0:1080,0:1920] = cv2.resize(images[0] , (1920,1080))
         #ui[y1:y2,x1:x2] = logo
         if len(images) > 1:
            xoff = 50
            yoff = 50
            ui[yoff:yoff+images[1].shape[0],xoff:xoff+images[1].shape[1]] = images[1]
         ui = self.watermark_image(ui, logo, x1, y1, .5, text_data)

      self.default_frame = ui


      return(ui)

   def watermark_video(self, video_file):
      frames = load_frames_simple(video_file)
      photo_credit = "AMS119 - Steinar Midtskogen, Gaustatoppen, Norway"
      margin_x = 1920 - 350 
      lh = 960 
      #tx,ty,text_size,text_weight,text_color,text
      text_data = [[500,25,1,1,[255,255,255],photo_credit]]
      if os.path.exists("tmp_frames") is False:
         os.makedirs("tmp_frames")
      else:
         os.system("rm tmp_frames/*")

      fc = 0
      for frame in frames:

         if frame is not None:
            fn = "{:03d}".format(fc)
            wt_frame = self.watermark_image(frame, self.logo_320, margin_x, lh, .6, text_data)
            #cv2.imshow('pepe', wt_frame)
            #cv2.waitKey(30)
            cv2.imwrite("tmp_frames/" + fn + ".jpg", 255*wt_frame)
            fc += 1

   def watermark_image(self, background, logo, x=0,y=0, opacity=1,text_data=[], make_int=False):

      h,w = background.shape[:2]
      orig = background.copy() 
      orig = orig.astype(float)
      canvas = np.zeros((h,w,3),dtype=np.uint8)
      mask = np.zeros((h,w,3),dtype=np.uint8)
      logo_image = np.zeros((h,w,3),dtype=np.uint8)

      background = cv2.resize(background, (w,h))
      background = background.astype(float)

      ah = logo.shape[0]
      aw = logo.shape[1]
      logo_image[y:y+ah, x:x+aw] = logo
      _, mask = cv2.threshold(logo_image, 22, 255, cv2.THRESH_BINARY)
      mask = mask.astype(float)/255

      foreground = logo_image
      alpha = mask

      foreground = foreground.astype(float)
      foreground = cv2.multiply(alpha, foreground)

      background = cv2.multiply(1.0 - alpha, background)
      outImage = cv2.add(foreground, background)

      if opacity < 1:
         #blend = cv2.addWeighted(background/255, .5, outImage/255, 1-opacity, opacity)
         blend = cv2.addWeighted(orig/255, 1-opacity, outImage/255, opacity, 0)
      else:
         blend = outImage/255

      if len(text_data) > 0:
         for tx,ty,text_size,text_weight,text_color,text in text_data:
            cv2.putText(blend, text,  (tx,ty), cv2.FONT_HERSHEY_SIMPLEX, text_size, text_color, text_weight)
         #blend cvtColor(inputMat, outputMat, CV_BGRA2BGR);
         blend = cv2.cvtColor(blend, cv2.COLOR_BGRA2BGR)
      #blend = blend * 255
      if make_int is True:
         blend *= 255
         blend = blend.astype(np.uint8)
      #print("WATERMARK BLEND:", type(blend), blend.shape, blend[500,500])
      #blend = blend.astype(np.uint8)
      blend = blend * 255
      return(blend.astype(np.uint8))
