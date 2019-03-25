import glob
from lib.FileIO import load_json_file


def solutions(json_conf, form):
   print("<h2>Solutions</h2>")
   day = form.getvalue("day") 
   scmd = form.getvalue("scmd")
   if scmd == 'view_event':
      view_event(json_conf,form)
   dir_str = "/mnt/ams2/multi_station/" + day + "/*solved.json"
   files = glob.glob(dir_str)
   for file in files:
      fig = file.replace("-solved.json", "-solved-fig2.png")
     
      print("<a href=webUI.py?cmd=solutions&scmd=view_event&solved_file=" + file + "><img src=" + fig + "></a>")

def view_event(json_conf,form):
   (st, sr, sc, et, er, ec) = div_table_vars()
   solved_file = form.getvalue("solved_file")
   fig = solved_file.replace("-solved.json", "-solved-fig2.png")


   meteor = load_json_file(solved_file)
   print("<img src=" + fig + "><br>")
   reduction_file_obs1 = meteor['obs1']['reduction_file']
   meteor_json = load_json_file(reduction_file_obs1)
   sd_stack_obs1 = meteor_json['sd_stack']
   sd_video_file_obs1 = meteor_json['sd_video_file']
   if "stacked" not in sd_stack_obs1:
      sd_stack_obs1 = sd_stack_obs1.replace(".png", "-stacked.png")
   print("<img src=" + sd_stack_obs1 + "><br>")

   print("<a href=/pycgi/webUI.py?cmd=reduce&video_file=" + sd_video_file_obs1 + ">View Meteor Reduction</a>")
   kml_file = solved_file.replace(".json", ".kml")
   print("<a href=" + kml_file + ">KML</a>")


   for key in meteor['meteor_points_lat_lon']:
      print("<P>")
      print(st + sr)
      print(sc + "Combo" + ec + sc + "Frame Time" + ec + sc + "Frame Num" + ec + sc + "Longitude" + ec + sc + "Latitude" + ec + sc + "Altitude" + ec + er)
      for point in meteor['meteor_points_lat_lon'][key]:
         ft, fn, mlon, mlat, malt = point 
         #print(str(mlat) + "," + str(mlon) + "," + str(malt) + "<BR>")
         print(sr + sc + key + ec + sc + ft + ec + sc + fn + ec + sc + str(mlon) + ec + sc + str(mlat) + ec + sc + str(malt) + ec + er)
      print(et)


   for key in meteor:
      if "obs" in key:
         obs_num = key.replace("obs", "")
         print("<B>Observer " + obs_num + "</B><BR>")
      for okey in meteor[key]:
         if okey == 'lat' or okey == 'lon' or okey == 'alt' or okey == 'station_name' :
            print("<B>" + okey + ":</B> " + str(meteor[key][okey]) + "<BR>")


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

