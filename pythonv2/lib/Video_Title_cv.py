import cv2 
import numpy as np
from PIL import ImageFont, ImageDraw, Image
from lib.VIDEO_VARS import * 
from lib.Video_Tools_cv import add_text

# From Mike
from lib.VideoLib import load_video_frames, make_movie_from_frames

TITLE_1280x720 = "/home/ams/amscams/dist/vids/ams_intro/1280x720.mp4"
DEFAULT_TITLE = TITLE_1280x720
ALL_SKY_CAMS_FRAME = "/home/ams/amscams/dist/vids/allskycams.png"

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
def create_title_video(text,text2,output,title_color=(255,255,255,255)):

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


    # TITLE OF THE VIDEO
    title_duration = 95
    
    # Initial Position of the rectangle
    rect_x_init = int(1280/2)  
    rect_x = rect_x_init
    rect_w = 0
    rect_y = 327
    rect_h = 1
    fc = 0
    rect_min_x = 350
    rect_max_w = 650
    rect_anim_duration = int(title_duration/2)

    title_y = 250
    title_size = 60
    sub_title_y = 340
    sub_title_zize = 20


    # Title BG
    for x in range(0, title_duration):

        fc +=1

        # Title
        n_frame = add_big_text(frames[0],text,title_y, title_color, title_size)

        #2nd ligne smaller
        n_frame = add_big_text(n_frame,text2,sub_title_y, title_color, sub_title_zize,VIDEO_FONT)

        #Rectangle 
        #rect_x = int(fc*((rect_min_x-rect_x_init)/rect_anim_duration)+rect_x_init)
        #rect_w = int(fc*(max_rect_half_width/rect_anim_duration))
        
        rect_x = int(rect_x - fc*(rect_x-rect_min_x)/rect_anim_duration)

        cv2.rectangle(n_frame, (rect_x, rect_y), (rect_x+rect_w, rect_y+rect_h),title_color, 1)
        
        new_frames.append(n_frame)

    make_movie_from_frames(new_frames, [0,len(new_frames) - 1], output, 1)
    print('OUTPUT ' + output)


# Create thank you video
def create_thank_operator_video(operators,duration,output,line_height=45,op_font_size=30):

    top_y = 50
    top_size = 40  

    frame = np.zeros((750,1280,3), np.uint8)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) 

    # Add "Thank you on top"
    frame = add_big_text(frame,"Thank you to all the AMS Cam Operators", top_y, (255,255,255,255), top_size)
 
    all_frames = []
    how_many_operators = len(operators)

    op_c = 0

    for op in operators:
        frame = add_big_text(frame,op, (top_y + top_size + line_height )+ line_height*op_c, (255,255,255,255), op_font_size)
        op_c+=1


    for x in range(0,duration):
        all_frames.append(frame)        

    make_movie_from_frames(all_frames, [0,len(all_frames) - 1], output, 1)
    print('OUTPUT ' + output)


# Create Allskycams Add video
def create_allskycams_video(text1,text2,duration,output):
    
    # Get the original frames 
    cap = cv2.VideoCapture(ALL_SKY_CAMS_FRAME)

    frames = []
    frame_count = 0
    go = 1
    while go == 1:
        _ , frame = cap.read()
      
        if frame is not None: 
            #frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR) 
            frames.append(frame) 
        else:
            go = 0 
    
    cap.release()
    

    # Add text 1
    new_frame = add_big_text(frames[0],text1,380, (255,255,255,255), 40)

    # Add text 2
    new_frame = add_big_text(new_frame,text2,440, (255,255,255,255), 30)

    all_frames = []
    for x in range(0,duration):
        all_frames.append(new_frame)        

    make_movie_from_frames(all_frames, [0,len(all_frames) - 1], output, 1)
    print('OUTPUT ' + output)