import glob
from lib.FileIO import load_json_file, cfe, save_json_file

        #if isinstance(obj, np.integer):
        #elif isinstance(obj, np.floating):
        #elif isinstance(obj, np.ndarray):
        #elif isinstance(obj, datetime.datetime):


def make_sol_index(output_dir):
   solutions = {}
   dirs = glob.glob(output_dir + "*")
   for dir in dirs:
      el = dir.split("/")
      fn = el[-1]
      json_file = dir + "/" + fn + ".json" 
      if cfe(json_file) == 1:
         try:
            json_data = load_json_file(json_file)
         except:
            print("BAD JSON:", json_file, "<BR>")
      solutions[fn] = {}
     
   save_json_file("/var/www/html/solutions.json", solutions) 

def sol_detail(json_conf, form):
   print("<h3>Video Meteor Event</h3>")
   event = form.getvalue("event")
   open_key = form.getvalue("open_key")
   event_dir = "/home/ams/dvida/WesternMeteorPyLib/wmpl/Trajectory/output/" + event + "/"
   event_url = "/output/" + event + "/"
   json_file = event_dir + event + ".json"
   json_data = load_json_file(json_file)
   for key in sorted(json_data):
      print(key + "<BR>")
      if open_key == key:
         for okey in json_data[key]:
            print(" &nbsp; - " + okey + "<BR>")
            

   summary_img = event_url + event + "-all.jpg"
   print("<img src=" + summary_img + ">")

def solutions(json_conf, form):
   sol_dir = "/var/www/html/output/*"
   make_sol_index(sol_dir)
   dirs = glob.glob(sol_dir)
   for dir in sorted(dirs, reverse=True):
      el = dir.split("/")
      fd = el[-1]
      orb = dir + "/" + fd + "_orbit_top.png"
      if cfe(orb) == 1:
         link = "/viewEvent.html?event=" + fd 
         orb_url = "/output/" + fd + "/thumbs/" + fd + "_orbit_top.png"
         print("<figure><a href=" + link + "><img width=300 height=300 src=" + orb_url + "></a><figcaption>" + fd + "</figcaption></figure>")
   print("<div style='clear: both'></div>")

def solutions_old(json_conf, form):
   print("<h2>Solutions</h2>")
   

   day = form.getvalue("day") 
   scmd = form.getvalue("scmd")
   if scmd == 'view_event':
      view_event(json_conf,form)
      return()
   if day is not None:
      dir_str = "/mnt/ams2/multi_station/" + day + "/*solved.json"
      files = glob.glob(dir_str)
      for file in files:
         fig = file.replace("-solved.json", "-solved-fig2.png")
     
         print("<a href=webUI.py?cmd=solutions&scmd=view_event&solved_file=" + file + "><img src=" + fig + "></a>")
   else:
      msdirs = sorted(glob.glob("/mnt/ams2/multi_station/*"), reverse=True)
      for msdir in msdirs:
         solutions = glob.glob(msdir + "/*solved.json")
         day_desc = msdir[-10:]
         if len(solutions) > 0:
            print(day_desc + " " + str(len(solutions)) + " solved meteors<BR>")
         for solution in solutions:
            fig1 = solution.replace(".json", "-fig2.png")
            fig2 = solution.replace(".json", "-fig_vel.png")

            el = solution.split("/")
            desc = el[-1] 
            desc = desc.replace("-solved.json", "")
            print("<B>" + desc + "</B><BR>")

            print("<a href=webUI.py?cmd=solutions&scmd=view_event&solved_file=" + solution + "><img src=" + fig1 + "><img src=" + fig2 + "></a><BR>")

