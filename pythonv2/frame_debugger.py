import sys


from lib.MeteorReduce_Tools import *


json_file = "/mnt/ams2/meteor_archive/AMS7/METEOR/2019/08/14/2019_08_14_09_32_02_520_010040_AMS7_HD.json"
meteor_json_file = load_json_file(json_file) 
get_frame_time(meteor_json_file,29)

