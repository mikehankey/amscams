AMS_HOME = "/home/ams/amscams"
CONF_DIR = AMS_HOME + "/conf"
STATION_ID = "AMS1"
ARC_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/"
METEOR_ARC_DIR = "/mnt/ams2/meteor_archive/" + STATION_ID + "/METEOR/"
CLOUD_DIR = "/mnt/archive.allsky.tv/" + STATION_ID + "/"
CLOUD_METEOR_DIR = CLOUD_DIR + "METEOR/"
CLOUD_CAL_DIR = CLOUD_DIR + "CAL/"

DATA_BASE_DIR = "/mnt/ams2"
PROC_BASE_DIR = "/mnt/ams2/SD/proc2"
PREVIEW_W = 300
PREVIEW_H = 169
SD_W = 704
SD_H = 576
HD_W = 1920
HD_H = 1080
HDM_X = 1920 / SD_W 
HDM_Y = 1080 / SD_H
# HD scale pix is .072 degrees per px
PX_SCALE = .072  # for HD

THUMB_W = 320
THUMB_H = 180
MEDIUM_W = 640
MEDIUM_H = 360
HIGH_W = 1280
HIGH_H = 720

#DEFAULT FONTS
VIDEO_FONT = "/home/ams/amscams/dist/fonts/Roboto_Condensed/RobotoCondensed-Regular.ttf"
VIDEO_FONT_BOLD = "/home/ams/amscams/dist/fonts/Roboto_Condensed/RobotoCondensed-Bold.ttf"
VIDEO_FONT_SIZE = 25
VIDEO_FONT_SMALL_SIZE = 16 # For Radiant
VIDEO_LINE_HEIGHT = 0
VIDEO_FONT_SMALL_COLOR = (250,250,209,255) # For Radiant


