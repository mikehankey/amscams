#!/usr/bin/python3
allsky_console = """
  ____  _      _      _____ __  _  __ __
 /    || |    | |    / ___/|  |/ ]|  |  |
|  o  || |    | |   (   \_ |  ' / |  |  |
|     || |___ | |___ \__  ||    \ |  ~  |
|  _  ||     ||     |/  \ ||     ||___, |
|  |  ||     ||     |\    ||  .  ||     |
|__|__||_____||_____| \___||__|\_||____/

AllSky.com/ALLSKY7 - NETWORK SOFTWARE
Copywrite Mike Hankey LLC 2016-2022
Use permitted for licensed users only.
Contact mike.hankey@gmail.com for questions.
"""
print(allsky_console)

import time
import seaborn as sns
import pickle
from lib.PipeUtil import cfe
import sys
import glob
from wmplPlots import wmplPlots
import cv2
import os
from lib.PipeUtil import load_json_file


def todict(obj, classkey=None):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, classkey)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast())
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
            for key, value in obj.__dict__.items()
            if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj

def evdir_from_event_id(eid):
   Y = eid[0:4] 
   M = eid[4:6] 
   D = eid[6:8] 
   print(Y,M,D)
   evdir = "/mnt/ams2/EVENTS/" + Y + "/" + M + "/" + D + "/" + eid + "/"
   return(evdir)

def meteor_cell_html(obs_id):
   cloud_root  = "/mnt/archive.allsky.tv/"
   cloud_vroot = "https://archive.allsky.tv/"
   station_id = obs_id.split("_")[0]
   year = obs_id.split("_")[1]
   month = obs_id.split("_")[2]
   dom = obs_id.split("_")[3]
   day = year + "_" + month + "_" + dom 
   cloud_dir = cloud_root + station_id + "/METEORS/" + year + "/" + day + "/"
   cloud_vdir = cloud_vroot + station_id + "/METEORS/" + year + "/" + day + "/"
   prev_img_file = cloud_dir + obs_id.replace(".mp4","-prev.jpg")
   prev_img_url = cloud_vdir + obs_id.replace(".mp4","-prev.jpg")
   div_id = obs_id.replace(".mp4", "")
   disp_text = obs_id + "<br>"
   if os.path.exists(prev_img_file) is True:
      html = """
         <div id="{:s}" style="
              background-image: url('{:s}');
              background-repeat: no-repeat;
              background-size: 320px;
              width: 320px;
              height: 180px;
              margin: 5px ">
              <div class="show_hider"> {:s} </div>
         </div>
      """.format(div_id, prev_img_url, disp_text)
   else:
      html = "" 
      #station_id + " " + obs_id.replace(".mp4", "")
   return(html)


def cascade_html(eid, items, header):
   cascade = header + """
      <div id="carouselExampleFade" class="carousel slide carousel-fade" data-bs-ride="carousel">
        <div class="carousel-inner">
   """
   for item in items:
      cascade += """
          <div class="carousel-item active">
          {:s}
          </div>
      """.format(item)

   cascade += """
        </div>
        <button class="carousel-control-prev" type="button" data-bs-target="#carouselExampleFade" data-bs-slide="prev">
          <span class="carousel-control-prev-icon" aria-hidden="true"></span>
          <span class="visually-hidden">Previous</span>
        </button>
        <button class="carousel-control-next" type="button" data-bs-target="#carouselExampleFade" data-bs-slide="next">
          <span class="carousel-control-next-icon" aria-hidden="true"></span>
          <span class="visually-hidden">Next</span>
        </button>
      </div>
   """
   return(cascade)


