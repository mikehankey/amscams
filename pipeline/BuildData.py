import os
import cv2
import json
import pandas as pd
import glob


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

json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

# non meteor objs
training_csv_file = "meteor_yn_training.csv"
train_files = {}

nm_index = "/mnt/ams2/non_meteors_confirmed/all-reduced.txt"
if os.path.exists(nm_index) is False:
#if True:
   cmd = "find /mnt/ams2/non_meteors_confirmed/ |grep json |grep reduced > " + nm_index
   print(cmd)
   os.system(cmd)

fp = open(nm_index)
#meteor_id = 0
csv_data = []

# get non-meteors
if True:
    for line in fp:

        line = line.replace("\n", "")
        meteor_id = station_id + "_" + line.split("/")[-1].replace("-reduced.json", "")
        if line not in train_files:
            train_files[line] = {}
            #meteor_id += 1
        data = load_json_file(line)
        if len(data['meteor_frame_data']) == 0:
            continue 
        first_fn = data['meteor_frame_data'][0][1]
        for row in data['meteor_frame_data']:
            (date, fn, x, y, w, h, intensity, ra, dec, az, el) = row
            csv_data.append((0, meteor_id, fn - first_fn, x, y, w, h, intensity))
        if len(csv_data) % 100 == 0:
            print(len(csv_data), "non meteor learning objects so far")

# Now get confirm meteors
total_no = len(csv_data)

mdir = "/mnt/ams2/meteors/"
mdirs = os.listdir(mdir)
for date in sorted(mdirs, reverse=True):
    if os.path.isdir(mdir + date) is True and date[0] == "2":
        print("Day:", date)
        mfiles = glob.glob(mdir + "/" + date + "/*-reduced.json")
        for line in mfiles:
            img_file = line.replace("-reduced.json", "-stacked.jpg")
            #if os.path.exists(img_file):
            #    img = cv2.imread(img_file)
            #    cv2.imshow('pepe', img)
            #    cv2.waitKey(0)
            meteor_id = station_id + "_" + line.split("/")[-1].replace("-reduced.json", "")
            #line.split("/")[-1].replace("-reduced.json", "")
            if line not in train_files:
                train_files[line] = {}

            data = load_json_file(line)
            if len(data['meteor_frame_data']) == 0:
                continue 
            first_fn = data['meteor_frame_data'][0][1]
            for row in data['meteor_frame_data']:
                (date, fn, x, y, w, h, intensity, ra, dec, az, el) = row
                csv_data.append((1, meteor_id, fn - first_fn, x, y, w, h, intensity))
            if len(csv_data) % 100 == 0:
                print(len(csv_data), "non meteor learning objects so far")

        if len(csv_data) > (total_no * 2):
           break

df = pd.DataFrame(csv_data, columns=['label', 'meteor_id', 'frame_number', 'x', 'y', 'w', 'h', 'intensity'])
df.to_csv(training_csv_file, index=False)
print("saved training file with", len(csv_data), "items")

os.system("/usr/bin/python3 GroupData.py")
