#!/usr/bin/python3

import glob
from lib.PipeUtil import load_json_file
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

files = glob.glob("/mnt/ams2/meteor_archive/" + station_id + "/CAL/AUTOCAL/2021/FAILED/*" )
print("/mnt/ams2/meteor_archive/" + station_id + "/CAL/AUTOCAL/2021/FAIL/*" )
out = ""
for file in files:
   fn = file.split("/")[-1]
   out += "<a href=" + fn + ">" + fn + "</a><br>\n"
save_file = "/mnt/ams2/meteor_archive/" + station_id + "/CAL/AUTOCAL/2021/FAILED/failed.html"
fp = open(save_file, "w")
fp.write(out)
