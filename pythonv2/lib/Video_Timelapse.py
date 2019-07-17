import glob, os, os.path, sys
import subprocess 
import cgitb
import json
from pathlib import Path
from os import listdir,makedirs
from os.path import isfile, join, exists
from lib.VIDEO_VARS import * 
 
 

#Input list of SD files, path of the current image, date, camID
#Position of watermark & text = tr=>Top Right, bl=>Bottom Left
#Output Video with watermark & text
def create_sd_vid(frames, path, date, camID, fps="15", dimensions="1920:1080", text_pos='bl', watermark_pos='tr', enhancement=0 ) : 

    #Create temporary folder to store the frames for the video
    newpath = r''+path+'/tmp/'
    if not os.path.exists(newpath):
        os.makedirs(newpath)

    #Create destination folder if it doesn't exist yet
    if not os.path.exists(VID_FOLDER):
        os.makedirs(VID_FOLDER)

    watermark = "/home/ams/amscams/dist/img/ams_watermark.png"
    
    # Watermark position based on options
    if(watermark_pos=='tr'):
        watermark_position = "main_w-overlay_w-20:20"
    elif (watermark_pos=='tl'):
        watermark_position = "20:20"    
    elif (watermark_pos=='bl'):
        watermark_position = "20:main_h-overlay_h-20"
    else: 
        watermark_position = "main_w-overlay_w-20:main_h-overlay_h-20"

    # Text position based on options
    if(text_pos=='tr'):
        text_position = "x=main_w-text_w-20:y=20"
    elif (text_pos=='tl'):
        text_position = "x=20:y=20"    
    elif (text_pos=='bl'):
        text_position = "x=20:y=main_h-text_h-20"
    else: 
        text_position = "x=main_w-text_w-20:y=main_h-text_h-20"
 
    for idx,f in enumerate(frames): 
        #Resize the frames, add date & watermark in /tmp  
        text = 'AMS Cam #'+camID+ ' ' + get_meteor_date_ffmpeg(f) 
        if(enhancement!=1):
            cmd = 'ffmpeg -hide_banner -loglevel panic \
                    -y \
                    -i ' + path+'/'+ f + '    \
                    -i ' + watermark + ' \
                    -filter_complex "[0:v]scale='+dimensions+'[scaled]; \
                    [scaled]drawtext=:text=\'' + text + '\':fontcolor=white@1.0:fontsize=18:'+text_position+'[texted]; \
                    [texted]overlay='+watermark_position+'[out]" \
                    -map "[out]"  ' + newpath + '/' + str(idx) + '.png'      
        else:
            cmd = 'ffmpeg -hide_banner -loglevel panic \
                    -y \
                    -i ' + path+'/'+ f + '    \
                    -i ' + watermark + ' \
                    -filter_complex "[0:v]scale='+dimensions+'[scaled]; \
                    [scaled]eq=contrast=1.3[sat];[sat]drawtext=:text=\'' + text + '\':fontcolor=white@1.0:fontsize=18:'+text_position+'[texted]; \
                    [texted]overlay='+watermark_position+'[out]" \
                    -map "[out]"  ' + newpath + '/' + str(idx) + '.png'                
         
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")

    #Create Video based on all newly create frames
    def_file_path =  VID_FOLDER +'/'+date +'_'+ camID +'.mp4' 
    cmd = 'ffmpeg -hide_banner -loglevel panic -y  -r '+ str(fps) +' -f image2 -s 1920x1080 -i ' + newpath+ '/%d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p ' + def_file_path
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   
    #Rename and Move the first frame in the dest folder so we'll use it as a thumb
    cmd = 'mv ' + newpath + '/0.png ' +   VID_FOLDER + '/'+date +'_'+ camID +'.png'        
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")

    #DELETING RESIZE FRAMES
    filelist = glob.glob(os.path.join(newpath, "*.png"))
    for f in filelist:
        os.remove(f) 

    return def_file_path



# GENERATE TIMELAPSE - STEP 1
def generate_timelapse(cam_id,date,fps,dim,text_pos,wat_pos): 
    files, path, date, camID = get_sd_frames(cam_id,date)
    return create_sd_vid(files,path, date, camID,fps,dim,text_pos,wat_pos)


