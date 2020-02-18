import json
import os 
import subprocess 
import cgitb
import glob 
import cv2
import sys
import numpy as np

from os.path import isfile, join, exists
from lib.FileIO import load_json_file, save_json_file
from lib.UtilLib import bound_cnt
from lib.VideoLib import load_video_frames 
from lib.Sync_HD_SD_videos import get_masks
from lib.VIDEO_VARS import HD_H, HD_W, SD_W, SD_H

TMP_FRAME_FOLDER = '/mnt/ams2/TMP'
FRAME_THUMB_W = 50  #In pixel
FRAME_THUMB_H = 50 


# Update position of multiple frames
def update_multiple_frames_ajax(json_conf, form):
    cgitb.enable()  
    sd_video_file = form.getvalue("sd_video_file")
    all_frames_to_update = form.getvalue("frames") 
    
    #Why? In case of...
    #os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py dm " + sd_video_file + " > /mnt/ams2/tmp/rrr.txt")
    all_frames_to_update = json.loads(all_frames_to_update)
    mrf = sd_video_file.replace(".mp4", "-reduced.json")
 
    mr = load_json_file(mrf)

    #We update all the frames
    for val in all_frames_to_update: 
        fn =  int(val['fn'])
        #print("Fn " + str(fn)) 
        #print('VAL X ' + str(int(val['x'])))
        #print('VAL Y ' + str(int(val['y']))) 
        mr['metframes'][str(fn)]['hd_x'] = int(val['x'])
        mr['metframes'][str(fn)]['hd_y'] = int(val['y'])

    
    save_json_file(mrf, mr)
   
    resp = {}
    resp['msg'] = "frames updated."  
    os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + " > /mnt/ams2/tmp/rrr.txt") 
    os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + " > /mnt/ams2/tmp/rrr.txt") 
    print(json.dumps(resp))
 

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

    # this will update all values (ra,dec etc) and make new thumbs from new point. 
    os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt") 


# Add a new frame or update an existing frame
# based on hd_x & hd_y defined by the user 
# though the "select meteor" interface
def real_add_frame(json_conf, sd_video_file, fr_id, hd_x, hd_y): 
     
    # DEBUG 
    cgitb.enable() 

    # Load the JSON from the video path
    mrf = sd_video_file.replace(".mp4", "-reduced.json")
    mr = load_json_file(mrf)
    #print(mr)
    #exit()

    # Load existing data
    metframes = mr['metframes']
    metconf = mr['metconf']

    # Does the frame, already exist?
    if fr_id in metframes:
        update_frame(sd_video_file,fr_id,hd_x,hd_y) 
        print(json.dumps({'msg': "frame  #"+ fr_id +" updated.", 'newframe': mr['metframes'][fr_id]}))
        return

    else: 
         
        # Create frame with some missing info that will come from reducer3
        metframes[fr_id] = {}
        metframes[fr_id]['fn'] = fr_id 
        metframes[fr_id]['hd_x'] = int(hd_x)
        metframes[fr_id]['hd_y'] = int(hd_y)
        metframes[fr_id]['w']    = 5 #????
        metframes[fr_id]['h']    = 5 #????
        metframes[fr_id]['sd_x'] = int(int(hd_x) * SD_W/HD_W)
        metframes[fr_id]['sd_y'] = int(int(hd_y) * SD_H/HD_H)
        metframes[fr_id]['sd_w'] = 6 #????
        metframes[fr_id]['sd_h'] = 6 #????
        metframes[fr_id]['sd_cx'] = metframes[fr_id]['sd_x'] + metframes[fr_id]['sd_w']/2
        metframes[fr_id]['sd_cy'] = metframes[fr_id]['sd_y'] + metframes[fr_id]['sd_h']/2
        metframes[fr_id]['ra']   = 0
        metframes[fr_id]['dec']  = 0
        metframes[fr_id]['az'] = 0
        metframes[fr_id]['el'] = 0
        metframes[fr_id]['max_px'] = 0 
        metframes[fr_id]['est_x'] = 0 
        metframes[fr_id]['est_y'] = 0 
  

        mr['metframes'] = metframes
        save_json_file(mrf, mr)
        mr = load_json_file(mrf)
        os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py mfd " + mrf + "> /mnt/ams2/tmp/rrr.txt")
        
        # We need to do it twice
        mr = load_json_file(mrf)
        os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt")

        os.system("cd /home/ams/amscams/pythonv2/; ./reducer3.py cm " + mrf + "> /mnt/ams2/tmp/rrr.txt")
 
        print(json.dumps({'msg': "new frame added.", 'newframe':metframes[fr_id]}))
        return


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
def get_a_frame(fr_id,sd_vid):

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

        #We generate all the frames at 1280x720 as they'll be used in the front-end
        cmd =  'ffmpeg -y -hide_banner -loglevel panic -i '+ sd_vid + ' -s 1280x720 ' + TMP_FRAME_FOLDER + '/' + cur_name + '_%d.png ' 
        output = subprocess.check_output(cmd, shell=True).decode("utf-8")    
        return json.dumps({'full_fr':TMP_FRAME_FOLDER + '/' + cur_name + '_' + fr_id + '.png', 'id': fr_id})
 



