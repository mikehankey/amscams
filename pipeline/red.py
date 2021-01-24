#!/usr/bin/python3

import redis
from lib.PipeUtil import load_json_file,save_json_file
from lib.PipeAutoCal import fn_dir 
r = redis.Redis(decode_responses=True)



def load_meteor_index(r ):
   json_conf = load_json_file("../conf/as6.json")
   amsid = json_conf['site']['ams_id']
   index_file = "/mnt/ams2/meteors/" + amsid + "-meteors.info"
   index = load_json_file(index_file)
   for row in index:
      if len(row) == 8:
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot,msm) = row
      else:
         (meteor, reduced, start_time, dur, ang_vel, ang_dist, hotspot) = row
         msm = 0

      mfn,dd = fn_dir(meteor)
      key = "mi:" + mfn
      val = str([reduced,start_time,dur,ang_vel,ang_dist,hotspot,msm])
      r.mset({key: val})
      print("setting.", meteor, start_time)

#xxx = r.get("test")
#print(xxx)

#load_meteor_index(r)
for key in sorted(r.scan_iter("mi:*")):
   print(key, r.get(key))