def obs_html(eid):
   html = "<h1>AllSky7 Meteor Event - " + eid + "</h1>"
   enav_html = """
   <div class=pnav>
      <a href="#obs">Observations</a> - 
      <a href="#trajectory">Trajectory & Orbit</a> - 
      <a href="#velocity">Velocity</a> - 
      <a href="#residuals">Residuals</a> - 
      <a href="#details">Details</a> 
   </div> 

   """
   html += enav_html 
   html += """<a name="obs"></a><h2>Observations</h2>"""
   html += "<div>\n"
   ev_dir = evdir_from_event_id(event_id)
   good_obs_file = ev_dir + eid + "_GOOD_OBS.json"
   obs_ids = []
   no_prev = ""

   if os.path.exists(good_obs_file) is True:
      good_obs = load_json_file(good_obs_file)
   for station_id in good_obs:
      for obs_file in good_obs[station_id]:
         if station_id not in obs_file:
            ob_file = station_id + "_" + obs_file
         else:
            ob_file = obs_file
         obs_ids .append(ob_file )
   obs_ids = sorted(obs_ids)
   for ob in obs_ids:
      if ob == "":
         continue
      temp = meteor_cell_html(ob)
      if temp != "" and temp != " " :
         html += """<div class="cell">"""
         html += temp
         html += """</div>\n"""
      else:
         no_prev += ob + "<br>" 
   html += "</div>\n"
   html += """<div style="clear: both"></div>""";

   return(html, no_prev)

event_id = sys.argv[1]

obs_gallery, no_prev = obs_html(event_id)
print(obs_gallery)
   

ev_dir = evdir_from_event_id(event_id)

#ev_dir = evdir_from_event_id(event_id)
report_file = ev_dir + event_id + "_report.txt"
report_txt = allsky_console + "\n\n"
if os.path.exists(report_file):
   fp = open(report_file)
   for line in fp:
      report_txt += line

pickle_file = ev_dir + event_id + "_trajectory.pickle"
cloud_pickle_file = pickle_file.replace("ams2/", "archive.allsky.tv/")

if cfe(pickle_file) == 0:
   if cfe(cloud_pickle_file) == 1:
      if cfe(ev_dir,1) == 0:
         os.makedirs(ev_dir)
         cmd = "cp " + cloud_pickle_file + " " + pickle_file
         print(cmd)
         os.system(cmd)


with open(pickle_file, 'rb') as handle:
   vida_data = pickle.load(handle)

traj_dict = todict(vida_data)
wmplPlots = wmplPlots()

wmplPlots.dict = {}

for key in traj_dict:
   #print("DICT:", key)
   wmplPlots.dict[key] = traj_dict[key]
   if key == "traj":
      wmplPlots.traj = traj_dict['traj']
   if key == "orbit":
      wmplPlots.orbit = traj_dict['orbit']

   if key == "timing_res":
      wmplPlots.timing_res= traj_dict['timing_res']
   if key == "velocity_fit":
      wmplPlots.velocity_fit = traj_dict['velocity_fit']
   if key == "jacchia_fit":
      wmplPlots.jacchia_fit = traj_dict['jacchia_fit']
   if key == "v_init":
      wmplPlots.v_init = traj_dict['v_init']
   if key == "observations":
      wmplPlots.observations = traj_dict[key]
      #print("FOUND", key) #, traj_dict[key])
      #for okey in traj_dict['observations']:
      #   print(okey)

output_dir = "test/"
year = event_id[0:4]
month = event_id[4:6]
day = event_id[6:8]
cloud_dir = "/mnt/archive.allsky.tv/EVENTS/" + year + "/" + month + "/" + day + "/" + event_id + "/" 
output_dir = "/mnt/ams2/EVENTS/" + year + "/" + month + "/" + day + "/" + event_id + "/" 
file_name = event_id

#wmplPlots.savePlots(output_dir, file_name, show_plots=False, ret_figs=False)
#exit()

#wmplPlots.savePlots(output_dir, file_name, show_plots=False, ret_figs=False)
try:
   #foo = 1
   wmplPlots.savePlots(output_dir, file_name, show_plots=False, ret_figs=False)
except:
   print("error saveing plots")
