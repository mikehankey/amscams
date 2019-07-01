import os
import subprocess
from os import listdir,makedirs
from os.path import isfile, join, exists



SD_PATH='/mnt/ams2/SD/proc2/'

#Input: camID, date
#Ouput: list of sd frames found for this date
def get_sd_frames(camID,date):
    #ex:camID:010034, date:2019_06_23
    cur_path = SD_PATH + date + "/images/"
    onlyfiles = [cur_path+f for f in listdir(cur_path) if camID in f and "-tn" not in f and isfile(join(cur_path, f))]
    return(sorted(onlyfiles), cur_path)
 
#Input list of SD files, path of the current image
#Output Video of resized frames
def create_sd_vid(frames, path): 

    #Create temporary folder to store the frames for the video
    newpath = r''+path+'/tmp/'
    if not os.path.exists(newpath):
        os.makedirs(newpath)

    for f in frames: 
        #Resize 
        #ffmpeg -i input.jpg -vf scale=320:240 output_320x240.png
        cmd = 'ffmpeg -i ' + f + " -vf scale=1920:1080 newpath/" + f
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        print(output)


files, path = get_sd_frames("010034","2019_06_23")
create_sd_vid(files,path)