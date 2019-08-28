import cv2 
import numpy as numpy
from lib.VIDEO_VARS import * 
from lib.Video_Tools_cv import add_text

TITLE_1280x720 = "/home/ams/amscams/dist/vids/ams_intro/1280x720.png"
DEFAULT_TITLE = TITLE_1280x720
 
# This function create a quick video (lenght of DEFAULT_TITLE ~ 3sec )
# with the animated AMS logo and a custom text (ONE LINE TEXT ONLY)
def create_title_video(text,output,res_w=1280, res_h=720):

    # Open the blank title video
    cap = cv2.VideoCapture(TITLE_1280x720)

    # Define the codec and create VideoWriter object
    fourcc  = cv2.VideoWriter_fourcc(*'MP4V')
    out     = cv2.VideoWriter(output,fourcc, FPS_HD, (res_w,res_h))
    
    while(cap.isOpened()):
        ret, frame = cap.read()

        if ret==True:
            # Add Text
            frame = add_text(frame,text,0,0,True)

            # Write the Frame
            out.write(frame)
        
        else:
            break


    cap.release()
    out.release()