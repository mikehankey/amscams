from Classes.AIDB import AllSkyDB
import sys

try:
   from Classes.AllSkyUI import AllSkyUI
   noUI = False 
except:
   noUI = True 

AIDB = AllSkyDB()
if noUI is False:
   AIUI = AllSkyUI()

con = AIDB.connect_database("AMS1")
cur = con.cursor()

if len(sys.argv) > 1:
   cmd = sys.argv[1]
   if cmd == "load":
      selected_day = sys.argv[2]

print("HELLO", cmd, noUI)

if cmd == "load":
   # This will load up the DB with the lastest files
   if selected_day == "ALL":   
      selected_day = None
   print("LOADING METEORS ", selected_day) 
   AIDB.load_all_meteors(selected_day)

if cmd == "run" and noUI is False:
   print("RUN STARTUP")
   AIUI.startup()


