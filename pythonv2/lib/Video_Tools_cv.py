import cv2
import datetime
import numpy as numpy
from lib.VIDEO_VARS import *   
from lib.Video_Tools_cv_pos import *
from lib.Video_Parameters import get_video_job_default_parameters
from lib.UtilLib import convert_filename_to_date_cam
from PIL import ImageFont, ImageDraw, Image  
from lib.FileIO import load_json_file, cfe

# From Mike
from lib.VideoLib import load_video_frames, make_crop_box, make_movie_from_frames

# Test if 2 rectangles (A & B) overlap 
# (used to move logo or text around if a meteor is behind)
def do_rect_overlap(Ax1,Ay1,Ax2,Ay2,Bx1,By1,Bx2,By2): 
    return Ax1 < Bx2 and Ax2 > Bx1 and Ay1 < By2 and Ay2 > By1

# Test if the meteor box overlap
# the object passed in argment 
# cv2_image  is a cv2 image
# cv2_image_pos is pos "br|bl|tl|tr"
# bg_image is a frame (so we can test the position of the image compared to the frame)
def overlaps_with_image(meteor_box_x1,meteor_box_y1,meteor_box_x2,meteor_box_y2,cv2_image,cv2_image_pos, bg_image): 
    cv2_image_width,cv2_image_height  = cv2_image.shape[1], cv2_image.shape[0]
    # Get overlay position - see lib.Video_Tools_cv_lib compare to the first frame
    image_x,image_y = get_overlay_position_cv(bg_image,cv2_image,cv2_image_pos) 
    return do_rect_overlap(image_x,image_y,image_x + cv2_image_width,image_y + cv2_image_height,meteor_box_x1, meteor_box_y1, meteor_box_x2, meteor_box_y2)
  

# Add text on x,y with default small font (for radiant or other info)
# If centered = the text is placed as if x,y is the center
def add_text(background,text,x,y,centered=False):

    # Convert background to RGB (OpenCV uses BGR)  
    cv2_background_rgb = cv2.cvtColor(background,cv2.COLOR_BGR2RGB)  
    
    # Pass the image to PIL to use ttf fonts
    pil_im  = Image.fromarray(cv2_background_rgb)  
    draw    = ImageDraw.Draw(pil_im)  
    font    = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SMALL_SIZE)  
    
    if(centered==True):
        # Get font.getsize(txt) 
        x = x - font.getsize(text)[0]/2
    
    draw.text((x, y), text, font=font, fill=VIDEO_FONT_SMALL_COLOR)  
    return  cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)  


# Return the coordinates of the box that 
# correspond to a text inside a frame
def get_text_box(background,text,position,line_number=1,bold=False):
    # Convert background to RGB (OpenCV uses BGR)  
    cv2_background_rgb = cv2.cvtColor(background,cv2.COLOR_BGR2RGB)  
    
    # Pass the image to PIL  
    pil_im = Image.fromarray(cv2_background_rgb)  
    draw = ImageDraw.Draw(pil_im)  
 
    # use DEFAULT truetype font  
    if(bold==True): 
        font = ImageFont.truetype(VIDEO_FONT_BOLD, VIDEO_FONT_SIZE)  
    else:
        font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SIZE)  

    # Get Text position - see lib.Video_Tools_cv_lib
    # it returns y,x,w,h
    return get_text_position_cv(background,text,position,line_number,font)
    
  
# Add text over background
# WARNING: bg is NOT a cv image but a full path (for PIL)
# Position = br, bl, tr, tl (ex: br = bottom right)
# and line_number that corresponds to the # of the line to write
# ex: if line_number = 1 => first line at this position
#                    = 2 => second line at this position
# return updated cv matrix
def add_text_to_pos(background,text,position,line_number=1,bold=False):

    # Convert background to RGB (OpenCV uses BGR)  
    cv2_background_rgb = cv2.cvtColor(background,cv2.COLOR_BGR2RGB)  
    
    # Pass the image to PIL  
    pil_im = Image.fromarray(cv2_background_rgb)  
    draw = ImageDraw.Draw(pil_im)  
 
    # use DEFAULT truetype font  
    if(bold==True): 
        font = ImageFont.truetype(VIDEO_FONT_BOLD, VIDEO_FONT_SIZE)  
    else:
        font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SIZE)  

    # Get Text position - see lib.Video_Tools_cv_lib
    y,x,w,h = get_text_position_cv(background,text,position,line_number,font)

    # Draw the text
    draw.text((x, y), text, font=font)  

    # Get back the image to OpenCV  
    cv2_im_processed = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)  

    # We now return the image AND the box position of the text 
    # so we can check if the meteors flies behind the text 
    return cv2_im_processed,y,x,w,h



