import glob, os, os.path, sys
import subprocess 
import json
from pathlib import Path 
from os.path import isfile, join, exists
from lib.Video_Timelapse import generate_timelapse

SD_PATH='/mnt/ams2/SD/proc2/'
WAITING_JOBS_FOLDER = SD_PATH + '/custom_videos/'
WAITING_JOBS = WAITING_JOBS_FOLDER + 'waiting_jobs.json'

#READ THE waiting_jobs file if it exist 
js_file = Path(WAITING_JOBS)
if js_file.is_file():

    #Open the waiting_job & Load the data
    with open(WAITING_JOBS, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            # in case something went wrong
            data = {} 

    #Do we have any jobs
    alljobs = data['jobs']
    if(alljobs is not None):

        cur_idx = 0

        #Get the first "waiting" job
        for idx, cur_jobs in enumerate(alljobs):
            if(cur_jobs['status']=='waiting'):
                cur_job = cur_jobs
                cur_idx = idx
                break;

        if(cur_jon is not None):

            #Change Status of the job in the JSON
            data['jobs'][cur_idx]['status'] = 'processing'
            with open(WAITING_JOBS, 'w') as outfile:
                json.dump(data, outfile)

            # Generate Video
            #print(str(cur_job))
            video_path = generate_timelapse(cur_job['cam_id'],cur_job['date'],cur_job['fps'],cur_job['dim'],cur_job['text_pos'],cur_job['wat_pos'])

            data['jobs'][0]['status'] = 'ready'
            data['jobs'][0]['path']   = video_path
            with open(WAITING_JOBS, 'w') as outfile:
                json.dump(data, outfile)

        