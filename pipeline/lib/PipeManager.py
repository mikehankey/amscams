"""

   multi-station functions here

"""
import time
import cv2
import numpy as np
import os
from lib.PipeTrans import vid_from_imgs
from lib.PipeVideo import ffprobe , load_frames_simple 
from lib.DEFAULTS import *
import glob
from lib.PipeUtil import cfe, load_json_file, save_json_file, convert_filename_to_date_cam
from lib.PipeLIVE import det_table, swap_pic_to_vid
from lib.PipeReport import mk_css
from lib.PipeDetect import get_trim_num , detect_meteor_in_clip, analyze_object
from datetime import datetime
import datetime as dt
MLN_CACHE_DIR = "/mnt/ams2/MLN_CACHE/"

#/mnt/ams2/meteor_archive/AMS2/LIVE/METEORS/2020_08_13/2020_08_13-AMS2-METEORS.json

def check_add_event(events, meteor):
   found = 0
   file = meteor['hd_file']
   station = meteor['station']
   (f_datetime, cam, f_date_str,fy,fmin,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
   ekey = file.split("/")[-1]
   trim_num = get_trim_num(file)
   trim_num = trim_num.replace("HDmeteor", "")
   trim_num = int(trim_num)
   extra_sec = trim_num / 25
   event_start_time = f_datetime + dt.timedelta(0,extra_sec)

   if len(events) == 0:
      events = add_event(events, ekey, station, file, event_start_time)
      print("FIRST EVENT:", len(events))
      return(events)

   new_events = []
   for event in events:
      time_diff = abs((f_datetime - event['start_times'][-1]).total_seconds())
      if time_diff < 60:
         print("TIME DIFF:", time_diff)
         print("UPDATE FOUND EVENT:", len(events))
         up_event = update_event(event, ekey, station, file, event_start_time)
         new_events.append(up_event)
         found = 1
      else:
         new_events.append(event)

   if found == 1:
      print("RETURN UPDATED EVENTS!")
      return(new_events)

   # EVENT NOT FOUND MAKE NEW ONE
   print("NOT FOUND ADD NEW EVENT:", len(events))
   events = add_event(events, ekey, station, file, event_start_time)
   return(events)



def add_event(events, ekey, station, file, event_start_time):
   print("ADD EVENTS:", len(events), ekey)
   event = {}
   event['stations'] = []
   event['stations'].append(station)
   event['files'] = []
   event['files'].append(file)
   event['start_times'] = []
   event['start_times'].append(event_start_time)
   events.append(event)
   return(events)

def update_event(event, ekey, station, file, event_start_time):
   print("UPDATE EVENT:", ekey)
   event['stations'].append(station)
   event['files'].append(file)
   event['start_times'].append(event_start_time)
   return(event)

def sync_event_frames(event, ofns, oints):

   print("SYNC:", event)
   max_len = 0
   i = 0
   for ofn in ofns:
      print("OFN:", ofn, len(ofn), max_len)
      print("OINT:", oints[i], len(ofn), max_len)
      dur = len(ofn)
      if dur > max_len:
         dom_ofn = i
         max_len = dur
      i += 1

   dom_br_fr = sorted( [(x,i) for (i,x) in enumerate(oints[dom_ofn])], reverse=True )[:1] 
   print("MAX FRAMES:", max_len)
   print("DOM FNS:", ofns[dom_ofn])
   print("DOM MAG:", oints[dom_ofn])
   print("DOM BR FR:", dom_br_fr)
   new_ofns_list = []
   for i in range(0,len(ofns)):
      if i == dom_br_fr:
         print(i, "Skip dom")
         print(i, "DOM BRIGHTEST ", dom_br_fr)
      else:
         br_fr = sorted( [(x,i) for (i,x) in enumerate(oints[i])], reverse=True )[:1] 
         start_offset = dom_br_fr[0][1] - br_fr[0][1]
         end_offset = len(ofns[dom_ofn]) - len(ofns[i]) - start_offset
         new_ofns = []
         for c in range(0,start_offset):
            new_ofn = ofns[i][0] - start_offset + c
            new_ofns.append(new_ofn)
         for c in range(0,len(ofns[i])):
            new_ofns.append(ofns[i][c])
         for c in range(0,end_offset):
            new_ofn = ofns[i][-1] + c
            new_ofns.append(new_ofn)

         print(i, "THIS BRIGHTEST s/e offsets", br_fr, start_offset, end_offset)
         print(i, "OLD FR:", ofns[i])
         print(i, "NEW FR:", new_ofns)
         new_ofns_list.append(new_ofns)
   event['syncd_ofns'] = new_ofns_list
   

   return(event)

def multi_station_video(event ):
   VID_DIR = "/mnt/ams2/MLN_CACHE/VIDS/"
   print("MSM", event)
   mframes = {}
   mjsons = {}
   fc = 0
   ofns = []
   oints = []
   for file in event['files']:
      station = event['stations'][fc]
      day = file[0:10]
      print(station)
      print(event['start_times'][fc])
      print(file)
      vid_file = VID_DIR + file
      print("VF:", vid_file)
      json_file = vid_file.replace(".mp4", ".json")
      js_fn = json_file.split("/")[-1]
      crop_file = vid_file.replace(".mp4", "-crop.mp4")
      cf_fn = crop_file.split("/")[-1]
      if cfe(json_file) == 0:
         cmd= "cp /mnt/archive.allsky.tv/" + station + "/LIVE/METEORS/" + day + "/" + js_fn + " " + json_file
         print(cmd)
         os.system(cmd)
      if cfe(crop_file) == 0:
         cmd= "cp /mnt/archive.allsky.tv/" + station + "/LIVE/METEORS/" + day + "/" + cf_fn + " " + crop_file 
         print(cmd)
         os.system(cmd)
      mjsons[json_file] = load_json_file(json_file)
      cropbox_1080 = mjsons[json_file]['cropbox_1080']
      hd_objects, frames = detect_meteor_in_clip(crop_file, None, 0, cropbox_1080[0], cropbox_1080[1], 0)
      mjsons[json_file]['hd_meteors'] = []
      hd_meteors = []
      for obj in hd_objects:
         hd_objects[obj] = analyze_object(hd_objects[obj])
            
         if hd_objects[obj]['report']['meteor'] == 1:
            mjsons[json_file]['hd_meteors'].append(hd_objects[obj])
            hd_meteors.append(hd_objects[obj])
         

    

      mjs=mjsons[json_file]
      if len(hd_meteors) == 0:
         print(hd_objects)
         exit()
      ofns.append(mjs['hd_meteors'][0]['ofns'])
      oints.append(mjs['hd_meteors'][0]['oint'])
      mframes[file] = load_frames_simple(vid_file)
      print("FRAMES:", len(mframes[file]))
      fc += 1 
   event = sync_event_frames(event, ofns, oints)
   event['ofns'] = ofns
   event['oints'] = ofns

   fc = 0
   for file in mframes:
      print("ORIG FRAMES:", event['ofns'])
      print("SYNC FRAMES:", event['syncd_ofns'])
      print("FILE:", file)
      print("FRAMES:", len(mframes[file]))
      sf = event['syncd_ofns'][fc][0]
      ef = event['syncd_ofns'][fc][-1]


      print("SF/EF:", sf, ef)
      temp_frames = mframes[file][sf:ef]
      #temp_frames = mframes[file]
      frc = 0
      for frame in temp_frames:
         cv2.putText(frame, str(frc),  (40,40), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 255, 255), 1)
         cv2.imshow('pepe', frame)
         cv2.waitKey(0)
         frc += 1
      fc += 1

