import json
import os 
import subprocess 
import cgitb
import glob
from os.path import isfile, join, exists
from lib.FileIO import load_json_file, save_json_file

TMP_FRAME_FOLDER = '/mnt/ams2/TMP'
FRAME_THUMB_W = 50
FRAME_THUMB_H = 50

HDM_X = 2.7272727272727272
HDM_Y = 1.875

# Add a new frame or update an existing frame
# based on hd_x & hd_y defined by the user 
# though the "select meteor" interface
def add_frame(json_conf, sd_video_file, fr_id, hd_x, hd_y, w=50, h=50): 

    # Load the JSON from the video path
    mrf = sd_video_file.replace(".mp4", "-reduced.json")
    mr = load_json_file(mrf)

    # Load existing data
    metframes = mr['metframes']
    metconf = mr['metconf']
    
    # Does the frame already exist in metframes?
    if fr_id in metframes:

        #We erase the old data  
        #So we can replace the frame 
        try: 
            mr['metframes'][fr_id]['hd_x'] = int(hd_x)
            mr['metframes'][fr_id]['hd_y'] = int(hd_y)
        except Exception: 
            os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py dm " + sd_video_file + "> /mnt/ams2/tmp/rrr.txt")
            mrf = sd_video_file.replace(".mp4", "-reduced.json")
            mr = load_json_file(mrf)   
            mr['metframes'][fn]['hd_x'] = int(new_x)
            mr['metframes'][fn]['hd_y'] = int(new_y)

        #JSON Update
        save_json_file(mrf, mr)
        print('FRAME UPDATED')

        else:
            print('THE FRAME ALREADY EXISTS - PASS NEW X & Y IF YOU WANT TO UPDATE')

    
    else:

        # it is a new frame
        metframes[fr_id] = {
            'fn':   fr_id,
            'hd_x': hd_x,
            'hd_y': hd_y,
            'w':    w,
            'h':    h,
            'sd_x': hd_x #???
            'sd_y': hd_y #???
            'sd_w': w,  #???
            'sd_h': h, #???
            'sd_cx': hd_x #???
            'sd_cy': hd_y #???
            'ra':0,
            'dec':0,
            'az':0,
            'el':0,
            'max_px':0}
            
        print(metframes[fr_id])

    # Generate new thumb and other stuff
    #os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/frame_update.txt")
 


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
 