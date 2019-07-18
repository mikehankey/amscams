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
    print("IN is_a_job_processing")     
    print(data)   
    print(str(len(data)))   
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

    if(alljobs is not None and len(alljobs)!=0):
        toReturn = alljobs[0]
 
        #We remove the job from the waiting list 
        data['jobs'].pop(0)
        
        with open(WAITING_JOBS, 'w') as outfile:
            json.dump(data, outfile)
        outfile.close()

        print('WAITING LIST UPDATED')
 
        #We add the job to the processing list
        with open(PROCESSING_JOBS, 'r+') as processingFile:
            try:
                data = json.load(processingFile) 
            except:
                #Nothing to do
                data = {} 
        processingFile.close()        

        #When the file is empty at first
        if(len(data)==0):
            data['jobs'] = {}

        toReturn['status'] = "processing"
        data['jobs'].append(toReturn)

        with open(PROCESSING_JOBS, 'w') as processingFile:
            json.dump(data, processingFile)
        processingFile.close()         

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
        error = False

        #TIMELAPSE
        if(job['name']=='timelapse'):
            video_path =  generate_timelapse(job['cam_id'],job['date'],job['fps'],job['dim'],job['text_pos'],job['wat_pos'],job['extra_text'],0) 

            #try:
            #except:
            #    error = True
 
        if(error == False):

            #We empty the list of processing file  
            processingFile = open(PROCESSING_JOBS, 'r+')
            processingFile.truncate(0)
            processingFile.close()  

            print("VIDEO PROCESSED " + video_path)

        else:

            print("ERROR PROCESSING THE VIDEO")
    
    else:
        print("NO JOB FOUND") 


        