# Add semi-transparent overlay over background on x,y
# return updated cv matrix
def add_overlay_x_y_cv(background, overlay, x, y):

    background_width,background_height  = background.shape[1], background.shape[0]
 
    if x >= background_width or y >= background_height:
        return background

    h, w = overlay.shape[0], overlay.shape[1]

    if x + w > background_width:
        w = background_width - x
        overlay = overlay[:, :w]

    if y + h > background_height:
        h = background_height - y
        overlay = overlay[:h]

    if overlay.shape[2] < 4:
        overlay = np.concatenate(
            [
                overlay,
                np.ones((overlay.shape[0], overlay.shape[1], 1), dtype = overlay.dtype) * 255
            ],
            axis = 2,
        )

    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0

    background[y:y+h, x:x+w] = (1.0 - mask) * background[y:y+h, x:x+w] + mask * overlay_image

    return background
 

# Add semi-transparent overlay over background
# Position = br, bl, tr, tl (ex: br = bottom right)
# return updated cv matrix
def add_overlay_cv(background, overlay, position):
    background_width,background_height  = background.shape[1], background.shape[0]
    # Get overlay position - see lib.Video_Tools_cv_lib
    x,y = get_overlay_position_cv(background,overlay,position) 
    return add_overlay_x_y_cv(background, overlay, x, y)


# Add radiant to a frame
def add_radiant_cv(radiant_image,background,x,y,text):
 
    # Add Image if possible (inside the main frame)
    try:
        background = add_overlay_x_y_cv(background,radiant_image,x-int(radiant_image.shape[1]/2),y-int(radiant_image.shape[0]/2))
    except: 
        background = background

    # Add text (centered bottom)
    background = add_text(background,text,x,y+int(radiant_image.shape[1]/2),True)

    return background