def view_event(json_conf,form):
   (st, sr, sc, et, er, ec) = div_table_vars()
   solved_file = form.getvalue("solved_file")
   fig = solved_file.replace("-solved.json", "-solved-fig2.png")
   fig_vel = solved_file.replace("-solved.json", "-solved-fig_vel.png")
   print("<a href=" + solved_file + ">" + solved_file + "</a><br>")

   meteor = load_json_file(solved_file)

   start_point = meteor['final_solution']['meteor_start_point']
   end_point = meteor['final_solution']['meteor_end_point']
   hund_point = meteor['final_solution']['100km']
   zero_point = meteor['final_solution']['0km']
   radiant_az = meteor['final_solution']['radiant_az']
   radiant_el = meteor['final_solution']['radiant_el']
   radiant_ra = meteor['final_solution']['radiant_ra']
   radiant_dec = meteor['final_solution']['radiant_dec']

   event_start_time = ""
   event_duration = ""
   event_avg_vel = ""
   event_int_vel = ""
   peak_mag = ""


   reduction_files = []
   mp4_files = []
   observers = []

   for key in meteor['sync_frames']:
      master_key = key
   observers.append(master_key)
   for key in meteor['vel_data']:
      if key != master_key: 
         observers.append(key)
   print("<div>")
   solve_cmd = "./mikeSolve.py "
   for key in meteor:
      if "obs" in key:
         red = meteor[key]['reduction_file']
         reduction_files.append(red)
         mp4_file = red.replace("-reduced.json", ".mp4" )
         stack_file = red.replace(".json", "-stacked.png" )
         if cfe(mp4_file) == 0:
            mp4_file = red.replace(".json", ".mp4" )
         if cfe(stack_file) == 0:
            stack_file = red.replace("-reduced.json", "-stacked.png" )
         el = stack_file.split("/")
         desc = el[-1]
        
         #print("<div style=\"border: 1px solid white\"><figure><a href=" + mp4_file + "><img width=480 height=270 src=" + stack_file + "></figcaption>" + desc + "</figcaption></a></figure>")
         print("<div style=\"border: 1px solid white; float: left\"><a href=" + mp4_file + "><figcaption><img width=480 height=270 src=" + stack_file + "></figcaption>" + desc + "</figcaption></a></figure>")
         reduced = load_json_file(red)
         print("<BR>")
         print(reduced['station_name'] + "<BR>")
         print("<a href=" + red+ ">Reduction File</a>" + "<BR>")
         solve_cmd = solve_cmd + red + " " 
         print(st)
         for fd in reduced['meteor_frame_data']:
            ft, fn, x, y, w, h, mxpx, ra, dec, az, el = fd
            print(sr + sc + str(ft) + ec + sc + str(fn) + ec + sc + str(x) + "," + str(y) +  ec + sc + str(mxpx) + ec + sc + str(ra)[0:6] + "/" + str(dec)[0:6] + ec + sc + str(az)[0:6] + "/" + str(el)[0:6] + ec + er)
         print(et)
         print("</div>")

   print("</div>")
   print("<div style='clear: both'></div>")
   print("Resolve command: " +  solve_cmd + "<BR>")
   print("<figure><img width=480 src=" + fig + "><figcaption>3D Track</figcaption></figure>")
   print("<figure><img width=480 src=" + fig_vel + "><figcaption>Velocity From Start</figcaption></figure>")
   print("<div style='clear: both'></div>")

   print("<B>Event Info</B>")
   print(st)
   print(sr + sc + "Event Start Time:" + ec + sc + str(event_start_time) + ec + er )
   print(sr + sc + "Event Duration:" + ec + sc + str(event_duration) + ec + er )
   print(sr + sc + "Average Velocity:" + ec + sc + str(event_avg_vel) + ec + er )
   print(sr + sc + "Initial Velocity:" + ec + sc + str(event_int_vel) + ec + er )
   print(sr + sc + "Peak Magnitude:" + ec + sc + str(peak_mag) + ec + er )
   print(sr + sc + "Start Point:" + ec + sc + str(start_point) + ec + er )
   print(sr + sc + "End Point:" + ec + sc + str(end_point) + ec + er )
   print(sr + sc + "100KM Point:" + ec + sc + str(hund_point) + ec + er )
   print(sr + sc + "0KM Point:" + ec + sc + str(zero_point) + ec + er )
   print(sr + sc + "Event Type:" + ec + sc + str("Meteor or Satellite") + ec + er )
   print(sr + sc + "Classification" + ec + sc + str("Shower or Sat Name ") + ec + er )
   print(et)

   reduction_file_obs1 = meteor['obs1']['reduction_file']
   meteor_json = load_json_file(reduction_file_obs1)
   sd_stack_obs1 = meteor_json['sd_stack']
   sd_video_file_obs1 = meteor_json['sd_video_file']
   if "stacked" not in sd_stack_obs1:
      sd_stack_obs1 = sd_stack_obs1.replace(".png", "-stacked.png")
   #print("<figure><img src=" + sd_stack_obs1 + "><caption></caption></figure>")

   print("<a href=/pycgi/webUI.py?cmd=reduce&video_file=" + sd_video_file_obs1 + ">View Meteor Reduction</a>")
   kml_file = solved_file.replace(".json", ".kml")
   print("<a href=" + kml_file + ">Event KML</a>")

   print("<P>")
   print("<B>Orbit Info</B>")

   print("<P>")
   print("<B>Syncronized Frames</B>")
   print(st + sr)
   print(sc + "Frame Time" + ec )
   for obs in observers:
      ttt, key_desc = obs.split("-")
      print(sc + obs + " point" + ec + sc + obs + " velocity" + ec)
   print(er)
      


   for master_key in meteor['sync_frames']:
      for ekey in meteor['sync_frames'][master_key]:
         print(sr)
         oc = 0
         for obs in observers:
            ms_fl_lon = master_key + "_lon"
            fl_ft = master_key + "_ft"
            fl_fn = obs + "_fn"
            fl_lon = obs + "_lon"
            fl_lat = obs + "_lat"
            fl_alt = obs + "_alt"
            fl_dfs = obs + "_dfs"
            fl_vfs = obs + "_vfs"
            if fl_lon in meteor['sync_frames'][master_key][ekey]:
               ft = meteor['sync_frames'][master_key][ekey][fl_ft]
               fn = meteor['sync_frames'][master_key][ekey][fl_fn]
               lon = meteor['sync_frames'][master_key][ekey][fl_lon]
               lat = meteor['sync_frames'][master_key][ekey][fl_lat]
               alt = meteor['sync_frames'][master_key][ekey][fl_alt]
               dfs = meteor['sync_frames'][master_key][ekey][fl_dfs]
               vfs = meteor['sync_frames'][master_key][ekey][fl_vfs]
               if obs == master_key :
                  print(sc + str(ft) +ec + sc + str(lat)[0:6] + " " + str(lon)[0:6] + " "  + str(alt)[0:6] + " " + ec + sc+ str(vfs) + ec)
               else:
                  print(sc + str(lon)[0:6] + " " + str(lat)[0:6] + " " + str(alt)[0:6] + ec + sc+ str(vfs)[0:6] + ec)
                  if fl_lon not in meteor['sync_frames'][master_key][ekey] :
                     print(sc + "&nbsp;" + ec + sc+ "&nbsp;" + ec)
            else:
               if ms_fl_lon in meteor['sync_frames'][master_key][ekey] :
                  print(sc + "&nbsp;" + ec + sc+ "&nbsp;" + ec)
            oc = oc + 1
         print(er)
   print(et)
         

   #for key in meteor['meteor_points_lat_lon']:
   #   print("<P>")
   #   print(st + sr)
   #   print(sc + "Combo" + ec + sc + "Frame Time" + ec + sc + "Frame Num" + ec + sc + "Longitude" + ec + sc + "Latitude" + ec + sc + "Altitude" + ec + er)
      #for point in meteor['meteor_points_lat_lon'][key]:
         #ft, fn, mlon, mlat, malt = point 
         #print(str(mlat) + "," + str(mlon) + "," + str(malt) + "<BR>")
         #print(sr + sc + key + ec + sc + ft + ec + sc + fn + ec + sc + str(mlon) + ec + sc + str(mlat) + ec + sc + str(malt) + ec + er)
      #print(et)


   #for key in meteor:
   #   if "obs" in key:
   #      obs_num = key.replace("obs", "")
   #      print("<B>Observer " + obs_num + "</B><BR>")
   #   for okey in meteor[key]:
   #      if okey == 'lat' or okey == 'lon' or okey == 'alt' or okey == 'station_name' :
   #         print("<B>" + okey + ":</B> " + str(meteor[key][okey]) + "<BR>")


def div_table_vars():
   start_table = """
      <div class="divTable" style="border: 1px solid #000;" >
      <div class="divTableBody">
   """
   start_row = """
      <div class="divTableRow">
   """
   start_cell = """
      <div class="divTableCell">
   """
   end_table = "</div></div>"
   end_row = "</div>"
   end_cell= "</div>"
   return(start_table, start_row, start_cell, end_table, end_row, end_cell)

