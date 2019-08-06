import os
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


    print("FRAMES FOUND")
    print(frames)
    print("IN " + cur_path)

    # Create dest dir if necessary
    create_HD_TMP_FOLDER_if_necessary()

    for idx,vid in enumerate(sorted(frames)):
            try:
                vid_out = vid.replace('.mp4','')
                cmd = 'ffmpeg -y -hide_banner -loglevel panic -i '+IMG_HD_SRC_PATH+'/'+vid+' -vframes 1 -f image2 '+ HD_FRAMES_PATH + vid_out + '.png' 
                output = subprocess.check_output(cmd, shell=True).decode("utf-8")
                print(HD_FRAMES_PATH + vid_out + '.png' )
                toReturn.append( vid_out + '.png' ) 
            except:
                print('PB')
                res = False
    
    print("DONE")