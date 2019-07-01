from os import listdir
from os.path import isfile, join



SD_PATH='/mnt/ams2/SD/proc2/'

#Input: camID, date
#Ouput: list of sd frames found for this date
def get_sd_frames(camID,date):
    #ex:camID:010035, date:2019_05_26
    cur_path = SD_PATH + date + "/images/"
    onlyfiles = [f for f in listdir(cur_path) if camID in f and "-tn" not in f and isfile(join(cur_path, f))]
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
        print(f)


files, path = get_sd_frames("010035","2019_05_26")
create_sd_vid(files,path)