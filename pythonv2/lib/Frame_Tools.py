import json
import os 
import subprocess 
import cgitb
import glob
import cv2
from os.path import isfile, join, exists
from lib.FileIO import load_json_file, save_json_file
from lib.UtilLib import bound_cnt
from lib.VideoLib import load_video_frames

TMP_FRAME_FOLDER = '/mnt/ams2/TMP'
FRAME_THUMB_W = 50  #In pixel
FRAME_THUMB_H = 50 

# SD Frames
SD_W = 704
SD_H = 576

# HD Frames
HD_W = 1920
HD_H = 1080
 

def update_frame(sd_video_file,fn,new_x,new_y):
     #Temporary but necessary
    try:
        mrf = sd_video_file.replace(".mp4", "-reduced.json")
        mr = load_json_file(mrf)   
        mr['metframes'][fn]['hd_x'] = int(new_x)
        mr['metframes'][fn]['hd_y'] = int(new_y)
    except Exception: 
        os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py dm " + sd_video_file + "> /mnt/ams2/tmp/rrr.txt")
        mrf = sd_video_file.replace(".mp4", "-reduced.json")
        mr = load_json_file(mrf)   
        mr['metframes'][fn]['hd_x'] = int(new_x)
        mr['metframes'][fn]['hd_y'] = int(new_y)

    mr['metframes'][fn]['hd_x'] = int(new_x)
    mr['metframes'][fn]['hd_y'] = int(new_y)
    save_json_file(mrf, mr)

    # this will make new thumbs
    # this will update all values (ra,dec etc) and make new thumbs from new point. 
    resp = {}
    resp['msg'] = "new frame added."
    resp['new_frame'] = mr['metframes'][fn]
    os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt")
    print(json.dumps(resp))



# Add a new frame or update an existing frame
# based on hd_x & hd_y defined by the user 
# though the "select meteor" interface
def add_frame(json_conf, sd_video_file, fr_id, hd_x, hd_y): 

    # Load the JSON from the video path
    mrf = sd_video_file.replace(".mp4", "-reduced.json")
    mr = load_json_file(mrf)

    # Load existing data
    metframes = mr['metframes']
    metconf = mr['metconf']

    # Does the frame, already exist?
    if fr_id in metframes:

        print('FRAME ALREADY EXISTS => WE UPDATE')
        update_frame(sd_video_file,fn,hd_x,hd_y)

    else:
        # First frame info
        first_frame = int(mr['metconf']['sd_fns'][0])
        first_x = int(mr['metconf']['sd_xs'][0]) 

        # Previous & Next frame ID
        prev_fn = str(int(new_fn) - 1)
        next_fn = str(int(new_fn) + 1)

        # If we have a frame before
        if prev_fn in metframes:

            # frame exists before make est from prev frame info
            last_x = metframes[prev_fn]['sd_cx']
            last_y = metframes[prev_fn]['sd_cy']
            fcc = (int(new_fn) - int(first_frame)) 
            est_x = int(first_x) + (metconf['x_dir_mod'] * (metconf['sd_seg_len']*fcc)) + (metconf['sd_acl_poly'] * (fcc**2))
            est_y = (metconf['sd_m']*est_x)+metconf['sd_b']
            sd_cx = last_x
            sd_cy = last_y
            est_x = int(sd_cx *HD_W/SD_W)
            est_y = int(sd_cy *HD_H/SD_H)

        # We have a frame after
        elif str(next_fn) in metframes:
            # this frame exists before any others so need to add est in reverse. 
            last_x = metframes[next_fn]['sd_cx']
            last_y = metframes[next_fn]['sd_cy']
            est_x = int(last_x) + (-1*metconf['x_dir_mod'] * (metconf['sd_seg_len']*1)) + (metconf['sd_acl_poly'] * 1)
            est_y = (metconf['sd_m']*est_x)+metconf['sd_b']
            sd_cx = est_x
            sd_cy = est_y
            sd_cx = last_x
            sd_cy = last_y
            est_x = int(sd_cx * HD_W/SD_W)
            est_y = int(sd_cy * HD_H/SD_H)

        elif:
            print('IMPOSSIBLE TO GENERATE THE FRAME')

        # We got the info
        metframes[new_fn] = {}
        metframes[new_fn]['fn'] = new_fn 
        metframes[new_fn]['hd_x'] = hd_x
        metframes[new_fn]['hd_y'] = hd_y
        metframes[new_fn]['w'] = 5
        metframes[new_fn]['h'] = 5
        metframes[new_fn]['sd_x'] = sd_cx
        metframes[new_fn]['sd_y'] = sd_cy
        metframes[new_fn]['sd_w'] = 6
        metframes[new_fn]['sd_h'] = 6
        metframes[new_fn]['sd_cx'] = sd_cx
        metframes[new_fn]['sd_cy'] = sd_cy
        metframes[new_fn]['ra'] = 0
        metframes[new_fn]['dec'] = 0
        metframes[new_fn]['az'] = 0
        metframes[new_fn]['el'] = 0
        metframes[new_fn]['max_px'] = 0
    
        x1,y1,x2,y2 = bound_cnt(est_x,est_y,1920,1080,6)
        frames = load_video_frames(sd_video_file, json_conf)
        ifn = int(new_fn)
        frame = frames[ifn]
        frame = cv2.resize(frame, (1920,1080)) 
        
        cnt_img = frame[y1:y2,x1:x2]
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
        hd_x = max_loc[0] + x1  
        hd_y = max_loc[1] + y1  
        metframes[new_fn]['hd_x'] = hd_x
        metframes[new_fn]['hd_y'] = hd_y 
        metframes[new_fn]['est_x'] = est_x
        metframes[new_fn]['est_y'] = est_y 


 
 


