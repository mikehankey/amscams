#Create TMP file with all video of the night for a given camera 
from os import listdir,makedirs
from os.path import isfile, join, exists
from lib.VIDEO_VARS import * 

#No date here as we only have the latest night
#ex:camID:010034  
def get_all_HD_vids(camID):
    cur_path = HD_VID_SRC_PATH + "/tmp"
    onlyfiles = [f for f in listdir(HD_VID_SRC_PATH) if camID in f and "-tn" not in f and "-trim" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
    #FOR DEBUG
    #onlyfiles = onlyfiles[1:50]
    return(sorted(onlyfiles), cur_path)

#Input list of HD (VIDEOS!) files, path of the current image, date, camID
#Position of watermark & text = tr=>Top Right, bl=>Bottom Left
#Output Video with watermark & text
def get_all_HD_frames(video_files, path, camID, fps="15", dimensions="1920:1080", text_pos='bl', watermark_pos='tr', enhancement=0 ) : 

    #We extract one frame per HD file at .5s and get proper dimension at well as logo & text
    for idx,f in enumerate(video_files): 
        
    
    
    ffmpeg -ss 0.5 -i inputfile.mp4 -t 1 -s 480x300 -f image2 imagefile.jpg
    