def multi_station_meteors(day):
   cluster_one = ['AMS1', 'AMS7', 'AMS9', 'AMS15']
   event_file = "events.json"
   if cfe(event_file) == 1:
      events = load_json_file(event_file)
   else:
      file = MLN_CACHE_DIR + day + "-all.json" 
      meteors = load_json_file(file) 
      events = []

      for meteor in meteors:
         if meteor['station'] in cluster_one:
            events = check_add_event(events, meteor)

      fevents = []
      for event in events:
         nst = []
     
         for start_times in event['start_times']:
            nst.append(str(start_times) )
         event['start_times'] = nst
         fevents.append(event)

      print("FINAL EVENTS:", len(events) )
      print("FINAL FEVENTS:", len(fevents) )
      save_json_file("events.json", fevents)
      print("events.json")

   for event in events: 
      if len(event['stations']) >= 2:
         if len(set(event['stations'])) >= 2:
            print("MULTI STATION EVENT:", set(event['stations']))
            multi_station_video(event)  
         else:
            print("MULTI CAMERA EVENT:", set(event['stations']))

def det_table_all(urls , type='dur'):
   rpt = ""
   uc = 0
   if type == 'dur':
      temp = sorted(urls, key=lambda x: x[2], reverse=True)
      print("SORT BY DUR!")
   if type == 'mag':
      
      print("SORT BY MAG!")
      temp = sorted(urls, key=lambda x: x[3], reverse=True)

   for station, file, dur,mag,fns in temp:
      vid_url = file
      crop_vid_url = file.replace(".mp4", "-crop-tn.mp4")
      id = vid_url.split("/")[-1]
      img_url = vid_url.replace(".mp4", "-tn.jpg")
      crop_img_url = vid_url.replace(".mp4", "-crop-tn.jpg")

      rpt += "<div class='float_div' id='" + id + "'>"

      link = "<a href=\"javascript:swap_pic_to_vid('" + id + "', '" + crop_vid_url + "')\">"
      del_link = "<A href=/pycgi/webUI.py?cmd=admin_logger&hd_file=" + file + "&station=" + station + "&issue=del>DEL</a>"
      rpt += link + """
         <img title="Meteor" src=\"""" + img_url + """\" onmouseover="this.src='""" + crop_img_url + """'" onmouseout="this.src='""" + img_url + """'" /></a>
      """
      mdate = id[0:20]
      rpt += "<br><label style='text-align: center'>" + link + mdate + "</a> " + str(dur) + " " + str(mag) + "<br>"
      rpt += del_link + "<br>"

      rpt += "</label></div>"

      #rpt += "<div class='float_div'>"
      #rpt += "<img src=" + img + ">"
      #link = "<a href=" + mf + ">"
      #rpt += "<br><label style='text-align: center'>" + link + fn + "</a> <br>"
      #rpt += "</label></div>"
      uc += 1

   return(rpt)


