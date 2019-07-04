import glob, os, os.path, sys
import subprocess 
import json
from pathlib import Path
from os import listdir,makedirs
from os.path import isfile, join, exists

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
        print(str(cur_job))
        