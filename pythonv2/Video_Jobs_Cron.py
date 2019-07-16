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
    with open(WAITING_JOBS, "r+") as jsonFile:
        try:
            data = json.load(jsonFile)
        except:
            # in case something went wrong
            data = {} 
    if(len(data)==0):
        return False
    else:
        return True


def video_job():
    
    #Test if we have a video currently being processed
    if(is_a_job_processing() == True):
        exit;

    #Read the waiting jobs lists
    js_file = Path(WAITING_JOBS)
    if js_file.is_file():

        #Open the waiting_job & Load the data
        with open(WAITING_JOBS, "r+") as jsonFile:
            try:
                data = json.load(jsonFile)
            except:
                # in case something went wrong
                data = {} 

        print("DATA FOUND ")
        print(str(data))

        #Do we have any jobs
        alljobs = data['jobs']

        print("ALL JOBS")
        print(str(alljobs))

        if(alljobs is not None):

            cur_idx = 0
            cur_job = 'X'
            processing = False

            #Get the first "waiting" job
            for idx, cur_jobs in enumerate(alljobs):
                if(cur_jobs['status']=='processing'):
                    processing = True
                    print("ONE PROCESSING FOUND")
                    break
                if(cur_jobs['status']=='waiting'):
                    cur_job = cur_jobs
                    cur_idx = idx
                    print("ONE WAITING FOUND")
                    break;

            #print('CURRENT JOB')
            #print(str(cur_job))

            if(cur_job != 'X' and processing==False):

                print("FIND ONE")

                #Change Status of the job in the JSON
                data['jobs'][cur_idx]['status'] = 'processing' 
                with open(WAITING_JOBS, 'w') as outfile:
                    json.dump(data, outfile)

                print(str(cur_job))

                if(cur_jobs['name']=='timelapse'): 
                    print("GENERATE VID FOR CAM_ID " + cur_job['cam_id'])
                    video_path =  generate_timelapse(cur_job['cam_id'],cur_job['date'],cur_job['fps'],cur_job['dim'],cur_job['text_pos'],cur_job['wat_pos'],cur_job['extra_text'],0) 

                    # Update the JSON so we dont process the same vid twice
                    data['jobs'][0]['status'] = 'ready'
                    data['jobs'][0]['path']   = video_path
                    with open(WAITING_JOBS, 'w') as outfile:
                        json.dump(data, outfile)

        