from lib.FileIO import get_proc_days, get_day_stats, get_day_files , load_json_file, get_trims_for_file, get_days, save_json_file, cfe

MS_DIR = "/mnt/ams2/stations/data/"

def multi_station_meteor_detail (json_conf, form):
   print("<h1>MSMD</h1>")
   day = form.getvalue("day")
   meteor = form.getvalue("meteor")
   red_file = meteor.replace(".json", "-reduced.json")
   red_data = load_json_file(red_file)
   print("My Station:" + str(red_data['station_name']) + "<BR>")    
   print("My Cam ID:" + str(red_data['device_name']) + "<BR>")    
   print("My Event Start Time:" + str(red_data['event_start_time']) + "<BR>")    
   print("My AZs:" + str(red_data['metconf']['azs']) + "<BR>")    
   print("My ELs:" + str(red_data['metconf']['els']) + "<BR>")    
   print("My RAs:" + str(red_data['metconf']['ras']) + "<BR>")    
   print("My DECs:" + str(red_data['metconf']['decs']) + "<BR>")    
   print("My Times:" + str(red_data['metconf']['times']) + "<BR>")    
   print("My Intensity:" + str(red_data['metconf']['intensity']) + "<BR>")    
   msms = load_json_file(MS_DIR + day + "-multi_station_data.json")
   msm = msms[meteor]
   #print(msm)
   for station_id in msm['obs']:
      print(station_id + "<BR>")
      print(str(msm['obs'][station_id]['sd_video_file']) + "<BR>")
      if "azs" in msm['obs'][station_id]:
         print(str(msm['obs'][station_id]['azs']) + "<BR>")
         print(str(msm['obs'][station_id]['els']) + "<BR>")
         print(str(msm['obs'][station_id]['ras']) + "<BR>")
         print(str(msm['obs'][station_id]['decs']) + "<BR>")
         print(str(msm['obs'][station_id]['times']) + "<BR>")
         print(str(msm['obs'][station_id]['intensity']) + "<BR>")
      else:
         print("Reduction data missing for : " + station_id + str(msm['obs'][station_id]))
def multi_station_meteors (json_conf, form):

   day = form.getvalue("day")
   msms = load_json_file(MS_DIR + day + "-multi_station_data.json")
   print("<h1>")
   print(str(len(msms)))
   print("Multi-station meteors for " + str(day) + "</h1>")
   for msm in msms:
      stack_file = msm.replace(".json", "-stacked.png")
      print("<a href=webUI.py?cmd=msmd&meteor=" + msm + "&day=" + str(day) + "><img width=320 height=180 src=" + stack_file + "></a>")


