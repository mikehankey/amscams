from FlaskLib.FlaskUtils import make_default_template
from lib.PipeUtil import get_file_info, fetch_url
import os
import time
#con = sqlite3.connect(station_id + "_ALLSKY.db")
#con.row_factory = sqlite3.Row
#cur = con.cursor()

def network_main(station_id, json_conf):
   local_days_file = "/mnt/ams2/network_meteor_days.html"
   cloud_days_file = "/mnt/archive.allsky.tv/APPS/network_meteor_days.html"

   if os.path.exists(local_days_file):
      sz, old = get_file_info(local_days_file)
      print("OLD:", old)
      if old > 100:
         cmd = "cp " + cloud_days_file + " " + local_days_file
         print(cmd)
         os.system(cmd)
   else:
      cmd = "cp " + cloud_days_file + " " + local_days_file
      os.system(cmd)

   select_days = ""
   if os.path.exists(local_days_file):
      fp = open(local_days_file, "r")
      for line in fp:
         select_days += line


   select_days = select_days.replace("F:/", "/NETWORK/METEORS/" + station_id + "?day=")

   template = make_default_template(station_id, "meteors_main.html", json_conf)
   out = """
        <iframe width=100% height=425 src="https://archive.allsky.tv/APPS/dist/maps/index.html?mf=https://archive.allsky.tv/EVENTS/ALL_STATIONS.kml&lat=40&lon=-46&zoom=3"></iframe>

       <h1>Meteor Events </h1>
      <div id='step1' class='text-lg-left' style='display:block'> 
       Select Meteor Day
       <p>
       {}
       </p>
      </div>
   """.format(select_days)

   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def network_map(station_id, json_conf):
   return("MAP")

def network_meteors(station_id,json_conf,in_data):
   rand = str(time.time())[0:-5]
   url = "https://archive.allsky.tv" + in_data['day']  + "?" + rand
           
   out = fetch_url(url)

   out = out.replace("F:/", "/NETWORK/METEORS/" + station_id + "?day=")

   template = make_default_template(station_id, "meteors_main.html", json_conf)
   #template = template.replace("AllSkyCams.com", "AllSky.com")
   template = template.replace("{MAIN_TABLE}", out)

   return(template)
