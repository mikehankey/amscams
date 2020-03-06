import os
import glob
import subprocess 
import datetime
import time
import shutil
import sys

from lib.VIDEO_VARS import * 
from os import listdir, remove
from os.path import isfile, join, exists
from shutil import copyfile
from lib.FileIO import load_json_file
from pathlib import Path
  


SIZE_THUMB = 50

# Create cropped Video from a video & a json
def define_crop_video(json_file,video):
   # ex: /AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298-SD.mp4
   #     /AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298.json
   # output:
   #     /AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298-SD-cropped.mp4
   # or
   #      /AMS7/METEOR/2019/12/24/2019_12_24_08_17_10_000_010041-trim1298-HD-cropped.mp4
 

   # Get the info from the json
   data = load_json_file(json_file)
    
   all_x = []
   all_y = []
   n_SIZE_THUMB = SIZE_THUMB

   # SD or HD?
   if('SD' in video):
      HD = False
   else:
      HD = True
      n_SIZE_THUMB = SIZE_THUMB*2

   # Get min x,y & w h
   if(data is not False):
      if('frames' in data):
         for frame in data['frames']:
            if('x' in frame):
               all_x.append(int(frame['x']))
            if('y' in frame):
               all_y.append(int(frame['y']))  

         x = min(all_x) - n_SIZE_THUMB    
         w = max(all_x) - x + n_SIZE_THUMB      
         y = min(all_y) - n_SIZE_THUMB
         h = max(all_y) - y + n_SIZE_THUMB
 
         # Create Output Name
         output_file = video.replace('.mp4','-cropped.mp4')

         # Cropp the video
         crop_video(video,w,h,x,y,output_file)

 
# Create Crop video
def crop_video(mp4,w,h,x,y,output):
   cmd = 'ffmpeg -y -i '+mp4+'  -filter:v "crop='+str(w)+':'+str(h)+':'+str(x)+':'+str(y)+'" '+ output

   # Test if it's doable
   try:
      subprocess.check_output(cmd, shell=True).decode("utf-8")   
      print("ffmpeg cmd successfull >> " +  output) 
   except subprocess.CalledProcessError as e:
      print("Command " + cmd + "  return on-zero exist status: " + str(e.returncode))
      sys.exit(0)   
 

# Fix a MP4 just copying it 
def fixmp4(path_to_mp4,save_backup=0):
   path = str(Path(path_to_mp4).parent.absolute())+os.sep
   name = os.path.basename(path_to_mp4)
   tmp_output_file = path + 'tmp.mp4'

   # We create a tmp fix mp4 under the same folder
   cmd = 'ffmpeg -y -hide_banner -loglevel panic -i ' + path_to_mp4 + ' ' + tmp_output_file
   
   # Test if it's doable
   try:
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")   
      #print("ffmpeg cmd successfull >> " +  tmp_output_file) 
   except subprocess.CalledProcessError as e:
      print("Command " + cmd + "  return on-zero exist status: " + str(e.returncode))
      sys.exit(0)

 
   if(save_backup==1):
      # We rename the original file 
      os.rename(path_to_mp4, path_to_mp4+'.backup.mp4')
      print(path_to_mp4 + ' renamed to ' + path_to_mp4+'.backup.mp4')
   else:
      # We delete the original file
      os.remove(path_to_mp4)
      print(path_to_mp4 + ' deleted')


   # We rename the ffmpeg output file
   os.rename(tmp_output_file,path_to_mp4)

   print(path_to_mp4 + ' fixed')
   

# Blend two images together
# org =  '/mnt/ams2/TIMELAPSE_IMAGES/2019_08_06_01_02_26_000_010039.png'
# stack = get_stack_from_HD_frame(org)
# blend(org,stack,40,'/mnt/ams2/TMP/test.png')
# WARNING: it only works if the images haven't the same size (HD_DIM resize)
def blend(image1, image2, perc_trans_image1, output_file):
    other_perc =  int(perc_trans_image1)/100
    cmd = 'ffmpeg -y -hide_banner -loglevel panic -i '+image2+' -i '+image1+' -filter_complex "[0:v]scale='+HD_DIM+'[scaled];[1:v]scale=1280x720[scaled2];[scaled][scaled2]blend=all_mode=\'multiply\':all_opacity='+str(other_perc)+'[out]" -map "[out]" '+ output_file
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")    
    return output_file
 
  
