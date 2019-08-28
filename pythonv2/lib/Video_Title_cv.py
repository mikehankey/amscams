import cv2 
import numpy as numpy
from lib.VIDEO_VARS import * 
from lib.Video_Tools_cv import add_text

TITLE_1280x720 = "/home/ams/amscams/dist/vids/ams_intro/1280x720.mp4"
DEFAULT_TITLE = TITLE_1280x720


# Return All frames from video
def get_video_frames(_input):
    frames = []
    vidcap = cv2.VideoCapture(_input)
    success,frame = vidcap.read() 
    while success:
        frames.append(frame)
        success,frame = vidcap.read()
    vidcap.release()
    return frames

 
# This function create a quick video (lenght of DEFAULT_TITLE ~ 3sec )
# with the animated AMS logo and a custom text (ONE LINE TEXT ONLY)
def create_title_video(text,output):

    # Get the original frames
    frames = get_video_frames(DEFAULT_TITLE)
    new_frames = []

    for frame in frames:
        frame = add_text(frame,text,0,0,True)
        new_frames.append(frame)

    make_movie_from_frames(new_frames, [0,len(new_frames) - 1], output, 1)
    print('OUTPUT ' + output)