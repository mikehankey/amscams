import os, sys
from Classes.Meteor import Meteor

meteor_file = sys.argv[1]

M = Meteor(meteor_file=meteor_file)
M.meteor_scan()

print("BEST METEOR:", M.best_meteor)
print("STATUS", M.meteor_scan_info['status'])
print("DESC", M.meteor_scan_info['desc'])
for obj_id in M.meteor_scan_info['sd_objects']:
   print(obj_id, M.meteor_scan_info['sd_objects'][obj_id].keys())
   print(obj_id, M.meteor_scan_info['sd_objects'][obj_id]['report'].keys())
   x1 = min(M.meteor_scan_info['sd_objects'][obj_id]['oxs'])
   x2 = max(M.meteor_scan_info['sd_objects'][obj_id]['oxs'])
   y1 = min(M.meteor_scan_info['sd_objects'][obj_id]['oys'])
   y2 = max(M.meteor_scan_info['sd_objects'][obj_id]['oys'])
   roi = [x1,y1,x2,y2]
   if "meteor" in M.meteor_scan_info['sd_objects'][obj_id]['report']:
      print("METEOR:", roi, obj_id, M.meteor_scan_info['sd_objects'][obj_id]['report']['meteor'], M.meteor_scan_info['sd_objects'][obj_id]['report']['bad_items'])
   else:
      print("NON METEOR:", roi, obj_id, M.meteor_scan_info['sd_objects'][obj_id]['report']['bad_items'])
 
