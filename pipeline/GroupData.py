import pandas as pd
import os
import json
from lib.PipeUtil import load_json_file
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

# label,meteor_id,frame_number,x,y,w,h,intensity
# Load CSV data
df = pd.read_csv("meteor_yn_training.csv")
new_data = []
last_meteor_id = None
for index, row in df.iterrows():
   #print(row['label'], row['meteor_id'], row['frame_number'], row['x'], row['y'], row['w'], row['h'], row['intensity'])
   if last_meteor_id == None or last_meteor_id != row['meteor_id'] :
      if last_meteor_id != None:
         new_data.append((last_label, last_meteor_id, ts, xs, ys, ws, hs, ints)) 
      ts = []
      xs = []
      ys = []
      ws = []
      hs = []
      ints = []
   ts.append(row['frame_number'])
   xs.append(row['x'])
   ys.append(row['y'])
   ws.append(row['w'])
   hs.append(row['h'])
   ints.append(row['intensity'])
   last_meteor_id = row['meteor_id']
   last_label = int(row['label'])

# Define column names
columns = ['label', 'meteor_id', 'ts', 'xs', 'ys', 'ws', 'hs', 'ints']

# Create a DataFrame
odf = pd.DataFrame(new_data, columns=columns)
odf.to_csv(station_id + '.meteor_yn_group_data.csv', index=False)
cmd = "cp " + station_id + '.meteor_yn_group_data.csv /mnt/archive.allsky.tv/'  + station_id + "/"
print(cmd)
os.system(cmd)
