"""
   v1.x
   funcs for purging bad meteors
"""
import datetime
from lib.DEFAULTS import *
import cv2
from lib.PipeDetect import fireball, obj_to_mj
from lib.PipeUtil import load_json_file, save_json_file,cfe, convert_filename_to_date_cam, get_file_info
from lib.PipeImage import quick_video_stack
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


def make_meteor_index(date, json_conf):

   hd_vids = {}
   sd_vids = {}
   meteor_dir = "/mnt/ams2/meteors/" + date + "/"
   if cfe(meteor_dir, 1) == 0:
      print("No meteors for this day.", meteor_dir)
      return()
   vids = glob.glob("/mnt/ams2/meteors/" + date + "/*.mp4")
   jsons = glob.glob("/mnt/ams2/meteors/" + date + "/*.json")
   trash = []

   for vid in vids: 
      if "crop" in vid or "preview" in vid and "720" not in vid:
         trash.append(vid)
         continue
      w,h,bit_rate, total_frames= ffprobe(vid)

      if total_frames == 0 or w == 0:
         print("This video is bad, we should delete it and all children.")
         wild = vid.replace(".mp4", "*.*")
         trash_dir = "/mnt/ams2/trash/" + date + "/"
         if cfe(trash_dir, 1) == 0:
            os.makedirs(trash_dir)
         cmd = "mv " + wild + " " + trash_dir
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
         #os.system(cmd)
         print(cmd)

   meteor_index_file = "/mnt/ams2/meteors/" + date + "/" + json_conf['site']['ams_id'] + "_" + date + ".meteors"
   save_json_file(meteor_index_file, meteor_index)
   print(meteor_index_file)
   return(meteor_index, meteor_index_file)

def recover_trash(mi,date, json_conf):
   # look for missing HD files.
   missing_hd = []
   trash_dir = "/mnt/ams2/trash/" + date + "/" 
   miss = 0
   ok = 0
   for key in mi:
      found = 0
      print(mi[key]['sd_file'], mi[key]['hd_file'])
      if mi[key]['hd_file'] is None:
         hd_file = find_matching_hd( mi[key]['sd_file'], trash_dir)
         miss += 1
         missing_hd.append(mi[key]['sd_file'])
      else:
         ok += 1
         print("HD OK:",  mi[key]['sd_file'], trash_dir)
   print("HD OK:", ok)
   print("HD MISSING:", miss)
   print(missing_hd)

     
