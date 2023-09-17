import os
import time
import requests
import cv2
import json
import pandas as pd
import glob
import numpy as np
import argparse
import subprocess
import numpy as np

def check_running(progname, sec_grep = None):
   cmd = "ps -aux |grep \"" + progname + "\" | grep -v grep |wc -l"

   output = subprocess.check_output(cmd, shell=True).decode("utf-8")
   #print(cmd)
   print(output)
   output = int(output.replace("\n", ""))
   if int(output) > 0:
      return(output)
   else:
      return(0)

def compute_center(x, y, w, h):
    """Compute the center of a bounding box."""
    return x + w/2, y + h/2

def compute_direction(p1, p2):
    """Compute the direction between two points."""
    return np.arctan2(p2[1]-p1[1], p2[0]-p1[0])

def straight_path(xs, ys, ws, hs, tolerance=0.1):
    """
    Determine if the path followed by the centers of bounding boxes is straight.
    
    Parameters:
    - xs, ys, ws, hs: Arrays representing the bounding box for each frame.
    - tolerance: Allowed variation in direction to still be considered straight. In radians.
    
    Returns:
    - True if the path is straight, False otherwise.
    """
    
    # Compute centers of bounding boxes
    centers = [compute_center(x, y, w, h) for x, y, w, h in zip(xs, ys, ws, hs)]
    
    # Compute directions between consecutive centers
    directions = [compute_direction(centers[i], centers[i+1]) for i in range(len(centers)-1)]
    
    # Check if directions are consistent (within tolerance)
    min_dir, max_dir = min(directions), max(directions)
    print("DIRECTIONS:", directions)
    print(" MAX/MIN DIRECTION:", max_dir / min_dir)
    if max_dir - min_dir > tolerance:
        return False
    
    return True

def compute_distance(p1, p2):
    """Compute the Euclidean distance between two points."""
    return np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)

def analyze_distances(distances, threshold=1.1):
    """
    Analyze distances to detect significant variations.

    Parameters:
    - distances: List of distances between consecutive blob centers.
    - threshold: Allowed variation in distance to still be considered consistent.
                 For instance, a threshold of 1.1 means a 10% change is acceptable.

    Returns:
    - True if distances are consistent, False otherwise.
    """
    avg_distance = np.mean(distances)
    for dist in distances:
        if not (avg_distance / threshold <= dist <= avg_distance * threshold):
            return False
    return True

def meteor_path_analysis(xs, ys, ws, hs, distance_threshold=1.1, direction_tolerance=0.1):
    """
    Analyze the path followed by the centers of bounding boxes for consistency.

    Parameters:
    - xs, ys, ws, hs: Arrays representing the bounding box for each frame.
    - distance_threshold: Allowed variation in distance to still be considered consistent.
    - direction_tolerance: Allowed variation in direction to still be considered straight. In radians.

    Returns:
    - True if the path is consistent (both direction and distance), False otherwise.
    """

    # Compute centers of bounding boxes
    centers = [compute_center(x, y, w, h) for x, y, w, h in zip(xs, ys, ws, hs)]

    # Compute distances between consecutive centers
    distances = [compute_distance(centers[i], centers[i+1]) for i in range(len(centers)-1)]

    print(" DISTANCES:", distances)

    # Analyze distances for consistency
    if not analyze_distances(distances, threshold=distance_threshold):
        return False

    # Analyze directions for consistency
    if not straight_path(xs, ys, ws, hs, tolerance=direction_tolerance):
        return False

    return True


def load_json_file(json_file):
    try:
        with open(json_file, 'r') as file:
            data = json.load(file)
            return data 
    except FileNotFoundError:
        return {}

def save_json_file(json_file, json_data):
    with open(json_file, 'w') as file:
        json.dump(json_data, file)

