from lib.PipeUtil import load_json_file, save_json_file
import os
import sqlite3

class AIAgent():

   def __init__(self):
      print("AI INIT")
      self.json_conf = load_json_file("../conf/as6.json")
      self.meteor_dir = "/mnt/ams2/meteors/"
      self.station_id = self.json_conf['site']['ams_id']
      self.non_meteor_dir = "/mnt/ams2/non_meteors/"
      self.non_meteor_dir_confirmed = "/mnt/ams2/non_meteors_confirmed/"

      self.ai_dir = "/mnt/ams2/AI/DATA/"
      if os.path.exists(self.ai_dir) is False:
         os.makedirs(self.ai_dir)
      self.job_file = self.ai_dir + "jobs.json"
      if os.path.exists(self.job_file) :
         self.all_days = load_json_file(self.job_file)
      else:
         self.all_days = {}

      # Connecting to sqlite
      # connection object
      self.con = sqlite3.connect(self.station_id + '_ALLSKY.db')

      # cursor object
      self.cur = self.con.cursor()


   def index_archive_tasks(self ):
      mdirs = os.listdir(self.meteor_dir)
      print("AI Index archive...", self.meteor_dir) 
      for md in sorted(mdirs, reverse=True):
         if md not in self.all_days:
           
            mdir = self.meteor_dir + md + "/" 
            if os.path.isdir(mdir) is False:
               continue
            print("Working on ", md)
            ai_data_file = mdir + self.station_id + "_" + md + "_AI_DATA.info"
            my_event_file = mdir + self.station_id + "_" + md + "_EVENTS.info"
            aws_data_file = mdir + self.station_id + "_" + md + "_AWS_METEORS.info"
            mso_file = mdir + "_MY_MS_OBS.info"
            if md not in self.all_days: 
               self.all_days[md] = {}
               self.all_days[md]['jobs'] = {}
            if "ai_scan_meteors" not in self.all_days[md]['jobs']:
               self.all_days[md]['jobs']['ai_scan_meteors'] = os.path.exists(ai_data_file) 
            if "my_events" not in self.all_days[md]['jobs']:
               self.all_days[md]['jobs']['my_events'] = os.path.exists(my_event_file) 
            if "aws_sync" not in self.all_days[md]['jobs']:
               self.all_days[md]['jobs']['aws_sync'] = os.path.exists(aws_data_file) 
            #self.all_days[md]['aws_meteors'] = {}
            #self.all_days[md]['local_meteors'] = {}
            #self.all_days[md]['events'] = {}
            
         
         #print(md, self.all_days[md]) 

   def create_jobs_table(self):



      # Drop the GEEK table if already exists.
      cursor_obj.execute("DROP TABLE IF EXISTS GEEK")

      # Creating table
      table = """ CREATE TABLE GEEK (
            Email VARCHAR(255) NOT NULL,
            First_Name CHAR(25) NOT NULL,
            Last_Name CHAR(25),
            Score INT
      ); """

      cursor_obj.execute(table)
      print("Table is Ready")