def find_matching_hd(trim_time,trim_num, sd_file,hd_list):
   (t_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(sd_file)
   files = hd_list
   best = []
   for data in files:
      
      file, w, h, total_frames, bitrate = data
      if cam not in file:
         continue
      #print("HD FILE:", file)
      hd_trim_time, hd_trim_num = find_trim_time(file)
      #(t_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)
      diff = (trim_time - hd_trim_time ).total_seconds()
      if -50 < diff < 50:
         if str(trim_num) in file:
            best.append((file,diff))
   

   return(best)

def find_trim_time(file):
   (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(file)

   if "-trim-" in file:
      xxx = file.split("-trim-")[-1]
   else:
      xxx = file.split("trim")[-1]
   #print("XXX:", xxx)
   xxx = xxx.replace(".mp4", "")
   #print("XXX:", xxx)
   if "-" in xxx:
      el = xxx.split("-")
      trim_num = int(el[0])
   else:
      trim_num = int(xxx)

   extra_sec = trim_num / 25

   #print("TRIM NUM:", trim_num)
   trim_time = f_datetime + datetime.timedelta(0,extra_sec)
   #print("F TIME:", f_datetime)
   #print("TRIM TIME:", trim_time)
   return(trim_time, trim_num)


def fix_meteor_dir(date, json_conf):
   meteor_mp4s = glob.glob("/mnt/ams2/meteors/" + date + "/*.mp4")
   trash_mp4s = glob.glob("/mnt/ams2/trash/" + date + "/*.mp4")
   backup_mp4s = glob.glob("/mnt/backup/ams2/meteors/" + date + "/*.mp4")

   mi = {} #meteor_index
   hd_files = []
   trash_files = []
   for file in meteor_mp4s:
      trim_time, trim_num = find_trim_time(file)
      
      if "crop" in file or "720" in file:
         trash_files.append(file)
         continue
      w,h,bit_rate,total_frames = ffprobe(file)
      w = int(w)
      h = int(h)
      if total_frames == 0:
         trash_files.append(file)
      if w == 1920:
         hd_files.append((file,w,h,total_frames,int(bit_rate)))
      else:
         mi[file] = {}
         mi[file]['sd_file'] = file
         mi[file]['trim_time'] = trim_time
         mi[file]['trim_num'] = trim_num
         mi[file]['sd_dim'] = [int(w),int(h)]
         mi[file]['sd_total_frame'] = int(total_frames)
         mi[file]['sd_bit_rate'] = int(bit_rate)
         mi[file]['hd_file'] = ""
         mi[file]['hd_dim'] = [0,0]
         mi[file]['hd_total_frame'] = 0
         mi[file]['hd_bit_rate'] = 0

   for sd_file in sorted(mi.keys()):
      json_file = sd_file.replace(".mp4", ".json")
      best_hd = find_matching_hd(mi[sd_file]['trim_time'], mi[sd_file]['trim_num'], sd_file,hd_files)
      if len(best_hd) > 0:
         mi[sd_file]['hd_file'] = best_hd[0][0]
         w,h,bit_rate,total_frames = ffprobe(file)
         if cfe(json_file) == 1:
            mj = load_json_file(json_file)
         else:
            print("ORPHAN VIDEO, NO JS WITH IT.", sd_file)
            mj = 0
         if mj != 0: 
            if mj['hd_trim'] != best_hd[0][0]:
               print("UPDATE JSON HD FILES WITH:", best_hd[0][0])
               mj['hd_trim'] = best_hd[0][0]
               mj['hd_file'] = best_hd[0][0]
               mj['hd_crop'] = best_hd[0][0]
               hd_stack = best_hd[0][0].replace(".mp4", ".jpg")
               if cfe(hd_stack) == 0:
                  hd_stack = best_hd[0][0].replace(".mp4", "-stacked.jpg")

               mj['hd_stack'] = hd_stack
               print("hd stack:", hd_stack)
               print("SAVE:", json_file)
               save_json_file(json_file, mj)
               #exit()
            if mj['sd_video_file'] != sd_file:
               mj['sd_video_file'] = sd_file
               print("SAVE:", json_file)
         mi[sd_file]['hd_dim'] = [0,0]
         mi[sd_file]['hd_total_frame'] = total_frames
         mi[sd_file]['hd_bit_rate'] = bit_rate
      mi[sd_file]['trim_time'] = str(mi[sd_file]['trim_time'])
      print(mi[sd_file])      
   meteor_index_file = "/mnt/ams2/meteors/" + date + "/" + json_conf['site']['ams_id'] + "-" + date + ".meteors"
   print("Saving:", meteor_index_file)
   save_json_file(meteor_index_file, mi)

def move_hd_trash_files_back():
   trash = glob.glob("/mnt/ams2/trash/*")
   for tt in trash:
      date = tt.split("/")[-1]
      cmd = "cp /mnt/ams2/trash/" + date + "/*HD-meteor.mp4" + " /mnt/ams2/meteors/" + date + "/"
      os.system(cmd)
      print(cmd)

def roi_box(mj):
   min_x, min_y, max_x, max_y = 0,0,0,0
   for key in mj:
      print(key)
   if len(mj['hd_objects']) > 0:
      min_x = min(mj['hd_objects']['oxs'])
      max_x = max(mj['hd_objects']['oxs'])
      max_y = max(mj['hd_objects']['oys'])
      min_y = max(mj['hd_objects']['oys'])
   elif len(mj['sd_objects']) > 0:
      for obj in mj['sd_objects']:
         if "history" in obj:
            oxs = []
            oys = []
            for hist in obj['history']:
               oxs.append(hist[1]) 
               oys.append(hist[2]) 
            min_x = min(oxs) - 25
            max_x = max(oxs) + 25
            max_y = max(oys) - 25
            min_y = min(oys) + 25
   return(min_x,min_y,max_x,max_y)
 
def restack_meteor_dir(date,json_conf):
   print("RESTACK")
   vids = glob.glob("/mnt/ams2/meteors/" + date + "/*.mp4")
   for vid in vids:
      json_file = vid.replace(".mp4", ".json")
      if cfe(json_file) == 1:
         mj = load_json_file(json_file)
      else:
         mj = 0
      stack_file = vid.replace(".mp4", "-stacked.jpg")
      stack_file_tn = vid.replace(".mp4", "-stacked-tn.jpg")
      if cfe(stack_file) == 0:
         stack_frame = quick_video_stack(vid, 0, 1)
      else:
         stack_frame = cv2.imread(stack_file)
      if mj != 0: 
         obj_frame = stack_frame.copy()
         x1,y1,x2,y2 = roi_box(mj)
         cv2.rectangle(obj_frame, (int(x1), int(y1)), (int(x2) , int(y2) ), (255, 255, 255), 1)
         obj_frame_tn = cv2.resize(obj_frame, (THUMB_W,THUMB_H))
         obj_frame_tn_file = stack_file.replace(".jpg", "-obj-tn.jpg")
         cv2.imwrite(obj_frame_tn_file, obj_frame_tn)
         print("OBJ:",obj_frame_tn_file)
      stack_frame_tn = cv2.resize(stack_frame, (THUMB_W,THUMB_H))
      cv2.imwrite(stack_file_tn, stack_frame_tn)
      print("DONE:", stack_file, stack_file_tn)

      
 

def fix_meteor_orphans(date, json_conf):
   
   #move_hd_trash_files_back() 
   fix_meteor_dir(date, json_conf)
   #meteor_index, meteor_index_file = make_meteor_index(date, json_conf)
   #recover_trash(meteor_index, date, json_conf)
   #restack_meteor_dir(date, json_conf)
   exit()

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
   small_jpgs(date, json_conf)
   print(meteor_index_file)
   return()
   #exit() 


def convert_meteor_pngs_to_jpgs():
   os.system("find /mnt/ams2/meteors/ |grep .png > /tmp/pngs.txt")
   fp = open("/tmp/pngs.txt")
   files = []
   for line in fp:
      line = line.replace("\n", "")
      files.append(line)
   for line in sorted(files):
      new_file = line.replace(".png", ".jpg")
      cmd = "convert -quality 70 " + line + " " + new_file
      print(cmd)
      os.system(cmd)
      cmd = "rm " + line
      print(cmd)
      os.system(cmd)

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
   purge_days = {}
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
      dday = base[0:10]
      purge_days[dday] = 1

   for day in purge_days:
      cmd = "./Process.py mmi_day " + day
      print(cmd)
      os.system(cmd)




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
            if js['hd_trim'] is not None:
               hd_base = js['hd_trim'].split("/")[-1].replace(".mp4", "")
            else:
               hd_base = None
            print("HD_BASE STR:", hd_base)
         else:
            print("NO HD_BASE:", jsf)
            hd_base = None
            return ()
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
      if hd_base is not None and hd_base != "" and len(hd_base) > 5:
         temp = glob.glob(meteor_dir + hd_base + "*")
         for f in temp:
            print("HD BASE DEL:", f)
            files_to_del.append(f)
      # ARC METEOR SD & HD FILES
      arc_base = None
      if arc_base is not None:
         if arc_sd_vid is not None:
            arc_sd_base = arc_sd_vid.replace(".mp4", "")
            temp = glob.glob(arc_sd_base + "*")
            for f in temp:
               files_to_del.append(f)
         if arc_hd_vid is not None:
            arc_hd_base = arc_hd_vid.replace(".mp4", "")
            temp = glob.glob(arc_hd_base + "*")
            for f in temp:
               files_to_del.append(f)

           

      for file in files_to_del:
         cmd = "mv " + file + " " + trash_dir
         print(cmd)
         os.system(cmd)