def crop_training_image(image, xs,ys):
    image = cv2.resize(image, (1920, 1080))
    xs = np.array(xs)
    ys = np.array(ys)
    # Calculate the center of the ROI
    center_x = int(np.mean(xs))
    center_y = int(np.mean(ys))

    # Define the crop boundaries
    half_width = 100  # half of 200
    half_height = 100  # half of 200

    x_min = max(0, center_x - half_width)
    x_max = min(1920, center_x + half_width)
    y_min = max(0, center_y - half_height)
    y_max = min(1080, center_y + half_height)

    if x_min == 0:
        x_max = 200
    if y_min == 0:
        y_max = 200
    if x_max == 1920:
        x_min = 1720
    if y_max == 1080:
        y_min = 880

    # Crop the image
    cropped_image = image[y_min:y_max, x_min:x_max]
    return(cropped_image, [x_min,y_min,x_max,y_max])

def export_non_meteors():
    key = 0
    global ai_data
    nm_index = "/mnt/ams2/non_meteors_confirmed/all-reduced.txt"
    if os.path.exists(nm_index) is False:
    #if True:
       cmd = "find /mnt/ams2/non_meteors_confirmed/ |grep json |grep reduced > " + nm_index
       print(cmd)
       os.system(cmd)
    
    fp = open(nm_index)
    #meteor_id = 0
    csv_data = []
    
    #ai
    # get non-meteors
    rows = []
    for line in fp:
        rows.append(line.replace("\n", ""))
    c = 0
    next_val = 0
    if True:
        #for line in fp:
    
        while True:
            print("C / NEXT VAL:", c, next_val)
            c = c + next_val
            if c >= len(rows):
                rows = 0
                print("DONE DATA!")
                return(csv_data)
            line = rows[c]
    
            line = line.replace("\n", "")
            mfile = line.split("/")[-1].replace("-reduced.json", "")
            day = mfile[0:10]
            obs_id = line.split("/")[-1].replace("-reduced.json", "")
            meteor_id = station_id + "_" + line.split("/")[-1].replace("-reduced.json", "")
            if line not in train_files:
                train_files[line] = {}
                #meteor_id += 1
            data = load_json_file(line)
            if len(data['meteor_frame_data']) == 0:
                print("NO MFD")
                continue 
            first_fn = data['meteor_frame_data'][0][1]
            fmfile = "/mnt/ams2/non_meteors_confirmed/" + day + "/" + obs_id + "-stacked.jpg"
            roi_file = "/mnt/ams2/non_meteors_confirmed/" + day + "/" + obs_id + "-roi.jpg"
    
            fns = []
            xs = []
            ys = []
            ws = []
            hs = []
            ints = []
            azs = []
            els = []
            for row in data['meteor_frame_data']:
                (date, fn, x, y, w, h, intensity, ra, dec, az, el) = row
                csv_data.append((0, meteor_id, fn - first_fn, x, y, w, h, intensity))
                fns.append(fn)
                xs.append(x)
                ys.append(y)
                ws.append(w)
                hs.append(h)
                ints.append(ints)
                azs.append(azs)
                els.append(els)
            desc4 = round((len(xs) / 25),2)


            meteor_path_ok = meteor_path_analysis(xs, ys, ws, hs, distance_threshold=1.1, direction_tolerance=0.1)
            print("METEOR PATH OK:", meteor_path_ok)

            # don't repeat work that is already done!
            #if os.path.exists(out_file) is False and os.path.exists(fmfile):
            if os.path.exists(fmfile):
                image = cv2.imread(fmfile)
                input_video = fmfile.replace("-stacked.jpg", ".mp4")
                crop_img,roi = crop_training_image(image, xs,ys)
    
    
                clean_crop_img = crop_img.copy()
                cv2.imwrite(roi_file, clean_crop_img)
    
                url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(roi_file)
                #try:
                if obs_id not in ai_data:
                    try:
                        response = requests.get(url)
                        content = response.content.decode()
                        d = json.loads(content)
                        ai_data[obs_id] = d
                    except:
                        running = check_running("AIServer.py")
                        if running == 0:
                            os.system("/usr/bin/python3.6 AIServer.py  > /dev/null 2>&1 &")
                            time.sleep(60)
                            print("Sleep for 60 while the AI models load!")
                            continue
                else:
                    d = ai_data[obs_id]
                    print("AI already done for", obs_id)
                ai_data[obs_id]['xs'] = xs 
                ai_data[obs_id]['ys'] = ys 
                ai_data[obs_id]['ws'] = ws 
                ai_data[obs_id]['hs'] = hs 
                ai_data[obs_id]['ints'] = ints
                ai_data[obs_id]['azs'] = azs
                ai_data[obs_id]['els'] = els 
                ai_data[obs_id]['img'] = roi_file

                if True:
                    print("AI:", d.keys())
                    desc1 = str(round(d['meteor_yn'],1)) + "% Meteor " 
                    desc2 = str(round(d['fireball_yn'],1)) + "Fireball " 
                    desc3 = str(round(d['mc_class_conf'],1)) + "% " + " " +  d['mc_class']
    
                    if d['mc_class'] != 'meteor' and d['mc_class'] != "fireball" and (d['mc_class_conf'] >= d['meteor_yn'] and d['mc_class_conf'] >= d['fireball_yn']):
                        color = (0,0,255)
                        tag = 0
                        label = "non"
                        anti_label = "meteors"
                    elif d['meteor_yn'] > 55 :
                        color = (0,255,0)
                        tag = 1
                        label = "meteors"
                        anti_label = "non"
                    elif d['fireball_yn'] > 55 :
                        color = (0,255,0)
                        color = (0,255,0)
                        tag = 1
                        label = "meteors"
                        anti_label = "non"
                    else:
                        color = (0,0,255)
                        tag = 0  
                        label = "non"
                        anti_label = "meteors"
    
                    out_file = EXPORT_DIR + label + "/" + station_id + "_" + mfile.split("/")[-1] + ".jpg"
                    anti_out_file = EXPORT_DIR + anti_label + "/" + station_id + "_" + mfile.split("/")[-1] + ".jpg"
    
                    output_video = EXPORT_DIR + label + "/" + station_id + "_" + mfile.split("/")[-1] + "-ROI.mp4"
                    if os.path.exists(output_video) is False :
                        width = roi[2] - roi[0] 
                        height = roi[3] - roi[1] 
                        x = roi[0]
                        y = roi[1]
                        ffcmd = """ffmpeg -i {:s} -vf "scale=-1:1080,crop={:s}:{:s}:{:s}:{:s}" "{:s}" """.format(input_video,str(width), str(height), str(x), str(y), output_video) 
                        print(ffcmd)
                        os.system(ffcmd)
    
                    if os.path.exists(out_file) or os.path.exists(anti_out_file):
                        print("skip. Already saved learning image", out_file)
                        next_val = 1
                        continue
    
                    cv2.rectangle(crop_img, (0,0), (crop_img.shape[1]-1, crop_img.shape[0]-1) , color, 2)
                    cv2.putText(crop_img, desc1,  (5,10), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
                    cv2.putText(crop_img, desc2,  (5,25), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
                    cv2.putText(crop_img, desc3,  (5,40), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
                    cv2.putText(crop_img, str(desc4) + " sec",  (5,50), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
    
                    if args.preview is True: 
                        cv2.imshow('pepe', crop_img)
                        key = cv2.waitKey(0)
                        print("KEY", key)
                    next_val = 1
                    if key == 112 : 
                        # p = play
                        print("PLAY")
                        cmd = "mpv " + output_video
                        os.system(cmd)
                    if key == 32 : #or key == 109:
                        # space or M
                        save = True
                        label = "meteors"
                        tag = 1
                        color = 0,255,0
                        if args.preview is True: 
                            cv2.rectangle(crop_img, (roi[0], roi[3]), (roi[2], roi[1]), color, 1)
                            cv2.imshow('pepe', crop_img)
                            xxx = cv2.waitKey(100)
    
                        #if os.path.exists(met_outfile) is True:
                        #    os.system("rm " + nonmet_outfile)
                    elif key == 120:
                        # x
                        save = True
                        label = "non"
                        tag = 0
                        #if os.path.exists(met_outfile) is True:
                        #    os.system("rm " + met_outfile)
                        color = 255,0,0
                        if args.preview is True: 
                            cv2.rectangle(crop_img, (roi[0], roi[3]), (roi[2], roi[1]), color, 1)
                            cv2.imshow('pepe', crop_img)
                            xxx = cv2.waitKey(100)
                    elif key == 27:
                       # escape
                       #self.save_and_exit(date)
                       print("QUIT!")
                       save_json_file(ai_data_file, ai_data)
                       print("SAVED:", ai_data_file)
                       exit()
                    elif key == 83:
                        # right arrow
                        save=False
                        next_val = +1
                    elif key == 81:
                        # left arrow
                        save=False
                        next_val = -1
    
                    out_file = EXPORT_DIR + label + "/" + station_id + "_" + mfile.split("/")[-1] + ".jpg"
                    print("Saved", out_file)
                    cv2.imwrite(out_file, clean_crop_img)
                    if os.path.exists(anti_out_file):
                        os.system("rm " + anti_out_file)
    
            if len(csv_data) % 100 == 0:
                print(len(csv_data), "non meteor learning objects so far")
    
    # Now get confirm meteors
    return(csv_data)


def export_meteors(csv_data):
    global ai_data 
    key = 0
    total_no = len(csv_data)
    total_no = 100
    print(total_no, "Non meteors so far...")
    
    mdir = "/mnt/ams2/meteors/"
    mdirs = os.listdir(mdir)
    for date in sorted(mdirs, reverse=True):
        if os.path.isdir(mdir + date) is True and date[0] == "2":
            mfiles = glob.glob(mdir + "/" + date + "/*-reduced.json")
            print("Day:", date, len(mfiles)) 
            for line in mfiles:
                mfile = line.split("/")[-1].replace("-reduced.json", "")
                img_file = line.replace("-reduced.json", "-stacked.jpg")
                roi_file = line.replace("-reduced.json", "-roi.jpg")
                if os.path.exists(img_file):
                    img = cv2.imread(img_file)
                meteor_id = station_id + "_" + line.split("/")[-1].replace("-reduced.json", "")
                obs_id = meteor_id
                #line.split("/")[-1].replace("-reduced.json", "")
                if line not in train_files:
                    train_files[line] = {}
    
                data = load_json_file(line)
                if len(data['meteor_frame_data']) == 0:
                    print("Skip no MFD")
                    continue 
                first_fn = data['meteor_frame_data'][0][1]
                xs = []
                ys = []
                ws = []
                hs  = []
                ints = []
                azs = []
                els = []
                for row in data['meteor_frame_data']:
                    (date, fn, x, y, w, h, intensity, ra, dec, az, el) = row
                    xs.append(x)
                    ys.append(y)
                    ws.append(w)
                    hs.append(h)
                    ints.append(ints)
                    azs.append(azs)
                    els.append(els)
                    csv_data.append((1, meteor_id, fn - first_fn, x, y, w, h, intensity))
                meteor_path_ok = meteor_path_analysis(xs, ys, ws, hs, distance_threshold=1.1, direction_tolerance=0.1)
                print("METEOR PATH OK:", meteor_path_ok)
    
                crop_img,roi = crop_training_image(img, xs,ys)
                print("ROI FILE:", roi_file)
                cv2.imwrite(roi_file, crop_img)
                if len(csv_data) % 100 == 0:
                    print(len(csv_data), "non meteor learning objects so far")
    
                url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(roi_file)
                #try:
                if obs_id not in ai_data:
                    response = requests.get(url)
                    content = response.content.decode()
                    d = json.loads(content)
                else:
                    d = ai_data[obs_id]
                if obs_id not in ai_data:
                    ai_data[obs_id] = d
                ai_data[obs_id]['xs'] = xs 
                ai_data[obs_id]['ys'] = ys 
                ai_data[obs_id]['ws'] = ws 
                ai_data[obs_id]['hs'] = hs 
                ai_data[obs_id]['ints'] = ints
                ai_data[obs_id]['azs'] = azs
                ai_data[obs_id]['els'] = els 
                ai_data[obs_id]['img'] = roi_file


                if True:
                    print(d)
                    desc1 = str(round(d['meteor_yn'],1)) + "% Meteor "
                    desc2 = str(round(d['fireball_yn'],1)) + "Fireball "
                    desc3 = str(round(d['mc_class_conf'],1)) + "% " + " " +  d['mc_class']
    
                    if d['mc_class'] != 'meteor' and d['mc_class'] != "fireball" and (d['mc_class_conf'] >= d['meteor_yn'] and d['mc_class_conf'] >= d['fireball_yn']):
                        color = (0,0,255)
                        tag = 0
                        label = "non"
                    elif d['meteor_yn'] > 55 :
                        color = (0,255,0)
                        tag = 1
                        label = "meteors"
                    elif d['fireball_yn'] > 55 :
                        color = (0,255,0)
                        color = (0,255,0)
                        tag = 1
                        label = "meteors"
                    else:
                        color = (0,0,255)
                        tag = 0
                        label = "non"
    
                    out_file = EXPORT_DIR + label + "/" + station_id + "_" + mfile.split("/")[-1] + ".jpg"
                    print("SAVED:", out_file)
                    cv2.imwrite(out_file, crop_img)

    
                    cv2.rectangle(crop_img, (0,0), (crop_img.shape[1]-1, crop_img.shape[0]-1) , color, 2)
                    cv2.putText(crop_img, desc1,  (5,10), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
                    cv2.putText(crop_img, desc2,  (5,25), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)
                    cv2.putText(crop_img, desc3,  (5,40), cv2.FONT_HERSHEY_SIMPLEX, .5, (255,255,255), 1)

                    if args.preview is True:
                        cv2.imshow('pepe', crop_img)
                        key = cv2.waitKey(0)

    
    df = pd.DataFrame(csv_data, columns=['label', 'meteor_id', 'frame_number', 'x', 'y', 'w', 'h', 'intensity'])
    df.to_csv(training_csv_file, index=False)
    print("saved training file with", len(csv_data), "items")
    save_json_file(ai_data_file, ai_data)
    print("saved ai data file with", len(ai_data.keys()), "items")
    print("saved ai data file ", ai_data_file)
    os.system("/usr/bin/python3 GroupData.py")
    return(csv_data)

if __name__ == "__main__":

    running = check_running("AIServer.py")
    if running == 0:
        os.system("/usr/bin/python3.6 AIServer.py  > /dev/null 2>&1 &")
        print("Sleep for 60 while the AI models load!")
        time.sleep(60)

    parser = argparse.ArgumentParser(description="Script Description")

    # Define the command-line arguments
    parser.add_argument("--preview", type=bool, required=False, help="Interactive Preview.")

    # Additional arguments can be added similarly

    args = parser.parse_args()

    json_conf = load_json_file("../conf/as6.json")
    station_id = json_conf['site']['ams_id']



    EXPORT_DIR = "/mnt/ams2/LEARNING/data/torch/"
    ai_data_file = EXPORT_DIR + station_id + "_ai_data.json"
    if os.path.exists(ai_data_file) :
        print("load:", ai_data_file)
        with open(ai_data_file, 'r') as file:
            ai_data = json.load(file)
    else:
        ai_data = {}

    if os.path.exists(EXPORT_DIR + "non/") is False:
        os.makedirs(EXPORT_DIR + "non/")
    if os.path.exists(EXPORT_DIR + "meteors/") is False:
        os.makedirs(EXPORT_DIR + "meteors/")

    # non meteor objs
    training_csv_file = "meteor_yn_training.csv"
    train_files = {}
    csv_data = []
    #csv_data = export_non_meteors()
    csv_data = export_meteors(csv_data)
    save_json_file(ai_data_file, ai_data)
    print("SAVED:", ai_data_file)
