import os
import subprocess 
import time
from lib.VIDEO_VARS import *   
from os import listdir, remove, path
from os.path import isfile, join, exists

# This script is call once an hour and 
# extract one HD frame per HD video 
# and store them in HD_FRAMES_PATH
 

#Create Directory if it doesn't exist
def create_HD_TMP_FOLDER_if_necessary():
    if not os.path.exists(HD_FRAMES_PATH):
        os.makedirs(HD_FRAMES_PATH)


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
               # WARNING: we're using JPGs now
               vid_out = vid.replace('.mp4','.jpg')

               if(os.path.isfile(HD_FRAMES_PATH + vid_out) is not True):
                    #WARNING WE HAVE THE -n option here = Do not overwrite output files = double check with is file
                    cmd = 'ffmpeg -n -hide_banner -loglevel panic -i '+IMG_HD_SRC_PATH+'/'+vid+' -qscale:v 4 -vframes 1 -f image2 -vf scale='+HD_DIM + ' ' + HD_FRAMES_PATH + vid_out  
                    output = subprocess.check_output(cmd, shell=True).decode("utf-8") 
        except:
                res = False
                print('PB with video (it may simply already exist)' +  vid.replace('.png','.mp4'))

# Delete files or directories
def remove(path):
    if os.path.isdir(path):
        try:
            os.rmdir(path)
        except OSError:
            print("Unable to remove folder: %s" % path)
    else:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            print("Unable to remove file: %s" % path)


#Delete all the images that are older than DELETE_HD_FRAMES_AFTER_HOURS hours
def cleanup_HD_frames_hours(number_of_hours,path):
    time_in_secs = time.time() - (number_of_hours * 60 * 60)
    for root, dirs, files in os.walk(path, topdown=False):
        for file_ in files:
           
            full_path = os.path.join(root, file_)
            stat = os.stat(full_path)
            filename, file_extension = os.path.splitext(full_path)

            if stat.st_mtime <= time_in_secs and file_extension!='.json':
                remove(full_path)
                print(full_path + " deleted because it was more than " + str(number_of_hours) + " hours old")


get_all_HD_pic()
cleanup_HD_frames_hours(DELETE_HD_FRAMES_AFTER_HOURS, HD_FRAMES_PATH)