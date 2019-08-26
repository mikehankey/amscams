import cv2
import numpy as numpy
from lib.VIDEO_VARS import *   
from lib.Video_Tools_cv_pos import *
from PIL import ImageFont, ImageDraw, Image  


# Add text on x,y with default small font
def add_text(background,text,x,y):
    # Convert background to RGB (OpenCV uses BGR)  
    cv2_background_rgb = cv2.cvtColor(background,cv2.COLOR_BGR2RGB)  
    # Pass the image to PIL  
    pil_im = Image.fromarray(cv2_background_rgb)  
    draw = ImageDraw.Draw(pil_im)  
    font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SMALL_SIZE, fill=VIDEO_FONT_SMALL_COLOR)  
    draw.text((x, y), text, font=font)  
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
  

# Add semi-transparent overlay over background
# Position = br, bl, tr, tl (ex: br = bottom right)
# return updated cv matrix
def add_overlay_cv(background, overlay, position):

    background_width,background_height  = background.shape[1], background.shape[0]

    # Get overlay position - see lib.Video_Tools_cv_lib
    x,y = get_overlay_position_cv(background,overlay,position) 
    
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


# Add radiant to a frame
def add_radiant_cv(background,x,y,text):
    cv2.circle(background,(x,y), 25 , (128,128,128), 1)
    background = add_text(background,text,)
    cv2.putText(image, "Perseid Radiant",  (new_cat_x, new_cat_y), cv2.FONT_HERSHEY_SIMPLEX, .5, (145, 145, 145), 1)

