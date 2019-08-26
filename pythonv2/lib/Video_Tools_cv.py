import cv2
import datetime
import numpy as numpy
from lib.VIDEO_VARS import *   
from lib.Video_Tools_cv_pos import *
from lib.Video_Parameters import get_video_job_default_parameters
from lib.UtilLib import convert_filename_to_date_cam
from PIL import ImageFont, ImageDraw, Image  
from lib.FileIO import load_json_file

# From Mike
from lib.VideoLib import load_video_frames, make_crop_box, make_movie_from_frames

 
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


  
# Add text over background
# WARNING: bg is NOT a cv image but a full path (for PIL)
# Position = br, bl, tr, tl (ex: br = bottom right)
# and line_number that corresponds to the # of the line to write
# ex: if line_number = 1 => first line at this position
#                    = 2 => second line at this position
# return updated cv matrix
def add_text_to_pos(background,text,position,line_number=1):
    # Convert background to RGB (OpenCV uses BGR)  
    cv2_background_rgb = cv2.cvtColor(background,cv2.COLOR_BGR2RGB)  
    
    # Pass the image to PIL  
    pil_im = Image.fromarray(cv2_background_rgb)  
    draw = ImageDraw.Draw(pil_im)  
 
    # use DEFAULT truetype font  
    if(line_number==1):
        # We go bold on the first line
        font = ImageFont.truetype(VIDEO_FONT_BOLD, VIDEO_FONT_SIZE)  
    else:
        font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SIZE)  

    # Get Text position - see lib.Video_Tools_cv_lib
    y,x = get_text_position_cv(background,text,position,line_number,font)

    # Draw the text
    draw.text((x, y), text, font=font)  

    # Get back the image to OpenCV  
    cv2_im_processed = cv2.cvtColor(np.array(pil_im), cv2.COLOR_RGB2BGR)  
    
    return cv2_im_processed



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
def add_radiant_cv(background,x,y,text):

    # Add Image if possible (inside the main frame)
    try:
        radiant_image = cv2.imread(RADIANT_IMG, cv2.IMREAD_UNCHANGED) 
        background = add_overlay_x_y_cv(background,radiant_image,x-int(radiant_image.shape[1]/2),y-int(radiant_image.shape[0]/2))
    except:
        background = background

    # Add text (centered bottom)
    background = add_text(background,text,x,y+int(radiant_image.shape[1]/2),True)

    return background


# Add logo, radiant(s), etc
def remaster(data):

    video_file = data['video_file']
    json_conf  = data['json_conf']

    #Get the meteor data & frames
    frames = load_video_frames(video_file, json_conf, 0, 0, [], 1)
    json_file = video_file.replace(".mp4", ".json")
    meteor_data = load_json_file(json_file)

    
    #OUTPUT FILE
    marked_video_file = video_file.replace(".mp4", "-pub.mp4")

    # Add AMS Logo
    ams_logo = cv2.imread(AMS_WATERMARK, cv2.IMREAD_UNCHANGED)

    # Custom Logo
    # We take the default logo in DEFAULT_VIDEO_PARAM
    params = get_video_job_default_parameters()
    params = params['param']
    
    try:
        extra_logo = params['extra_logo']
        extra_logo_pos = params['logo_pos']
    except:
        extra_logo = False
 
    # AMS Logo default position
    try:
        ams_logo_pos = params['wat_pos']
    except:
        ams_logo_pos = D_AMS_LOGO_POS #Default
    
    # Extra text
    try:
        extra_text = params['extra_text']
        extra_text_pos = params['text_pos']
    except:
        extra_text = False

    #Define buffer
    start_buff = int(meteor_data['start_buff'])
    start_sec = (start_buff / 25) * -1 

    #Get Date & time 
    (hd_datetime, sd_cam, sd_date, sd_y, sd_m, sd_d, sd_h, sd_M, sd_s) = convert_filename_to_date_cam(video_file)
   
    # Get Stations id & Cam Id to display
    station_id = json_conf['site']['ams_id'] + "-" + sd_cam
    station_id = station_id.upper()


    # Get Specifc info 
    el = video_file.split("_")
    station = el[-2]   
    cam = el[-3]   
 
    # Video Dimensions = as the first frame
    ih, iw = frames[0].shape[:2]
 
    start_frame_time = hd_datetime + datetime.timedelta(0,start_sec)
    start_frame_str = hd_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    # Crop box info 
    cx1, cy1, cx2, cy2 = make_crop_box(meteor_data, iw, ih)
   


    fc = 0
    new_frames = []
    for frame in frames:

        frame_sec = fc / FPS_HD
        frame_time = start_frame_time + datetime.timedelta(0,frame_sec)
        frame_time_str = frame_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        hd_img = frame

        # Fading the box
        color = 150 - fc * 3
        if color > 50:
            cv2.rectangle(hd_img, (cx1, cy1), (cx2, cy2), (color,color,color), 1)

        # Add AMS Logo
        print('AMS LOGO POS ' + ams_log_pos)
        hd_img = add_overlay_cv(hd_img,cv2.imread(AMS_WATERMARK, cv2.IMREAD_UNCHANGED),ams_logo_pos)

        # Add Date & Time
        frame_time_str = station_id + ' - ' + frame_time_str + ' UT'
        hd_img = add_text_to_pos(hd_img,frame_time_str,extra_text_pos,2)

        # Add Extra_info
        if(extra_text is not False):
            hd_img = add_text_to_pos(hd_img,extra_text,extra_text_pos,1) 

        # Add Radiant (todo)
        new_frames.append(hd_img) 
        fc = fc + 1

    make_movie_from_frames(new_frames, [0,len(new_frames) - 1], marked_video_file, 1)
    print(marked_video_file)