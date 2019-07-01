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
    onlyfiles = [f for f in listdir(cur_path) if camID in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
    return(sorted(onlyfiles), cur_path, date, camID)
 
#Input list of SD files, path of the current image
#Output Video of resized frames
def create_sd_vid(frames, path, date, camID): 

    #Create temporary folder to store the frames for the video
    newpath = r''+path+'/tmp/'
    if not os.path.exists(newpath):
        os.makedirs(newpath)

    for idx,f in enumerate(frames): 
        #Resize the frames in /tmp
        cmd = 'ffmpeg -hide_banner -loglevel panic -i ' + path+'/'+ f + ' -vf scale=1920:1080 ' + newpath + '/' + str(idx) + '.png'
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        #print(output)

    #Create Video based on all newly create frames
    cmd = 'ffmpeg -hide_banner -loglevel panic -r 25 -f image2 -s 1920x1080 -i ' + newpath+ '/%d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p '+newpath+'/'+date +'_'+ camID+'.mp4'
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    #print(output)
    print('VIDEO READ AT '+newpath+'/'+date + '_' + camID + '.mp4' )

files, path, date, camID = get_sd_frames("010034","2019_06_23")
create_sd_vid(files,path, date)