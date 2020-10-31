"""
   v1.x
   funcs for purging bad meteors
"""
from lib.DEFAULTS import *
import cv2
from lib.PipeDetect import fireball, obj_to_mj
from lib.PipeUtil import load_json_file, save_json_file,cfe, convert_filename_to_date_cam, get_file_info
import os,sys
import glob
from lib.FFFuncs import ffprobe, lower_bitrate, resize_video

def small_jpgs(date, json_conf):
   print("Make small JPG:")
   files = glob.glob("/mnt/ams2/meteors/" + date + "/*.jpg")
   for file in files:
      if "temp" in file:
         continue
      size, tdiff = get_file_info(file)
      if "obj.jpg" in file:
         # remove these files (old/not used)
         cmd = "rm " + file
         print(cmd)
         os.system(cmd)
      elif "-tn.jpg" in file:
         if size > 2000:
            print("TN SIZE TOO BIG, LOWER QUALITY.", file, size)
            make_jpg_small(file, 60)
         else:
            print("TN SIZE GOOD.", file, size)
      elif size > 100000:
         print("IMG SIZE TOO BIG, LOWER QUALITY.", file, size)
         make_jpg_small(file, 60)
      else:
         # check the img size, if it is SD and > X adjust quality (also resize dims if they are not 640x360
         img = cv2.imread(file)
         try:
            h,w = img.shape[:2]
         except:
            print("IMG BAD:", file)
            os.system("rm " + file)
            continue
         if w == 1920:
            print("HD IMG:", file, size)
         else:
            img = cv2.resize(img, (640,360))
            cv2.imwrite(file, img)
            print("SD IMG:", file, w,h, size)
            make_jpg_small(file, 60)

def make_jpg_small(file, qual):
   tmp_file = file.replace(".jpg", "-temp.jpg") 
   cmd = "convert -quality " + str(qual) + " "  + file + " " + tmp_file
   os.system(cmd)
   cmd = "mv " + tmp_file + " " + file
   os.system(cmd)
    

def fix_thumbs(date, json_conf):
   thumb = glob.glob("/mnt/ams2/meteors/" + date + "/*tn.jpg")
   for file in thumb:
      img = cv2.imread(file)
      try:
         h,w = img.shape[:2]
      except:
         print("BAD IMAGE:", file)
         continue
      if w != THUMB_W and h != THUMB_H:
        img = cv2.resize(img, (THUMB_W,THUMB_H))
        cv2.imwrite(file, img)
        print("FIXED:", h,w,file)

def fix_meteor_month(wild,json_conf):
   mdirs = glob.glob("/mnt/ams2/meteors/" + str(wild) + "*")
   for mdir in sorted(mdirs):
      print("CLEAN:", mdir)
      date = mdir.split("/")[-1]
      fix_meteor_orphans(date,json_conf)

