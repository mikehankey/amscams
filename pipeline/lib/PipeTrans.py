"""

   funcs for various video transitions and effects

   long meteors
   mutli-station meteors
   twilight meteors
   brightest meteors

"""

from lib.PipeVideo import load_frames_simple
import cv2
import os
def trans_test(clip1, clip2):
   print("TEST")
   cf1 = load_frames_simple(clip1)
   cf2 = load_frames_simple(clip2)
   print(len(cf1))
   print(len(cf2))
   print(cf1[0].shape)
   print(cf2[0].shape)

   os.system("rm tmp_vids/*")
   # dump all frames from both clips to temp dir
   i = 0
   file_pref1 = clip1.split("/")[-1]
   file_pref2 = clip2.split("/")[-1]
   file_pref1 = file_pref1.replace(".mp4", "-")
   file_pref2 = file_pref2.replace(".mp4", "-")

   for f in cf1:
      of = file_pref1 + '{:03d}'.format(i) + ".jpg"
      if f is not None:
         cv2.imwrite("tmp_vids/" + of, f)
      i += 1

   last_i = i 

   i = 0

   for f in cf2:
      of = file_pref2 + '{:03d}'.format(i) + ".jpg"
      if f is not None:
         cv2.imwrite("tmp_vids/" + of, f)
      i += 1
  


   slide_left(cf1[-2], cf2[0], file_pref1, last_i)

def slide_left(pic1, pic2, pref, start_count):
   trans_time = 15

   print(pic1.shape, pic2.shape)
 
   ih, iw = pic1.shape[:2]

   seg_width = int(iw/trans_time)

   for i in range(0,trans_time):
      new_img = pic2.copy()
      crop_x2 = iw - (seg_width *i)
      old_img = pic1[0:ih, 0:crop_x2]

      ny, nx = old_img.shape[:2]
      new_img[0:ih, 0:nx] = old_img 
      cv2.line(new_img, (nx,0), (nx,720), (100,100,100), 1)
      #cv2.imshow('pepe', old_img) 
      #cv2.waitKey(0)
      cv2.imshow('pepe', new_img) 
      cv2.waitKey(50)
      of = pref + '{:03d}'.format(start_count + i) + ".jpg"
      cv2.imwrite("tmp_vids/" + of, new_img)
   #i += 1
   #of = pref + '{:03d}'.format(i) + ".jpg"
   #cv2.imwrite("tmp_vids/" + of, pic2)
   #cv2.imshow('pepe', pic2) 
   #cv2.waitKey(180)
   vid_from_imgs("tmp_vids/", "tmp_vids/out.mp4")

def vid_from_imgs(TMP_DIR, outfile):
   cmd = """/usr/bin/ffmpeg -y -framerate 25 -pattern_type glob -i '""" + TMP_DIR + """*.jpg' \
        -c:v libx264 -r 25 -pix_fmt yuv420p -y """ + outfile
   print(cmd)
   os.system(cmd)

