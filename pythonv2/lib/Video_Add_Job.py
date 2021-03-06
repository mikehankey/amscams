import glob, os, os.path, sys
import subprocess 
import cgitb
import json
from datetime import datetime, timedelta
from pathlib import Path
from os import listdir,makedirs
from os.path import isfile, join, exists
from lib.VIDEO_VARS import * 
from lib.Video_Parameters import save_video_job_parameters



#ADD Job to WAITING_JOBS

def add_video_job(name,cam_ids,date,time,duration,fps,dim,text_pos,wat_pos,blend_sd,extra_text,extra_text_pos,logo,logo_pos):

    if(logo is None ):
        logo = ""
   
    #Save current params as default
    save_video_job_parameters(fps,dim,logo,wat_pos,text_pos,logo_pos,extra_text,extra_text_pos)
 
    #If we only have one cam_id
    if(type(cam_ids) is str):
        cam_ids = [cam_ids]
 
    #Is the waiting_job folder exists? 
    if not os.path.exists(WAITING_JOBS_FOLDER):
        os.makedirs(WAITING_JOBS_FOLDER)

    #Create JSON file if it doesn't exist yet (PROCESSING)
    js_file = Path(PROCESSING_JOBS)
    if js_file.is_file()== False:
        f= open(PROCESSING_JOBS,"w+")
        f.close()    
 
    #Create JSON file if it doesn't exist yet (WAITING)
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
    jsonFile.close()

    #Do we have any jobs
    alljobs = data.get('jobs') 
    if(alljobs is None):
        data['jobs'] = []   

    
    res = {}
    ok_list = ''
    bad_list = '' 

    # Get start date & time
    # and end date & time
    start_date = datetime.strptime(date + ' ' + time, '%Y/%m/%d %H:%M')
    end_date = start_date + timedelta(hours=int(duration))

     

    for cam_id in cam_ids:

        #Define new job
        new_job = {  
            'name': name,
            'cam_id': cam_id,
            'date': date.replace('/','_'),
            'start_date': format(start_date, '%Y/%m/%d %H:%M'),
            'end_date': format(end_date, '%Y/%m/%d %H:%M'),
            'fps': fps,
            'dim':dim,
            'text_pos':text_pos,
            'wat_pos':wat_pos,
            'status': 'waiting',
            'extra_text':extra_text,
            'extra_text_pos':extra_text_pos,
            'logo': logo,
            'logo_pos': logo_pos,
            'blend_sd': blend_sd
        }
 
        duplicate = False

        #Search if the job already exist (avoid duplicates)
        for job in data['jobs']:
            try:
                this_extra_text = job['extra_text']
            except KeyError as e:
                this_extra_text = ""
            if(job['logo'] == logo and job['logo_pos'] == logo_pos and this_extra_text == extra_text and job['name'] == name and job['cam_id']== cam_id and job['date']== date and job['fps']== fps and job['dim']== dim and job['text_pos']== text_pos and job['wat_pos']== wat_pos and job['blend_sd']== blend_sd ):
                duplicate = True
                break

    
        if(duplicate == False):

            #Add the new job
            data['jobs'].append(new_job)

            with open(WAITING_JOBS, 'w') as outfile:
                json.dump(data, outfile)
            outfile.close()

            ok_list += '<li><b>Cam ID ' + cam_id + ' - ' + date + '</b> ADDED</li>'
        
        else:

            bad_list += '<li><b>Cam ID ' + cam_id + ' - ' + date + '</b> NOT ADDED - This video is already on the wainting list</li>'


    res['msg'] = '<h4>Video(s) added to the waiting list</h4><div class="mr-3 ml-3">The video(s) will be ready in 5 or 10 minutes.<ul>'+ok_list+bad_list+'</ul>Go to the <a href="/pycgi/webUI.py?cmd=video_tools">Custom Videos</a> page to download the video.'
    print(json.dumps(res))
           