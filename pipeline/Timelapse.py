import sys
import glob

def timelapse_live_weather(date,station_id, cam_id):
   path = "/mnt/archive.allsky.tv/" + station_id + "/LATEST/" + date + "/" 
   out = """
   <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.0/jquery.min.js"></script>
   <script type='text/javascript' src='https://archive.allsky.tv/APPS/js/mTimeLapse.js'></script>
   <link rel="stylesheet" href="https://archive.allsky.tv/APPS/css/timelapse.css">
   """
   out += """ <div id="mTimeLapse"> """

   files = sorted(glob.glob(path + "*" + cam_id + "*.jpg"))
   for filename in files:
      if "mark" in filename:
         continue
      desc = filename.split("/")[-1].replace(".jpg", "")   + "<br>&nbsp;<br>"
      desc = desc.replace("-marked", "")
      out += '''<img src="''' + filename.replace("/mnt/", "https://") + '''" data-stamp="''' + desc  + '''">\n'''

   out += """  </div> """
   return(out)

x, date, station_id, cam_id = sys.argv
out = timelapse_live_weather(date,station_id, cam_id)
print(out)
