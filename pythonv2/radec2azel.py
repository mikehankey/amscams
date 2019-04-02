#!/usr/bin/python3

from lib.CalibLib import radec_to_azel
from lib.FileIO import load_json_file 
import sys
json_conf = load_json_file("../conf/as6.json")




def ra2az(ra,dec,date,json_conf):
   (fy,fm,fd, fh, fmin, fs) = date.split("_")
   date = fy + "/" + fm + "/" + fd + " " + fh + ":" + fmin + ":" + fs

   az, el= radec_to_azel(ra,dec, date,json_conf)
   return(az,el)

ra, dec, date = sys.argv[1], sys.argv[2], sys.argv[3]
az, el = ra2az(ra,dec,date,json_conf)

print("IN DATE:", date)
print("IN RA/DEC:", ra, dec)
print("OUT AZ/EL:", az, el)