#Get Video date from file name 
def get_meteor_date(_file):
	fn = _file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "_" + fn[1] + "_" + fn[2]


#Get Time from file name without seconds!!
def get_meteor_time(_file):
    fn = _file.split("/")[-1]
    fn = fn.split(".")[0]
    fn = fn.split("_")
    return fn[3] + '_' + fn[4] 

#Get date & time with  second 
def get_meteor_date_and_time_ws(_file):
    fn = _file.split("/")[-1] 
    fn = fn.split("_",6)
    return fn[0] + '/' + fn[1] + '/' + fn[2]   +  ' ' + fn[3] + ':' + fn[4] + ':' + fn[5]


#Get date & time without second 
def get_meteor_date_and_time_wts(_file):
    fn = _file.split("/")[-1] 
    fn = fn.split("_",6)
    return fn[0] + '/' + fn[1] + '/' + fn[2]   +  ' ' + fn[3] + ':' + fn[4]

#Get date & time (python object from file name)
def get_meteor_date_and_time_object(_file):
    return time.strptime(get_meteor_date_and_time_wts(_file), "%Y/%m/%d %H:%M")

#Get date & time (python object from file name) with SECONDS
def get_meteor_date_and_time_object_ws(_file):
    return time.strptime(get_meteor_date_and_time_ws(_file), "%Y/%m/%d %H:%M:%S")

#Return nothing or the HD stack that correspond to the same time/cam of the time passed as parameters
#ex:
# get_stack('/mnt/ams2/TIMELAPSE_IMAGES/2019_08_06_01_02_26_000_010039.png')
# return /mnt/ams2/meteors/2019_08_06/2019_08_06_01_02_26_000_010039-trim-885-HD-meteor-stacked.png
def get_stack_from_HD_frame(org_image):

    #print('ORG FILE ' + org_image)

    #Get date from file
    date = get_meteor_date(org_image) 

    #Get the cam id 
    cam_id = org_image.split("/")[-1]
    cam_id = cam_id.split(".")[0]
    cam_id = cam_id.split("_")[-1]
    #print("CAM ID " + cam_id)

    #Get time from fime
    time = get_meteor_time(org_image)
    date_and_time = date + "_" + time

    #print("date_and_time " + date_and_time)
    #print("WE SEARCH IN " + STACK_FOLDER+date)

    #print(str(listdir(STACK_FOLDER+date)))
 
    #find in STACK_FOLDER/date/ all the files that starts with date and have same cam id
    stacks = [f for f in listdir(STACK_FOLDER+date) if date_and_time in f and cam_id in f and "HD" not in f and "obj" not in f and "-tn" not in f and "-night" not in f and "json" not in f and "mp4" not in f and "crop" not in f]
 
    #print("STACKS FROM get_stack_from_HD_frame " + str(stacks))

    #return only one
    if(stacks is not None and len(stacks)!=0):
        #print('NON HD STACK FOUND')
        return STACK_FOLDER+date+'/'+stacks[0]
    else:
        # We search for the HD version
        stacks = [f for f in listdir(STACK_FOLDER+date) if date_and_time in f  and cam_id in f and "obj" not in f and "-tn" not in f and "-night" not in f and "json" not in f and "mp4" not in f and "crop" not in f]
        if(stacks is not None and len(stacks)!=0):
            #print('HD STACK FOUND')
            return STACK_FOLDER+date+'/'+stacks[0]
        else: 
            return False



