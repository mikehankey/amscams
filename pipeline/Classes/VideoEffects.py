from PIL import ImageFont, ImageDraw, Image, ImageChops
import numpy as np
import cv2
from Classes.RenderFrames import RenderFrames

class VideoEffects():
   def __init__(self):
      self.version = "1"
#ALLSKY7_LOGO_BLACK.png        ALLSKY_LOGO_BLACK_GLOBAL_NETWORK.png             logo.png
#ALLSKY7_LOGO_PROD_PLAIN.png   ALLSKY_LOGO_BLACK_METEORS_OF_THE_LAST_NIGHT.png  stemp.png
#ALLSKY7_LOGO_TRANSPARENT.png  ALLSKY_LOGO_BLACK_NO_SUBTITLE.png                temp.png
#ALLSKY_LOGO.png               ALLSKY_LOGO_TRANSPARENT.png

      self.allsky7_logo_black = cv2.imread("ALLSKY7_LOGO_BLACK.png")
      self.allsky7_logo_black_global_network = cv2.imread("ALLSKY_LOGO_BLACK_GLOBAL_NETWORK.png")
      self.allsky7_logo_black_meteors = cv2.imread("ALLSKY_LOGO_BLACK_METEORS_OF_THE_LAST_NIGHT.png")
      self.allsky7_logo_black_no_subtitle = cv2.imread("ALLSKY_LOGO_BLACK_NO_SUBTITLE.png")
      self.allsky7_logo_transparent = cv2.imread("ALLSKY_LOGO_TRANSPARENT.png")

      self.rf = RenderFrames()
      if False:
         cv2.imshow('pepe', self.allsky7_logo_black)
         cv2.waitKey(0)

         cv2.imshow('pepe', self.allsky7_logo_black_global_network)
         cv2.waitKey(0)

         cv2.imshow('pepe', self.allsky7_logo_black_meteors)
         cv2.waitKey(0)

         cv2.imshow('pepe', self.allsky7_logo_black_no_subtitle)
         cv2.waitKey(0)
     
         cv2.imshow('pepe', self.allsky7_logo_transparent)
         cv2.waitKey(0)

         cv2.imshow('pepe', self.allsky7_logo_black_global_network)
         cv2.waitKey(0)



   def intro_as7(self):
      print("HI")

   def set_outdir(self, outdir):
      self.outdir = outdir
      if os.path.exists(self.outdir) is False:
         os.makedirs(self.outdir)

   def type_text(self, phrases=["Well, hello there..."], base_frame = None, duration=1, font_face=None, font_size=20, font_color="white", pos_x=None, pos_y=None, x_space=20 , phrase_pause=20):

      if base_frame is None:
         base_frame = blank_image = np.zeros((1080,1920,3),dtype=np.uint8)
      if len(base_frame.shape) > 3:
         #convert the image from RGBA2RGB
         base_frame = cv2.cvtColor(base_frame, cv2.COLOR_BGRA2BGR)
      base_frame = (base_frame * 255).astype(np.uint8)
      image = Image.fromarray(base_frame.copy())
      draw = ImageDraw.Draw(image)    

      if pos_x is None:
         # try to center the text!
         #pos_x = int(int(base_frame.shape[1] / 2) - int(int(len(phrases[0]) / 2) * (5)) )
         print("PHRAS", len(phrases[0]))
         print("FONT SIZE", int(font_size/3))
         print("POS X", pos_x)

      if font_face is None:
         font = ImageFont.truetype("/usr/share/fonts/truetype/DejaVuSans.ttf", font_size, encoding="unic" )
      else:
         font = ImageFont.truetype(font_face, font_size, encoding="unic" )


      desc = ""
      #if pos_x < base_frame.shape[1] / 4:
      #   pos_x = int(base_frame.shape[1] / 4)

      for phrase in phrases:
         image = Image.fromarray(base_frame.copy())
         draw = ImageDraw.Draw(image)    
         desc = ""
         pc = 0
         for char in phrase:
            for w in range(0,duration):
               if w == 0:
                  desc = desc + char
                  pos_x = int(int(base_frame.shape[1] / 2) - int(int(len(phrase) / 2) * (font_size/2)) )
                  print(pos_x, pos_y, len(phrase))
                  draw.text((pos_x, pos_y), str(desc), font = font, fill=font_color)
               show_img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
               cv2.imshow("pepe", show_img)
               cv2.waitKey(30)
               if pc == len(phrase) -2:
                  for q in range(0,phrase_pause):
                     cv2.imshow("pepe", show_img)
                     cv2.waitKey(30)
            pc += 1


       
