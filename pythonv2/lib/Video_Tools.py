import os
import glob
import subprocess 
import datetime
from lib.VIDEO_VARS import * 
from os import listdir, remove
from os.path import isfile, join, exists
from shutil import copyfile


#Return Video length
def getLength(filename):
    cmd = "ffprobe -i "+filename +"  -show_entries format=duration -v quiet"
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    out = [line for line in output.split('\n') if "duration" in line]
    out = out[0][9:]
    return str(datetime.timedelta(seconds=round(float(out),0)))  


#Return Date & Time based on file name (that ends with a date)
def get_meteor_date_ffmpeg(_file):
	fn = _file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "/" + fn[1] + "/" + fn[2] + " " + fn[3] + "\:" + fn[4] + "\:" + fn[5]



#Input: camID, date
#Ouput: list of sd frames found for this date/cam
#ex:camID:010034, date:2019_06_23 
def get_sd_frames(camID,date,limit_frame=False):
    cur_path = IMG_SD_SRC_PATH + date + "/images"
    #print(cur_path)
    frames = [f for f in listdir(cur_path) if camID in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
    
    #DEBUG ONLY!! 
    if(limit_frame is not False):
        frames = frames[1:50]

    if not frames:
        print('NO INPUT FOR VID CamID:' + camID + ' - DATE ' + date)
        print('FOLDER: ' + cur_path)
        return([] , cur_path)
    else:    
        #Move the frames to a tmp folder so we can delete them once we're done with the video
        tmppath = r''+TMP_IMG_HD_SRC_PATH
        
        #Create directory if necessary
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)  

        for frame in frames:
            copyfile(cur_path+'/'+frame, tmppath+frame)
       
        return(sorted(frames) , tmppath)



#Input! camID, date
#Ouput: list of HD frames found for this date or get_sd_frames if no HD frame has been found
#ex: get_hd_frames('010040','2019_07_08')
def get_hd_frames(camID,date,limit_frame=False):
    cur_path = IMG_HD_SRC_PATH
    #test if we have at least one file name - YYYY_DD_MM_HH_ii_SS[_000_]CAM_ID.mp4
    test = [f for f in listdir(cur_path) if f.startswith(date) and f.endswith(camID+'.mp4') and isfile(join(cur_path, f))]
    if not test:
        print('NO HD Frames found - Searching for SD')
        #If nothing is found we try the SD
        return get_sd_frames(camID,date,limit_frame)
    else:
        frames = [f for f in listdir(cur_path) if camID in f and date in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]

        #DEBUG ONLY!! 
        if(limit_frame is not False):
            frames = frames[1:50]
          
        
        #Check temporary folder to store the frames of all the videos
        tmppath = r''+TMP_IMG_HD_SRC_PATH
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)
        else:
            #Clean the directory (maybe necessary)
            files = glob.glob(tmppath+'/*')
            for f in files:
                os.remove(f)
        #We extract one frame per video and add it to the array to return
        toReturn = []
        for idx,vid in enumerate(sorted(frames)):
            vid_out = vid.replace('.mp4','')
            cmd = 'ffmpeg -y -hide_banner -loglevel panic -i '+IMG_HD_SRC_PATH+'/'+vid+' -vframes 1 -f image2 '+ tmppath + vid_out + '.png' 
            output = subprocess.check_output(cmd, shell=True).decode("utf-8")
            toReturn.append( vid_out + '.png' )
            #print(tmppath + '/'  + vid_out + '.png' )
            #print(output)
        return(sorted(toReturn), tmppath)  
 


#Return ffmpeg code for watermarkposition
def get_watermark_pos(watermark_pos):
    if(watermark_pos=='tr'):
        return "main_w-overlay_w-20:20"
    elif (watermark_pos=='tl'):
        return "20:20"    
    elif (watermark_pos=='bl'):
        return "20:main_h-overlay_h-20"
    else: 
       return "main_w-overlay_w-20:main_h-overlay_h-20"


#Return ffmpeg code for Info position (text only)
def get_text_pos(text_pos):
    if(text_pos=='tr'):
        return "x=main_w-text_w-20:y=20"
    elif (text_pos=='tl'):
        return  "x=20:y=20"    
    elif (text_pos=='bl'):
        return "x=20:y=main_h-text_h-20"
    else: 
        return "x=main_w-text_w-20:y=main_h-text_h-20"


#Add AMS Logo, Info and eventual logo (todo)
#Resize the frames 
def add_info_to_frames(frames, path, date, camID, extra_text, dimensions="1920:1080", text_pos='bl', watermark_pos='tr', enhancement=0):
 
    newpath = r''+path 
    
    #Create destination folder if it doesn't exist yet
    if not os.path.exists(VID_FOLDER):
        os.makedirs(VID_FOLDER) 

    # Watermark position based on options
    watermark_position = get_watermark_pos(watermark_pos)

    # Info position based on options
    text_position = get_text_pos(text_pos)

    # Do we have extra text?
    if(extra_text.strip()==''):
        extra_text=''

    # Treat All frames
    for idx,f in enumerate(frames): 
        #Resize the frames, add date & watermark in /tmp
        text = 'AMS Cam #'+camID+ ' ' + get_meteor_date_ffmpeg(f) + 'UT'
        #Add extra text
        text =  extra_text + "\n" + text 
        
        #line_height = str(int(FONT_SIZE) +5)
        #print('LINE HEIGHT ' + line_height)

        if(enhancement!=1):
            cmd = 'ffmpeg -hide_banner -loglevel panic \
                    -y \
                    -i ' + path+'/'+ f + '    \
                    -i ' + AMS_WATERMARK + ' \
                    -filter_complex "[0:v]scale='+dimensions+'[scaled]; \
                    [scaled]drawtext=:text=\'' + text + '\':fontcolor=white@'+FONT_TRANSPARENCY+':fontsize='+FONT_SIZE+':'+text_position+'[texted]; \
                    [texted]overlay='+watermark_position+'[out]" \
                    -map "[out]"  ' + newpath + '/' + str(idx) + '.png'      
        else:
            cmd = 'ffmpeg -hide_banner -loglevel panic \
                    -y \
                    -i ' + path+'/'+ f + '    \
                    -i ' + AMS_WATERMARK + ' \
                    -filter_complex "[0:v]scale='+dimensions+'[scaled]; \
                    [scaled]eq=contrast=1.3[sat];[sat]drawtext=:text=\'' + text + '\':fontcolor=white@'+FONT_TRANSPARENCY+':fontsize='+FONT_SIZE+':'+text_position+'[texted]; \
                    [texted]overlay='+watermark_position+'[out]" \
                    -map "[out]"  ' + newpath + '/' + str(idx) + '.png'                
         
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")  

        #Remove the source 
        os.remove(path+'/'+ f)  

    return(newpath)



#Create a video based on a set of frames
def create_vid_from_frames(frames, path, date, camID, fps="25") :
    
    #Create Video based on all newly create frames
    
    #Destination folder
    def_file_path =  VID_FOLDER +'/'+date +'_'+ camID +'.mp4' 
    
    cmd = 'ffmpeg -hide_banner -loglevel panic -y  -r '+ str(fps) +' -f image2 -s 1920x1080 -i ' + path+ '/%d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p ' + def_file_path
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   
    #Rename and Move the first frame in the dest folder so we'll use it as a thumb
    cmd = 'mv ' + path + '/0.png ' +   VID_FOLDER + '/'+date +'_'+ camID +'.png'        
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")

    #DELETING RESIZE FRAMES
    #filelist = glob.glob(os.path.join(path, "*.png"))
    #for f in filelist:
    #    os.remove(f) 

    return def_file_path 