#Delete Video From Path
def delete_video(vid):

    #Get path to thumb
    thumb = vid.replace(".mp4",".png")

    if os.path.isfile(vid):
        os.remove(vid)
    else:    
        print("Error: %s video not found" % vid)

    if os.path.isfile(thumb):
        os.remove(thumb)
    else:    
        print("Error: %s thumb not found" % thumb)


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

  
#Drawbox
def drawbox_on_vid(path,vid,x,y,w,h):
    cmd = 'ffmpeg -i ' + path +'/'+ vid + ' -vf "drawbox=enable=\'between(n,28,32)\' : x='+str(x)+' : y='+str(y)+' : w='+str(w)+' : h='+str(h)+' : color=red" -codec:a copy '+  path +'/boxed_'+vid
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")    
    return 'boxed_'+str(vid)



#Input: camID, date
#Ouput: list of sd frames found for this date/cam
#ex:camID:010034, date:2019_06_23 
def get_sd_frames(camID,date,limit_frame=False):
    cur_path = IMG_SD_SRC_PATH + date + "/images"
    #print(cur_path)
    if(os.path.isdir(cur_path)):

        frames = [f for f in listdir(cur_path) if camID in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
        
        #DEBUG ONLY!! 
        if(limit_frame is not False):
            frames = frames[1:50]

        if not frames:
            #print('NO INPUT FOR VID CamID:' + camID + ' - DATE ' + date)
            #print('FOLDER: ' + cur_path)
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
    
    else:
        return([] , cur_path)


# Get first frame of the equivalent of the SD video from an HD video
# ex:
# from /mnt/ams2/HD/2019_08_06_09_09_40_000_010037.mp4
# WE SEARCH FIRST UNDER 
#   /mnt/ams2/SD/proc2/2019_08_06/images
# IF WE DIDN'T FIND THE RIGHT IMAGE WE SEARCH UNDER
#   /mnt/ams2/SD/proc2/2019_08_06/success
# IF WE DIDN'T FIND THE RIGHT IMAGE WE SEARCH UNDER
#   /mnt/ams2/SD/proc2/2019_08_06/success
# IF WE DIDN'T FIND THE RIGHT IMAGE WE GET THE VIDEO 
#      /mnt/ams2/SD/2019_08_06/2019_08_06_09_40_45_000_010037.mp4
#      AND WE EXTRACT THE PROPER IMAGE
# IMPORTANT: 
# - the seconds are different in the file names
# - we need to resize all the images to HD_DIM
def get_sd_frames_from_HD_video(hd_video_file, camID):
    date = get_meteor_date(hd_video_file)
    date_and_time = date + "_" + get_meteor_time(hd_video_file)
    
    # sd_path = /mnt/ams2/SD/proc2/[DATE]/
    sd_path = IMG_SD_SRC_PATH +  date + '/'
    tmppath = r''+TMP_IMG_HD_SRC_PATH
    
    # First we seach under /mnt/ams2/SD/proc2/[DATE]/images where we only have .png
    potential_frames = [f for f in listdir(sd_path+'/images') if camID in f and ".png" in f and "-tn" not in f  and "-obj" not in f and date_and_time in f]
    if(potential_frames is not None and len(potential_frames)!=0):
        #print('FRAME FOUND UNDER '+ sd_path+'/images/' +  potential_frames[0])
        output_name = '/To_blend_' + potential_frames[0]  
        cmd = 'ffmpeg -y -hide_banner -loglevel panic  -i '+sd_path+'/images'+'/'+potential_frames[0]+'  -vf scale='+HD_DIM + ' ' + tmppath  + output_name
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        #print('WE RETURN ' +  output_name)
        #print(cmd)
        #print('***************')
        return output_name
    #else: 
        #print('CAM ID ' + camID)
        #print('date_and_time' + date_and_time)
        #print('NOT FOUND IN ' +  sd_path+'/images')

    potential_frames = [f for f in listdir(sd_path+'/passed') if camID in f  and ".png" in f and "-tn" not in f and "-obj" not in f and date_and_time in f]
    if(potential_frames is not None and len(potential_frames)!=0):
        #print('FRAME FOUND UNDER '+ sd_path+'/passed/' +  potential_frames[0])
        output_name = '/To_blend_' + potential_frames[0]  
        cmd = 'ffmpeg -y -hide_banner -loglevel panic  -i '+sd_path+'/passed'+'/'+potential_frames[0]+'  -vf scale='+HD_DIM + ' ' + tmppath  + output_name
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        return output_name   
    #else: 
        #print('CAM ID ' + camID)
        #print('date_and_time' + date_and_time)
        #print('NOT FOUND IN ' +  sd_path+'/passed')

    potential_frames = [f for f in listdir(sd_path+'/failed') if camID in f  and ".png" in f and "-tn" not in f and "-obj" not in f and date_and_time in f]
    if(potential_frames is not None and len(potential_frames)!=0):
        #print('FRAME FOUND UNDER '+ sd_path+'/failed/' +  potential_frames[0])
        output_name = '/To_blend_' + potential_frames[0] 
        cmd = 'ffmpeg -y -hide_banner -loglevel panic  -i '+sd_path+'/failed'+'/'+potential_frames[0]+'  -vf scale='+HD_DIM + ' ' + tmppath  + output_name
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        return output_name   
    #else: 
        #print('CAM ID ' + camID)
        #print('date_and_time' + date_and_time)
        #print('NOT FOUND IN ' +  sd_path+'/failed')

    potential_videos = [f for f in listdir(sd_path) if camID in f and date_and_time in f]
    if(potential_videos is not None and len(potential_videos)!=0):
        # We extract the first frame of this video and we return it with dimension = HD_DIM
        output_name = '/To_blend_' + potential_videos[0] + '.png' 
        cmd = 'ffmpeg -y -hide_banner -loglevel panic  -i '+sd_path+'/'+potential_videos[0]+' -vframes 1 -f image2  -vf scale='+HD_DIM + ' ' + tmppath  + output_name
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
        return output_name
    
    
    return False


#NEW STUFF HERE TO TAKE start_date & end_date into account and SEARCH in HD FRAMES FIRST
#We test if we have at least one image under HD_FRAMES_PATH that matches the cam_id
#And that has a date <= start_date
def get_hd_frames_from_HD_repo(camID,date,start_date,end_date,blend_sd=False,limit_frame=False):
    cur_path = HD_FRAMES_PATH
    res = True

    #Change date as it appears in the file names
    date =  date.replace('/','_')
    date =  date.replace(' ','_')
    date =  date.replace(':','_')
    #test if we have at least one file name - YYYY_DD_MM_HH_ii_SS[_000_]CAM_ID.mp4 under HD_FRAMES_PA 
    test = [f for f in listdir(cur_path) if isfile(join(cur_path, f))]
 
    if test:
     
        # We need to get all of them from start_date to end_date
        frames = [f for f in listdir(cur_path) if camID in f]
        real_frames = []
 

        start_date_obj = time.strptime(start_date, "%Y/%m/%d %H:%M")
        end_date_obj = time.strptime(end_date, "%Y/%m/%d %H:%M")
 
        #Check temporary folder to store the frames of all the videos
        tmppath = r''+TMP_IMG_HD_SRC_PATH
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)
        else:
            #Clean the directory (maybe necessary)
            files = glob.glob(tmppath+'/*')
            for f in files:
                os.remove(f)

        
        for f in frames:
            cur_date = get_meteor_date_and_time_object(f)

            # We test if the frame is within the proper period
            if(cur_date >= start_date_obj and cur_date <= end_date_obj):
                real_frames.append(f)

                # Here we eventually blend with the corresponding SD video
                # The SD videos are under /mnt/ams2/SD/proc2/[2019_08_08]/[2019_08_08_04_58_53_000_010042.mp4]
                # and blend it with the HD frame
                #print('BEFORE FRAME TO BLEND')
                if(blend_sd==True):
                    frame_to_blend = get_sd_frames_from_HD_video(f, camID)
                    print('BLEND FRAME FOUND')

                    if(frame_to_blend is not False):
                        frame_to_blend = TMP_IMG_HD_SRC_PATH + frame_to_blend
                        f2 = blend(cur_path + '/' + f,frame_to_blend,BLENDING_SD,cur_path + '/' + f)
                        shutil.copy2(f2, tmppath + '/' + f)
                    else:
                        shutil.copy2(cur_path+ f, tmppath + '/' + f)
               
                else:
                    shutil.copy2(cur_path+ f, tmppath + '/' + f)


        if(real_frames is not None):
            return(sorted(real_frames), tmppath)  
        else:
            print('No frame found for the period - see Video_HD_Images_Cron.py')
            return False
    else:
        print('The Cron job for the HD frames didnt run properly - see Video_HD_Images_Cron.py')
        return False



