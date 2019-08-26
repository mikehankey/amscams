import cv2
import numpy as numpy
from lib.VIDEO_VARS import *   
from lib.Video_Tools_cv_lib import *
from PIL import ImageFont, ImageDraw, Image  



# Add text over background
# WARNING: bg is NOT a cv image but a full path (for PIL)
# Position = br, bl, tr, tl (ex: br = bottom right)
# return updated cv matrix
def add_text(background,text,position):
    # Convert background to RGB (OpenCV uses BGR)  
    cv2_background_rgb = cv2.cvtColor(background,cv2.COLOR_BGR2RGB)  
    
    # Pass the image to PIL  
    pil_im = Image.fromarray(cv2_background_rgb)  
    draw = ImageDraw.Draw(pil_im)  

    # use DEFAULT truetype font  
    font = ImageFont.truetype(VIDEO_FONT, VIDEO_FONT_SIZE)  

    # Draw the text
    draw.text((10, 10), text, font=font)  

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
