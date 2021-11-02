import pickle
from lib.PipeUtil import cfe
import sys
import glob
from wmplPlots import wmplPlots
import cv2
import os

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

event_id = sys.argv[1]
ev_dir = evdir_from_event_id(event_id)

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
   print("DICT:", key)
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
      print("FOUND", key) #, traj_dict[key])
      for okey in traj_dict['observations']:
         print(okey)

output_dir = "test/"
file_name = "test"
wmplPlots.savePlots(output_dir, file_name, show_plots=False, ret_figs=False)
plt_files = glob.glob(output_dir + "*.png")
plot_html = ""
html_sec = {}
html_sec['all'] = ""
html_sec['res'] = ""
html_sec['orb'] = ""
html_sec['traj'] = ""
html_sec['lag'] = ""
html_sec['length'] = ""
html_sec['vel'] = ""
for p in sorted(plt_files):
   fn = p.split("/")[-1]
   #plot_html += "<img src=" + fn.replace(".png", ".jpg") + "><br>"
   print("FN:", fn)
   if "all" in fn or "total" in fn:
      html_sec['all'] += "<img src=" + fn.replace(".png", ".jpg") + "><br>"
   elif "res" in fn:
      html_sec['res'] += "<img src=" + fn.replace(".png", ".jpg") + "><br>"
   elif "ground" in fn:
      html_sec['traj'] += "<img src=" + fn.replace(".png", ".jpg") + "><br>"
   elif "orb" in fn:
      html_sec['orb'] += "<img src=" + fn.replace(".png", ".jpg") + "><br>"
   elif "vel" in fn:
      html_sec['vel'] += "<img src=" + fn.replace(".png", ".jpg") + "><br>"
   elif "length" in fn:
      html_sec['length'] += "<img src=" + fn.replace(".png", ".jpg") + "><br>"

   jpg = cv2.imread(p)
   j = p.replace(".png", ".jpg")
   ph,pw = jpg.shape[:2]
   if "orb" in fn:
      nw = int(pw * .4)
      nh = int(ph * .4)
   else:
      nw = int(pw * .5)
      nh = int(ph * .5)
   jpg = cv2.resize(jpg, (nw,nh))
   print(nw, nh)
   cv2.imwrite(j, jpg, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
   os.system("rm " + p)
plot_html += "<h2>Trajectory</h2>"
plot_html += html_sec['traj']

plot_html += "<h2>Orbit</h2>"
plot_html += html_sec['orb']
plot_html += "<h2>Velocity</h2>"
plot_html += html_sec['vel']
plot_html += "<h2>Length</h2>"
plot_html += html_sec['length']
plot_html += "<h2>All Station Residuals</h2>"
plot_html += html_sec['all']
plot_html += "<h2>Per Station Residuals</h2>"
plot_html += html_sec['res']
fp = open("test/plots.html", "w")
fp.write(plot_html)
fp.close()