def best_of(days):
   log = open("/mnt/ams2/admin_logger/log.txt")
   bad_files = {}
   for line in log:
      data = line.split(",")
      if len(data) == 3:
         st, fl, issue = line.split(",")
         fln = fl.split("/")[-1] 
         bad_files[fln] = st

   #days = [ '2020_08_10', '2020_08_11', '2020_08_12', '2020_08_13' ]
   all_meteors = []
   day_counter = {}
   for day in days:
      file = MLN_CACHE_DIR + day + "-all.json" 
      day_data = load_json_file(file)
      for data in day_data:
         station = data['station']
         fns = data['fns']
         print("FNS:", fns)

         if day not in day_counter:
            day_counter[day] = {}
         if station not in day_counter[day]:
            day_counter[day][station] = 0
         else:
            day_counter[day][station] += 1
         if data['hd_file'] not in bad_files:

            all_meteors.append(data)
   print("TOTAL METEORS:", len(all_meteors))
   #exit()
 

   for day in day_counter:
      for station in day_counter[day]:
         print(day, station, day_counter[day][station])

   ranked = []
   mfiles = []
   minfo = []
   for meteor in all_meteors:
      if "hd_file" in meteor:
         file = meteor['hd_file']
         dur = len(meteor['xs'])
         station = meteor['station']
         fns = meteor['fns']
         intensity = np.max(meteor['ints'])
         day = file[0:10]
         url = "http://archive.allsky.tv/" + station + "/LIVE/METEORS/" + day + "/" + file
         
         ranked.append((station, url, dur, intensity,fns))
         #mfiles.append(url)
         #minfo.append(dur)
      else:
         print("*** BAD:", meteor)
         exit()

   head = mk_css()
   head += swap_pic_to_vid()

   temp = sorted(ranked, key=lambda x: x[2], reverse=True)

   table = det_table_all(ranked)
   out = open("/mnt/ams2/bestof-dur.html", "w")
   out.write(head)
   out.write(table)
   out.close()

   table = det_table_all(ranked, 'mag')
   out = open("/mnt/ams2/bestof-mag.html", "w")
   temp = sorted(ranked, key=lambda x: x[3], reverse=True)
   out.write(head)
   out.write(table)
   out.close()

   for meteor in temp:
      if "hd_file" not in meteor:
         foo = "bar"
         #print("*** BEST:", meteor)
      else:
         print("*** ERROR:", meteor)
         exit()
   print ("/mnt/ams2/bestof-mag.html")
   print ("/mnt/ams2/bestof-dur.html")

   #make video lists for top 25 longest that are not in brightest etc

   longest = sorted(ranked, key=lambda x: x[2], reverse=True)[0:30]
   brightest = sorted(ranked, key=lambda x: x[3], reverse=True)[0:30]
   idx = {}
   for station, url, dur, mag,fns in brightest:
      idx[url] = 1

   list = ""
   local_dir = "/mnt/ams2/MLN_CACHE/VIDS/" 
   trim_dir = "/mnt/ams2/MLN_CACHE/VIDS/TRIM/" 
   longest = sorted(longest, key=lambda x: x[2], reverse=False)
   brightest = sorted(brightest, key=lambda x: x[3], reverse=False)

   bad = {}

   for station, url, dur, intensity,fns in longest:
      fn = url.split("/")[-1]
      local_file = "/mnt/ams2/MLN_CACHE/VIDS/" + fn
      print(url, local_file)
      if cfe(local_file) == 0:
         cmd = "wget " + url + " -O " + local_dir + fn
         print("GET:", cmd)
         os.system(cmd)
      else:
         print("SKIP:")

      trim_file = "/mnt/ams2/MLN_CACHE/VIDS/TRIM/" + fn
      if cfe(trim_file) == 0:
         print("FFTRIM", local_file, trim_file)
         first_frame =  fns[0]
         w,h,tf = ffprobe(local_file)
         if fns[0] >= 10:
            start = fns[0] - 15
            if start < 0:
               start = 0
         else :
            start = 0
         end_buf = tf - fns[-1]  
         if end_buf >= 20:
            end = fns[-1] + 10
         if end > int(tf):
            end = int(tf)
         

         if fns[0] < 5:
            bad[trim_file] = 1
       
         cmd = "/usr/bin/ffmpeg -i " + local_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -vsync 0 -start_number " + str(start) + " -y " + trim_file 
         print(cmd)
         os.system(cmd)

      if url not in idx:
         list += "file '" + trim_file + "'\n"

   for station, url, dur, intensity,fns in brightest:
      fn = url.split("/")[-1]
      local_file = "/mnt/ams2/MLN_CACHE/VIDS/" + fn
      print(url, local_file)
      if cfe(local_file) == 0:
         cmd = "wget " + url + " -O " + local_dir + fn
         os.system(cmd)

      trim_file = "/mnt/ams2/MLN_CACHE/VIDS/TRIM/" + fn
      if cfe(trim_file) == 0:
         print("FFTRIM", local_file, trim_file)
         first_frame =  fns[0]
         if fns[0] >= 10:
            start = fns[0] - 10

         if fns[0] < 5:
            bad[trim_file] = 1

         end = fns[-1] + 10
       
         cmd = "/usr/bin/ffmpeg -i " + local_file + " -vf select='between(n\," + str(start) + "\," + str(end) + ")' -vsync 0 -start_number " + str(start) + " " + trim_file
         print(cmd)
         os.system(cmd)



      list += "file '" + trim_file + "'\n"

   local_list = "/mnt/ams2/MLN_CACHE/VIDS/list_longest.txt" 
   fp = open(local_list, "w")
   fp.write(list)
   fp.close()
   cmd = "/usr/bin/ffmpeg -re -f concat -safe 0 -i " + local_list + " /mnt/ams2/MLN_CACHE/FINAL/longest.mp4"
   print(cmd)
   os.system(cmd)

 

   exit()
   
