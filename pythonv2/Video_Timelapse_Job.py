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
        #Get the first one data 
        cur_job = alljobs[0]
        #{'fps': '10', 'dim': '1280:720', 'name': 'timelapse', 'text_pos': 'tr', 'wat_pos': 'bl', 'date': '2019_07_03', 'cam_id': '010038'}
        print(generate_timelapse(cur_job['cam_id'],cur_job['date'],cur_job['fps'],cur_job['dim'],cur_job['text_pos'],cur_job['wat_pos']))
        

        