# Create & Return a cropped frame image (thumb)
def crop_frame(fr_id,src,x,y):
    cgitb.enable()
    w=FRAME_THUMB_W
    h=FRAME_THUMB_W

    # Name & Path of the frame
    frame_name = src.split(".")[0] 
    s = frame_name.rfind('_')
    frame_name = frame_name[:s]+ "-frm" + str(fr_id) + ".png"
  
    try:
        cmd = "ffmpeg -y -hide_banner -loglevel panic -i " + src + " -vf \"crop="+str(w)+":"+str(h)+":"+str(x)+":"+str(y)+"\" " + frame_name
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")      
        return json.dumps({'fr':frame_name})
    except:
        return json.dumps({'res':'false'})


# Return a given frame for a given vid
# (create all the frames in TMP_FRAME_FOLDER if they don't exists)
def get_frame(fr_id,sd_vid):

    #cgitb.enable()

    #Get the eventual file name 
    filename = sd_vid.split("/")[-1]
    cur_name = os.path.splitext(filename)[0];
    name = cur_name + '_' + str(fr_id) +  '.png'

    #Is the TMP_FRAME_FOLDER folder exists? 
    if not os.path.exists(TMP_FRAME_FOLDER):
        os.makedirs(TMP_FRAME_FOLDER)
    
    #First we test if the frame already exist
    if os.path.isfile(name):
        return json.dumps({'full_fr': name, 'id': fr_id})
    else:
        #We need to generate all the frames in TMP_FRAME_FOLDER

        #First we delete all from TMP_FRAME_FOLDER
        filelist = glob.glob(os.path.join(TMP_FRAME_FOLDER,'.png'))
        for f in filelist: 
            os.remove(f)

        #We generate all the frames
        cmd =  'ffmpeg -y -hide_banner -loglevel panic -i '+ sd_vid + ' -s 1280x720  ' + TMP_FRAME_FOLDER + '/' + cur_name + '_%d.png ' 
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")    
        return json.dumps({'full_fr':TMP_FRAME_FOLDER + '/' + cur_name + '_' + fr_id + '.png', 'id': fr_id})
 