def super_stack_list():
   stack_dir = "/mnt/ams2/MLN_CACHE/super_stacks/"
   all_stacks = []
   #for staion in 
   stacks = glob.glob(stack_dir + "*meteors.mp4")
   print(stack_dir + "*meteors.mp4")

   data = {}
   html = ""
   for stack in stacks:
      fn = stack.split("/")[-1]
 
      station, day, cam, tag = fn.split("-")
      if station not in data:
         data[station] = {}
      if cam not in data[station]:
         data[station][cam] = {}
         data[station][cam]['files'] = []
      data[station][cam]['files'].append(stack)
      print(fn)


   list = ""
   for station in data:
      print("STATION:", station)
      for cam in sorted(data[station].keys()):
         print("CAM:", cam)
         for file in sorted(data[station][cam]['files']):
            print("   ", file)
            #print("MIKE:", station, cam, file)
            list += "file '" + file + "'\n"
            ifn = file.replace(".mp4", ".jpg")
            html += "<img src=" + ifn + "><BR>"
   out = open("/mnt/ams2/MLN_CACHE/super_stacks/all.html", "w")
   out.write(html)
   fp = open("/mnt/ams2/MLN_CACHE/LISTS/super_stacks.txt", "w")
   fp.write (list)
   fp.close() 
   print("/mnt/ams2/MLN_CACHE/LISTS/super_stacks.txt")