# Load Frames and returns (previously in Mike's flex-detect)
def load_frames_fast(input_file, analysed_input_file, limit=0, mask=0,crop=(),color=0,resize=[]):
   
   cgitb.enable()

   cap = cv2.VideoCapture(input_file)
   masks = None
   last_frame = None
   last_last_frame = None

   masks = get_masks(analysed_input_file['cam_id'],1)
   if "crop" in input_file:
      masks = None
   
   color_frames = []
   frames = []
   subframes = []
   sum_vals = []
   max_vals = []
   frame_count = 0
   go = 1
   while go == 1:
      if True :
         _ , frame = cap.read()
         if frame is None:
            if frame_count <= 5 :
               cap.release()
               return(frames,color_frames,subframes,sum_vals,max_vals)
            else:
               go = 0
         else:
            if color == 1:
               color_frames.append(frame)
            if limit != 0 and frame_count > limit:
               cap.release()
               return(frames)
            if len(frame.shape) == 3 :
               frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            if mask == 1 and frame is not None:
               if frame.shape[0] == HD_H:
                  hd = 1
               else:
                  hd = 0
               masks = get_masks(cam, hd)
               frame = mask_frame(frame, [], masks, 5)

            if last_frame is not None:
               subframe = cv2.subtract(frame, last_frame) 
               sum_val =cv2.sumElems(subframe)[0]
  
               if sum_val > 1000 and last_last_frame is not None:
                  subframe = cv2.subtract(subframe, last_last_frame)
                  sum_val =cv2.sumElems(subframe)[0]
               subframes.append(subframe)


               if sum_val > 100:
                  min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
               else:
                  max_val = 0
               if frame_count < 5:
                  sum_val = 0
                  max_val = 0
               sum_vals.append(sum_val)
               max_vals.append(max_val)

            if len(crop) == 4:
               ih,iw = frame.shape
               x1,y1,x2,y2 = crop
               x1 = x1 - 25
               y1 = y1 - 25
               x2 = x2 + 25
               y2 = y2 + 25
               if x1 < 0:
                  x1 = 0
               if y1 < 0:
                  y1 = 0
               if x1 > iw -1:
                  x1 = iw -1
               if y1 > ih -1:
                  y1 = ih -1 
               crop_frame = frame[y1:y2,x1:x2]
               frame = crop_frame
            if len(resize) == 2:
               frame = cv2.resize(frame, (resize[0],resize[1]))
       
            frames.append(frame)
            if last_frame is not None:
               last_last_frame = last_frame
            last_frame = frame
      frame_count = frame_count + 1
   cap.release()
   if len(crop) == 4:
      return(frames,x1,y1)
   else:
      return(frames, color_frames, subframes, sum_vals, max_vals)


def fast_check_events(sum_vals, max_vals, subframes):
   print("Fast check events.")
   events = []
   event = []
   event_info = []
   events_info = []
   cm = 0
   nomo = 0
   i = 0
   #med_sum = np.median(sum_vals[0:10])
   #med_max = np.median(max_vals[0:10])
   med_sum = np.median(sum_vals)
   med_max = np.median(max_vals)
   median_frame = cv2.convertScaleAbs(np.median(np.array(subframes[0:25]), axis=0))

   if subframes[0].shape[1] == 1920:
      hd = 1
      sd_multi = 1
   else:
      hd = 0
      sd_multi = 1920 / subframes[0].shape[1]

   for sum_val in sum_vals:
      
      #max_val = max_vals[i]
      subframe = subframes[i]
      #subframe = cv2.subtract(subframe, median_frame)
      min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
      #print(i, med_sum, med_max, sum_val , max_val)
      if sum_val > med_sum * 2 or max_val > med_max * 2:
         min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(subframe)
         desc = str(i)
        
         if max_val > 10:
            #cv2.putText(subframe, str(desc),  (10,10), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 255, 255), 1)
            event_info.append((sum_val, max_val, mx, my))
            event.append(i)
            cm = cm + 1
            nomo = 0
         else:
            nomo = nomo + 1
      else:
         nomo = nomo + 1
      if cm > 2 and nomo > 5:
         events.append(event)
         events_info.append(event_info)
         event = []
         event_info = []
         cm = 0
      elif nomo > 5:
         event = []
         event_info = []
         cm = 0

      if show == 1:
         cv2.circle(subframe,(mx,my), 10, (255,0,0), 1)
         cv2.imshow('pepe', subframe)
         cv2.waitKey(70)

      i = i + 1

   if show == 1:
      cv2.destroyWindow('pepe')

   if len(event) >= 3:
      events.append(event)
      events_info.append(event_info)

   print("TOTAL EVENTS:", len(events))
   filtered_events = []
   filtered_info = []
   i = 0
   for ev in events:
      max_cm = calc_cm_for_event(ev)
      if max_cm >= 2:
         filtered_events.append(ev)
         filtered_info.append(events_info[i])
      else:
         print("FILTERED:", max_cm, ev)
         print("FILTERED:", events_info[i])
      i = i + 1
   print("FILTERED EVENTS:", len(filtered_events))
   events = filtered_events
   events_info = filtered_info

   i = 0
   objects = {}
   for event in events:
      ev_z = event[0]
      object = None
      fc = 0
      for evi in events_info[i]:
         sv, mv, mx, my = evi
         fn = event[fc]
         object, objects = find_object(objects, fn,mx, my, 5, 5, mv, hd, sd_multi)
         #print("OBJECT:", fn, object, objects[object])
         #if 500 <= ev_z <= 700:
         fc = fc + 1
      i = i + 1

   for obj in objects:
      object = objects[obj] 
      objects[obj] = analyze_object_final(object, hd=0, sd_multi=1)

   pos_meteors = {}
   mc = 1
   for object in objects:
      if objects[object]['report']['meteor_yn'] == "Y":
         pos_meteors[mc] = objects[object]
         mc = mc + 1

   return(events, pos_meteors)