import glob
from lib.FileIO import load_json_file, cfe

def solutions(json_conf, form):
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

   reduction_files = []
   mp4_files = []
   observers = []

   for key in meteor['sync_frames']:
      master_key = key
   observers.append(master_key)
   for key in meteor['vel_data']:
      if key != master_key: 
         observers.append(key)
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
        
         print("<figure><a href=" + mp4_file + "><img width=480 height=270 src=" + stack_file + "><figcaption>" + desc + "</figcaption></a></figure>")

   print("<div style='clear: both'></div>")
   print("<figure><img width=480 src=" + fig + "><figcaption>3D Track</figcaption></figure>")
   print("<figure><img width=480 src=" + fig_vel + "><figcaption>Velocity From Start</figcaption></figure>")
   print("<div style='clear: both'></div>")
   reduction_file_obs1 = meteor['obs1']['reduction_file']
   meteor_json = load_json_file(reduction_file_obs1)
   sd_stack_obs1 = meteor_json['sd_stack']
   sd_video_file_obs1 = meteor_json['sd_video_file']
   if "stacked" not in sd_stack_obs1:
      sd_stack_obs1 = sd_stack_obs1.replace(".png", "-stacked.png")
   #print("<figure><img src=" + sd_stack_obs1 + "><caption></caption></figure>")

   #print("<a href=/pycgi/webUI.py?cmd=reduce&video_file=" + sd_video_file_obs1 + ">View Meteor Reduction</a>")
   kml_file = solved_file.replace(".json", ".kml")
   print("<a href=" + kml_file + ">Event KML</a>")

   print("<P>")
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

