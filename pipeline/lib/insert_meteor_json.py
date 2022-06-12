import sys
import sqlite3
from lib.PipeUtil import load_json_file, save_json_file, convert_filename_to_date_cam

def starttime_from_file(self, filename):
   print("FILE:", filename)
   (f_datetime, cam, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(filename)
   trim_num = get_trim_num(filename)
   extra_sec = int(trim_num) / 25
   extra_sec += 2
   event_start_time = f_datetime + dt.timedelta(0,extra_sec)
   return(event_start_time)

def dynamic_insert(con, cur, table_name, in_data):
   # Pass in the table name
   # and a dict of key=value pairs
   # then the dict will be converted to sql and insert or replaced into the table.


   values = []
   fields = []
   sql = "INSERT INTO " + table_name + " ( "
   vlist = ""
   flist = ""
   for key in in_data:
      if flist != "":
         flist += ","
         vlist += ","
      flist += key
      vlist += "?"
      fields.append(key)
      values.append(in_data[key])

   flist += ")"
   vlist += ")"
   sql += flist + " VALUES (" + vlist

   cur.execute(sql, values)
   con.commit()
   return(cur.lastrowid)

def insert_meteor_json(root_fn, con, cur):

   date = root_fn[0:10]

   mdir = "/mnt/ams2/meteors/{}/".format(date)
   mfile = mdir + root_fn + ".json"

   if os.path.exists(mfile) is False:
      return(False, "no mfile: "+ mfile)
   else:
      # each iter is 1 meteor json file getting loaded into the SQL.
      # break out into a function?
      if mfile in loaded_meteors :
         if loaded_meteors[mfile] == 1:
            foo = 1
      mdir = mfile[0:10]
      el = mfile.split("_")
      mjf = meteor_dir + mdir + "/" + mfile.replace(".mp4", ".json")
      mjrf = meteor_dir + mdir + "/" + mfile.replace(".mp4", "-reduced.json")
      start_time = None
      if os.path.exists(mjf) is True:
         try:
            mj = load_json_file(mjf)
         except:
            errors[mjf] = "couldn't open json file"

      mfd = ""
      if os.path.exists(mjrf) is True:
         try:
            mjr = load_json_file(mjrf)
         except:
            mjr = None
         if mjr is not None:
            if "meteor_frame_data" in mjr :
               if len(mjr['meteor_frame_data']) > 0:
                  mfd = mjr['meteor_frame_data']
                  start_time = mfd[0][0]
         reduced = 1
      else:
         mjr = None
         reduced = 0

      if start_time is None:
         start_time = starttime_from_file(mfile)
         start_time = start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
      if "sd_video_file" not in mj:
         return() 
      sd_vid = mj['sd_video_file'].split("/")[-1]
      hd_vid = ""
      if "hd_trim"  in mj:
         if mj['hd_trim'] is not None:
            if isinstance(mj['hd_trim'], str) is True:
               hd_vid = mj['hd_trim'].split("/")[-1]

      if 'multi_station_event' in mj:
         mse = 1
         if "event_id" in mj['multi_station_event']:
            event_id = mj['multi_station_event']['event_id']
         else:
            event_id = 0
            mse = 0
      else:
         mse = 0
         event_id = 0

      if "hc" in mj :
         human_confirmed = 1
      else:
         human_confirmed = 0



      if "user_mods" in mj :
         if len(mj['user_mods'].keys()) > 0:
            human_confirmed = 1
            user_mods = mj['user_mods']
         else:
            user_mods = ""
      else:
         user_mods = ""
      ang_vel = 0
      if "best_meteor" in mj:
         if "report" in mj['best_meteor']:
            if "ang_vel" in mj['best_meteor']['report']:
               ang_vel =  mj['best_meteor']['report']['ang_vel']

      if mjr is not None:
         if "meteor_frame_data" in mjr:
            mfd = mjr['meteor_frame_data']

      calib = ""
      if "cp" in mj:
         cp = mj['cp']
         if cp is not None:
            calib = [cp['ra_center'], cp['dec_center'], cp['center_az'], cp['center_el'], cp['position_angle'], cp['pixscale'], float(len(cp['cat_image_stars'])), float(cp['total_res_px'])]
            mj['calib'] = calib

      if "calib" in mj:
         calib = mj['calib']
      if "sync_status" in mj:
         sync_status = json.dumps(mj['sync_status'])
      else:
         sync_status = ""

      if mfd != "":
         duration = len(mfd) / 25
      else:
         duration = "0"

      hd_roi = ""
      if "hd_roi" in mj:
         hd_roi = mj['hd_roi']
      if mjr is not None:
         if "meteor_frame_data" in mjr:
            x1,y1,x2,y2 = mfd_roi(mfd)
            mj['hd_roi'] = [x1,y1,x2,y2]
            hd_roi = [x1,y1,x2,y2]


      ext = el[-1]
      camera_id = ext.split("-")[0]

      #self.verify_media(self.station_id, mfile.replace(".mp4", ""))

      in_data = {}
      in_data['station_id'] = self.station_id
      in_data['camera_id'] = camera_id
      in_data['root_fn'] = mfile.replace(".mp4", "")
      in_data['sd_vid'] = sd_vid
      in_data['hd_vid'] = hd_vid
      in_data['start_datetime'] = start_time
      in_data['meteor_yn'] = ""
      in_data['meteor_yn_conf'] = ""
      in_data['human_confirmed'] = human_confirmed
      in_data['reduced'] = reduced
      in_data['multi_station'] = mse
      in_data['event_id'] = event_id
      in_data['ang_velocity'] = float(ang_vel)
      in_data['duration'] = float(duration)
      if hd_roi != "":
         in_data['roi'] = json.dumps(hd_roi)
      in_data['sync_status'] = sync_status
      in_data['calib'] = json.dumps(calib)
      in_data['mfd'] = json.dumps(mfd)
      in_data['user_mods'] = json.dumps(user_mods)
      if mfile in loaded_meteors:
         del (in_data['human_confirmed'])
         self.update_meteor(in_data)
         #print("UPDATE EXISTING")
      else:
         dynamic_insert(con, cur, "meteors", in_data)
         #print("INSERT NEW")
      mj['in_sql'] = 1
      save_json_file(mjf, mj)
      return(True, mjf + " loaded")
