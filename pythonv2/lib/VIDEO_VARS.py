ORG_PATH = '/mnt/ams2/'


IMG_SD_SRC_PATH = ORG_PATH + 'SD/proc2/'
IMG_HD_SRC_PATH=  ORG_PATH + 'HD/'

#To temporirly store the frame from the HD vids (all day timelapse)
TMP_IMG_HD_SRC_PATH = IMG_HD_SRC_PATH + 'tmp/'

#Store JSON
WAITING_JOBS_FOLDER = ORG_PATH + '/CUSTOM_VIDEOS/'
WAITING_JOBS = WAITING_JOBS_FOLDER + 'waiting_jobs.json'

#Store Vidos
VID_FOLDER = WAITING_JOBS_FOLDER 

#AMS WATERMARK
AMS_WATERMARK = "/home/ams/amscams/dist/img/ams_watermark.png"

#Size of the FONT for the text info
FONT_SIZE = "20"
FONT_TRANSPARENCY = "0.6" # between 0 and 1
