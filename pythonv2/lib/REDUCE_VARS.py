
# CURRENT CONFIG
JSON_CONFIG = "/home/ams/amscams/conf/as6.json"

# PATH WHERE ALL THE FILES GO 
MAIN_FILE_PATH = "/mnt/ams2/"
CACHE_PATH = MAIN_FILE_PATH + "CACHE/"

METEOR_ARCHIVE = MAIN_FILE_PATH + "meteor_archive/"
METEOR = "METEOR/" # Sub folder in the archive

# Cache subfolders
FRAMES_SUBPATH= "/FRAMES/"          # For the HD Frames
CROPPED_FRAMES_SUBPATH = "/THUMBS/" # For the Cropped Frames (thumbs)
STACKS_SUBPATH   = "/STACKS/"       # For the Stacks
TMP_CROPPED_FRAMES_SUBPATH = "/CR_THUMBS" # For the temporary cropped fames (manual reduction)

# Folder where the calibration are
CALIB_PATH = MAIN_FILE_PATH + "cal/freecal/"

# STACK DIMENSIONS ("half-stack")
STACK_W = 960
STACK_H = 540

# PATTERN FOR THE JSON FILE NAMES
# YYYY_MM_DD_HH_MM_SS_MSS_CAM_STATION[_HD].EXT
FILE_NAMES_REGEX = r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{3})_(\w{6})_([^_^.]+)(_HD|_SD)?(\.)?(\.[0-9a-z]+$)"
FILE_NAMES_REGEX_GROUP = ["name","year","month","day","hour","min","sec","ms","cam_id","station_id","HD","ext"]

# PATTERN FOR "OLD" VIDEO OR JSON FILE NAMES
# (with "-trimdddd")
OLD_FILE_NAME_REGEX =  r"(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{3})_(\w{6})(-trim\d{4})?(\.[0-9a-z]+$)"


# EXTENSION FOR THE FRAMES
EXT_HD_FRAMES = "_HDfr"
EXT_CROPPED_FRAMES = "_frm"

# THUMBS (CROPPED FRAMES)
THUMB_W = 100
THUMB_H = 100
 
# SIZE OF THE SELECT BOX WHEN THE USER SELECTS THE METEOR FROM A HD FRAME
THUMB_SELECT_W = THUMB_W
THUMB_SELECT_H = THUMB_H

# Default Values for Az and El
Az_DEFAULT = 9999
El_DEFAULT = Az_DEFAULT
Ra_DEFAULT= Az_DEFAULT
Dec_DEFAULT= Az_DEFAULT
Intensity_DEFAULT= Az_DEFAULT
Maxpx_DEFAULT= Az_DEFAULT 
W_DEFAULT = 50
H_DEFAULT = 50