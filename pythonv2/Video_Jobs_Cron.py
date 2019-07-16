import glob, os, os.path, sys
import subprocess 
import json
from pathlib import Path 
from os.path import isfile, join, exists
from lib.Video_Timelapse import generate_timelapse, get_meteor_date_ffmpeg
from lib.VIDEO_VARS import * 

#Test if we are already taking care of a video
def is_a_job_processing():
    js_file = Path(PROCESSING_JOBS)
    with open(PROCESSING_JOBS, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            # in case something went wrong
            data = {} 
    if(len(data)==0):
        return False
    else:
        return True

#Return a job to process 
#of False if no waiting job found
def get_job_to_process():
    js_file = Path(WAITING_JOBS)
    
    #Open the waiting_job & Load the data
    with open(WAITING_JOBS, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            #Nothing to do
            return False

    alljobs = data['jobs']
    if(alljobs is not None):
        return alljobs[0]
    else:
        return False        



def video_job():
    
    #Test if we have a video currently being processed
    if(is_a_job_processing() == True):
        print("ONE IS ALREADY PROCESSING")
        sys.exit(0)

    #Get Job to Process
    job = get_job_to_process();
    
    if(job is not False):
        print("WE FOUND A JOB")
    else:
        print("NO JOB FOUND")


        