#TEMPORARTY remaster with moving logo & text
def new_remaster(data):
    
    video_file = data['video_file']
    json_conf  = data['json_conf']

    if "rad_x" in data:
       rad_x = data['rad_x']
       rad_y = data['rad_y']  
    else:
       rad_x = None

    #Get the meteor data & frames
    frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)

    if(len(frames) <= 0):
        print(video_file  + ' is messed up. We cannot remaster the video.')
        exit()

    json_file = video_file.replace(".mp4", ".json")
    meteor_data = load_json_file(json_file)

    #OUTPUT FILE
    marked_video_file = video_file.replace(".mp4", "-pub.mp4")
 
    # We get the different element of customization of the videos
    # from DEFAULT_VIDEO_PARAM
    params = get_video_job_default_parameters()
    params = params['param'] 

    # AMS Logo
    ams_logo = cv2.imread(AMS_WATERMARK, cv2.IMREAD_UNCHANGED) 
    try:
        ams_logo_pos = params['wat_pos'] #From the JSON (get_video_job_default_parameters)
    except:
        ams_logo_pos = D_AMS_LOGO_POS #Default
    
    # Eventual Extra Logo
    try:
        extra_logo     = params['extra_logo']
        extra_logo_pos = params['logo_pos']
        if cfe(extra_logo) == 0:
            extra_logo = False
        else:
            # We get the cv2 image here once for all
            extra_logo = cv2.imread(extra_logo, cv2.IMREAD_UNCHANGED)
    except:
        extra_logo = False
  
    # Extra text (customizable through /pycgi/webUI.py?cmd=video_tools)
    try:
        extra_text = params['extra_text']
        extra_text_pos = params['extra_text_pos']
    except:
        extra_text = False

    # Date & Time position
    try:
        date_time_pos = params['text_pos']
    except:
        date_time_pos = D_CAM_INFO_POS
 
    # Radiant
    try:
        rad_x = data['rad_x']
        rad_y = data['rad_y']
        rad_name = data['rad_name']
        radiant = True 
        # We load it here once for all
        radiant_image =  cv2.imread(RADIANT_IMG, cv2.IMREAD_UNCHANGED)  
    except:
        radiant = False  

    #Define buffer
    start_buff = int(meteor_data['start_buff'])
    start_sec = (start_buff / 25) * -1 

    #Get Date & time 
    (hd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)
    
    # Get Specifc info 
    el = video_file.split("_")
    station = el[-2]   
    cam = el[-3]   

    # Get Stations id & Cam Id to display
    station_id = station + "-" + sd_cam
    station_id = station_id.upper()
 
    # Video Dimensions = as the first frame
    ih, iw = frames[0].shape[:2]
 
    start_frame_time = hd_datetime + datetime.timedelta(0,start_sec)
    start_frame_str  = hd_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    # Crop box info 
    cx1, cy1, cx2, cy2 = make_crop_box(meteor_data, iw, ih)

    # Before working the frames, we need to make sure 
    # the meteor doesn't go behind on of the extra elements (AMS Logo, extra logo, text = date + extra_text)
    # if it doesn't we need to move stuff around 
    ams_logo_overlaps = False

    # We compare the meteor box with the AMS logo and its position within the first frame
    if(overlaps_with_image(cx1,cy1,cx2,cy2,ams_logo,ams_logo_pos,frames[0])): 
        # We move the logo here since it overlaps 
        ams_logo_overlaps = True
         
        # By default, we put it on the BOTTOM LEFT - 50px above the bottom (ONLY WORK WITH 720!!)
        if(ams_logo_pos == D_AMS_LOGO_POS):
            ams_logo_pos_x = VIDEO_MARGINS 
            ams_logo_pos_y = frames[0].shape[0] - ams_logo.shape[0] - VIDEO_MARGINS - 50
        
        #TODO... setup different x,y when the AMS Logo is somewhere on the page (different ams_logo_pos)
    
    
    extra_logo_overlaps = False

    # We compare the meteor box with the eventual extra logo and its position within the first frame
    if(extra_logo is not False and overlaps_with_image(cx1,cy1,cx2,cy2,extra_logo,extra_logo_pos,frames[0])): 
     
        # We move the extra logo here since it overlaps 
        extra_logo_overlaps = True

        # By default, we put it on the BOTTOM RIGHT - 50px above the bottom (ONLY WORK WITH 720!!) 
        if(extra_logo_pos == D_CUS_LOGO_POS):
            extra_logo_pos_x = frames[0].shape[1] - extra_logo.shape[1]  - VIDEO_MARGINS 
            extra_logo_pos_y = frames[0].shape[0] - extra_logo.shape[0] - VIDEO_MARGINS - 50

            #TODO... setup different x,y when the AMS Logo is somewhere on the page (different ams_logo_pos)
    

    extra_text_overlaps = False

    # We compare the meteor box with the "box" for the extra_text
    if(extra_text is not False):

        # We get the coordinates of the box of the extra_text:
        # Line 2 / Font Bold
        extra_text_y,extra_text_x,extra_text_w,extra_text_h =  get_text_box(frames[0],extra_text,extra_text_pos,2,True)

        # We test if it overlaps with the meteor 
        if(do_rect_overlap(cx1,cy1,cx2,cy2,extra_text_x,extra_text_y,extra_text_x+extra_text_w,extra_text_y+extra_text_h)):
            # Here is overlaps, so we need to move the extra text (ONLY IF IT'S ON THE DEFAULT PLACE = D_EXTRA_INFO_POS)
            if(extra_text_pos == D_CAM_INFO_POS):
                extra_text_overlaps = True

    
    # We compare the meteor box with the "box" for the Date & Time
    dt_text_overlaps = False

    # We get the coordinates of the box of the date & time with the longest dummy we could think of
    # + a code like "AMS7-010042-"
    # ex: AMS999-999999 - 9999-99-99 99:99:99.999 UT
    # (not bold so no "True" at the end of the get_text_box call)
    dt_y,dt_x,dt_w,dt_h =  get_text_box(frames[0],"AMS999-999999 - 9999-99-99 99:99:99.999 UT",date_time_pos,2)

    # We test if it overlaps with the meteor
    if(do_rect_overlap(cx1,cy1,cx2,cy2,dt_x,dt_y,dt_x+dt_w,dt_y+dt_h)):
            # Here is overlaps, so we need to move the extra text (ONLY IF IT'S ON THE DEFAULT PLACE = D_EXTRA_INFO_POS)
            if(date_time_pos == D_EXTRA_INFO_POS):
               dt_text_overlaps = True
 
    fc = 0
    new_frames = []

    for frame in frames:

        frame_sec = fc / FPS_HD
        frame_time = start_frame_time + datetime.timedelta(0,frame_sec)
        frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        fn = str(fc)
        hd_img = frame

        # Fading the box
        color = 150 - fc * 3
        if color > 50:
            cv2.rectangle(hd_img, (cx1, cy1), (cx2, cy2), (color,color,color), 1, cv2.LINE_AA)

        # Add AMS Logo 
        if(ams_logo_overlaps is False):
            # No meteor Behind
            hd_img = add_overlay_cv(hd_img,ams_logo,ams_logo_pos)
        else:
            # Meteor Behind 
            hd_img = add_overlay_x_y_cv(hd_img, ams_logo, ams_logo_pos_x, ams_logo_pos_y)
 
        # Add Eventual Extra Logo
        if(extra_logo is not False and extra_logo is not None):
            if(extra_logo_overlaps is False):
                # No meteor Behind
                hd_img = add_overlay_cv(hd_img,extra_logo,extra_logo_pos)
            else:
                # Meteor Behind 
                hd_img = add_overlay_x_y_cv(hd_img, extra_logo, extra_logo_pos_x, extra_logo_pos_y)


        # Add Date & Time
        frame_time_str = station_id + ' - ' + frame_time_str + ' UT' 

        # Add Date & Time & Cam Info
        if(dt_text_overlaps):

            # Here we automatically put them both on top of each other on the opposite (bottom) side
            hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,frame_time_str,D_CAM_INFO_POS,2)  

             # Add Extra_info 
            if(extra_text is not False):
                hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,extra_text,D_CAM_INFO_POS,1,True)      

        else:
                 
            hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,frame_time_str,date_time_pos,2)  

            # Add Extra_info 
            if(extra_text is not False):
                if(extra_text_overlaps is False):
                    hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,extra_text,extra_text_pos,2,True)  
                else:
                    # It overlaps
                    hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,extra_text,D_EXTRA_INFO_POS,1,True)      
    
        # Add Radiant
        if(radiant is not False):
            if hd_img.shape[0] == 720 :
                rad_x = int(rad_x * .66666)
                rad_y = int(rad_y * .66666)  
            hd_img = add_radiant_cv(radiant_image,hd_img,rad_x,rad_y,rad_name)  

        new_frames.append(hd_img) 
        fc = fc + 1

    make_movie_from_frames(new_frames, [0,len(new_frames) - 1], marked_video_file, 1) 
    print('OUTPUT ' + marked_video_file )


