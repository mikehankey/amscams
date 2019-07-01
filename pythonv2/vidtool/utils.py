from os import listdir
from os.path import isfile, join



SD_PATH='/mnt/ams2/SD/proc2/'

#Input: camID, date
#Ouput: list of sd frames found for this date
def get_sd_frames(camID,date):
    #ex:camID:010035, date:2019_05_26
    cur_path = SD_PATH + date + "/" + images
    onlyfiles = [f for f in listdir(cur_path) if camID in f and isfile(join(cur_path, f))]
    print onlyfiles


get_sd_frames("010035","2019_05_26")