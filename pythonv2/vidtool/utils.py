import glob, os, os.path
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
    #FOR DEBUG
    onlyfiles = onlyfiles[1:10]
    return(sorted(onlyfiles), cur_path, date, camID)
 

#Input list of SD files, path of the current image, date, camID
#Position of watermark & text = tr=>Top Right, bl=>Bottom Left
#Output Video with watermark & text
def create_sd_vid(frames, path, date, camID, fps="25", watermark_pos='tr', text_pos='bl'): 

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
    def_file_path =  newpath +'/'+date +'_'+ camID+'.mp4'
    tmp_file_path =  newpath +'/'+date + camID + '.mp4'
    cmd = 'ffmpeg -hide_banner -loglevel panic -r '+ str(fps) +' -f image2 -s 1920x1080 -i ' + newpath+ '/%d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p ' + tmp_file_path
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    
    watermark = "./dist/img/ams_watermark.png"
    text = "AMS Cams #"+camID+ " " +  str(date.replace("_", "/"))  

    # Watermark position based on options
    if(watermark_pos=='tr'):
        watermark_position = "main_w-overlay_w-20:20"
    elif (watermark_pos=='tl'):
        watermark_position = "20:20"    
    elif (watermark_pos=='bl'):
        watermark_position = "20:main_h-overlay_h-20"
    elif (watermark_pos=='br'): 
        watermark_position = "main_w-overlay_w-20:main_h-overlay_h-20"

    # Text position based on options
    if(text_pos=='tr'):
        text_position = "main_w-text_w-20:20"
    elif (text_pos=='tl'):
        text_position = "20:20"    
    elif (text_pos=='bl'):
        text_position = "20:main_h-text_h-20"
    elif (text_pos=='br'): 
        text_position = "main_w-text_w-20:main_h-text_h-20"
    
    #ffmpeg -i /mnt/ams2/SD/proc2/2019_06_23/images/tmp/2019_06_23010034.mp4 -i ./dist/img/ams_watermark.png -filter_complex "[0:v]drawtext=:text='TESTING TESTING':fontcolor=white@1.0:fontsize=36:x=00:y=40[text];[text][1:v]overlay[filtered]" -map "[filtered]"   -codec:v libx264 -codec:a copy /mnt/ams2/SD/proc2/2019_06_23/images/tmp/output.mp4
    cmd = 'ffmpeg \
         -i ' + tmp_file_path  +' \
         -i ' + watermark + ' -filter_complex \
        "[0:v]drawtext=:text=\'' + text + '\':fontcolor=white@1.0:fontsize=30:'+text_position+'[text]; [text][1:v]overlay='+watermark_position+'[filtered]" -map "[filtered]" \
        -codec:v libx264 -codec:a copy ' + def_file_path
    print ('TEST COMMAND')
    print (cmd)
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")


    #DELETING RESIZE FRAMES
    filelist = glob.glob(os.path.join(newpath, "*.png"))
    for f in filelist:
        os.remove(f) 

    #DELETING TMP VIDEO 
    os.unlink(tmp_file_path)

    #print(output)
    print('VIDEO READY AT '+newpath+'/'+date + '_' + camID + '.mp4' )

files, path, date, camID = get_sd_frames("010034","2019_06_23")
create_sd_vid(files,path, date, camID)