# Add logo, radiant(s), etc
def remaster(data):

    video_file = data['video_file']
    json_conf  = data['json_conf']

    if "rad_x" in data:
       rad_x = data['rad_x']
       rad_y = data['rad_y']  
    else:
       rad_x = None

    #Get the meteor data & frames
    frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)

    if(len(frames) <= 0):
        print(video_file  + ' is messed up. We cannot remaster the video.')
        exit()

    json_file = video_file.replace(".mp4", ".json")
    meteor_data = load_json_file(json_file)

    #OUTPUT FILE
    marked_video_file = video_file.replace(".mp4", "-pub.mp4")

    
    # We get the different element of customization of the videos
    # from DEFAULT_VIDEO_PARAM
    params = get_video_job_default_parameters()
    params = params['param']


    # AMS Logo
    ams_logo = cv2.imread(AMS_WATERMARK, cv2.IMREAD_UNCHANGED) 
    try:
        ams_logo_pos = params['wat_pos'] #From the JSON (get_video_job_default_parameters)
    except:
        ams_logo_pos = D_AMS_LOGO_POS #Default
    
    # Eventual Extra Logo
    try:
        extra_logo     = params['extra_logo']
        extra_logo_pos = params['logo_pos']
        if cfe(extra_logo) == 0:
            extra_logo = False
        else:
            # We get the cv2 image here once for all
            extra_logo = cv2.imread(extra_logo, cv2.IMREAD_UNCHANGED)
    except:
        extra_logo = False
  
    # Extra text (customizable through /pycgi/webUI.py?cmd=video_tools)
    try:
        extra_text = params['extra_text']
        extra_text_pos = params['extra_text_pos']
    except:
        extra_text = False

    # Date & Time position
    try:
        date_time_pos = params['text_pos']
    except:
        date_time_pos = D_CAM_INFO_POS
 
    # Radiant
    try:
        rad_x = data['rad_x']
        rad_y = data['rad_y']
        rad_name = data['rad_name']
        radiant = True 
        # We load it here once for all
        radiant_image =  cv2.imread(RADIANT_IMG, cv2.IMREAD_UNCHANGED)  
    except:
        radiant = False  

    #Define buffer
    start_buff = int(meteor_data['start_buff'])
    start_sec = (start_buff / 25) * -1 

    #Get Date & time 
    (hd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)
    
    # Get Specifc info 
    el = video_file.split("_")
    station = el[-2]   
    cam = el[-3]   

    # Get Stations id & Cam Id to display
    station_id = station + "-" + sd_cam
    station_id = station_id.upper()
 
    # Video Dimensions = as the first frame
    ih, iw = frames[0].shape[:2]
 
    start_frame_time = hd_datetime + datetime.timedelta(0,start_sec)
    start_frame_str  = hd_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    # Crop box info 
    cx1, cy1, cx2, cy2 = make_crop_box(meteor_data, iw, ih)

    
    fc = 0
    new_frames = []

    for frame in frames:

        frame_sec = fc / FPS_HD
        frame_time = start_frame_time + datetime.timedelta(0,frame_sec)
        frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        fn = str(fc)
        hd_img = frame

        # Fading the box
        color = 150 - fc * 3
        if color > 50:
            cv2.rectangle(hd_img, (cx1, cy1), (cx2, cy2), (color,color,color), 1, cv2.LINE_AA)

        # Add AMS Logo 
        hd_img = add_overlay_cv(hd_img, ams_logo, ams_logo_pos)
 
        # Add Eventual Extra Logo
        if(extra_logo is not False and extra_logo is not None):
            hd_img = add_overlay_cv(hd_img,extra_logo,extra_logo_pos)
           
        # Add Date & Time
        frame_time_str = station_id + ' - ' + frame_time_str + ' UT' 
        hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,frame_time_str,date_time_pos,2) #extra_text_pos => bl?

        # Add Extra_info 
        if(extra_text is not False):
            hd_img,xx,yy,ww,hh = add_text_to_pos(hd_img,extra_text,extra_text_pos,2,True)  #extra_text_pos => br?
 
        # Add Radiant
        if(radiant is not False):
            if hd_img.shape[0] == 720 :
                rad_x = int(rad_x * .66666)
                rad_y = int(rad_y * .66666)  
            hd_img = add_radiant_cv(radiant_image,hd_img,rad_x,rad_y,rad_name)  

        new_frames.append(hd_img) 
        fc = fc + 1

    make_movie_from_frames(new_frames, [0,len(new_frames) - 1], marked_video_file, 1) 
    print('OUTPUT ' + marked_video_file )