plt_files = glob.glob(output_dir + "*.png")
header_html = """

<!doctype html>
<html lang="en">
   <head>
      <!-- Required meta tags -->
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>AllSky.com</title>
      <!-- Bootstrap CSS -->
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-eOJMYsd53ii+scO/bJGFsiCZc+5NDVN2yr8+0RDqr0Ql0h+rP48ckxlpbzKgwra6" crossorigin="anonymous">
      <link rel="alternate" type="application/rss+xml" title="RSS 2.0" href="https://www.datatables.net/rss.xml">
      <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta3/dist/js/bootstrap.bundle.min.js" integrity="sha384-JEW9xMcG8R+pH31jmWH6WWP0WintQrMb4s7ZOdauHnUtxwoG2vI5DkLtS3qm9Ekf" crossorigin="anonymous"></script>
      <script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.24/js/jquery.dataTables.min.js"></script>
      <header>
<style>
@import url("https://cdn.jsdelivr.net/npm/bootstrap-icons@1.4.1/font/bootstrap-icons.css");
h1 {
   color: #FFFFFF;
}
h2 {
   color: #FFFFFF;
}
.main-footer {
   color: #FFFFFF;
}
.show_hider {
   opacity: 0;
   color: #FFFFFF;
   font-size: 10px;
}
.show_hider:hover {
   opacity: 1;
   color: #FFFFFF;
   font-size: 10px;
}

body {
  background-color: black;
  text: white;
}
.cell {
   float: left;
   padding: 5px;
   border: 1px #ffffff solid;
}
</style>
"""
plot_html = header_html
plot_html += """
<div class="container-fluid">
"""
plot_html += obs_gallery
html_sec = {}
html_sec['all'] = ""
html_sec['res'] = ""
html_sec['orb'] = ""
html_sec['orb_side'] = ""
html_sec['traj'] = ""
html_sec['lag'] = ""
html_sec['length'] = ""
html_sec['vel'] = ""
html_sec['lags'] = ""
rand = str(time.time())[-4:]
for p in sorted(plt_files):
   fn = p.split("/")[-1]
   #plot_html += "<img src=" + fn.replace(".png", ".jpg") + "><br>"
   if "lags" in fn:
      html_sec['lags'] += "<img width=400 height=300 src=" + fn.replace(".png", ".jpg?") + rand + "><br>\n"
   elif "all" in fn or "total" in fn:
      html_sec['all'] += "<img width=400 height=300 src=" + fn.replace(".png", ".jpg?") + rand + "><br>\n"
   elif "res" in fn:
      html_sec['res'] += "<img width=320 height=240 src=" + fn.replace(".png", ".jpg?") + rand + "><br>\n"
   elif "ground" in fn:
      html_sec['traj'] += "<img width=800 height=600 src=" + fn.replace(".png", ".jpg?") + rand + "><br>\n"
   elif "orbit_top" in fn:
      html_sec['orb'] += "<img width=400 height=300 src=" + fn.replace(".png", ".jpg?") + rand + ">\n"
   elif "orbit_side" in fn:
      html_sec['orb_side'] += "<img width=400 height=300 src=" + fn.replace(".png", ".jpg?") + rand + ">\n"
   elif "orbit_side" in fn:
      foo = 1
      #html_sec['orb'] += "<img width=640 height=480 src=" + fn.replace(".png", ".jpg?") + rand + "><br>\n"
   elif "vel" in fn:
      html_sec['vel'] += "<img width=400 height=300 src=" + fn.replace(".png", ".jpg?") + rand + "><br>\n"
   elif "length" in fn:
      html_sec['length'] += "<img width=400 height=300 src=" + fn.replace(".png", ".jpg?") + rand + "><br>\n"
   else:
      html_sec['res'] += "<img width=400 height=300 src=" + fn.replace(".png", ".jpg?") + rand + "><br>\n"

   jpg = cv2.imread(p)
   j = p.replace(".png", ".jpg" )
   ph,pw = jpg.shape[:2]
   if "orb" in fn:
      nw = int(pw * .5)
      nh = int(ph * .5)
   else:
      nw = int(pw * .5)
      nh = int(ph * .5)
   if "ground" in j :
      nw,nh = 1280,960
   elif "orbit" in j:
      nh,nw = jpg.shape[:2]
   else:
      nw,nh = 640,480
   if "orbit_top" in j:
      orb_top_img = jpg
      orb_top_file = j
   if "orbit_side" in j:
      orbit_side_img = jpg
      orb_side_file = j
      #.replace(".jpg", "-custom.jpg")
   if "ground" in j:
      ground_track_img = jpg
      ground_track_file = j
   jpg = cv2.resize(jpg, (nw,nh))
   print("NEW WIDTH HEIGHT", nw, nh)

   cv2.imwrite(j, jpg, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
   os.system("rm " + p)

# make nice orbit image
oh,ow = orbit_side_img.shape[0:2]
hh = int(oh / 2)
y1 = hh - 200
y2 = hh + 200
cx = int(ow/2)
x1 = cx - 600
x2 = cx + 600

orb_side_img = orbit_side_img[y1:y2,x1:x2]
#print(orb_side_img.shape)
#cv2.imwrite(orb_side_file2, orb_side_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

cx = int(orb_top_img.shape[1]/2)
cy = int(orb_top_img.shape[0]/2)
y1 = cy - 600
y2 = cy + 600
x1 = cx - 600
x2 = cx + 600
otop_img = orb_top_img[y1:y2,x1:x2]

y2 = orb_side_img.shape[0]
x2 = orb_side_img.shape[1]
#otop_img[0:y2,0:x2] = orb_side_img
cv2.imwrite(orb_top_file, otop_img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])


