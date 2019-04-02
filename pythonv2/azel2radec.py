#!/usr/bin/python3

from lib.CalibLib import radec_to_azel, AzEltoRADec, HMS2deg
from lib.FileIO import load_json_file 
import sys
json_conf = load_json_file("../conf/as6.json")




def az2ra(az,el,date,cal_params,json_conf):
   file_date = date
   (fy,fm,fd, fh, fmin, fs) = date.split("_")
   date = fy + "/" + fm + "/" + fd + " " + fh + ":" + fmin + ":" + fs
   file_date = file_date + "_000_00000.mp4"
   rah,dech = AzEltoRADec(az,el,file_date,cal_params,json_conf)

   rah = str(rah).replace(":", " ")
   dech = str(dech).replace(":", " ")

   ra, dec= HMS2deg(str(rah),str(dech))


   return(ra,dec)

az, el, date,cal_params_file = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3], sys.argv[4]
cal_params = load_json_file(cal_params_file)
ra, dec = az2ra(az,el,date,cal_params,json_conf)

print("IN DATE:", date)
print("IN CAL:", cal_params_file)
print("IN AZ/EL:", az, el)
print("OUT RA/DEC:", ra, dec)