def super_stacks_to_video():
   super_stack_list()
   exit()
   fps = 25
   stack_dir = "/mnt/ams2/MLN_CACHE/super_stacks/"
   os.system("rm tmp_vids/*")
   stack_vids = []
   for station in stations: 
      print(station)
      stacks = glob.glob(stack_dir + station + "*.jpg")
      for stack in stacks:
         stack720 = stack.replace(".jpg", "-720.jpg")
       
         if cfe(stack720) == 0:
            stack_img = cv2.imread(stack)
            stack_img720 = cv2.resize(stack_img, (1280,720))
            cv2.imwrite(stack720, stack_img720) 
         vid_of = stack.replace(".jpg", ".mp4")
         stack_vids.append(vid_of)
         if True:
         #if cfe(vid_of) == 0:
            ofn = vid_of.split("/")[-1]
            print(stack) 
            for i in range(0, fps):
               counter = '{:03d}'.format(i) 
               nf = stack.replace(".jpg", "-" + counter + ".jpg")
               nfn = nf.split("/")[-1]
               cmd = "cp " + stack720 + " tmp_vids/" +  nfn
               print(cmd)
               os.system(cmd)
            #make FFMPEG
            print("OUT:", vid_of)
            vid_from_imgs("tmp_vids/", vid_of )
            
            os.system("rm tmp_vids/*")

   cat_list = ""
   for stack_vid in sorted(stack_vids):
      cat_list += "file '" + stack_vid + "'\n"
   fp = open("tmp_vids/cat_list.txt", "w")
   fp.write(cat_list)
   fp.close()
   time.sleep(1)
   #cmd = "/usr/bin/ffmpeg -re -f concat -safe 0 -i /home/ams/amscams/pipeline/tmp_vids/cat_list.txt /mnt/ams2/MLN_CACHE/super_stacks/all_stations.mp4"
   #print(cmd)
   #os.system(cmd)
   super_stack_list()
      
 
