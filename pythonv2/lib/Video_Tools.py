import os
import subprocess 
from lib.VIDEO_VARS import * 
from os import listdir, remove
from os.path import isfile, join, exists


#Return Date & Time based on file name (that ends with a date)
def get_meteor_date_ffmpeg(file):
	fn = file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "/" + fn[1] + "/" + fn[2] + " " + fn[3] + "\:" + fn[4] + "\:" + fn[5]



#Input: camID, date
#Ouput: list of sd frames found for this date/cam
#ex:camID:010034, date:2019_06_23
def get_sd_frames(camID,date):
    cur_path = IMG_SD_SRC_PATH + date + "/images"
    #print(cur_path)
    onlyfiles = [f for f in listdir(cur_path) if camID in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
    if not onlyfiles:
        print('NO INPUT FOR VID CamID:' + camID + ' - DATE ' + date)
    return(sorted(onlyfiles), cur_path, date, camID)



#Input! camID, date
#Ouput: list of HD frames found for this date or get_sd_frames if no HD frame has been found
#ex: get_hd_frames('010040','2019_07_08')
def get_hd_frames(camID,date):
    cur_path = IMG_HD_SRC_PATH
    #test if we have at least one file name - YYYY_DD_MM_HH_ii_SS[_000_]CAM_ID.mp4
    test = [f for f in listdir(cur_path) if f.startswith(date) and f.endswith(camID+'.mp4') and isfile(join(cur_path, f))]
    if not test:
        #If nothing is found we try the SD
        return get_sd_frames(camID,date)
    else:
        onlyfiles = [f for f in listdir(cur_path) if camID in f and date in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
        #Check temporary folder to store the frames of all the videos
        tmppath = r''+TMP_IMG_HD_SRC_PATH
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)
        else:
            #Clean the directory
            files = glob.glob(tmppath+'/*')
            for f in files:
                os.remove(f)
        #We extract one frame per video
        for idx,vid in enumerate(sorted(onlyfiles)):
            print(str(idx) + " ====> " + vid)
            cmd = 'ffmpeg -y -i '+IMG_HD_SRC_PATH+'/'+vid+' -vframes 1 -f image2 '+ tmppath + str(idx) + '.png' 
            output = subprocess.check_output(cmd, shell=True).decode("utf-8")
            print(tmppath + '/'  + str(idx) + '.png' )
            print(output)
        #return(sorted(onlyfiles), cur_path, date, camID)  
 


