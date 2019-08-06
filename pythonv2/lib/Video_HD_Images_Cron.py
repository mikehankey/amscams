import os
import subprocess 
from lib.VIDEO_VARS import *   
from os import listdir, remove, path
from os.path import isfile, join, exists

# This script is call once an hour and 
# extract one HD frame per HD video 
# and store them in HD_FRAMES_PATH

#Get Video time from file name 
def get_meteor_date(_file):
	fn = _file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "_" + fn[1] + "_" + fn[2]


#Create Directory if it doesn't exist
def create_HD_TMP_FOLDER_if_necessary():
    if not os.path.exists(HD_FRAMES_PATH):
        os.makedirs(HD_FRAMES_PATH)


#Return nothing or the HD stack that correspond to the same time/cam of the time passed as parameters
#ex:
# get_stack('/mnt/ams2/TIMELAPSE_IMAGES/2019_08_06_01_02_26_000_010039.png')
# return /mnt/ams2/meteors/2019_08_06/2019_08_06_01_02_26_000_010039-trim-885-HD-meteor-stacked.png
def get_stack(org_image):

    #Get date from file
    date = get_meteor_date(org_image)
    print("DATE " + date)

    #Get the cam id 
    cam_id = org_image.split("/")[-1]
    cam_id = cam_id.split(".")[0]
    cam_id = cam_id.split("_")[-1]
    print("CAM ID " + cam_id)


    print("WE SEARCH IN " + STACK_FOLDER+date)
 
    #find in STACK_FOLDER/date/ all the files that starts with date and have same cam id
    stacks = [f for f in listdir(STACK_FOLDER+date) if date in f and cam_id in f and "-tn" not in f and "-night" not in f and "trim" not in f]

    print('STACKS FOUND')
    print(stacks)


#Get All HD images available if they don't exist
def get_all_HD_pic():
    cur_path = IMG_HD_SRC_PATH
    res= True

    #test if we have at least one file name - YYYY_DD_MM_HH_ii_SS[_000_]CAM_ID.mp4
    test = [f for f in listdir(cur_path) if isfile(join(cur_path, f))] 

    if not test:
        #NOT HD FILES FOUND
        exit()
    else:
        frames = [f for f in listdir(cur_path) if f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
 
    # Create dest dir if necessary
    create_HD_TMP_FOLDER_if_necessary()

    for idx,vid in enumerate(sorted(frames)):
        try:
                vid_out = vid.replace('.mp4','.png')
                #WARNING WE HAVE THE -n option here = Do not overwrite output files!
                cmd = 'ffmpeg -n -hide_banner -loglevel panic -i '+IMG_HD_SRC_PATH+'/'+vid+' -vframes 1 -f image2 '+ HD_FRAMES_PATH + vid_out  
                output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
                res = False
                print('PB with video ' +  vid.replace('.png','.mp4'))
    