import cv2
import numpy as numpy
from lib.VIDEO_VARS import *   
from lib.Video_Tools_cv_lib import *
from PIL import ImageFont, ImageDraw, Image  



# Add text over background
# Position = br, bl, tr, tl (ex: br = bottom right)
# return updated cv matrix
def add_text(background,text,position):
    cv2.putText(background,  
           "Hershey Simplex : " + text,  
           (20, 40),  
           fontFace=cv2.FONT_HERSHEY_SIMPLEX,  
           fontScale=1,  
           color=(255, 255, 255))  
    return background
  

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
