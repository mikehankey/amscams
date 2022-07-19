from lib.PipeUtil import load_json_file, save_json_file, mfd_roi
import sys, os
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

def ai_check(roi_file):
   if os.path.exists(roi_file) is True:
      print("ROI FILE EXISTS!", roi_file)

      if True:
         url = "http://localhost:5000/AI/METEOR_ROI/?file={}".format(roi_file)
         try:
            response = requests.get(url)
            content = response.content.decode()
            ai_dict[mj] = json.loads(content)
            print(content)
         except Exception as e:
            print("HTTP ERR:", e)
   else:
      print("NO ROI FILE EXISTS!", roi_file)

def check_day(station_id, day):
   mdir = "/mnt/ams2/meteors/" + day + "/"
   nmdir = "/mnt/ams2/non_meteors/" + day + "/"
   files = os.listdir (nmdir)
   ai_data = load_json_file(mdir + station_id + "_" + day + "_AI_DATA.info")
   ai_dict = {}

   for row in ai_data:
      print(row)
      key = row[1] 
      ai_dict[key] = row

   meteors= []
   for f in files:
      if ".json" in f and "reduced" not in f:
         f = f.replace(".json", "")
         meteors.append(f) 

   for m in meteors:
      if m in ai_dict:
         print("YES", ai_dict[m])
      else:
         print("NO AI", m)
      roi_file = nmdir + m + "-ROI.jpg"
      if os.path.exists(roi_file) is False:
         print("MISSING:", roi_file)
         if os.path.exists(roi_file.replace("-ROI.jpg", "-reduced.json")) is True:
            red = load_json_file(roi_file.replace("-ROI.jpg", "-reduced.json"))
            if "meteor_frame_data" in red:
               mfd = red['meteor_frame_data']
               roi = mfd_roi(mfd)
               print("ROI:", roi)
            else:
               print("FAIL:", red.keys())
         else:
            print("Missing:", roi_file.replace("-ROI.jpg", "-reduced.json")) 
   print(len(files), nmdir)

check_day(station_id, sys.argv[1])
