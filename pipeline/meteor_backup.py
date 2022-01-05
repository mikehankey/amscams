#!/usr/bin/python3
import time
import os
import glob
from lib.PipeUtil import get_file_info , load_json_file, save_json_file

# fast / light backup script that only backs up the SD & HD mp4 and json files for each meteor. This is the minimal data abackup needed for meteors. stacks, jpgs etc will have to be 'restored' later  recovery is needed.
# will also do a simliar process for the cal data. and also backup minimal needed config. from these files a 'restore' process would be run to get the system back to its previous state. This approach uses the minimal data though, so think of it as a 'compressed meteor archive'. 


def get_mdirs(meteor_root=None):
   mdirs = []
   if meteor_root is None:
      meteor_root = "/mnt/ams2/meteors/"
   dirs = os.listdir(meteor_root)
   for dd in dirs:
      #print(meteor_root + dd)   
      if os.path.isdir(meteor_root + dd) is True:
         mdirs.append(dd)   
   return(mdirs)

def get_mfiles(mdir):

   temp = glob.glob(mdir + "/*.json")
   mfiles = []
   for json_file in temp:
      if "\\" in json_file:
         json_file = json_file.replace("\\", "/")
      if "frame" not in json_file and "events" not in json_file and "index" not in json_file and "cloud" not in json_file and "import" not in json_file and "report" not in json_file and "reduced" not in json_file and "calparams" not in json_file and "manual" not in json_file and "starmerge" not in json_file and "master" not in json_file:
         vfn = json_file.split("/")[-1].replace(".json", ".mp4")
         mfiles.append(vfn)
   return(mfiles)

def main_loop():
   get_size = False
   meteor_dict_file = "meteor_dict.json" 
   if os.path.exists(meteor_dict_file):
      meteor_dict = load_json_file(meteor_dict_file)
   else:
      meteor_dict = {}
   backup_dir = "/mnt/ams2/meteor_backup/"   
   meteor_root = "/mnt/ams2/meteors/"
   mdirs = sorted(get_mdirs(meteor_root ), reverse=True)
   for md in mdirs:
      mfs = get_mfiles(meteor_root + md)
      back = backup_dir + md + "/"
      print(md, len(mfs), back)
      if os.path.exists(back) is False:
         os.makedirs(back)
      for mf in mfs:
         #if mf in meteor_dict:
         #continue 
         json_corrupt = False 
         if mf not in meteor_dict:
            meteor_dict[mf] = {}
         mdir = meteor_root + md + "/"
         mjf = mf.replace(".mp4", ".json")
         try:
            mj = load_json_file(mdir + mjf)
            print("MJ LOADED")
            if "hd_trim" in mj:
               if mj['hd_trim'] is not None:
                  if mj['hd_trim'] != 0:
                     if os.path.exists(mj['hd_trim']) is True:
                        meteor_dict[mf]['hd_trim'] = mj['hd_trim']
                        if get_size is True:
                           tsize,tdiff = get_file_info(mdir + mf)            
                         
                           meteor_dict[mf]['hd_size'] = tsize
                           meteor_dict[mf]['hd_tdiff'] = tdiff
                           print("HD SSIZE!", tsize)
         except:
            print("Could not read the json file!", mdir + mjf)
            json_corrupt = True
         if get_size is True:         
            tsize,tdiff = get_file_info(mdir + mjf)            
            meteor_dict[mf]['json_size'] = tsize
            meteor_dict[mf]['json_tdiff'] = tdiff
            tsize,tdiff = get_file_info(mdir + mf)            
            meteor_dict[mf]['sd_size'] = tsize
            meteor_dict[mf]['sd_tdiff'] = tdiff
            print(tdiff, tsize, mdir + mf)
      save_json_file(meteor_dict_file, meteor_dict)
   total_size = 0

   save_json_file(meteor_dict_file, meteor_dict)
   mc = 0
   print("STARTING BACKUP.")
   for mf in meteor_dict:
      print("BACKUP", mf)
      if 'backed_up' not in meteor_dict[mf]:
         meteor_dict[mf]['backed_up'] = {}
      mjf = mf.replace(".mp4", ".json")
      mjrf = mf.replace(".mp4", "-reduced.json")

      if get_size is True:
         total_size += meteor_dict[mf]['json_size'] 
         if 'sd_size' in meteor_dict[mf]:
            total_size += meteor_dict[mf]['sd_size']
         if 'hd_size' in meteor_dict[mf]:
            total_size += meteor_dict[mf]['hd_size']
         # copy files to bk dir

      backup_dir = "/mnt/ams2/meteor_backup/"   
      day = mf[0:10]
      bkdir = backup_dir + day + "/"
      mdir = meteor_root + day + "/"


      if os.path.exists(bkdir + mf) is False:
         meteor_dict[mf]['backed_up']['sd_vid'] = time.time()
         cmd = "cp " + mdir + mf + " " + bkdir
         print(cmd)
         os.system(cmd)

      if os.path.exists(bkdir + mjf) is False:
         meteor_dict[mf]['backed_up']['json_file'] = time.time()
         cmd = "cp " + mdir + mjf + " " + bkdir
         print(cmd)
         os.system(cmd)

      if os.path.exists(mdir + mjrf) is True :
         meteor_dict[mf]['backed_up']['reduced_file'] = time.time()
         if os.path.exists(bkdir + mjrf) is True:
            print("RED BK EXISTS ALREADY", bkdir + mjrf)
         else:
            cmd = "cp " + mdir + mjrf + " " + bkdir
            print(cmd)
            os.system(cmd)
      else:
         print("NO REDUCE:", mdir + mjrf)

      if "hd_trim" in meteor_dict[mf]:
         hd_trim = meteor_dict[mf]['hd_trim'].split("/")[-1]
         if os.path.exists(bkdir + hd_trim) is False:
            cmd = "cp " + mdir + hd_trim + " " + bkdir
            print(cmd)
            os.system(cmd)
            meteor_dict[mf]['backed_up']['hd_vid'] = time.time()
         else:
            print("HD EXISTS", bkdir + hd_trim)
      else:
         print("NO HD TRIM?")
      mc += 1
      if mc % 50 == 0:
         save_json_file(meteor_dict_file, meteor_dict)
   if get_size is True:
      print("TOTAL SIZE IN MEGABYTES", round(total_size / 1000000, 2))
   save_json_file(meteor_dict_file, meteor_dict)

main_loop()
