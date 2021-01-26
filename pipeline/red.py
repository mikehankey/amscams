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
make_day_totals = 0
if make_day_totals == 1:
   mid = {}
   for key in sorted(r.scan_iter("mi:*")):
      data = eval(r.get(key))
      reduced, start_time,dir, avg_vel, ang_dist, max_int, msm = data
      dkey = key.replace("mi:","")
      day = dkey[0:10]
      #   print("DAY:", day)
      if day not in mid:
         mid[day] = {}
         mid[day]['total'] = 0
         mid[day]['red'] = 0
         mid[day]['msm'] = 0
      mid[day]['total'] += 1
      if reduced == 1:
         mid[day]['red'] += 1
      if msm == 1:
         mid[day]['msm'] += 1

   for day in sorted(mid.keys()):
      print("DAY:", day, mid[day])
      key = "mid:" + day
      val = str(mid[day])
      r.mset({key: val})

all_total = 0
for key in sorted(r.scan_iter("mid:*")):
   data = eval(r.get(key))
   print(key, data)
   all_total += data['total']
print("TOTAL:", all_total)
