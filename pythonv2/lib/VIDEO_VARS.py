ORG_PATH = '/mnt/ams2/'

IMG_SD_SRC_PATH = ORG_PATH + 'SD/proc2/'
IMG_HD_SRC_PATH=  ORG_PATH + 'HD/'
 
# HD & SD resolution
HD_W = 1920
HD_H = 1080
SD_W = 704
SD_H = 480
 

#To temporirly store the frame from the HD vids (all day timelapse)
TMP_IMG_HD_SRC_PATH = IMG_HD_SRC_PATH + 'tmp/'

#Store JSON for JOBS
WAITING_JOBS_FOLDER = ORG_PATH + '/CUSTOM_VIDEOS/'
WAITING_JOBS = WAITING_JOBS_FOLDER + 'waiting_jobs.json'

PROCESSING_JOBS = WAITING_JOBS_FOLDER + 'processing_jobs.json'

#DEFAULT PARAMETERS FOR ALL VIDEOS
DEFAULT_VIDEO_PARAM_PATH = WAITING_JOBS_FOLDER
DEFAULT_VIDEO_PARAM = WAITING_JOBS_FOLDER + 'default_parameters.json'

#Store Videos
VID_FOLDER = WAITING_JOBS_FOLDER 

#Temporary store all HD frames available
HD_FRAMES_PATH = ORG_PATH + 'TIMELAPSE_IMAGES/'

#Where the Stacks are
METEOR_FOLDER = ORG_PATH + '/meteors/'
STACK_FOLDER = METEOR_FOLDER 
 

#AMS WATERMARK
AMS_WATERMARK = "/home/ams/amscams/dist/img/ams_watermark.png"
AMS_WATERMARK_R = "/home/ams/amscams/dist/img/ams_watermark_r.png" #On the right

#AMS WATERMARK ANIMATED
AMS_WATERMARK_ANIM_FRAMES = 30
AMS_WATERMARK_ANIM_PATH_1920x1080 = "/home/ams/amscams/dist/img/ams_logo_vid_anim/1920x1080/"
AMS_WATERMARK_ANIM_PATH_1280x720 = "/home/ams/amscams/dist/img/ams_logo_vid_anim/1280x720/"
AMS_WATERMARK_ANIM_PATH_640x360 = "/home/ams/amscams/dist/img/ams_logo_vid_anim/640x360/"

#NUMBER OF DAYS WE KEEP THE CUSTOM VIDEOS
DELETE_VIDS_AFTER_DAYS = 7

#NUMBER OF HOURS WE KEEP THE HD FRAMES WE GET FROM get_all_HD_pic()
DELETE_HD_FRAMES_AFTER_HOURS = 36

#Size of the FONT for the text info
FONT_SIZE = "18"
FONT_TRANSPARENCY = "0.85" # between 0 and 1

#DEFAULT VALUES FOR CUSTOM VIDEOS
D_FPS = "30"
D_DIM = "1920:1080" #" DEFAULT DIM FOR VIDEOS " 
D_EXTRA_LOGO = " " # No Extra Logo 
D_AMS_LOGO_POS = "tl" # top left
D_CAM_INFO_POS = "bl" # bottom left
D_CUS_LOGO_POS = "tr" # top right
D_EXTRA_INFO = " " # WARNING - This is updated in Video_Parameters
D_EXTRA_INFO_POS = "br" # OPERATOR INFO

EMPTY_CORNER = "br" # Where to put stuff when the meteor overlaps
HD_DIM = "1280x720" #for ffmpeg - used to extract the HD frames in HD_FRAMES_PATH
BLENDING_SD = 30 #For the amount of SD blending on HD frames (when SD is found)

# PREVIEW FOR DETECTION IN ARCHIVE
PREVIEW_W = 300
PREVIEW_H = 169


#CURRENT FPS OF HD VIDEO
FPS_HD = 25

#Margins between the logo & text and the border of the frames
VIDEO_MARGINS = 10 

#DEFAULT FONTS
VIDEO_FONT = "/home/ams/amscams/dist/fonts/Roboto_Condensed/RobotoCondensed-Regular.ttf"
VIDEO_FONT_BOLD = "/home/ams/amscams/dist/fonts/Roboto_Condensed/RobotoCondensed-Bold.ttf"
VIDEO_FONT_SIZE = 25
VIDEO_FONT_SMALL_SIZE = 16 # For Radiant
VIDEO_LINE_HEIGHT = 0
VIDEO_FONT_SMALL_COLOR = (250,250,209,255) # For Radiant

#RADIANT IMAGE
RADIANT_IMG = "/home/ams/amscams/dist/img/radiant.png"

#NEW TEMPORARY REPO FOR FRAMES
TMP_FRAME_FOLDER = "/home/ams/tmpvids/"



# FRAME/THUMB FACTOR WHEN CREATING
# THE CROPPED VIDEO FOR THE OBS REPORT
# See Video_Tools.py
FT_FACTOR = 20

FRAME_THUMB_W = int(HD_W/FT_FACTOR)
FRAME_THUMB_H = int(HD_H/FT_FACTOR)