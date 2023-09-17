import plotly.express as px
import pickle
import cv2
import glob
import datetime
import pickle
import plotly.graph_objects as go
import argparse
import simplejson as json
import numpy as np
import os
PREVIEW = True 

def get_template(file):
   fp = open(file, "r")
   text = ""
   for line in fp:
      text += line
   return(text)

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

def load_json_file(json_file):
   with open(json_file, 'r' ) as infile:
      json_data = json.load(infile)
   return json_data

def save_json_file(json_file, json_data, compress=False):
   with open(json_file, 'w') as outfile:
      if(compress==False):
         json.dump(json_data, outfile, indent=4, allow_nan=True )
      else:
         json.dump(json_data, outfile, allow_nan=True)
   outfile.close()

def load_pickle(pickle_file):
   print("PICK:", pickle_file)
   with open(pickle_file, 'rb') as handle:
      pickle_data = pickle.load(handle)

   traj_dict = todict(pickle_data)
   return(traj_dict)



def plot_three_d_trajectory(event_id, traj_dict, outdir):
   series_data = []
   fig = go.Figure()
   outc = 0
   for key in traj_dict:
      if type(traj_dict[key]) == dict :
         #A print(key, traj_dict[key].keys())
         foo = "dict"
      elif key == 'observations':
         for odata in traj_dict[key]:
            #print(odata.keys())
            station_id = odata['station_id']
            st_id = station_id.split("-")[0]
            lat = np.degrees(odata['lat'])
            lon= np.degrees(odata['lon'])
            xs = np.degrees(odata['model_lat'])
            ys = np.degrees(odata['model_lon'])
            zs = odata['model_ht']

            #np.append(arr=xs, values=lat )
            #np.append(arr=ys, values=lon )
            #np.append(arr=zs, values=100 )
            series_data.append((station_id, xs, ys, zs))

            # station location 
            fig.add_trace(go.Scatter3d(x=[lat], y=[lon], z=[200],
               mode='lines+markers+text', name=st_id, 
               marker=dict(
               ),
               text = st_id,
               showlegend=False,
               marker_symbol='cross',
               marker_size=2
               ))

            # start line
            lxs = [lat,xs[0]]
            lys = [lon,ys[0]]
            lzs = [200,zs[0]]
            fig.add_trace(go.Scatter3d(x=lxs, y=lys ,z=lzs,
               marker_symbol='cross',
               marker_size=2,
               showlegend=False,
               line=dict(color='darkgreen', width=2),
                  name=station_id + " Start", 
               ))

            # end line
            lxs = [lat,xs[-1]]
            lys = [lon,ys[-1]]
            lzs = [200,zs[-1]]
            fig.add_trace(go.Scatter3d(x=lxs, y=lys ,z=lzs,
               marker_symbol='cross',
               marker_size=3,
               showlegend=False,
               line=dict(color='darkred', width=2),
                  name=station_id + " Start", 
               ))


            # points of solution
            fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs,
               mode='markers', name=station_id, 
               marker_size=2,
               ))

      else:
         #print(key, traj_dict[key])
         foo = "other"
 
   fig.update_layout(scene = dict(
      zaxis=dict(nticks=5, range=[0,120000])
      ))

       #up=dict(x=-0, y=0, z=0),
       #center=dict(x=0, y=0, z=0),
   tries = [

           [1,2.5,1], 
           [1,2.5,.9], 
           [1,2.5,.8],
           [1,2.5,.7],
           [1,2.5,.6],
           [1,2.5,.5],
           [1,2.5,.4],
           [1,2.5,.3],
           [1,2.5,.2],
           [1,2.5,.1],
           [.9,2.5,.1],
           [.8,2.5,.1],
           [.7,2.5,.1], 
           [.6,2.5,.1],
           [.5,2.5,.1], 
           [.4,2.5,.1], 
           [.3,2.5,.1], 
           [.2,2.5,.1], 
           [.1,2.5,.1],
           [.1,2.4,.1],
           [.1,2.3,.1], 
           [.1,2.2,.1], 
           [.1,2.1,.1], 
           [.1,2.0,.1], 

           [.1,1.9,.1], 
           [.2,1.8,.2], 
           [.3,1.7,.3], 
           [.4,1.6,.4], 
           [.5,1.5,.5], 
           [.6,1.5,.6], 
           [.7,1.4,.7], 
           [.8,1.3,.8], 
           [.9,1.2,.9], 
           [1,1.1,.9], 

           [1,1.1,.9], 
           [1.1,1.1,.9], 
           [1.2,1.1,.9], 
           [1.3,1.1,.9], 
           [1.4,1.1,.9], 
           [1.5,1.1,.9], 
           [1.6,1.1,.9], 
           [1.7,1.1,.9], 
           [1.8,1.1,.9], 
           [1.9,1.1,.9], 
           [2,1.1,.9], 

           [2.1,1.1,.9], 
           [2.2,1.1,.9], 
           [2.3,1.1,.9], 
           [2.4,1.1,.9], 
           [2.5,1.1,.9], 


           ] 
   for xxx in tries:
      camera = dict(
       eye=dict(x=xxx[0], y=xxx[1], z=xxx[2])
      )

      fig.update_layout(
         scene_camera=camera,
         title=event_id + " : 3D Trajectory"
      )
      outfile = outdir + event_id + "_3D_{:03d}.jpg".format(outc)  
      print("Saved 3D Trajectory:", outfile)
      fig.write_image(outfile)
      outc += 1 
      #fig.show()

