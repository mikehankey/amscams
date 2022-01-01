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

if False:
   sql = "SELECT Substr(root_fn,0,11) as day, count(*) from ml_samples group by day order by day desc"
   #station_id, camera_id, root_fn, roi_fn, meteor_yn_final, meteor_yn_final_conf, main_class, sub_class, meteor_yn, meteor_yn_conf, multi_class, multi_class_conf, human_confirmed, human_label, suggest_class, ignore FROM ml_samples WHERE camera_id = ? ORDER BY root_fn LIMIT ? OFFSET ?"
   cur.execute(sql)
   #cur.execute(sql, ('010006', 10,1))
   rows = cur.fetchall()
   for row in rows:
      print(row[0], row[1])
   cur.close()

if cmd == "load":
   # This will load up the DB with the lastest files

   AIDB.load_all_meteors(selected_day)

if True and noUI is False :
   AIUI.startup()