def copy_super_stacks(day=None):
   for station in stations:
      station_dir = "/mnt/archive.allsky.tv/" + station + "/LIVE/METEORS/" + day + "/"

      # get super stacks
      super_files = glob.glob(station_dir + "*meteors.jpg")
      super_dir = "/mnt/ams2/MLN_CACHE/super_stacks/"
      for sf in super_files:
         sfn = sf.split("/")[-1]
         if cfe(super_dir + sfn) == 0:
            cmd = "cp " + sf + " " + super_dir + station + "-" + sfn
            print(cmd)
            os.system(cmd)
 

def mln_report(day=None):

   #now = dt.strptime(day, "%Y_%m_%d")
   no_data_stations = [] 
   all_meteors = []
   # yesterday = now - datetime.timedelta(days = 1)
   for station in stations:
      station_dir = "/mnt/archive.allsky.tv/" + station + "/LIVE/METEORS/" + day + "/"
      data_file = station_dir + day + "-" + station + "-METEORS.json"
      new_data_dir =  "/mnt/ams2/MLN_CACHE/DATA/" 
      if cfe(new_data_dir,1) == 0:
         os.makedirs(new_data_dir)
      new_data_file = new_data_dir + day + "-" + station + "-METEORS.json"
      cmd = "cp " + data_file + " " + new_data_file

      # get super stacks
      super_files = glob.glob(station_dir + "*meteors.jpg") 
      super_dir = "/mnt/ams2/MLN_CACHE/super_stacks/"
      for sf in super_files:
         sfn = sf.split("/")[-1]
         if cfe(super_dir + sfn) == 0:
            cmd = "cp " + sf + " " + super_dir + station + "-" + sfn
            os.system(cmd)
      
      print(cmd)
      if cfe(data_file) == 1:
         if cfe(new_data_file) == 0 :
            print(cmd)
            os.system(cmd) 
         else:
            print("We have no new data file?", new_data_file, data_file)
         print("LOAD:", new_data_file)
         if cfe(new_data_file) == 1:
            meteors = load_json_file (new_data_file)
            print(station, " METEORS: ", len(meteors))
            for meteor in meteors:
               meteor['station'] = station
               print("METEOR:", meteor)
               if "xs" in meteor:
                  print("GOOD!")
                  all_meteors.append(meteor)
      else:
         no_data_stations.append(station)
   print("SAVE:", MLN_CACHE_DIR + day + "-all.json")
   save_json_file(MLN_CACHE_DIR + day + "-all.json", all_meteors)
   ranked = []
   for meteor in all_meteors:
      if "hd_file" in meteor:
         file = meteor['hd_file']
         dur = len(meteor['xs'])
         station = meteor['station']
         fns = meteor['fns']
         intensity = np.max(meteor['ints'])
         day = file[0:10]
         url = "http://archive.allsky.tv/" + station + "/LIVE/METEORS/" + day + "/" + file

         ranked.append((station, url, dur, intensity,fns))
         #mfiles.append(url)
         #minfo.append(dur)
      else:
         print("*** BAD:", meteor)
         exit()

   head = mk_css()
   head += swap_pic_to_vid()

   temp = sorted(ranked, key=lambda x: x[2], reverse=True)

   table = det_table_all(ranked)
   year, mon, dom = day.split("_")
   out = open("/mnt/archive.allsky.tv/LIVE/" + year + "/" + day + ".html", "w")
   out.write(head)
   out.write(table)
   out.close()
 

def mln_best(day, days_after = 1) :
   all_meteors = load_json_file(MLN_CACHE_DIR + day + "-all.json")
   all_sorted = sorted(all_meteors, key=lambda k: len(k['xs']), reverse=True)
      

   html = "<h1>Meteors Last Night " + day + "</h1><ul>\n"

   for m in all_sorted:
      file = m['hd_file'].split("/")[-1]
      station = m['station']
      link = "https://archive.allsky.tv/" + station + "/LIVE/METEORS/" + file
      print(station, len(m['xs']), link)
      html += "<li><a href=" + link + ">" + station + " " + file + "</a></li>\n"
 
   html += "</ul>"
   all_file = "/mnt/archive.allsky.tv/LAST_NIGHT/" + day + ".html"
   fp = open(all_file, "w")
   fp.write(html)
   fp.close()
   print(all_file)
   