def parse_event_id(event_id):
   year = event_id[0:4]
   mon = event_id[4:6]
   day = event_id[6:8]
   date = year + "_" + mon + "_" + day
   event_dir = "/mnt/f/EVENTS/{:s}/{:s}/{:s}/{:s}/".format(year, mon, day, event_id)
   return(date, event_dir)

def event_light_curves(event_id):
   date, event_dir = parse_event_id (event_id)
   outfile = event_dir + event_id + "_LIGHTCURVES.jpg"  
   event_file = event_dir + event_id + "_EVENT_DATA.json"
   pickle_file = event_dir + event_id + "_trajectory.pickle"
   event_data = load_json_file(event_file)
   print("EVENT_FILE:", event_file)
   print(event_data.keys())
   traj_dict = load_pickle(pickle_file)

   outdir = event_dir + "/PLOT_FRAMES/"
   if os.path.exists(outdir) is False:
      os.makedirs(outdir)
   
   plot_three_d_trajectory(event_id, traj_dict, outdir)
   print("Obs", traj_dict['observations'])

   # try to sync time from WMPL values???
   print("Time diffs", traj_dict['time_diffs'])
   stations = []
   for o in traj_dict['observations']:
      stations.append(o['station_id'])
   time_sync = {} 
   for i in range(0,len(stations)):
      time_sync[stations[i]] = traj_dict['time_diffs'][i]
   print(time_sync)
   time_matrix = {} 

   for obs in event_data['obs']:
      el = obs.split("_")
      station_id = el[0]
      cam_id = el[8].split("-")[0]
      st_id = station_id + "-" + cam_id
      if st_id in time_sync:
         time_mod = time_sync[st_id] * 100
      else:
         time_mod = 0
      times = event_data['obs'][obs]['times']
      ints = event_data['obs'][obs]['ints']
      new_times = []
      if max(ints) == 0:
         # missing ints!
         get_missing_ints(obs, event_data['obs'])
      print("TIME MOD FOR", obs, station_id + "-" + cam_id, time_mod, max(ints))

      for ot in times:
         otdt = datetime.datetime.strptime(ot, "%Y-%m-%d %H:%M:%S.%f")
         otts = datetime.datetime.timestamp(otdt)
         ntts = otts - time_mod
         ntdt = datetime.datetime.fromtimestamp(ntts)
         new_times.append(ntdt)
         if ntdt not in time_matrix:
            time_matrix[ntdt] = {}
         if st_id not in time_matrix[ntdt]:
            time_matrix[ntdt][st_id] = {}
      event_data['obs'][obs]['times'] = new_times


   # need better time sync!

   #exit()
   #fig = px.scatter()
   fig = go.Figure()
   for obs in event_data['obs']:
      times = event_data['obs'][obs]['times']
      ints = event_data['obs'][obs]['ints']
      el = obs.split("_")
      obs_name = el[0] + "-" + el[8]
      obs_name = obs_name.replace("-trim-", "-")
      fig.add_trace(go.Line(x=times, y=ints, name=obs_name))
   fig.update_layout(
      font_family="Courier New",
      font_color="blue",
      title_font_family="Times New Roman",
      title_font_color="red",
      legend_title_font_color="green",
      title= event_id + " : Light Curves for all Observations"  
   )
   fig.write_image(outfile)
   fig.show()

