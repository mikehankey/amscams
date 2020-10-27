"""
   funcs for purging bad meteors
"""
from lib.PipeDetect import fireball
from lib.PipeUtil import load_json_file, save_json_file,cfe
import os,sys
import glob
from lib.FFFuncs import ffprobe


def fix_meteor_orphans(date, json_conf):
   print("FMO:", date)
   
   vids = glob.glob("/mnt/ams2/meteors/" + date + "/*.mp4")
   jsons = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   hd_vids = {}
   sd_vids = {}
   for vid in vids: 
      if "crop" in vid:
         continue
      w,h,total_frames = ffprobe(vid)
      if total_frames == 0 or w == 0:
         print("This video is bad, we should delete it and all children.")
         wild = vid.replace(".mp4", "*.*")
         trash = "/mnt/ams2/trash/" + date + "/" 
         cmd = "mv " + wild + " " + trash
         print(cmd) 
         continue
      elif int(w) == 1920:
         print("HD:", vid, w, h, total_frames)
         hd_vids[vid] = [vid,w,h,total_frames]
      else:
         print("SD:", vid, w, h, total_frames)
         sd_vids[vid] = [vid,w,h,total_frames]

   print("JSONS:", jsons)
   print("HD VIDS:", hd_vids)
   print("SD VIDS:", sd_vids)

   orphans = 0
   meteor_index = {}
   for file in sd_vids:
      vid, w,h,total_frames = sd_vids[file]
      meteor_index[file] = {}
      meteor_index[file]['sd_file'] = file
      meteor_index[file]['hd_file'] = ""
      json_file = file.replace(".mp4",".json")
      if cfe(json_file) == 0:
         meteor_index[file]['json_file'] = 0
         meteor_index[file]['sd_dim'] = [int(w),int(h)]
         meteor_index[file]['sd_total_frame'] = int(total_frames)
         orphans += 1
      else:
         meteor_index[file]['json_file'] = 1
         js = load_json_file(json_file)
         if "hd_trim" in js:
            meteor_index[file]['hd_file'] = js['hd_trim']
            if js['hd_trim'] in hd_vids:
               vid, w,h,total_frames = hd_vids[js['hd_trim']]
            else:
               vid, w,h,total_frames = None, 0, 0, 0
               if js['hd_trim'] in sd_vids:
                  vid, w,h,total_frames =  sd_vids[js['hd_trim']] 

            meteor_index[file]['hd_dim'] = [int(w),int(h)]
            meteor_index[file]['hd_total_frame'] = int(total_frames)

   for file in meteor_index:
      if meteor_index[file]['json_file'] == 0:
         print("REDETECT:", file)
         best_meteor,sd_stack_img = fireball(file, json_conf)
         print("Best meteor:", best_meteor)

   if orphans > 0:
      print("Orphans detected.", orphans)



def meteor_png_to_jpg(date, json_conf):
   print("P2J", date)



def purge_meteors_for_date(json_conf):
   station_id = json_conf['site']['ams_id']
   del_file = "/mnt/ams2/SD/proc2/json/" + station_id  + ".del"
   if cfe(del_file) == 0:
      print("No delete file.")
      return()
   else:
      del_data = load_json_file(del_file)
   cmd = "mv " + del_file + " /mnt/ams2/trash/" 
   os.system(cmd)
   print(cmd)

   for base in del_data:
      delete_from_base(base,json_conf)





def delete_from_base(base, json_conf):
   # MUST BASE IN THE SD BASE METEOR AND THEN ALL ASSOICATED FILES WILL BE MOVED TO THE TRASH FOLDER
   # IN A DIR FOR THAT DATE (IN CASE SOMETHING WAS DELETED BY ACCIDENT
   print("PURGE METEOR:", base)
   date = base[0:10]
   meteor_dir = "/mnt/ams2/meteors/" + date + "/" 
   trash_dir = "/mnt/ams2/trash/" + date + "/" 
   if cfe(trash_dir,1) == 0:
      os.makedirs(trash_dir)
   if True:
      jsf = meteor_dir + base + ".json"
      if cfe(jsf) == 1:
         print(jsf)
         js = load_json_file(jsf)
         if "hd_trim" in js:
            hd_base = js['hd_trim'].split("/")[-1].replace(".mp4", "")
            print("HD_BASE:", hd_base)
         else:
            print("NO HD_BASE:", jsf)
            hd_base = None
         if "archive_file" in js:
            arc_base = js['archive_file'].split("/")[-1].replace(".json", "")
            arc_js_file = js['archive_file']
            arc_js = load_json_file(js['archive_file'])
            arc_hd_vid = arc_js['info']['hd_vid']
            arc_sd_vid = arc_js['info']['sd_vid']
            arc_dir = arc_js_file.replace( js['archive_file'].split("/")[-1], "")
         else:
            arc_base = None
      else:
         print("JSF DOESNT EXIST?", jsf)
         return()
         #exit()
   
      files_to_del = []
      # METEOR SD FILES
      temp = glob.glob(meteor_dir + base + "*")
      for f in temp:
         files_to_del.append(f)
      # METEOR HD FILES
      if hd_base is not None:
         temp = glob.glob(meteor_dir + hd_base + "*")
         for f in temp:
            files_to_del.append(f)
      # ARC METEOR SD & HD FILES
      if arc_base is not None:
         arc_sd_base = arc_sd_vid.replace(".mp4", "")
         arc_hd_base = arc_hd_vid.replace(".mp4", "")

         temp = glob.glob(arc_sd_base + "*")
         for f in temp:
            files_to_del.append(f)

         temp = glob.glob(arc_hd_base + "*")
         for f in temp:
            files_to_del.append(f)

           

      for file in files_to_del:
         cmd = "mv " + file + " " + trash_dir
         print(cmd)
         os.system(cmd)