#Input! camID, date
#Ouput: list of HD frames found for this date or get_sd_frames if no HD frame has been found
#ex: get_hd_frames('010040','2019_07_08')
def get_hd_frames(camID,date,start_date,end_date,limit_frame=False):
    cur_path = IMG_HD_SRC_PATH
    res= True

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
        
        #We create all the frames under TMP_IMG_HD_SRC_PATH/
        for idx,vid in enumerate(sorted(frames)):
            try:
                vid_out = vid.replace('.mp4','')
                cmd = 'ffmpeg -y -hide_banner -loglevel panic -i '+IMG_HD_SRC_PATH+'/'+vid+' -vframes 1 -f image2 '+ tmppath + vid_out + '.png' 
                output = subprocess.check_output(cmd, shell=True).decode("utf-8")
                toReturn.append( vid_out + '.png' )
                #print(tmppath + '/'  + vid_out + '.png' )
                #print(toReturn)
            except:
                #print('PB')
                res = False
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


#Return ffmpeg code for Info position (text only + extra text)
def get_text_pos(text_pos, extra_text_here):

    if(extra_text_here==False):
        if(text_pos=='tr'):
            return ("x=main_w-text_w-20:y=20","")
        elif (text_pos=='tl'):
            return ("x=20:y=20","")    
        elif (text_pos=='bl'):
            return("x=20:y=main_h-text_h-20","")
        else: 
            return ("x=main_w-text_w-20:y=main_h-text_h-20","")
    else:
        line_height_spacing = "8"

        if(text_pos=='tr'):
            return ("x=main_w-text_w-20:y=20+line_h+"+line_height_spacing,"x=main_w-text_w-20:y=20")
        elif (text_pos=='tl'):
            return ("x=20:y=20+line_h+"+line_height_spacing,"x=20:y=20")    
        elif (text_pos=='bl'):
            return("x=20:y=main_h-text_h-20","x=20:y=main_h-text_h-20-line_h-"+line_height_spacing)
        else: 
            return ("x=main_w-text_w-20:y=main_h-text_h-20","x=main_w-text_w-20:y=main_h-text_h-20-line_h-"+line_height_spacing)                