def res_for_day(args):
   date = args.date
   y,m,d = date.split("_")
   event_dir = "/mnt/f/EVENTS/{:s}/{:s}/{:s}/".format(y,m,d,date)
   event_file = "/mnt/f/EVENTS/{:s}/{:s}/{:s}/{:s}_ALL_EVENTS.json".format(y,m,d,date)
   solve_stats = {}
   res_dict = {}
   if os.path.exists(event_file):
      events = load_json_file(event_file)
      for ev in events:
         st = ev['solve_status']
         if st not in solve_stats:
            solve_stats[st] = 1 
         else:
            solve_stats[st] += 1
         ev_base = event_dir + ev['event_id'] + "/"
         res = ev_base + ev['event_id'] + "_all_spatial_total_residuals_height.jpg"
         pickle_file = ev_base + ev['event_id'] + "_trajectory.pickle"
         print(ev['solve_status'], ev_base)
         if os.path.exists(pickle_file) is True:
            with open(pickle_file, 'rb') as file:
               data = pickle.load(file)
               event_dict = todict(data)
               #print(event_dict.keys())
               for obs in event_dict['observations']:
                  hres = obs['h_res_rms']
                  vres = obs['v_res_rms']
                  if str(hres) == "nan":
                     hres = 999 
                  if str(vres) == "nan":
                     vres = 999 
                  print(obs['station_id'], hres, vres)
                  if obs['station_id'] not in res_dict:
                     res_dict[obs['station_id']] = []
                  res_dict[obs['station_id']].append(hres)
                  res_dict[obs['station_id']].append(vres)
               
                         # obs['h_residuals'], 
                         # obs['h_res_rms'], 
                         # obs['v_residuals'], 
                         # obs['v_res_rms'])
                  #print(obs.keys())
               
         if os.path.exists(res) is True:
            foo = 1
            #img = cv2.imread(res)
            #cv2.imshow('pepe', img)
            #cv2.waitKey(30)
         else:
            print("404:", res)
   for st in solve_stats:
      print(st, solve_stats[st])
   final = []
   for cam in res_dict:
      total = len(res_dict[cam])
      print(res_dict[cam])
      final.append((cam,np.mean(res_dict[cam]),total))

   for cam, avg_res, total in sorted(final, key=lambda x: x[1], reverse=True):
      print(cam, avg_res, total)

def obs_by_day(args):
   year = args.year
   obs_dir = "/mnt/f/EVENTS/OBS/DAYS/"
   obs_wild = obs_dir + year + "*.json"
   print(obs_wild)
   ev_files = glob.glob(obs_wild)
   for ef in ev_files:
      data = load_json_file(ef)
      print(ef, len(data))


def events_by_day(args):
   year = args.year
   ev_file = "/mnt/f/EVENTS/DBS/{:s}_ALL_EVENTS.json".format(year)
   ev_data = load_json_file(ev_file)
   total = len(ev_data)

   days = []
   day_values = []
   hours = []
   hour_values = []
   totals_per_hour = []
   by_day = {}
   by_hour = {}
   for e in ev_data:
      day = e['event_day']
      if type(e['start_datetime']) is list :
         if len(e['start_datetime']) > 0: 
            hour = min(e['start_datetime']).split(":")[0]  + ":00:00"
         else:
            print(e)
            print("ERR no start_datetime")

      else:
         print(e)
         input("ERR")
      #print(hour)
      #input("X")
      if day not in by_day:
        by_day[day] = 0
      else:
        by_day[day] += 1
      if hour not in by_hour:
        by_hour[hour] = 0
      else:
        by_hour[hour] += 1


   for day in sorted(by_day.keys()):
      print(day, by_day[day]) 
      days.append(day)
      day_values.append(by_day[day])

   for hour in sorted(by_hour.keys()):
      if "2023" in hour:
         print(hour, by_hour[hour]) 
         hours.append(hour)
         hour_values.append(by_hour[hour])

   #scatter(hours,by_hour,"2023_events_by_hour.png",title="2023 Events By Hour")
   print("HOURS", hours)
   print("by_hour", hour_values)
   line(hours,hour_values,"/mnt/f/EVENTS/2023_events_by_hour.png",title="2023 Events By Hour")
   line(days,day_values,"/mnt/f/EVENTS/2023_events_by_day.png",title="2023 Events By Day")

   print("The Year for this report is:", year)
   print("The total number of events for the year is:", total)

def get_missing_ints(obs, obs_data):
   print("YO")


def line(xs,ys,outfile,title=""):
   #outfile = resource + ".jpg"
   fig = px.line(x=xs, y=ys)
   fig.write_image(outfile)
   if PREVIEW is True:
      fig.show()

   js_temp = get_template("events-by-day-plotly.html")
   js_temp = js_temp.replace("{X_DATA}", str(xs))
   js_temp = js_temp.replace("{Y_DATA}", str(ys))
   print(outfile)
   html_outfile = outfile.replace(".png", ".html")
   fpo = open(html_outfile, "w")
   fpo.write(js_temp)
   fpo.close()
   print("WROTE", html_outfile)

   return(js_temp)

def scatter(xs,ys,outfile,title=""):
   #outfile = resource + ".jpg"
   fig = px.scatter(x=xs, y=ys)
   fig.write_image(outfile)
   if PREVIEW is True:
      fig.show()

def parse_arguments():

   parser = argparse.ArgumentParser(description='ALLSKY7 Plot Maker')
   parser.add_argument('resource') 
   parser.add_argument('-p', '--plot_type') 
   parser.add_argument('-d', '--date') 
   parser.add_argument('-y', '--year') 
   parser.add_argument('-m', '--month') 
   args = parser.parse_args()
   print(args, args.resource, args.plot_type)
   return(args)

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

if __name__ == "__main__":
   args = parse_arguments()
   if args.plot_type == "event_light_curves":
      event_light_curves(args.resource)
   if args.plot_type == "events_by_day":
      events_by_day(args)
   if args.plot_type == "obs_by_day":
      obs_by_day(args)
   if args.plot_type == "res_for_day":
      res_for_day(args)
