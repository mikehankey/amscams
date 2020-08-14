import cv2 
import numpy as np
import subprocess 
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


# Create just a title splash screen with Main Title & Subtitle
def create_simple_title_video(text,text2,output,title_color=(255,255,255,255), rect= True):
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
            go == 0
    
    cap.release()
   
    new_frames = []

    #AMS LOGO
    anim_duration  = 85
    end_fade_in_ams_logo = 65
 
    fc = 0
    transp = 0

   # TITLE OF THE VIDEO
   title_duration = 95
   
   # Initial Position of the rectangle
   rect_x_init = int(1280/2)  
   rect_x = rect_x_init
   rect_w = 0
   rect_y = 327
   rect_h = 1
   fc = 0
   rect_min_x = 250 
   rect_anim_duration = int(title_duration/2)

   title_y = 250
   title_size = 60
   sub_title_y = 355
   sub_title_zize = 32

   # Title BG
   for x in range(0, title_duration):

      fc +=1

      # Title
      n_frame = add_big_text(frames[0],text,title_y, title_color, title_size)

      #2nd ligne smaller
      n_frame = add_big_text(n_frame,text2,sub_title_y, title_color, sub_title_zize,VIDEO_FONT)

      #Rectangle 
      if(rect is True):

         if(rect_x > rect_min_x):
               rect_x = int(rect_x - fc*(rect_x-rect_min_x)/rect_anim_duration)

         rect_w = 1280-rect_x*2     

         cv2.rectangle(n_frame, (rect_x, rect_y), (rect_x+rect_w, rect_y+rect_h),title_color, 1)
      
      new_frames.append(n_frame)

   make_movie_from_frames(new_frames, [0,len(new_frames) - 1], output, 1)
   print('OUTPUT ' + output)

# This function create a quick video (lenght of DEFAULT_TITLE ~ 3sec )
# with the animated AMS logo and a custom text (ONE LINE TEXT ONLY)
def create_title_video(text,text2,output,title_color=(255,255,255,255), logo=True, rect= True):

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
    if(logo is True):
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
    rect_min_x = 250 
    rect_anim_duration = int(title_duration/2)

    title_y = 250
    title_size = 60
    sub_title_y = 355
    sub_title_zize = 32


    # Title BG
    for x in range(0, title_duration):

        fc +=1

        # Title
        n_frame = add_big_text(frames[0],text,title_y, title_color, title_size)

        #2nd ligne smaller
        n_frame = add_big_text(n_frame,text2,sub_title_y, title_color, sub_title_zize,VIDEO_FONT)

        #Rectangle 
        if(rect is True):

            if(rect_x > rect_min_x):
                rect_x = int(rect_x - fc*(rect_x-rect_min_x)/rect_anim_duration)

            rect_w = 1280-rect_x*2     

            cv2.rectangle(n_frame, (rect_x, rect_y), (rect_x+rect_w, rect_y+rect_h),title_color, 1)
        
        new_frames.append(n_frame)

    make_movie_from_frames(new_frames, [0,len(new_frames) - 1], output, 1)
    print('OUTPUT ' + output)


# Create thank you video
def create_thank_operator_video(operators,duration,output,_with_line_animation,line_height=45,op_font_size=30):

    top_y = 50
    top_size = 40  

    frame = np.zeros((720,1280,3), np.uint8)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) 

    # Add "Thank you on top"
    frame = add_big_text(frame,"Thank you to all the AMS Camera Operators", top_y, (255,255,255,255), top_size)
 
    all_frames = []
    #how_many_operators = len(operators)
  
    op_c = 0

    for op in operators:
        frame = add_big_text(frame,op, (top_y + top_size + line_height )+ line_height*op_c, (255,255,255,255), op_font_size)
        op_c +=1
  
 
    # Initial Position of the rectangle
    rect_x_init = int(1280/2)  
    rect_x = rect_x_init
    rect_w = 0
    rect_y = 110
    rect_h = 1
    rect_min_x = 325
    rect_max_w = 1280-(rect_min_x*2)
    rect_anim_duration = duration
 
    fc = 0
    new_frame = frame 

    for x in range(0,duration): 
 
        if(_with_line_animation is True):
            fc +=1

            if(rect_x > rect_min_x):
                rect_x = int(rect_x - int(fc*(rect_x-rect_min_x)/rect_anim_duration))
            rect_w = 1280-rect_x*2     
            cv2.rectangle(new_frame, (rect_x, rect_y), (rect_x+rect_w, rect_y+rect_h),(255,255,255,255), 1)

        all_frames.append(new_frame)           

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
    
    # Add top text
    new_frame = add_big_text(frames[0],"All meteor videos recorded with the All Sky 6 Camera System", 50, (255,255,255,255), 30)

    # Add text 1
    new_frame = add_big_text(new_frame,text1,520, (255,255,255,255), 40)

    # Add text 2
    #new_frame = add_big_text(new_frame,text2,440, (255,255,255,255), 30)

    all_frames = []
    for x in range(0,duration):
        all_frames.append(new_frame)        

    make_movie_from_frames(all_frames, [0,len(all_frames) - 1], output, 1)
    print('OUTPUT ' + output)


# Create  
def create_credit_video(_text1,_text2,_text3,_duration,_output):

    frame = np.zeros((720,1280,3), np.uint8)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) 

    # Add _text1
    frame = add_big_text(frame,_text1, 220, (255,255,255,255), 40)

    # Add _text2
    frame = add_big_text(frame,_text2, 270, (255,255,255,255), 60)

    # Add _text3
    frame = add_big_text(frame,_text3, 340, (255,255,255,255), 30)

    all_frames = []
    for x in range(0,_duration):
        all_frames.append(frame)        

    make_movie_from_frames(all_frames, [0,len(all_frames) - 1], _output, 1)
    print('OUTPUT ' + _output)


# Concat 2 videos with a fading effect of X frames
def concat_videos_fade(video1,video2,output,_from,_to):
    cmd = ' ffmpeg -y -i '+video1+' -i '+video2+' -f lavfi -i  color=black:s=1280x720 -filter_complex \
            "[0:v]format=pix_fmts=yuva420p,fade=t=out:st='+str(_from)+':d=1:alpha=1,setpts=PTS-STARTPTS[va0];\
             [1:v]format=pix_fmts=yuva420p,fade=t=in:st=0:d=1:alpha=1,setpts=PTS-STARTPTS+'+str(_from)+'/TB[va1];\
             [2:v]scale=1280x720,trim=duration='+str(_to)+'[over];\
             [over][va0]overlay[over1];\
             [over1][va1]overlay=format=yuv420[outv]" \
            -vcodec libx264 -map [outv] '+output
  
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")     
    print(output) 