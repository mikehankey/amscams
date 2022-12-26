from FlaskLib.FlaskUtils import make_default_template
from lib.PipeUtil import get_file_info, fetch_url, load_json_file, save_json_file
import os
import time
#con = sqlite3.connect(station_id + "_ALLSKY.db")
#con.row_factory = sqlite3.Row
#cur = con.cursor()


def network_events(station_id, date, json_conf):

   y,m,d = date.split("_")
   local_event_dir = "/mnt/ams2/EVENTS/" + y + "/" + m + "/" + d + "/"
   cloud_event_dir = "/mnt/archive.allsky.tv/EVENTS/" + y + "/" + m + "/" + d + "/"
   event_file = local_event_dir + date + "_ALL_EVENTS.json"
   cloud_event_file = cloud_event_dir + date + "_ALL_EVENTS.json"
   if os.path.exists(event_file) is False:
      if os.path.exists(cloud_event_file) is True:
         os.system("cp " + cloud_event_file + " " + event_file)
   event_data = load_json_file(event_file)
   center_lat = json_conf['site']['device_lat']
   center_lon = json_conf['site']['device_lng']

   template = make_default_template(station_id, "meteors_main.html", json_conf)
   orb_link = "https://archive.allsky.tv" + local_event_dir.replace("/mnt/ams2/", "/") + "ALL_ORBITS.json"
   short_date = date.replace("_", "")
   kml_link = "https://archive.allsky.tv" + local_event_dir.replace("/mnt/ams2/", "/") + "ALL_TRAJECTORIES.kml"
   map_link = """https://archive.allsky.tv/APPS/dist/maps/index.html?mf={:s}&lat={:s}&lon={:s}&zoom=3""".format(kml_link, str(center_lat), str(center_lon))
   out = """
      <h2>All Radiants on {:s}</h2>
      <iframe width=100% height=660 src="https://archive.allsky.tv/APPS/dist/radiants.html?d={:s}"></iframe>
      <h2>All Orbits </h2>
      <iframe width=100% height=450 src="https://orbit.allskycams.com/index_emb.php?file={:s}"></iframe>
      <h2>All Trajectories</h2>
      <iframe width=100% height=450 src="{:s}"></iframe>
   """.format(date, short_date, orb_link, map_link)
   template = template.replace("{MAIN_TABLE}", out)

   return(template)


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

   my_lat = str(json_conf['site']['device_lat'])
   my_lon = str(json_conf['site']['device_lng'])
   select_days = select_days.replace("F:/", "/NETWORK/METEORS/" + station_id + "?day=")

   template = make_default_template(station_id, "meteors_main.html", json_conf)
   out = """
        <iframe width=100% height=425 src="https://archive.allsky.tv/APPS/dist/maps/index.html?mf=https://archive.allsky.tv/EVENTS/ALL_STATIONS.kml&lat={:s}&lon={:s}&zoom=5"></iframe>

   """.format(my_lat, my_lon)

   extra = """
       <h1>Meteor Events </h1>
      <div id='step1' class='text-lg-left' style='display:block'> 
       Select Meteor Day
       <p>
       {}
       </p>
      </div>
   """.format(my_lat, my_lon, select_days)

   template = template.replace("{MAIN_TABLE}", out)
   return(template)

def get_template(template_file):
   html = ""
   fp = open(template_file)
   for line in fp:
      html += line
   return(html)

def network_map(station_id, json_conf):
  
   all_stations_file = "/mnt/ams2/EVENTS/ALL_STATIONS.json"
   asurl = "https://archive.allsky.tv/EVENTS/ALL_STATIONS.json"
   size, tdiff = get_file_info(all_stations_file)
   tdiff = (tdiff / 60 )/ 24
   print("TDIFF IS :", tdiff)
   if tdiff > 1:
      cmd = "wget " + asurl + " -O " + all_stations_file
      print(cmd)
      os.system(cmd)

   asdata = load_json_file(all_stations_file)
   labels = []
   lats = []
   lons = []
   colors = []
   textpos = []
   for data in asdata:
      labels.append(data['station_id'])
      lats.append(data['lat'])
      lons.append(data['lon'])
      colors.append("#000000")
      textpos.append("top right")
      print(data)

   temp_file = "FlaskTemplates/map_plotly.html"
   #labels = ["test"]
   #lats = [40]
   #lons = [-76]
   #colors = ['#bebada']
   #textpos = ['top right']
   min_lat = float(json_conf['site']['device_lat']) - 4.5 
   max_lat = float(json_conf['site']['device_lat']) + 4.6
   min_lon = float(json_conf['site']['device_lng']) - 8
   max_lon = float(json_conf['site']['device_lng']) + 8
   out = get_template(temp_file)
   out = out.replace("{LABELS}", str(labels))
   out = out.replace("{MIN_LAT}", str(min_lat))
   out = out.replace("{MIN_LON}", str(min_lon))
   out = out.replace("{MAX_LAT}", str(max_lat))
   out = out.replace("{MAX_LON}", str(max_lon))
   out = out.replace("{LATS}", str(lats))
   out = out.replace("{LONS}", str(lons))
   out = out.replace("{COLOR}", str(colors))
   out = out.replace("{TEXTPOSITION}", str(textpos))
   return(out)

def network_meteors(station_id,json_conf,in_data):
   rand = str(time.time())[0:-5]
   url = "https://archive.allsky.tv" + in_data['day']  + "?" + rand
           
   out = fetch_url(url)

   out = out.replace("F:/", "/NETWORK/METEORS/" + station_id + "?day=")

   template = make_default_template(station_id, "meteors_main.html", json_conf)
   #template = template.replace("AllSkyCams.com", "AllSky.com")
   template = template.replace("{MAIN_TABLE}", out)

   return(template)
