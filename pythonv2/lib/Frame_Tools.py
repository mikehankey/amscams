import json
import os 
import subprocess 
import cgitb
from os.path import isfile, join, exists

TMP_FRAME_FOLDER = '/mnt/ams2/TMP'

def get_frame(fr_id,sd_vid):

    cgitb.enable()

    #Get the eventual file name 
    filename = sd_vid.split("/")[-1]
    cur_name = os.path.splitext(filename)[0];
    name = cur_name + '_' + str(fr_id) +  '.png'

    #Is the TMP_FRAME_FOLDER folder exists? 
    if not os.path.exists(TMP_FRAME_FOLDER):
        os.makedirs(TMP_FRAME_FOLDER)
    
    #First we test if the frame already exist
    if os.path.isfile(name):
        return {'full_fr': name, 'id': fr_id}
    else:
        #We need to generate all the frames in TMP_FRAME_FOLDER
        cmd =  'ffmpeg -y -hide_banner -loglevel panic -i '+ sd_vid + '  ' + TMP_FRAME_FOLDER + '/' + cur_name + '_%04d.png ' 
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")    
        return {'full_fr':TMP_FRAME_FOLDER + '/' + cur_name + '_' + fr_id + '.png', 'id': fr_id}