def fix_meteor_orphans(date, json_conf):

   print("FMO:", date)
   meteor_dir = "/mnt/ams2/meteors/" + date + "/"
   if cfe(meteor_dir, 1) == 0:
      print("No meteors for this day.", meteor_dir)
      return()
   vids = glob.glob("/mnt/ams2/meteors/" + date + "/*.mp4")
   jsons = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   if len(vids) == 0:
      print("No meteors for this day", meteor_dir) 
      return()
   hd_vids = {}
   sd_vids = {}
   for vid in vids: 
      if "crop" in vid or "preview" in vid and "720" not in vid:
         continue
      w,h,bit_rate, total_frames= ffprobe(vid)
      print(vid, w, h, bit_rate, total_frames)

      if total_frames == 0 or w == 0:
         print("This video is bad, we should delete it and all children.")
         wild = vid.replace(".mp4", "*.*")
         trash = "/mnt/ams2/trash/" + date + "/" 
         if cfe(trash, 1) == 0:
            os.makedirs(trash)
         cmd = "mv " + wild + " " + trash
         os.system(cmd)
         print(cmd) 
         continue
      elif int(w) == 1920:
         print("HD:", vid, w, h, total_frames)
         hd_vids[vid] = [vid,w,h,bit_rate,total_frames]
      else:
         print("SD:", vid, w, h, total_frames)
         if int(w) != 640:
            temp_out = vid.replace(".mp4", "-temp.mp4")
            temp_out = resize_video(vid, temp_out, "640","360","25")

            print(temp_out)
            cmd = "mv " + temp_out + " " + vid
            os.system(cmd)
         sd_vids[vid] = [vid,w,h,bit_rate,total_frames]

   #print("JSONS:", jsons)
   #print("HD VIDS:", hd_vids)
   #print("SD VIDS:", sd_vids)

   orphans = 0
   meteor_index = {}
   used_hd = {}
   for file in sd_vids:
      hd_bit_rate = 0
      print("FILE:",file)
      vid, w,h,sd_bit_rate,total_frames = sd_vids[file]
      meteor_index[file] = {}
      meteor_index[file]['sd_file'] = file
      meteor_index[file]['hd_file'] = ""
      meteor_index[file]['sd_dim'] = [int(w),int(h)]
      meteor_index[file]['sd_total_frame'] = int(total_frames)
      meteor_index[file]['sd_bit_rate'] = int(sd_bit_rate)
      json_file = file.replace(".mp4",".json")
      nojson = 0
      if cfe(json_file) == 0:
         meteor_index[file]['json_file'] = 0
         orphans += 1 
         nojson = 1
      try:
         js = load_json_file(json_file)
      except:
         nojson = 1
         os.system("rm " + json_file)
         meteor_index[file]['json_file'] = 0

      if nojson == 0:
         meteor_index[file]['json_file'] = 1
         js = load_json_file(json_file)
         if "hd_trim" in js:
            meteor_index[file]['hd_file'] = js['hd_trim']
            if js['hd_trim'] in hd_vids:
               vid, w,h,hd_bit_rate,total_frames = hd_vids[js['hd_trim']]
               used_hd[js['hd_trim']] = 1
            else:
               vid, w,h,total_frames = None, 0, 0, 0
               if js['hd_trim'] in sd_vids:
                  vid, w,h,hd_bit_rate,total_frames =  sd_vids[js['hd_trim']] 


            meteor_index[file]['hd_dim'] = [int(w),int(h)]
            meteor_index[file]['hd_total_frame'] = int(total_frames)
            meteor_index[file]['hd_bit_rate'] = int(hd_bit_rate)
         else:
            meteor_index[file]['hd_dim'] = [0,0]
            meteor_index[file]['hd_total_frame'] = 0
            meteor_index[file]['hd_bit_rate'] = 0

   # hd files
   for hd_vid in hd_vids:
      if len(hd_vid) < 5:
         continue
      if hd_vid in used_hd:
         print("USED:", hd_vid)
      else:
         print("ORPHANED:", hd_vid)
         wild = hd_vid.replace(".mp4", "*")
         trash_dir = "/mnt/ams2/trash/" + date + "/"
         if cfe(trash_dir, 1) == 0:
            os.makedirs(trash_dir)
         
         cmd = "mv " + wild + " " + trash_dir
         os.system(cmd)
         print(cmd)
 

   hd_missing = 0
   for file in meteor_index:
      (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      date = fy + "_" + fmon + "_" + fd
      print(meteor_index[file])
      if meteor_index[file]['hd_file'] == "":
          hd_missing += 1
      if meteor_index[file]['json_file'] == 0:
         print("REDETECT:", file)
         best_meteor,sd_stack_img,bad_objs = fireball(file, json_conf)
         if best_meteor is not None :
            print("Best meteor:", best_meteor)
            sd_objects = []
            sd_objects.append(best_meteor) 
            if len(meteor_index[file]['hd_file']) == 0:
               mj = obj_to_mj(file, "", sd_objects, [])
               mjf = file.replace(".mp4", ".json")
               save_json_file(mjf, mj)
               print("Saved orphan meteor:", mjf)
            else:
               print("DETECT THE HD OBJECTS TOO!", meteor_index[file]['hd_file'], "|", len(meteor_index[file]['hd_file']) )
         else:
            for obj in bad_objs:
               for key in bad_objs[obj]:
                  print(key, bad_objs[obj][key])
            print("No meteors found in file:", file)
            reject_dir = "/mnt/ams2/rejects/" + date + "/" 
            wild = file.replace(".mp4", "*")
            cmd = "mv " + wild + " " + reject_dir
            if cfe(reject_dir, 1) == 0:
               os.makedirs(reject_dir)
            print(cmd)
            os.system(cmd)
         print("Handled missing json for:", file )
         #exit()
  
   # lower the bit rate if needed. 
   for file in meteor_index:
      print("FILE:", file) 
      if meteor_index[file]['json_file'] != 0:
         if meteor_index[file]['hd_bit_rate'] > 2400:
            lower_bitrate(meteor_index[file]['hd_file'], 32)
         elif meteor_index[file]['hd_bit_rate'] > 2000:
            lower_bitrate(meteor_index[file]['hd_file'], 30)
         elif meteor_index[file]['hd_bit_rate'] > 1500:
            lower_bitrate(meteor_index[file]['hd_file'], 28)
         elif meteor_index[file]['hd_bit_rate'] > 1200:
            lower_bitrate(meteor_index[file]['hd_file'], 27)

         # convert pngs to jpgs
      meteor_png_to_jpg(meteor_index[file]['sd_file'], meteor_index[file]['hd_file'],json_conf)
   if orphans > 0:
      print("Orphans detected.", orphans)
   else:
      print("No orphaned meteors detected." )
   if hd_missing > 0:
      print(hd_missing, "missing hd files")
   else:
      print("No missing hd files." )
   fix_thumbs(date, json_conf)

   meteor_index_file = "/mnt/ams2/meteors/" + date + "/" + json_conf['site']['ams_id'] + "_" + date + ".meteors"
   save_json_file(meteor_index_file, meteor_index)
   print(meteor_index_file)
   small_jpgs(date, json_conf)
   return()
   #exit() 



def meteor_png_to_jpg(sd_file, hd_file, json_conf):
   mjf = sd_file.replace(".mp4", ".json")
   if cfe(mjf) == 1:
      mj = load_json_file(mjf)
      if "hd_stack" in mj:
         if "png" in mj['hd_stack'] :
            mj['hd_stack'] = mj['hd_stack'].replace(".png", ".jpg")
      if "sd_stack" in mj:
         if "png" in mj['sd_stack'] :
            mj['sd_stack'] = mj['sd_stack'].replace(".png", ".jpg")
         save_json_file(mjf, mj)

   if hd_file is not None:
      hd_wild = hd_file.replace(".mp4", "*.png")
      hd_pngs = glob.glob(hd_wild)
   else:
      hd_pngs = []
   sd_wild = sd_file.replace(".mp4", "*.png")
   sd_pngs = glob.glob(sd_wild)
   for png in sd_pngs:
      jpg = png.replace(".png",".jpg")
      cmd = "convert -quality 80 " + png + " " + jpg
      print(cmd)
      os.system(cmd)
      cmd = "rm " + png 
      os.system(cmd)
   for png in hd_pngs:
      jpg = png.replace(".png",".jpg")
      cmd = "convert -quality 80 " + png + " " + jpg
      print(cmd)
      os.system(cmd)
      cmd = "rm " + png 
      os.system(cmd)
   print("saved:", mjf)


def purge_meteors_for_date(json_conf):
   station_id = json_conf['site']['ams_id']
   del_file = "/mnt/ams2/SD/proc2/json/" + station_id  + ".del"
   if cfe(del_file) == 0:
      print("No delete file.", del_file)
      return()
   else:
      del_data = load_json_file(del_file)
   cmd = "mv " + del_file + " /mnt/ams2/trash/" 
   os.system(cmd)
   print(cmd)

   for base in del_data:
      if len(base) < 5:
         continue
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
      if hd_base is not None and hd_base != "" and len(hd_base) < 5:
         temp = glob.glob(meteor_dir + hd_base + "*")
         for f in temp:
            print("HD BASE DEL:", f)
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
