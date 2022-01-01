import datetime
import numpy as np
import json
import math

def convert_filename_to_date_cam(file, ms = 0):
   if "/" in file:
      el = file.split("/")
   else:
      el = file.split("\\")
   filename = el[-1]
   filename = filename.replace(".mp4" ,"")
   if "-" in filename:
      xxx = filename.split("-")
      filename = xxx[0]
   el = filename.split("_")
   if len(el) >= 8:
      fy,fm,fd,fh,fmin,fs,fms,cam = el[0], el[1], el[2], el[3], el[4], el[5], el[6], el[7]
   else:
      fy,fm,fd,fh,fmin,fs,fms,cam = "1999", "01", "01", "00", "00", "00", "000", "010001"
   if "-" in cam:
      cel = cam.split("-")
      cam = cel[0]

   #print("CAM:", cam)
   #exit()
   cam = cam.replace(".png", "")
   cam = cam.replace(".jpg", "")
   cam = cam.replace(".json", "")
   cam = cam.replace(".mp4", "")

   f_date_str = fy + "-" + fm + "-" + fd + " " + fh + ":" + fmin + ":" + fs
   f_datetime = datetime.datetime.strptime(f_date_str, "%Y-%m-%d %H:%M:%S")
   if ms == 1:
      return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs,fms)

   else:
      return(f_datetime, cam, f_date_str,fy,fm,fd, fh, fmin, fs)

def load_json_file(json_file):
   #try:
   if True:
      #print("Trying:", json_file)
      with open(json_file, 'r' ) as infile:
         json_data = json.load(infile)
   #except:
   #   json_data = False
   import ast
   try:
      json_data = ast.literal_eval(json_data)
   except:
      print("Nevermind.")
   return json_data

def save_json_file(json_file, json_data, compress=False):
   if "cp" in json_data:
      if json_data['cp'] is not None:
         for key in json_data['cp']:
            print(key, type(json_data['cp']))
            if type(json_data['cp'][key]) == np.ndarray:
               json_data['cp'][key] = json_data['cp'][key].tolist()

   json_data = str(json_data)

   with open("test.json", 'w') as outfile:
      json.dump(json_data, outfile, indent=4, allow_nan=True )
   outfile.close()
   try:
      test_json = load_json_file("test.json")
   except:
      print("trying to save failed:", json_file)
      return()
   # if this fails, the file is corrupt or there is a problem so do not save!

   with open(json_file, 'w') as outfile:
      if(compress==False):
         json.dump(json_data, outfile, indent=4, allow_nan=True )
      else:
         json.dump(json_data, outfile, allow_nan=True)
   outfile.close()


def angularSeparation(ra1,dec1, ra2,dec2):

   ra1 = math.radians(float(ra1))
   dec1 = math.radians(float(dec1))
   ra2 = math.radians(float(ra2))
   dec2 = math.radians(float(dec2))
   return math.degrees(math.acos(math.sin(dec1)*math.sin(dec2) + math.cos(dec1)*math.cos(dec2)*math.cos(ra2 - ra1)))


def get_file_info(file):
   cur_time = int(time.time())
   if cfe(file) == 1:
      st = os.stat(file)

      size = st.st_size
      mtime = st.st_mtime
      tdiff = cur_time - mtime
      tdiff = tdiff / 60
      return(size, tdiff)
   else:
      return(0,0)