plot_html += """<a name="trajectory"></a><h2>Trajectory & Orbit</h2>"""
plot_html += """
<div>
<div class="cell">
{:s}
</div>
<div class="cell">
{:s}<br>
{:s}
</div>
</div>
<div style="clear: both"></div>
<a name="velocity"></a>
<h2>Velocity, Length & Lags</h2>
<div>
<div class="cell">
{:s}
</div>
<div class="cell">
{:s}
</div>

<div class="cell">
{:s}
</div>

</div>

<a name="residuals"></a>
<div style="clear: both"></div>
<h2>Combined Residuals</h2>
<div>
""".format(html_sec['traj'], html_sec['orb'], html_sec['orb_side'], html_sec['vel'], html_sec['length'], html_sec['lags'])

#plot_html += "<h2>Orbit</h2>"
#plot_html += html_sec['orb']

#plot_html += "<h2>Velocity</h2>"
#plot_html += html_sec['vel']
#plot_html += "<h2>Length</h2>"
#plot_html += html_sec['length']
#plot_html += "<h2>Lags</h2>"
#plot_html += html_sec['lags']
#plot_html += "<h2>All Station Residuals</h2>"
cells = html_sec['all'].split("<br>")
for cell in cells:
   plot_html += """
      <div class="cell">
         {:s}
      </div>
   """.format(cell)
plot_html += """
   </div> <div style="clear: both"></div>


   """
plot_html += " <h2>Station Residuals</h2> <div>"
#plot_html += html_sec['all']
#plot_html += "<h2>Per Station Residuals</h2>"


cells = html_sec['res'].split("<br>")
plot_html += "<div>"
for cell in cells:
   plot_html += """
      <div class="cell">
         {:s}
      </div>
   """.format(cell)

plot_html += """
<div style="clear: both"></div>
<h2>Details</h2>
<div class="overflow-auto" style="color: #ffffff; width: 100%; height: 360px;">
<pre>
{:s}
</pre>
</div>
""".format(report_txt)
plot_html += """
   </div> 
   <div style="clear: both"></div>

   </div>
   <p>
   <footer class="main-footer">
    <!-- To the right -->
    <!-- Default to the left -->
    <strong>Copyright &copy; 2016-2022 <a href="https://www.allsky.com">AllSky.com</a>.</strong> All rights reserved.
   </footer>

   </html>
   """



#plot_html += html_sec['res']
fp = open(output_dir + event_id + "_plots.html", "w")
fp.write(plot_html)
fp.close()
items = ["1", "2", "3"]
html2 = cascade_html(event_id, items, header_html)
fp = open(output_dir + event_id + "_casc.html", "w")
fp.write(html2)
fp.close()


print("MOVE TO CLOUD DIR!", cloud_dir)
if os.path.exists(cloud_dir) is False:
   os.makedirs(cloud_dir)
cmd = "rsync -auv " + output_dir + "*"  + " " + cloud_dir
print(cmd)

#os.system(cmd)
