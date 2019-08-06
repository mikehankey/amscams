ORG_PATH = '/mnt/ams2/'

IMG_SD_SRC_PATH = ORG_PATH + 'SD/proc2/'
IMG_HD_SRC_PATH=  ORG_PATH + 'HD/'

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
STACK_FOLDER = ORG_PATH + '/meteors/'

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

#Size of the FONT for the text info
FONT_SIZE = "18"
FONT_TRANSPARENCY = "0.85" # between 0 and 1


#DEFAULT VALUES
D_FPS = "30"
D_DIM = "1920:1080"
D_EXTRA_LOGO = " " # No Extra Logo 
D_AMS_LOGO_POS = "tl" # top left
D_CAM_INFO_POS = "bl" # bottom left
D_CUS_LOGO_POS = "tr" # top right
D_EXTRA_INFO = " " # WARNING - This is updated in Video_Parameters