#Add text, logo, etc.. to a frame             
def add_info_to_frame(frame, cam_text, extra_text, text_position, extra_text_position, watermark, watermark_position, logo, logo_pos, newpath, dimensions="1920:1080",  enhancement=0, extension="png"):
     
    # Do we have extra text?
    if(extra_text is None):
        with_extra_text = False
        extra_text=''
    elif(extra_text.strip()==''):
        with_extra_text = False
        extra_text=''
    else:
        with_extra_text = True 
 
    # Start ffmpeg
    cmd = 'ffmpeg -hide_banner -loglevel panic \
            -y \
            -i ' + frame + '    \
            -i ' + watermark  

    if(logo_pos is not 'X'):
        cmd += ' -i ' +  logo
        with_extra_logo= True
    else:
        with_extra_logo= False
  
    cmd +=  ' -filter_complex "[0:v]scale='+dimensions+'[scaled]; \
            [scaled]drawtext=:text=\'' + cam_text +'\':fontfile=\'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf\':fontcolor=white@'+FONT_TRANSPARENCY+':fontsize='+FONT_SIZE+':'+text_position 
    
    #Extra Text
    if(with_extra_text is True):
        cmd+= '[texted];' 
        cmd+= '[texted]drawtext=:text=\''+ extra_text +'\':fontfile=\'/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf\':fontcolor=white@'+FONT_TRANSPARENCY+':fontsize='+FONT_SIZE+':'+extra_text_position+'[texted2];[texted2]'  
    else:
        cmd+= '[texted]; [texted]'

    #Watermark
    cmd += 'overlay='+watermark_position;

    #Extra Logo
    if(with_extra_logo is True):
        cmd+= '[wat];[wat]overlay='+logo_pos+'[out]"'
    else:
        cmd+= '[out]"'

    cmd += ' -map "[out]"  ' + newpath + '.' + extension      

  

    #print(cmd)
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")  
    return newpath



