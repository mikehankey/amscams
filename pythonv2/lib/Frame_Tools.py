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
 

# Add a new frame or update an existing frame
# based on hd_x & hd_y defined by the user 
# though the "select meteor" interface
def add_frame(json_conf, sd_video_file, fr_id, hd_x, hd_y, w=5, h=5): 

    # Load the JSON from the video path
    mrf = sd_video_file.replace(".mp4", "-reduced.json")
    mr = load_json_file(mrf)

    # Load existing data
    metframes = mr['metframes']
    metconf = mr['metconf']
    
    # Does the frame already exist in metframes?
    if fr_id in metframes:

        print("HERE")
        print(mrf)

        #We erase the old data  
        #So we can replace the frame 
        #mr['metframes'][fr_id]['hd_x'] = int(hd_x)
        #mr['metframes'][fr_id]['hd_y'] = int(hd_y)       

        #JSON Update
        #save_json_file(mrf, mr)

        #Run to update all info, create thumb, etc.
        #os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/frame_update.txt")
  
    else:

        # it is a new frame
        metframes[fr_id] = {}
        metframes[fr_id]['fn'] = fr_id 
        metframes[fr_id]['hd_x'] = hd_x
        metframes[fr_id]['hd_y'] = hd_y
        metframes[fr_id]['w'] = w
        metframes[fr_id]['h'] = h
        metframes[fr_id]['sd_x'] = hd_x*(HD_W/SD_W)
        metframes[fr_id]['sd_y'] = hd_y*(HD_H/SD_H)
        metframes[fr_id]['sd_w'] = 6
        metframes[fr_id]['sd_h'] = 6
        metframes[fr_id]['sd_cx'] = 0 #hd_x?
        metframes[fr_id]['sd_cy'] = 0 #hd_y?
        metframes[fr_id]['ra'] = 0
        metframes[fr_id]['dec'] = 0
        metframes[fr_id]['az'] = 0
        metframes[fr_id]['el'] = 0
        metframes[fr_id]['max_px'] = 0


        x1,y1,x2,y2 = bound_cnt(hd_x,hd_y,HD_W,HD_H,6)
        frames = load_video_frames(sd_video_file, json_conf) 
        frame = frames[int(fr_id)]
        frame = cv2.resize(frame, (1920,1080)) 
        
        cnt_img = frame[y1:y2,x1:x2]
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img) 

        print("MIN VAL ", min_val)
        print("max_val ", max_val)
        print("min_locL ", min_loc)
        print("max_locL ", max_loc)

        metframes[new_fn]['hd_x'] = ax_loc[0] + x1
        metframes[new_fn]['hd_y'] = max_loc[1] + y1
        metframes[new_fn]['est_x'] = hd_x
        metframes[new_fn]['est_y'] = hd_y 

        mr['metframes'] = metframes
        save_json_file(mrf, mr)

        print(mr)

        #Create Frame Thumb
        
        os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/frame_update.txt")
        os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/frame_update.txt")

        
        #mr = load_json_file(mrf )
        #resp = {}
        #resp['msg'] = "new frame added."
        #resp['newframe'] = mr['metframes'][fr_id] 
        #print(json.dumps(resp))
        #os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/frame_update.txt")

        #x1,y1,x2,y2 = bound_cnt(hd_x,hd_y,1920,1080,50)
        #frames = load_video_frames(sd_video_file, json_conf)
        #frame = frames[int(fr_id)]
        #frame = cv2.resize(frame, (1920,1080)) 

        #cnt_img = frame[y1:y2,x1:x2]
        #min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(cnt_img)
        #hd_x = max_loc[0] + x1  
        #hd_y = max_loc[1] + y1  
        #metframes[fr_id]['hd_x'] = hd_x
        #metframes[fr_id]['hd_y'] = hd_y 
        #metframes[fr_id]['est_x'] = est_x
        #metframes[fr_id]['est_y'] = est_y 
 
 


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
 