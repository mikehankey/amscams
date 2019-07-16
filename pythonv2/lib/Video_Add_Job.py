import glob, os, os.path, sys
import subprocess 
import cgitb
import json
from pathlib import Path
from os import listdir,makedirs
from os.path import isfile, join, exists
from lib.VIDEO_VARS import * 

#ADD Job to WAITING_JOBS
def add_video_job(name,cam_id,date,fps,dim,text_pos,wat_pos,extra_text):

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

    #Do we have any jobs
    alljobs = data.get('jobs') 
    if(alljobs is None):
        data['jobs'] = []   

    #Define new job
    new_job = {  
        'name': name,
        'cam_id': cam_id,
        'date': date,
        'fps': fps,
        'dim':dim,
        'text_pos':text_pos,
        'wat_pos':wat_pos,
        'status': 'waiting',
        'extra_text':extra_text
    }

    duplicate = False

    #Search if the job already exist (avoid duplicates)
    for job in data['jobs']:
        try:
            this_extra_text = job['extra_text']
        except KeyError as e:
            this_extra_text = ""
        if(this_extra_text == extra_text and job['name'] == name and job['cam_id']== cam_id and job['date']== date and job['fps']== fps and job['dim']== dim and job['text_pos']== text_pos and job['wat_pos']== wat_pos ):
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
