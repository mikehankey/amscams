import glob, os, os.path, sys
import subprocess 
import json
from pathlib import Path 
from os.path import isfile, join, exists
from lib.Video_Timelapse import generate_timelapse, get_meteor_date_ffmpeg
from lib.VIDEO_VARS import * 

#Test if we are already taking care of a video
def is_a_job_processing():
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
    #Open the waiting_job & Load the data
    with open(WAITING_JOBS, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            #Nothing to do
            return False
    jsonFile.close()

    alljobs = data['jobs']
    if(alljobs is not None):
        toReturn = alljobs[0]

        #We remove the job from the waiting list 
        alljobs.pop(0)
        
        with open(WAITING_JOBS, 'w') as outfile:
            json.dump(alljobs, outfile)
        outfile.close()

        print('WAITING LIST UPDATED')
 
        #We add the job to the processing list
        with open(PROCESSING_JOBS, 'r+') as processingFile:
            try:
                data = json.load(processingFile)
            except:
                #Nothing to do
                data = {}
                data['jobs'] = {}
        processingFile.close()        

        data.update(toReturn)

        with open(PROCESSING_JOBS, 'w') as processingFile:
            json.dump(data, processingFile)
        processingFile.close()        

        print('PROCESSING LIST UPDATED')

        return toReturn
    else:
        return False        


 




def video_job():
    
    #Test if we have a video currently being processed
    if(is_a_job_processing() == True):
        print("ONE JOB IS ALREADY PROCESSING")
        sys.exit(0)

    #Get Job to Process
    job = get_job_to_process();
    
    if(job is not False):
         print("WE FOUND A JOB")
        #We remove the job from the WAITING_JOBS and put it in PROCESSING_JOBS
 
    else:
        print("NO JOB FOUND") 


        