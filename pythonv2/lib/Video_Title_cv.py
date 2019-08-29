import cv2 
import numpy as np
from PIL import ImageFont, ImageDraw, Image
from lib.VIDEO_VARS import * 
from lib.Video_Tools_cv import add_text

# From Mike
from lib.VideoLib import load_video_frames, make_movie_from_frames

TITLE_1280x720 = "/home/ams/amscams/dist/vids/ams_intro/1280x720.mp4"
DEFAULT_TITLE = TITLE_1280x720
 

# Add big text centered 
def add_big_text(background,text,y,color,size, the_font=VIDEO_FONT_BOLD):

    # Convert background to RGB (OpenCV uses BGR)  
    cv2_background_rgb = cv2.cvtColor(background,cv2.COLOR_BGR2RGB)  
    
    # Pass the image to PIL to use ttf fonts
    pil_im  = Image.fromarray(cv2_background_rgb)  
    draw    = ImageDraw.Draw(pil_im)  
    font    = ImageFont.truetype(the_font, size)  

    x = cv2_background_rgb.shape[1]/2 - font.getsize(text)[0]/2
     
    draw.text((x, y), text, font=font, fill=color)  
    return  cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)  


# This function create a quick video (lenght of DEFAULT_TITLE ~ 3sec )
# with the animated AMS logo and a custom text (ONE LINE TEXT ONLY)
def create_title_video(text,text2,output):

    # Get the original frames 
    cap = cv2.VideoCapture(DEFAULT_TITLE)

    frames = []
    frame_count = 0
    go = 1
    while go == 1:
        _ , frame = cap.read()
      
        if frame is not None: 
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) 
            frames.append(frame) 
        else:
            go = 0 
    
    cap.release()
   
    new_frames = []

    #AMS LOGO
    anim_duration  = 85
    end_fade_in_ams_logo = 65

    # TITLE OF THE VIDEO
    title_duration = 95

    fc = 0
    transp = 0

    # Animation of the AMS LOGO
    for frame in frames:
        fc +=1

        if(fc<anim_duration):
            #Convert to proper colors
            n_frame = frame

            #Add Text 
            transp  = int(fc*255/(anim_duration-end_fade_in_ams_logo))
            n_frame = add_big_text(n_frame,"AMERICAN METEOR SOCIETY", 360, (transp,transp,transp,255), 25)
            new_frames.append(n_frame)
            fc += 1

    
    # Initial Position of the rectangle
    rect_x_init = int(1280/2)
    rect_x = rect_x_init
    rect_w = 10
    rect_y = 327
    rect_h = 1
    fc = 0
    max_rect_half_width = 250 
    rect_anim_duration = int(title_duration/2)


    # Title BG
    for x in range(0, title_duration):

        fc +=1

        # Title
        n_frame = add_big_text(frames[0],text,250, (250,250,209,255), 60)

        #2nd ligne smaller
        n_frame = add_big_text(n_frame,text2,340, (250,250,209,255), 20,VIDEO_FONT)

        #Rectangle
        #rect_x = rect_x - int(fc*max_rect_half_width/rect_anim_duration)  
        rect_w = rect_w # rect_w + int(fc*max_rect_half_width*2/(rect_anim_duration))

        rect_x = int(rect_x - (fc*rect_x_init/max_rect_half_width)/rect_anim_duration)
        
        cv2.rectangle(n_frame, (n_rect_x, rect_y), (n_rect_x+rect_w, rect_y+rect_h), (250,250,209,255), 1)
        
        new_frames.append(n_frame)

    make_movie_from_frames(new_frames, [0,len(new_frames) - 1], output, 1)
    print('OUTPUT ' + output)