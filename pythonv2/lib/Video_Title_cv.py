import cv2 
import numpy as numpy
from lib.VIDEO_VARS import * 
from lib.Video_Tools_cv import add_text

# From Mike
from lib.VideoLib import load_video_frames, make_movie_from_frames

TITLE_1280x720 = "/home/ams/amscams/dist/vids/ams_intro/1280x720.mp4"
DEFAULT_TITLE = TITLE_1280x720


# This function create a quick video (lenght of DEFAULT_TITLE ~ 3sec )
# with the animated AMS logo and a custom text (ONE LINE TEXT ONLY)
def create_title_video(text,output):

    # Get the original frames 
    cap = cv2.VideoCapture(DEFAULT_TITLE)

    frames = []
    frame_count = 0
    go = 1
    while go == 1:
      _ , frame = cap.read()
      
      if frame is None:
         if frame_count <= 5 :
            cap.release()
            break
         else:
            go = 0
      else:
         if len(frame.shape) == 3 and color == 0:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            print("CONVERSION COLOR_BGR2GRAY ")
         frames.append(frame)
         frame_count = frame_count + 1
    cap.release()
  
    print(str(len(frames)) + " found")


    #frames = load_video_frames(DEFAULT_TITLE,"")
    new_frames = []

    for frame in frames:
 
        #Convert to proper colors
        n_frame =  cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
        n_frame = frame

        #Add Text
        n_frame = add_text(n_frame,text,0,0,True)
        new_frames.append(n_frame)

    make_movie_from_frames(new_frames, [0,len(new_frames) - 1], output, 1)
    print('OUTPUT ' + output)