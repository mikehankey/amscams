import glob, os, os.path, sys
import subprocess 
import cgitb
import json
from pathlib import Path
from os import listdir,makedirs
from os.path import isfile, join, exists
 
SD_PATH='/mnt/ams2/SD/proc2/'
WAITING_JOBS_FOLDER = SD_PATH + '/custom_videos/'
WAITING_JOBS = WAITING_JOBS_FOLDER + 'waiting_jobs.json'

#Return Date & Time based on file name
def get_meteor_date_ffmpeg(file):
	fn = file.split("/")[-1] 
	fn = fn.split('_',6)
	return fn[0] + "/" + fn[1] + "/" + fn[2] + " " + fn[3] + "\:" + fn[4] + "\:" + fn[5]

#Input: camID, date
#Ouput: list of sd frames found for this date
def get_sd_frames(camID,date):
    #ex:camID:010034, date:2019_06_23
    cur_path = SD_PATH + date + "/images"
    onlyfiles = [f for f in listdir(cur_path) if camID in f and "-tn" not in f and "-night" not in f and "trim" not in f and isfile(join(cur_path, f))]
    #FOR DEBUG
    #onlyfiles = onlyfiles[1:50]
    return(sorted(onlyfiles), cur_path, date, camID)
 

#Input list of SD files, path of the current image, date, camID
#Position of watermark & text = tr=>Top Right, bl=>Bottom Left
#Output Video with watermark & text
def create_sd_vid(frames, path, date, camID, fps="15", dimensions="1920:1080", text_pos='bl', watermark_pos='tr', enhancement=0 ) : 

    #Create temporary folder to store the frames for the video
    newpath = r''+path+'/tmp/'
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
    def_file_path =  newpath +'/'+date +'_'+ camID +'.mp4' 
    cmd = 'ffmpeg -hide_banner -loglevel panic -y  -r '+ str(fps) +' -f image2 -s 1920x1080 -i ' + newpath+ '/%d.png -vcodec libx264 -crf 25 -pix_fmt yuv420p ' + def_file_path
    output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   
    #DELETING RESIZE FRAMES
    filelist = glob.glob(os.path.join(newpath, "*.png"))
    for f in filelist:
        os.remove(f) 

    return newpath+'/'+date + '_' + camID + '.mp4' 



# GENERATE TIMELAPSE - STEP 1
def generate_timelapse(cam_id,date,fps,dim,text_pos,wat_pos): 
    files, path, date, camID = get_sd_frames(cam_id,date)
    return create_sd_vid(files,path, date, camID,fps,dim,text_pos,wat_pos)


#ADD Job to /mnt/ams2/SD/proc2/timelapse.job.json
def add_timelapse_job(cam_id,date,fps,dim,text_pos,wat_pos):
    #Is the waiting_job folder exists? 
    if not os.path.exists(WAITING_JOBS_FOLDER):
        os.makedirs(WAITING_JOBS_FOLDER)
 
    #Create JSON file if it doesn't exist yet
    js_file = Path(WAITING_JOBS)
    if js_file.is_file()== False:
        f= open(WAITING_JOBS,"w+")
        f.close()

    #Open the waiting_job  
    with open(WAITING_JOBS, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            data = {} 

    #Do we have any jobs
    alljobs = data.get('jobs') 
    if(alljobs is None):
        data['jobs'] = []   

    #Define new job
    new_job = {  
        'name': 'timelapse',
        'cam_id': cam_id,
        'date': date,
        'fps': fps,
        'dim':dim,
        'text_pos':text_pos,
        'wat_pos':wat_pos,
        'status': 'waiting'
    }

    duplicate = False

    #Search if the job already exist (avoid duplicates)
    for job in data['jobs']:
        if(job['name'] == 'timelapse' and job['cam_id']== cam_id and job['date']== date and job['fps']== fps and job['dim']== dim and job['text_pos']== text_pos and job['wat_pos']== wat_pos ):
            duplicate = True
            break

    
    if(duplicate == False):

        #Add the new job
        data['jobs'].append(new_job)

        with open(WAITING_JOBS, 'w') as outfile:
            json.dump(data, outfile)

        res = {}
        res['msg'] = '<h4>Video added to the waiting list</h4><b>The video will be ready in 5 or 10 minutes.<br>Go to the <a href="/pycgi/webUI.py?cmd=video_tools">Custom Videos</a> page to download the video.</b>'
        print(json.dumps(res))
    
    else:

        res = {}
        res['msg'] = '<h4>This video is already on the waiting list.</h4><b>This video will be ready in 5 or 10 minutes.<br>Go to the <a href="/pycgi/webUI.py?cmd=video_tools">Custom Videos</a> page to download the video.</b>'
        print(json.dumps(res))
