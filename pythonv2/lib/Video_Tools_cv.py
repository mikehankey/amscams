import cv2
import numpy as np
import lib.VIDEO_VARS

 
# Get overlay position x,y 
# based on Position = br, bl, tr, tl (ex: br = bottom right)
# and margins (distance of the overlay from the borders of the frame)
# return x,y position of the overlay over the background
def get_overlay_position_cv(background, overlay, position, margins=VIDEO_MARGINS):
    h, w = overlay.shape[0], overlay.shape[1]
    if(position=='bl'):
        background_width,background_height  = background.shape[1], background.shape[0]
        return x,y = VIDEO_MARGINS,  background_height-VIDEO_MARGINS-h
    elif(position=='tl'):
        background_width,background_height  = background.shape[1], background.shape[0]
        return x,y = background_width-VIDEO_MARGINS-w, VIDEO_MARGINS 
    elif(position=='br'):
        background_width,background_height  = background.shape[1], background.shape[0]
        return x,y = background_width-VIDEO_MARGINS-w, background_height-VIDEO_MARGINS-h        
    else:
        return x,y = VIDEO_MARGINS, VIDEO_MARGINS
  

# Add semi-transparent overlay over background
# Position = br, bl, tr, tl (ex: br = bottom right)
# return updated cv matrix
def add_overlay_cv(background, overlay, position):

    background_width,background_height  = background.shape[1], background.shape[0]

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
