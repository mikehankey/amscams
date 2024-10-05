from Classes.AIDB import AllSkyDB
import sys
from lib.PipeUtil import load_json_file
json_conf = load_json_file("../conf/as6.json")
station_id = json_conf['site']['ams_id']

try:
   from Classes.AllSkyUI import AllSkyUI
   noUI = False 
except:
   noUI = True 

AIDB = AllSkyDB()
if noUI is False:
   AIUI = AllSkyUI()

con = AIDB.connect_database(station_id)
cur = con.cursor()

if len(sys.argv) > 1:
   cmd = sys.argv[1]
   if cmd == "load":
      selected_day = sys.argv[2]
else:
    cmd = "run"

if cmd == "load":
   # This will load up the DB with the lastest files
   if selected_day == "ALL":   
      selected_day = None
   print("LOADING METEORS ", selected_day) 
   AIDB.load_all_meteors(selected_day)

if cmd == "run" and noUI is False:
   print("RUN STARTUP")
   AIUI.startup()