#Add AMS Logo, Info and eventual logo (todo)
#Resize the frames 
def add_info_to_frames(frames, path, date, camID, extra_text, logo, logo_pos, dimensions="1920:1080", text_pos='bl', watermark_pos='tr', enhancement=0, extension="png"):
 
    newpath = r''+path 
    
    #Create destination folder if it doesn't exist yet
    if not os.path.exists(VID_FOLDER):
        os.makedirs(VID_FOLDER) 
  
    # Do we have extra text?
    if(extra_text is None):
        with_extra_text = False
        extra_text=''
    elif(extra_text.strip()==''):
        with_extra_text = False
        extra_text=''
    else:
        with_extra_text = True
  
    # Info position based on options
    text_position, extra_text_position = get_text_pos(text_pos, (extra_text!=''))

    # Watermark position based on options
    watermark_position = get_watermark_pos(watermark_pos)

    # Do we have extra logo
    if(logo is None):
        with_extra_logo = False 
        logo_position= 'X' 
    elif(logo.strip()==''):
        with_extra_logo = False
        logo_position = 'X'  
    else:
        with_extra_logo = True 
        logo_position = get_watermark_pos(logo_pos)     

    #Watermark R or L
    if('r' in watermark_pos):
        watermark = AMS_WATERMARK_R
    else:
        #We defined the PATH ONLY as it's an animation
        if(dimensions.startswith('1920')):
            water_path =  AMS_WATERMARK_ANIM_PATH_1920x1080
        elif(dimensions.startswith('1280')):
            water_path =  AMS_WATERMARK_ANIM_PATH_1280x720
        else:
            water_path =  AMS_WATERMARK_ANIM_PATH_640x360

    # Treat All frames
    for idx,f in enumerate(frames): 
        #Resize the frames, add date & watermark in /tmp
        text = 'AMS Cam #'+camID+ ' ' + get_meteor_date_ffmpeg(f) + 'UT'
        org_path = path+'/'+ f  
        t_newpath = newpath + '/' + str(idx)

        if('l' in watermark_pos):
            if(idx<=AMS_WATERMARK_ANIM_FRAMES):
                    if(idx<10):
                        watermark = water_path + "AMS0" + str(idx) + ".png"
                    else:
                        watermark = water_path + "AMS" + str(idx)  + ".png"
            else:
                watermark = water_path + "AMS" + str(AMS_WATERMARK_ANIM_FRAMES)  + ".png"  


        add_info_to_frame(org_path,text,extra_text,text_position,extra_text_position,watermark,watermark_position,logo,logo_position,t_newpath,dimensions,enhancement,extension)
 
        #Remove the source 
        os.remove(path+'/'+ f)  

    return(newpath)



