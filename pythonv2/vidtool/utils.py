import glob, os, os.path, sys
import subprocess 
from os import listdir,makedirs
from os.path import isfile, join, exists
 
SD_PATH='/mnt/ams2/SD/proc2/'

#Return Date & Time based on file name
def get_meteor_date_ffmpeg(file):
	fn = file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "/" + fn[1] + "/" + fn[2] + " " + fn[3] + "\:" + fn[4] + "\:" + fn[5]

#Input: camID, date
#Ouput: list of sd frames found for this date
def get_sd_frames(camID,date):
    #ex:camID:010034, date:2019_06_23
    cur_path = SD_PATH + date + "/images/"
    onlyfiles = [f for f in listdir(cur_path) if camID in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
    #FOR DEBUG
    #onlyfiles = onlyfiles[1:50]
    return(sorted(onlyfiles), cur_path, date, camID)
 

#Input list of SD files, path of the current image, date, camID
#Position of watermark & text = tr=>Top Right, bl=>Bottom Left
#Output Video with watermark & text
def create_sd_vid(frames, path, date, camID, fps="25", watermark_pos='tr', text_pos='bl'): 

    #Create temporary folder to store the frames for the video
    newpath = r''+path+'tmp'
    if not os.path.exists(newpath):
        os.makedirs(newpath)

    watermark = "./dist/img/ams_watermark.png"

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
        text_position = "x=main_w-text_w-20:y=20"
    elif (text_pos=='tl'):
        text_position = "x=20:y=20"    
    elif (text_pos=='bl'):
        text_position = "x=20:y=main_h-text_h-20"
    elif (text_pos=='br'): 
        text_position = "x=main_w-text_w-20:y=main_h-text_h-20"
 
    
    for idx,f in enumerate(frames): 
        #Resize the frames, add date & watermark in /tmp  
        text = 'AMS Cam #'+camID+ ' ' + get_meteor_date_ffmpeg(f) 
        cmd = 'ffmpeg -hide_banner -loglevel panic \
                -i ' + path+'/'+ f + '    \
                -i ' + watermark + ' \
                -filter_complex "[0:v]scale=1920:1080[scaled]; \
                [scaled]drawtext=:text=\'' + text + '\':fontcolor=white@1.0:fontsize=30:'+text_position+'[texted]; \
                [texted]overlay='+watermark_position+'[out]" \
                -map "[out]"  ' + newpath + '/' + str(idx) + '.png'      
         
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    
    
    #Create Video based on all newly create frames
    def_file_path =  newpath +'/'+date +'_'+ camID +'.mp4' 
    cmd = 'ffmpeg -hide_banner -loglevel panic -r '+ str(fps) +' -f image2 -s 1920x1080 -i ' + newpath+ '/%d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p ' + def_file_path
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   

    #DELETING RESIZE FRAMES
    filelist = glob.glob(os.path.join(newpath, "*.png"))
    for f in filelist:
        os.remove(f) 

    print('VIDEO READY AT '+newpath+'/'+date + '_' + camID + '.mp4' )

files, path, date, camID = get_sd_frames("010034","2019_07_01")
create_sd_vid(files,path, date, camID)