"""

   multi-station functions here

"""
import os
from lib.PipeTrans import vid_from_imgs
from lib.DEFAULTS import *
import glob
from lib.PipeUtil import cfe, load_json_file, save_json_file
from lib.PipeLIVE import det_table, swap_pic_to_vid
from lib.PipeReport import mk_css

MLN_CACHE_DIR = "/mnt/ams2/MLN_CACHE/"

#/mnt/ams2/meteor_archive/AMS2/LIVE/METEORS/2020_08_13/2020_08_13-AMS2-METEORS.json

def det_table_all(urls):
   rpt = ""
   for file in sorted(urls):
      vid_url = file
      crop_vid_url = file.replace(".mp4", "-crop-tn.mp4")
      print("CROP VID:", crop_vid_url)
      id = vid_url.split("/")[-1]
      img_url = vid_url.replace(".mp4", "-tn.jpg")
      crop_img_url = vid_url.replace(".mp4", "-crop-tn.jpg")

      rpt += "<div class='float_div' id='" + id + "'>"

      link = "<a href=\"javascript:swap_pic_to_vid('" + id + "', '" + crop_vid_url + "')\">"
      rpt += link + """
         <img title="Meteor" src=\"""" + img_url + """\" onmouseover="this.src='""" + crop_img_url + """'" onmouseout="this.src='""" + img_url + """'" /></a>
      """
      mdate = id[0:20]
      rpt += "<br><label style='text-align: center'>" + link + mdate + "</a> <br>"
      rpt += "</label></div>"

      #rpt += "<div class='float_div'>"
      #rpt += "<img src=" + img + ">"
      #link = "<a href=" + mf + ">"
      #rpt += "<br><label style='text-align: center'>" + link + fn + "</a> <br>"
      #rpt += "</label></div>"

   return(rpt)


def best_of():
   days = [ '2020_08_10', '2020_08_11', '2020_08_12', '2020_08_13' ]
   all_meteors = []
   day_counter = {}
   for day in days:
      file = MLN_CACHE_DIR + day + "-all.json" 
      day_data = load_json_file(file)
      for data in day_data:
         station = data['station']
         if day not in day_counter:
            day_counter[day] = {}
         if station not in day_counter[day]:
            day_counter[day][station] = 0
         else:
            day_counter[day][station] += 1
         all_meteors.append(data)
   print("TOTAL METEORS:", len(all_meteors))



   for day in day_counter:
      for station in day_counter[day]:
         print(day, station, day_counter[day][station])

   ranked = []
   mfiles = []
   for meteor in all_meteors:
      if "hd_file" in meteor:
         file = meteor['hd_file']
         dur = len(meteor['xs'])
         station = meteor['station']
         day = file[0:10]
         url = "http://archive.allsky.tv/" + station + "/LIVE/METEORS/" + day + "/" + file
         ranked.append((station, url, dur))
         mfiles.append(url)
      else:
         print("*** BAD:", meteor)
         exit()

   head = mk_css()
   head += swap_pic_to_vid()
   table = det_table_all(mfiles)
   out = open("/mnt/ams2/bestof.html", "w")
   out.write(head)
   out.write(table)
   out.close()

   temp = sorted(ranked, key=lambda x: x[2], reverse=True)
   for meteor in temp:
      if "hd_file" not in meteor:
         print("*** BEST:", meteor)
      else:
         print("*** ERROR:", meteor)
         exit()
   print ("/mnt/ams2/bestof.html")
   exit()
    
def super_stacks_to_video():
   fps = 25
   stack_dir = "/mnt/ams2/MLN_CACHE/super_stacks/"
   os.system("rm tmp_vids/*")
   stack_vids = []
   for station in stations: 
      print(station)
      stacks = glob.glob(stack_dir + station + "*.jpg")
      for stack in stacks:
         vid_of = stack.replace(".jpg", ".mp4")
         stack_vids.append(vid_of)
         if cfe(vid_of) == 0:
            ofn = vid_of.split("/")[-1]
            print(stack) 
            for i in range(0, fps):
               counter = '{:03d}'.format(i) 
               nf = stack.replace(".jpg", "-" + counter + ".jpg")
               nfn = nf.split("/")[-1]
               cmd = "cp " + stack + " tmp_vids/" +  nfn
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
   cmd = "/usr/bin/ffmpeg -re -f concat -safe 0 -i tmp_vids/cat_list.txt /mnt/ams2/MLN_CACHE/super_stacks/all_stations.mp4"
   print(cmd)
   os.system(cmd)
      
 
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
      new_data_file = "/mnt/ams2/MLN_CACHE/" + day + "-" + station + "-METEORS.json"
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
         print("LOAD:", new_data_file)
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
   