#Create a video based on a set of frames
def create_vid_from_frames(frames, path, date, camID, fps="25", ext="png") :
    
    #Create Video based on all newly create frames 

    if(frames is not None and len(frames)!=0):

        #Destination folder
        def_file_path =  VID_FOLDER +'/'+date +'_'+ camID +'.mp4' 
        
        cmd = 'ffmpeg -hide_banner -loglevel panic -y  -r '+ str(fps) +' -f image2 -s 1920x1080 -i ' + path+ '/%d.'+ext+' -vcodec libx264 -crf 25 -pix_fmt yuv420p ' + def_file_path
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")
    
        #Rename and Move the first frame in the dest folder so we'll use it as a thumb
        cmd = 'mv ' + path + '/0.'+ ext + ' ' +   VID_FOLDER + '/'+date +'_'+ camID + '.' + ext       
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")

        #DELETING RESIZE FRAMES
        #filelist = glob.glob(os.path.join(path, "*.png"))
        #for f in filelist:
        #    os.remove(f) 

        return def_file_path 

    else:
        return ""



#Get all meteors detections (return mp4s) from a given date (start & end) & cam_id
#Return an associative array that looks like
# {'2019/08/21 00:40': '2019_08_21_00_40_16_000_010037-trim-578-HD-meteor.mp4', ...
# And the path where to find the videos
def get_all_meteor_detections(date,start_date,end_date,cam_id):
 
    #Meteor Folder
    meteor_folder = METEOR_FOLDER+date

    #Create Date Objects
    start_date_obj = time.strptime(start_date, "%Y/%m/%d %H:%M")
    end_date_obj = time.strptime(end_date, "%Y/%m/%d %H:%M")

    # Get All the detection for the cur CAM ID & Date
    # Note: WE CARE ONLY ABOUT THE REDUCED METEORS (as the json for non-reduced is full of wrong paths)
    detections = [f for f in listdir(meteor_folder) if cam_id in f and ".json" in f and "-reduced" in f]
    real_detections = {}

    # Remove Detection outside of the timeframe
    for detection in detections:

        #Get the date & time of the video
        cur_date = get_meteor_date_and_time_object(str(detection))
        
        if(cur_date>=start_date_obj and end_date_obj>=cur_date):

            # Get the date without seconds
            cur_date_string = get_meteor_date_and_time_ws(str(detection))
            
            if cur_date_string not in real_detections: 
                
                #We parse the JSON to get the path to the HD
                if os.path.isfile(meteor_folder+'/'+detection): 
                    data = load_json_file(meteor_folder+'/'+detection)
                    real_detections[cur_date_string] = {"hd_video_file": data['hd_video_file'],"hd_stack": data['hd_stack'],"event_start_time":data['event_start_time']}
                   
                else:
                    print(detection + " is not a file")
    
    return real_detections, meteor_folder


#Extract all the frames from a video detection in order to add text, logo(s) & time
def get_all_detection_frames(path,vid):

    #Extract all frames
    vid_name = vid.split('.') 
    vid_name = vid_name[0] 
    cmd = 'ffmpeg -y -hide_banner -loglevel panic -i ' + path + '/' + vid + ' ' +  TMP_IMG_HD_SRC_PATH + '%04d' + '-' + vid_name + '.png' 
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")

    #We rename all the frames to the time match
    #We have an initial fps of FPS_HD
    #It means we had a sec every FPS_HD
    #It means we had a micro-sec every  

    #0001-2019_08_21_00_33_15_000_010037-trim-618-HD-meteor.png
    #0002-2019_08_21_00_33_15_000_010037-trim-618-HD-meteor.png

    #We get the start date
    all_frames = [f for f in listdir(TMP_IMG_HD_SRC_PATH) if vid_name in f]

    #Initial date
    initial_date = get_meteor_date_and_time_object_ws(vid)
    
    for idx,frame in enumerate(sorted(all_frames)):
        print(frame)
        print(initial_date)

    print(all_frames)

    print("DATE")
    print(get_meteor_date_and_time_object_ws(vid))

    print(TMP_IMG_HD_SRC_PATH + vid + '.png')